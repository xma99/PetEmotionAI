# Notes:

Requires Python 3

To run the image download script, you need a web API call: Google Programmable Search JSON API (API Key + CSE ID)

To run the quick data cleaning/labeling script, use a local Web UI: Gradio, to easily upload, preview, and categorize thousands of images

## Environment Installation

python --version

python -m pip --version

python -m pip install --upgrade pip

python -m pip install requests tqdm python-slugify pillow gradio

## Google Cloud Custom Search API and Programmable Search Engine

setx GOOGLE_API_KEY "API_KEY"

setx GOOGLE_CX "CSE_ID"

## Image Downloading and Saving

After running cat_dataset_search.py, images will be automatically organized into subfolders by cat breed.

After running labeler_tool.py, open localhost and select labels for images in the interface; categorized images will move into their class folders.
