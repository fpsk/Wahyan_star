import os
import sys
import json
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTOS_DIR = os.path.join(BASE_DIR, 'okf_output', 'photos')
OUTPUT_DIR = os.path.join(BASE_DIR, 'ocr_boxes')
MAC_OCR = os.path.join(BASE_DIR, 'scripts', 'mac_ocr')

os.makedirs(OUTPUT_DIR, exist_ok=True)

def ocr_single_image(img_path):
    if not os.path.exists(img_path):
        return []
    try:
        res = subprocess.run([MAC_OCR, img_path], capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            raw = json.loads(res.stdout)
            lines = []
            for item in raw:
                txt = item.get('text', '').strip()
                if not txt:
                    continue
                lines.append({
                    't': txt,
                    'x': round(float(item.get('x', 0)), 4),
                    'y': round(float(item.get('y', 0)), 4),
                    'w': round(float(item.get('width', 0)), 4),
                    'h': round(float(item.get('height', 0)), 4)
                })
            return lines
    except Exception as e:
        print(f"Error OCRing {img_path}: {e}", file=sys.stderr)
    return []

def process_volume(year, photo_files):
    output_file = os.path.join(OUTPUT_DIR, f"{year}.json")
    print(f"Processing Volume {year} ({len(photo_files)} pages)...")
    
    tasks = []
    for p_num, photo_name in photo_files:
        p_path = os.path.join(PHOTOS_DIR, photo_name)
        tasks.append((p_num, p_path))

    results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_page = {executor.submit(ocr_single_image, path): p_num for p_num, path in tasks}
        for future in future_to_page:
            p_num = future_to_page[future]
            try:
                lines = future.result()
                if lines:
                    results[str(p_num)] = lines
            except Exception as e:
                print(f"Failed page {p_num}: {e}", file=sys.stderr)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))

    total_lines = sum(len(v) for v in results.values())
    file_size_kb = os.path.getsize(output_file) / 1024
    print(f"Saved {output_file}: {len(results)} pages, {total_lines} lines ({file_size_kb:.1f} KB)")

def main():
    print("=== Extracting Apple Vision OCR Bounding Boxes for All Volumes ===")
    t0 = time.time()

    # Discover all full page photos grouped by year
    all_files = sorted(os.listdir(PHOTOS_DIR))
    volume_pages = {}

    for f in all_files:
        if not f.endswith('_full.webp'):
            continue
        # Extract year and page
        # e.g., 1974_page_106_full.webp, 1975_F5_Alumni_page_001_full.webp, Reunion_Gala_page_001_full.webp
        parts = f.replace('_full.webp', '').split('_page_')
        if len(parts) == 2:
            year = parts[0]
            try:
                page_num = int(parts[1])
                if year not in volume_pages:
                    volume_pages[year] = []
                volume_pages[year].append((page_num, f))
            except ValueError:
                continue

    for year in sorted(volume_pages.keys()):
        volume_pages[year].sort(key=lambda x: x[0])
        process_volume(year, volume_pages[year])

    elapsed = time.time() - t0
    print(f"=== Complete! All volumes processed in {elapsed:.1f}s ===")

if __name__ == '__main__':
    main()
