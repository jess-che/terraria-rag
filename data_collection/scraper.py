# !pip install requests tqdm

import os
import requests
from tqdm import tqdm

API_URL = "https://terraria.wiki.gg/api.php"
OUTPUT_DIR = "terraria_wiki_pages"

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Step 1: Get the list of all pages
def get_all_pages():
    params = {
        "action": "query",
        "list": "allpages",
        "aplimit": "max",
        "format": "json"
    }
    pages = []
    while True:
        response = requests.get(API_URL, params=params).json()
        pages.extend(response['query']['allpages'])
        if 'continue' in response:
            params.update(response['continue'])
        else:
            break
    return pages

# Step 2: Fetch expanded page content
def fetch_expanded_page_content(pageid):
    params = {
        "action": "parse",
        "pageid": pageid,
        "prop": "text",
        "format": "json"
    }
    response = requests.get(API_URL, params=params).json()
    if 'parse' in response:
        title = response['parse']['title']
        content = response['parse']['text']['*']  # Rendered HTML
        return title, content
    else:
        print(f"Failed to expand page ID {pageid}")
        return None, None

# Step 3: Save expanded content to files
def save_page_content(title, content):
    # Sanitize filename
    filename = f"{title.replace('/', '_')}.html"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def download_pages(pages):
    for page in tqdm(pages, desc="Downloading pages"):
        title, content = fetch_expanded_page_content(page['pageid'])
        if title and content:
            save_page_content(title, content)

def main():
    print("Fetching list of all pages...")
    pages = get_all_pages()
    print(f"Total pages to download: {len(pages)}")
    download_pages(pages)
    print("Download completed.")

if __name__ == "__main__":
    main()
