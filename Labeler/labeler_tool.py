import os, csv, shutil, glob, uuid, re
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, UnidentifiedImageError
import gradio as gr

ROOT = Path(__file__).parent.resolve()
UNLABELED_DIR = ROOT
OUT_ROOT = ROOT / "CatDataset"
CLASS_NAMES = ["Happy", "Sad", "Angry", "Other"]
CSV_PATH = OUT_ROOT / "labels.csv"

OUT_ROOT.mkdir(parents=True, exist_ok=True)
for c in CLASS_NAMES:
    (OUT_ROOT / c).mkdir(parents=True, exist_ok=True)
UNLABELED_DIR.mkdir(parents=True, exist_ok=True)

def list_images() -> list[str]:
    exts = ("*.jpg","*.jpeg","*.png","*.bmp","*.webp")
    files = []
    for e in exts:
        files.extend(glob.glob(str(UNLABELED_DIR / "**" / e), recursive=True))
    return sorted(files)

STATE = {
    "files": list_images(),
    "idx": 0,
    "count": 0,
}

def file_name_check(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, ext = dest.stem, dest.suffix
    return dest.with_name(f"{stem}_{uuid.uuid4().hex[:6]}{ext}")

def csv_lables(relpath: str, label: str):
    write_header = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["relpath","label"])
        if write_header:
            w.writeheader()
        w.writerow({"relpath": relpath, "label": label})

# sequential naming utilities
def next_seq_index(label: str) -> int:
    folder = OUT_ROOT / label
    max_idx = 0
    for p in folder.iterdir():
        if p.is_file():
            m = re.match(rf'^{re.escape(label)}(\d+)$', p.stem, flags=re.IGNORECASE)
            if m:
                try:
                    max_idx = max(max_idx, int(m.group(1)))
                except ValueError:
                    pass
    return max_idx + 1

def make_sequential_dest(src: Path, label: str) -> Path:
    ext = (src.suffix or ".jpg").lower()
    idx = next_seq_index(label)
    dest = OUT_ROOT / label / f"{label}{idx}{ext}"
    while dest.exists():
        idx += 1
        dest = OUT_ROOT / label / f"{label}{idx}{ext}"
    return dest

# Load current images
def load_images() -> Tuple[Optional[Image.Image], str]:
    files, idx = STATE["files"], STATE["idx"]
    total = len(files)
    if idx >= total:
        return None, f"Labeled: {STATE['count']}"
    p = Path(files[idx])
    try:
        img = Image.open(p).convert("RGB")
    except (UnidentifiedImageError, FileNotFoundError, PermissionError):
        STATE["idx"] += 1
        return load_images()
    msg = f"[{idx+1}/{total}] {p.relative_to(UNLABELED_DIR)}"
    return img, msg

def load_images_process(label: Optional[str]) -> Tuple[Optional[Image.Image], str]:
    files, idx = STATE["files"], STATE["idx"]
    total = len(files)
    if idx >= total:
        return None, f"Total: {STATE['count']}"

    src = Path(files[idx])
    if label in CLASS_NAMES:
        dest = make_sequential_dest(src, label)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dest))
            rel = str(dest.relative_to(OUT_ROOT))
            csv_lables(rel, label)
            STATE["count"] += 1
        except Exception:
            img, _ = load_images()
            return img, f"Labeled: {STATE['count']}"
    else:
        pass

    STATE["idx"] += 1
    img, _ = load_images()
    stats = f"Labeled: {STATE['count']}"
    return img, stats

def labeler_helper():
    STATE["files"] = list_images()
    STATE["idx"] = 0
    STATE["count"] = 0
    img, _ = load_images()
    return img, "Labeled: 0"

with gr.Blocks(title="labeler dataset") as demo:
    with gr.Row():
        img = gr.Image(type="pil", label="Current Images", height=480)
        with gr.Column():
            stats = gr.Markdown("Labeled: 0")
            reload_btn = gr.Button(" Reload Unlabeled/", variant="secondary")

    with gr.Row():
        b_happy = gr.Button("Happy", variant="primary")
        b_sad   = gr.Button("Sad")
        b_angry = gr.Button("Angry")
        b_other = gr.Button("Other")
        b_skip  = gr.Button("Skip")

    # Click for image label
    b_happy.click(lambda: load_images_process("Happy"), outputs=[img, stats])
    b_sad.click(lambda: load_images_process("Sad"),   outputs=[img, stats])
    b_angry.click(lambda: load_images_process("Angry"), outputs=[img, stats])
    b_other.click(lambda: load_images_process("Other"), outputs=[img, stats])
    b_skip.click(lambda: load_images_process(None),    outputs=[img, stats])
    reload_btn.click(labeler_helper, outputs=[img, stats])

    demo.load(lambda: (load_images()[0], "Labeled: 0"), outputs=[img, stats])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, show_error=True)
