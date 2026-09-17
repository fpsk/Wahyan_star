import os
import sys
import json
import re
import io
import subprocess
import pypdf
from PIL import Image
import numpy as np
import skimage.measure
import skimage.filters
import skimage.morphology

MAC_OCR_BIN = os.path.join(os.path.dirname(__file__), "mac_ocr")

def run_vision_ocr(image_path):
    if not os.path.exists(MAC_OCR_BIN):
        return ""
    try:
        res = subprocess.run([MAC_OCR_BIN, image_path], capture_output=True, text=True, check=True)
        text = res.stdout.strip()
        return clean_vision_ocr_text(text)
    except Exception as e:
        print(f"Vision OCR warning for {image_path}: {e}")
        return ""

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

def detect_and_crop_photos(img, page_num, year, output_dir):
    photos = []
    try:
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
    except Exception as e:
        print(f"Photo crop warning for Year {year} Page {page_num}: {e}")

    return photos

def process_year(year, pdf_path, output_base_dir):
    year_pages_dir = os.path.join(output_base_dir, "pages", str(year))
    photos_dir = os.path.join(output_base_dir, "photos")
    os.makedirs(year_pages_dir, exist_ok=True)
    os.makedirs(photos_dir, exist_ok=True)

    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"\n==========================================")
    print(f" Processing Year {year} PDF: '{pdf_path}' ({total_pages} pages)")
    print(f"==========================================")

    for idx in range(total_pages):
        page_num = idx + 1
        page = reader.pages[idx]

        full_img_name = f"{year}_page_{page_num:03d}_full.png"
        full_img_path = os.path.join(photos_dir, full_img_name)
        
        photos = []
        if not os.path.exists(full_img_path):
            page_images = page.images
            if page_images:
                try:
                    primary_img_file = page_images[0]
                    img = Image.open(io.BytesIO(primary_img_file.data)).convert('RGB')
                    img.save(full_img_path, "PNG")
                    photos = detect_and_crop_photos(img, page_num, year, photos_dir)
                except Exception as e:
                    print(f"Year {year} Page {page_num} extraction warning: {e}")

        ocr_text = run_vision_ocr(full_img_path)

        md_lines = [f"# Wah Yan Star {year} - Page {page_num}\n"]
        existing_photos = [f for f in os.listdir(photos_dir) if f.startswith(f"{year}_page_{page_num:03d}_photo_")]
        if existing_photos:
            md_lines.append("## Extracted Photos & Figures\n")
            for p_file in sorted(existing_photos):
                md_lines.append(f"![{year} Page {page_num} Photo](../photos/{p_file})")

        md_lines.append("\n## Page Text Content\n")
        if ocr_text:
            md_lines.append("```text")
            md_lines.append(ocr_text)
            md_lines.append("```\n")
        else:
            md_lines.append("*No text detected / Scanned image page.*\n")

        md_filename = f"page_{page_num:03d}.md"
        md_path = os.path.join(year_pages_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(md_lines))

        if page_num % 15 == 0 or page_num == total_pages:
            print(f"  Finished Year {year} Page {page_num} / {total_pages}...")

if __name__ == '__main__':
    process_year(1969, 'Files/1969.pdf', 'okf_output')
    process_year(1970, 'Files/1970.pdf', 'okf_output')
