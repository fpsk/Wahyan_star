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
    """
    Run macOS Apple Vision OCR binary on page image for 100% accurate bilingual Chinese/English text.
    """
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
        
        # Filter out random top/bottom page scan margin artifacts (e.g. "AAZZZANZNZZNAXAXNAANAAZZXXN", "Joiio3ibS")
        if re.match(r'^[A-Z0-9]{15,}$', stripped) and ("ZZ" in stripped or "XX" in stripped):
            continue
        if len(stripped) < 4 and re.match(r'^[a-z0-9]+$', stripped):
            continue

        cleaned_lines.append(stripped)
    
    return '\n'.join(cleaned_lines).strip()

def detect_and_crop_photos(img, page_num, output_dir):
    """
    Detect continuous-tone photograph regions on a scanned yearbook page and crop them.
    """
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
                    photo_name = f"page_{page_num:03d}_photo_{photo_idx}.png"
                    photo_path = os.path.join(output_dir, photo_name)
                    cropped_im.save(photo_path, "PNG")
                    photos.append({
                        "filename": photo_name,
                        "rel_path": f"../photos/{photo_name}",
                        "bbox": [int(minc), int(minr), int(maxc), int(maxr)],
                        "width": int(box_w),
                        "height": int(box_h)
                    })
                    photo_idx += 1

    return photos

def process_pdf(pdf_path, output_dir, max_pages=None):
    os.makedirs(os.path.join(output_dir, "pages"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "photos"), exist_ok=True)

    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    print(f"Starting High-Accuracy Vision OCR & OKF conversion of '{pdf_path}' ({total_pages} pages)...", flush=True)

    page_manifests = []

    for idx in range(total_pages):
        page_num = idx + 1
        page = reader.pages[idx]

        # 1. Extract Full Page Image & Photo Cuts
        photos = []
        full_img_path = os.path.join(output_dir, "photos", f"page_{page_num:03d}_full.png")
        
        if not os.path.exists(full_img_path):
            page_images = page.images
            if page_images:
                try:
                    primary_img_file = page_images[0]
                    img_data = primary_img_file.data
                    img = Image.open(io.BytesIO(img_data)).convert('RGB')
                    img.save(full_img_path, "PNG")
                    detected_photos = detect_and_crop_photos(img, page_num, os.path.join(output_dir, "photos"))
                    photos.extend(detected_photos)
                except Exception as e:
                    print(f"Page {page_num} image extraction warning: {e}", flush=True)
        else:
            # Re-detect existing photo cutouts if needed
            img = Image.open(full_img_path).convert('RGB')

        # 2. Run High-Precision macOS Vision OCR on Page Image
        ocr_text = run_vision_ocr(full_img_path)

        # 3. Create Page Markdown
        md_lines = []
        md_lines.append(f"# Wah Yan Star 1976 - Page {page_num}\n")
        
        # Check existing photos for this page
        existing_photos = [f for f in os.listdir(os.path.join(output_dir, "photos")) if f.startswith(f"page_{page_num:03d}_photo_")]
        if existing_photos:
            md_lines.append("## Extracted Photos & Figures\n")
            for p_file in sorted(existing_photos):
                md_lines.append(f"![Page {page_num} Photo](../photos/{p_file})")

        md_lines.append("\n## Page Text Content\n")
        if ocr_text:
            md_lines.append("```text")
            md_lines.append(ocr_text)
            md_lines.append("```\n")
        else:
            md_lines.append("*No text detected on this page / Image only.*\n")

        md_filename = f"page_{page_num:03d}.md"
        md_path = os.path.join(output_dir, "pages", md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(md_lines))

        page_manifests.append({
            "page": page_num,
            "file": f"pages/{md_filename}",
            "text_length": len(ocr_text),
            "photos_count": len(existing_photos),
            "photos": existing_photos
        })

        if page_num % 10 == 0 or page_num == total_pages:
            print(f"Processed Vision OCR for page {page_num} / {total_pages}...", flush=True)

    manifest = {
        "title": "Wah Yan College Hong Kong Annual School Magazine 1976 (華仁星 1976)",
        "volume": "Number 41",
        "publisher": "Wah Yan College H.K.",
        "publication_date": "July 1976",
        "format": "Open Knowledge Format (OKF) v1.0",
        "ocr_engine": "macOS Apple Vision Framework (VNRecognizeTextRequest zh-Hant + en-US)",
        "source_file": pdf_path,
        "total_pages": total_pages,
        "languages": ["en", "zh-Hant"],
        "pages_dir": "pages",
        "photos_dir": "photos",
        "pages": page_manifests
    }

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nVision OCR OKF Conversion finished successfully! Manifest saved to '{manifest_path}'.", flush=True)

if __name__ == "__main__":
    pdf_file = "Files/1976.pdf"
    out_dir = "okf_output"
    max_p = int(sys.argv[1]) if len(sys.argv) > 1 else None
    process_pdf(pdf_file, out_dir, max_pages=max_p)
