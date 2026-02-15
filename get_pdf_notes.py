import os
import requests
from PIL import Image
import json
import argparse
import sys
import concurrent.futures

# Parse command line arguments
parser = argparse.ArgumentParser(description="Download IoT notes and generate PDF.")
parser.add_argument('--1', dest='chapter_1', action='store_true', help="Download Chapter 1")
parser.add_argument('--2', dest='chapter_2', action='store_true', help="Download Chapter 2")
parser.add_argument('-c', '--chapter', type=int, help="Specify chapter number (e.g., 1 or 2)")
parser.add_argument('-w', '--workers', type=int, default=10, help="Number of parallel workers (default: 10)")

args = parser.parse_args()

chapter_num = None
if args.chapter_1:
    chapter_num = 1
elif args.chapter_2:
    chapter_num = 2
elif args.chapter:
    chapter_num = args.chapter
else:
    print("Please specify a chapter using --1, --2, or --chapter <n>")
    sys.exit(1)

# Load configuration from ch_code.json
try:
    config_path = os.path.join(os.path.dirname(__file__), "ch_code.json")
    with open(config_path, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: ch_code.json not found.")
    sys.exit(1)
except json.JSONDecodeError:
    print("Error: Failed to decode ch_code.json.")
    sys.exit(1)

chapter_key = f"ch{chapter_num}"
if chapter_key not in config:
    print(f"Configuration for '{chapter_key}' not found in ch_code.json")
    sys.exit(1)

ch_data = config[chapter_key]
code = ch_data.get("code")
end_page = ch_data.get("pages")

if not code or not end_page:
    print(f"Error: Missing 'code' or 'pages' in configuration for {chapter_key}.")
    sys.exit(1)

start_page = 1
# URL template: https://sbalpande.rf.gd/IoT/Ch{chapter}/files/mobile/{page}.jpg?{code}
url_template = f"https://sbalpande.rf.gd/IoT/Ch{chapter_num}/files/mobile/{{}}.jpg?{code}"

output_dir = os.path.join(os.path.dirname(__file__), f"ch{chapter_num}_images")
pdf_path = os.path.join(os.path.dirname(__file__), f"ch{chapter_num}.pdf")

# Ensure output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

headers = {
    'sec-ch-ua-platform': '"Windows"',
    'Referer': f'https://sbalpande.rf.gd/IoT/Ch{chapter_num}/mobile/index.html',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
}

def download_page(page_num):
    url = url_template.format(page_num)
    file_name = f"{page_num}.jpg"
    file_path = os.path.join(output_dir, file_name)
    
    # Check if file already exists
    if os.path.exists(file_path):
        return file_path

    print(f"Fetching page {page_num}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            return file_path
        else:
            print(f"Failed to fetch page {page_num}. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching page {page_num}: {e}")
        return None

downloaded_images = []

print(f"Starting parallel download of Chapter {chapter_num} ({end_page} pages) with {args.workers} workers...")

# Use ThreadPoolExecutor for parallel downloads
with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
    # map returns results in the order of the iterable
    results = executor.map(download_page, range(start_page, end_page + 1))
    
    # Collect successful downloads
    for res in results:
        if res:
            downloaded_images.append(res)

print("Download complete. Generating PDF...")

if downloaded_images:
    opened_images = [] # Keep track to close them later
    try:
        if not downloaded_images:
             print("No images downloaded.")
        else:
            image_objects = []
            
            # Open the first image
            first_image_path = downloaded_images[0]
            try:
                first_image = Image.open(first_image_path)
                opened_images.append(first_image)
                
                if first_image.mode != 'RGB':
                    first_image = first_image.convert('RGB')
                
                # Open and process the rest of the images
                for img_path in downloaded_images[1:]:
                    try:
                        img = Image.open(img_path)
                        opened_images.append(img)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        image_objects.append(img)
                    except Exception as e:
                        print(f"Warning: Could not open image {img_path}: {e}")

                # Save as PDF
                first_image.save(pdf_path, save_all=True, append_images=image_objects)
                print(f"PDF generated successfully: {pdf_path}")
                
            except Exception as e:
                 print(f"Error opening first image or saving PDF: {e}")

    except Exception as e:
        print(f"Error generating PDF: {e}")
    finally:
        # Close all image files to allow deletion
        for img in opened_images:
            img.close()

    # Delete downloaded images
    print("Cleaning up downloaded images...")
    for img_path in downloaded_images:
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except Exception as e:
            print(f"Error deleting {img_path}: {e}")
            
    # Optional: Remove the directory if it's empty
    try:
        os.rmdir(output_dir)
        print(f"Removed directory: {output_dir}")
    except OSError:
        pass # Directory might not be empty or other error

else:
    print("No images were downloaded, cannot generate PDF.")
