import os
import sys
import glob
import json
import re
import subprocess
from PIL import Image
import numpy as np
import skimage.measure
import skimage.filters
import skimage.morphology

MAC_OCR_BIN = os.path.join(os.path.dirname(__file__), "mac_ocr")

def clean_vision_ocr_text(text):
    if not text:
        return ""
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^[A-Z0-9]{15,}$', stripped) and ("ZZ" in stripped or "XX" in stripped):
            continue
        if len(stripped) < 4 and re.match(r'^[a-z0-9]+$', stripped):
            continue
        cleaned_lines.append(stripped)
    return '\n'.join(cleaned_lines).strip()

def run_vision_ocr(image_path):
    if not os.path.exists(MAC_OCR_BIN):
        return ""
    try:
        res = subprocess.run([MAC_OCR_BIN, image_path], capture_output=True, text=True, check=True)
        raw_json = res.stdout.strip()
        items = json.loads(raw_json)
        # Vision coords: y=1 top, y=0 bottom. Sort by descending y, then ascending x
        sorted_obs = sorted(items, key=lambda l: (-l['y'], l['x']))
        plain_text = '\n'.join([l['text'] for l in sorted_obs])
        return clean_vision_ocr_text(plain_text)
    except Exception as e:
        print(f"Warning: OCR failed for {image_path}: {e}")
        return ""

def detect_and_crop_photos(img, page_num, year, output_dir):
    photos = []
    gray = img.convert('L')
    arr = np.array(gray)
    h, w = arr.shape

    thresh = skimage.filters.threshold_otsu(arr)
    binary = arr < (thresh * 0.95)

    selem = skimage.morphology.rectangle(15, 15)
    closed = skimage.morphology.closing(binary, selem)
    
    labeled = skimage.measure.label(closed)
    regions = skimage.measure.regionprops(labeled)

    photo_idx = 1
    min_photo_area = (h * w) * 0.025
    max_photo_area = (h * w) * 0.85

    for reg in regions:
        area = reg.area
        if min_photo_area <= area <= max_photo_area:
            minr, minc, maxr, maxc = reg.bbox
            box_h = maxr - minr
            box_w = maxc - minc
            aspect_ratio = box_w / float(box_h)

            if 0.25 < aspect_ratio < 4.0 and box_h > 180 and box_w > 180:
                crop_arr = arr[minr:maxr, minc:maxc]
                std_dev = np.std(crop_arr)
                if std_dev > 28:
                    cropped_im = img.crop((minc, minr, maxc, maxr))
                    photo_name = f"{year}_page_{page_num:03d}_photo_{photo_idx}.png"
                    photo_path = os.path.join(output_dir, photo_name)
                    cropped_im.save(photo_path, "PNG")
                    photos.append(photo_name)
                    photo_idx += 1
    return photos

