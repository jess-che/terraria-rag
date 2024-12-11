import os
import re
from bs4 import BeautifulSoup

def remove_unwanted_pages(directory):
    # Iterate over all files in the directory
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        
        # Skip files that do not have .html extension
        if not filename.endswith(".html"):
            continue

        # Remove files with an underscore in the filename
        if '_' in filename:
            print(f"Removing file with underscore: {filename}")
            os.remove(filepath)
            continue

        # Open and parse the HTML file to check for the redirect text
        with open(filepath, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            redirect_text = soup.find('p', text=re.compile(r'Redirect to:'))
            
            # If the redirect text is found, remove the file
            if redirect_text:
                print(f"Removing redirect file: {filename}")
                os.remove(filepath)
                continue

if __name__ == "__main__":
    directory = 'terraria_wiki_pages'  
    remove_unwanted_pages(directory)
    print("Processing complete.")
