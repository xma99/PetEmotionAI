import os, time, math, hashlib, random
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import requests
from tqdm import tqdm
from slugify import slugify

"""
Enable Google Cloud Custom Search API
Enable Programmable Search Engine
"""
# API Key
API_KEY = os.getenv("GOOGLE_API_KEY", "API_KEY")
# Image Search Engine ID
CSE_ID  = os.getenv("GOOGLE_CX", "CSE_ID")

# All images are stored in the root folder
ROOT_DIR = "CatDataset"
os.makedirs(ROOT_DIR, exist_ok=True)

# The number of images required for each breed
Quantity_Requirements = 200

# Google JSON API Setting
NUM_PER_PAGE = 10
RESULTS_PER_QUERY_CAP = 100
API_RETRIES = 3
REQ_TIMEOUT = 15
API_SLEEP_SEC = 0.20
DOWNLOAD_WORKERS = 24
CHUNK_SIZE = 1024 * 64

"""
Enable Google Cloud Custom Search API
Enable Programmable Search Engine
"""
CAT_BREEDS = [
    "Abyssinian","Aegean","American Bobtail","American Curl","American Shorthair",
    "American Wirehair","Aphrodite Giant","Arabian Mau","Asian Semi-longhair","Asian Semi-shorthair",
    "Balinese","Bambino","Bengal","Birman","Bombay cat",
    "Brazilian Shorthair","British Longhair","British Shorthair","Burmese","Burmilla",
    "California Spangled","Chantilly-Tiffany","Chartreux","Chausie","Colorpoint Shorthair","Cornish Rex",
    "Long-haired Manx","Cyprus","Devon Rex","Donskoy","Chinese Li Hua",
    "Dwelf","Egyptian Mau","European Shorthair","Exotic Shorthair","Foldex",
    "German Rex","Havana Brown","Highlander","Himalayan cat","Japanese Bobtail",
    "Colorpoint Longhair","Kanaani","Karelian Bobtail","Kinkalow",
    "Korat","Korean Bobtail","Korn Ja","Kurilian Bobtail",
    "Lambkin","LaPerm","Lykoi","Maine Coon","Manx cat","Mekong Bobtail",
    "Minskin","Minuet","Munchkin","Nebelung","Neva Masquerade",
    "Ocicat","Ojos Azules","Oriental Bicolor","Oriental Longhair","Oriental Shorthair",
    "Persian","Peterbald","Pixie-bob","Ragamuffin","Ragdoll",
    "Raas cat","Russian Blue","Sam Sawet","Savannah","Scottish Fold",
    "Selkirk Rex","Serengeti","Siamese","Siberian Forest Cat","Singapura",
    "Snowshoe","Sokoke","Somali","Sphynx","Suphalak","Thai",
    "Tonkinese","Toybob","Toyger","Turkish Angora","Turkish Van",
    "Turkish Vankedisi","Ukrainian Levkoy","York Chocolate",
]
KEY_WORD = [
    "cat",
]

# 
def guess_ext_from_mime(mime: str) -> str:
    ext = mimetypes.guess_extension(mime or "") or ".jpg"
    return ".jpg" if ext in (".jpe",) else ext

def api_search(query: str, start_index: int):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": API_KEY, "cx": CSE_ID,
        "q": query, "searchType": "image",
        "num": NUM_PER_PAGE, "start": start_index,
    }
    for attempt in range(API_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=REQ_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            time.sleep(1 + attempt*2)
        except requests.RequestException:
            time.sleep(1 + attempt*2)
    return {}

def filename_for(url: str, content_type: str, breed_dir: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    ext = guess_ext_from_mime(content_type or "")
    return os.path.join(breed_dir, f"{h}{ext}")

def download_image(url: str, breed_dir: str):
    try:
        resp = requests.get(url, timeout=REQ_TIMEOUT, stream=True)
        if resp.status_code != 200:
            return False, None
        ctype = resp.headers.get("Content-Type","")
        if "image" not in ctype:
            return False, None
        path = filename_for(url, ctype, breed_dir)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return True, path
        with open(path, "wb") as f:
            for chunk in resp.iterate_content(CHUNK_SIZE) if hasattr(resp, "iterate_content") else resp.iter_content(CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        return True, path
    except Exception:
        return False, None

# Download different cat breeds to different folders
def harvest():
    if "API_KEY" in API_KEY or "CSE_ID" in CSE_ID:
        raise SystemExit("")

    # Avoid duplicate downloads
    urls_check = set()

    total_downloaded = 0

    for breed in CAT_BREEDS:
        # Create folder for each breeds
        breed_slug = slugify(breed, lowercase=False, separator=" ")
        breed_dir = os.path.join(ROOT_DIR, breed_slug)
        os.makedirs(breed_dir, exist_ok=True)

        have = len([f for f in os.listdir(breed_dir) if os.path.isfile(os.path.join(breed_dir, f))])
        if have >= Quantity_Requirements:
            print(f"{breed} have {have} images >=  {Quantity_Requirements}")
            total_downloaded += have
            continue

        print(f"\n{breed} have {have} image, Quantity_Requirements: {Quantity_Requirements} iamges")
        got_this_breed = have

        for m in KEY_WORD:
            if got_this_breed >= Quantity_Requirements:
                break

            query = f"{breed} {m}"
            pages = math.ceil(RESULTS_PER_QUERY_CAP / NUM_PER_PAGE)
            query_got = 0
            for p in range(pages):
                start_index = p*NUM_PER_PAGE + 1
                data = api_search(query, start_index)
                items = data.get("items", [])
                if not items:
                    break

                # Get url
                batch_urls = []
                for it in items:
                    link = it.get("link")
                    if not link or link in urls_check:
                        continue
                    urls_check.add(link)
                    batch_urls.append(link)

                # Download
                successes = 0
                with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as ex:
                    futures = [ex.submit(download_image, u, breed_dir) for u in batch_urls]
                    for fut in as_completed(futures):
                        ok, _ = fut.result()
                        if ok:
                            successes += 1
                            got_this_breed += 1
                            total_downloaded += 1
                            if got_this_breed >= Quantity_Requirements:
                                break

                query_got += successes

                if got_this_breed >= Quantity_Requirements:
                    break

                time.sleep(API_SLEEP_SEC)

            print(f"[{breed}] '{m}' -> +{query_got} images, Total: {got_this_breed}/{Quantity_Requirements}")

        print(f"Finish {breed}, Get {got_this_breed}/{Quantity_Requirements} images, dir: {breed_dir}")

    print(f"\nTotal downloads: {total_downloaded} images, root dir: {ROOT_DIR}")

if __name__ == "__main__":
    harvest()