def fix_inverted_pages():
    inverted_map = {
        '1969': [79, 104, 130, 148],
        '1971': [1, 12, 14, 15, 27, 39, 46, 49, 52, 58, 62, 70, 71, 72, 76, 83, 86, 105, 110, 111, 114, 128, 133, 139, 143, 145, 147, 149, 151, 153, 155, 157, 159, 161, 166],
        '1972': [5, 9, 14, 20, 34, 36, 44, 51, 55, 57, 64, 65, 66, 69, 72, 75, 76, 91, 94, 95, 96, 98, 106, 118, 185, 191, 193],
        '1973': [16, 32, 60, 65, 66, 78, 87, 126],
        '1974': [8, 41, 44, 55, 57, 59, 61, 65, 73, 78, 134],
        '1975': [3, 6, 19, 24, 37, 48, 50, 56, 61, 69, 72, 123],
        '1976': [3, 30, 34, 40, 43, 46, 48, 52, 57, 60, 66, 67, 69, 77, 84, 88, 89, 93, 156],
        '1977': [7, 12, 18, 21, 25, 36, 44, 50, 54, 55, 69, 70, 75, 79, 113, 116, 120],
        '1978': [1, 3, 5, 12, 18, 20, 22, 30, 31, 34, 37, 42, 45, 108, 111, 112, 114, 119, 189],
        '1979': [6, 12, 14, 17, 19, 20, 22, 34, 42, 62, 72, 73, 74, 75, 82, 90, 91, 93, 96, 151]
    }

    photos_dir = "okf_output/photos"
    pages_base = "okf_output/pages"
    entities_base = "okf_output/entities"

    total_pages_to_fix = sum(len(v) for v in inverted_map.values())
    print(f"==================================================")
    print(f"Starting Inversion Correction for {total_pages_to_fix} Pages")
    print(f"==================================================")

    processed = 0
    for year, pages in sorted(inverted_map.items()):
        print(f"\nProcessing Volume {year} ({len(pages)} inverted pages)...")
        for p in pages:
            full_img_name = f"{year}_page_{p:03d}_full.png"
            full_img_path = os.path.join(photos_dir, full_img_name)
            
            if not os.path.exists(full_img_path):
                print(f"  Warning: {full_img_path} not found, skipping.")
                continue

            # 1. Rotate Full Page Image by 180 degrees
            im = Image.open(full_img_path)
            im_rot = im.transpose(Image.ROTATE_180)
            im_rot.save(full_img_path, "PNG")

            # 2. Clean existing photo crops for this page
            old_crops = glob.glob(os.path.join(photos_dir, f"{year}_page_{p:03d}_photo_*.png"))
            for old_c in old_crops:
                try:
                    os.remove(old_c)
                except Exception as e:
                    print(f"  Error removing old crop {old_c}: {e}")

            # 3. Detect and crop photos on newly upright image
            new_crops = detect_and_crop_photos(im_rot, p, year, photos_dir)

            # 4. Run Vision OCR on upright full image
            ocr_text = run_vision_ocr(full_img_path)

            # 5. Update Markdown file
            md_lines = [f"# Wah Yan Star {year} - Page {p}\n"]
            if new_crops:
                md_lines.append("## Extracted Photos & Figures\n")
                for c in sorted(new_crops):
                    md_lines.append(f"![{year} Page {p} Photo](../photos/{c})")

            md_lines.append("\n## Page Text Content\n")
            if ocr_text:
                md_lines.append("```text")
                md_lines.append(ocr_text)
                md_lines.append("```\n")
            else:
                md_lines.append("*No text detected / Scanned image page.*\n")

            md_filename = f"page_{p:03d}.md"
            md_dir = os.path.join(pages_base, str(year))
            os.makedirs(md_dir, exist_ok=True)
            md_path = os.path.join(md_dir, md_filename)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(md_lines))

            # If 1976 top-level file exists, update it too
            if year == '1976':
                top_md_path = os.path.join(pages_base, md_filename)
                if os.path.exists(top_md_path):
                    with open(top_md_path, "w", encoding="utf-8") as f:
                        f.write('\n'.join(md_lines))

            # 6. Update structured entity file if present
            entity_path = os.path.join(entities_base, str(year), f"page_{p:03d}.json")
            if os.path.exists(entity_path):
                try:
                    with open(entity_path, "r", encoding="utf-8") as f:
                        entity_data = json.load(f)
                    entity_data["extracted_photos"] = new_crops
                    with open(entity_path, "w", encoding="utf-8") as f:
                        json.dump(entity_data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"  Warning: could not update entity {entity_path}: {e}")

            processed += 1
            if processed % 10 == 0 or processed == total_pages_to_fix:
                print(f"  Corrected {processed} / {total_pages_to_fix} pages...", flush=True)

    print(f"\n==================================================")
    print(f"✅ Successfully Corrected All {processed} Inverted Pages!")
    print(f"==================================================")

if __name__ == "__main__":
    fix_inverted_pages()
