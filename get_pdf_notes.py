import requests
from PIL import Image
import json
import argparse
import sys
import concurrent.futures
import os

# Parse command line arguments
parser = argparse.ArgumentParser(description="Download IoT notes and generate PDF.")
parser.add_argument('--1', dest='chapter_1', action='store_true', help="Download Chapter 1")
parser.add_argument('--2', dest='chapter_2', action='store_true', help="Download Chapter 2")
parser.add_argument('--3', dest='chapter_3', action='store_true', help="Download Chapter 3")
parser.add_argument('--4', dest='chapter_4', action='store_true', help="Download Chapter 4")
parser.add_argument('--5', dest='chapter_5', action='store_true', help="Download Chapter 5")
parser.add_argument('-c', '--chapter', type=int, help="Specify chapter number (e.g., 1, 2, 3, 4 or 5)")
parser.add_argument('-w', '--workers', type=int, default=10, help="Number of parallel workers (default: 10)")

args = parser.parse_args()

chapter_num = None
if args.chapter_1:
    chapter_num = 1
elif args.chapter_2:
    chapter_num = 2
elif args.chapter_3:
    chapter_num = 3
elif args.chapter_4:
    chapter_num = 4
elif args.chapter_5:
    chapter_num = 5
elif args.chapter:
    chapter_num = args.chapter
else:
    print("Please specify a chapter using --1, --2, --3, --4, --5, or --chapter <n>")
    sys.exit(1)

# ── Hardcoded codes for Ch4 and Ch5 ──────────────────────────────────────────
# Note: these codes are date-based and rotate daily.
# If downloads fail, grab a fresh code from F12 Network tab and update here.
HARDCODED = {
    4: {"code": "260410230608", "pages": None},  # pages=None triggers auto-detect
    5: {"code": "260410231650", "pages": None},
}

# Load configuration from ch_code.json (for Ch1/Ch2/Ch3 and manual overrides)
try:
    config_path = os.path.join(os.path.dirname(__file__), "ch_code.json")
    with open(config_path, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}
except json.JSONDecodeError:
    print("Error: Failed to decode ch_code.json.")
    sys.exit(1)

chapter_key = f"ch{chapter_num}"
code     = None
end_page = None

# Priority: ch_code.json > HARDCODED
if chapter_key in config:
    ch_data  = config[chapter_key]
    code     = ch_data.get("code")
    end_page = ch_data.get("pages")
elif chapter_num in HARDCODED:
    code     = HARDCODED[chapter_num]["code"]
    end_page = HARDCODED[chapter_num]["pages"]  # may be None → auto-detect below
else:
    print(f"Configuration for '{chapter_key}' not found in ch_code.json and no hardcoded entry exists.")
    sys.exit(1)

if not code:
    print(f"Error: Missing 'code' for {chapter_key}.")
    sys.exit(1)

headers = {
    'sec-ch-ua-platform': '"Windows"',
    'Referer': f'https://sbalpande.rf.gd/IoT/Ch{chapter_num}/mobile/index.html',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
}

# ── Auto-detect page count if not set ────────────────────────────────────────
def detect_pages(chapter_num, code):
    print(f"Auto-detecting page count for Chapter {chapter_num}...")
    lo, hi = 1, 300
    while lo < hi:
        mid = (lo + hi + 1) // 2
        url = f"https://sbalpande.rf.gd/IoT/Ch{chapter_num}/files/mobile/{mid}.jpg?{code}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                lo = mid
            else:
                hi = mid - 1
        except Exception:
            hi = mid - 1
    print(f"Detected {lo} pages for Chapter {chapter_num}.")
    return lo

if not end_page:
    end_page = detect_pages(chapter_num, code)

# ── Quality folders: best → worst ────────────────────────────────────────────
QUALITY_FOLDERS = ["large", "medium", "mobile"]

start_page = 1
output_dir = os.path.join(os.path.dirname(__file__), f"ch{chapter_num}_images")
pdf_path   = os.path.join(os.path.dirname(__file__), f"ch{chapter_num}.pdf")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# ── Download a single page (tries best quality first) ────────────────────────
def download_page(page_num):
    file_path = os.path.join(output_dir, f"{page_num}.jpg")

    if os.path.exists(file_path):
        return file_path

    for quality in QUALITY_FOLDERS:
        url = f"https://sbalpande.rf.gd/IoT/Ch{chapter_num}/files/{quality}/{page_num}.jpg?{code}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"Fetched page {page_num} [{quality}]")
                return file_path
        except Exception as e:
            print(f"Error fetching page {page_num} ({quality}): {e}")

    print(f"Failed to fetch page {page_num} at any quality.")
    return None

downloaded_images = []

print(f"Starting parallel download of Chapter {chapter_num} ({end_page} pages) with {args.workers} workers...")

with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
    results = executor.map(download_page, range(start_page, end_page + 1))
    for res in results:
        if res:
            downloaded_images.append(res)

print("Download complete. Generating PDF...")

if downloaded_images:
    opened_images = []
    try:
        image_objects = []
        first_image_path = downloaded_images[0]
        try:
            first_image = Image.open(first_image_path)
            opened_images.append(first_image)

            if first_image.mode != 'RGB':
                first_image = first_image.convert('RGB')

            for img_path in downloaded_images[1:]:
                try:
                    img = Image.open(img_path)
                    opened_images.append(img)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    image_objects.append(img)
                except Exception as e:
                    print(f"Warning: Could not open image {img_path}: {e}")

            first_image.save(pdf_path, save_all=True, append_images=image_objects)
            print(f"PDF generated successfully: {pdf_path}")

        except Exception as e:
            print(f"Error opening first image or saving PDF: {e}")

    except Exception as e:
        print(f"Error generating PDF: {e}")
    finally:
        for img in opened_images:
            img.close()

    print("Cleaning up downloaded images...")
    for img_path in downloaded_images:
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except Exception as e:
            print(f"Error deleting {img_path}: {e}")

    try:
        os.rmdir(output_dir)
        print(f"Removed directory: {output_dir}")
    except OSError:
        pass

else:
    print("No images were downloaded, cannot generate PDF.")