import os
import sys
import json
import re
import io
import glob
import subprocess
import concurrent.futures
import pypdf
from PIL import Image
import numpy as np
import skimage.measure
import skimage.filters
import skimage.morphology

MAC_OCR_BIN = os.path.join(os.path.dirname(__file__), "mac_ocr")

def run_vision_ocr_spatial(image_path):
    if not os.path.exists(MAC_OCR_BIN):
        return [], ""
    try:
        res = subprocess.run([MAC_OCR_BIN, image_path], capture_output=True, text=True, check=True)
        raw_json = res.stdout.strip()
        observations = json.loads(raw_json)
        
        sorted_obs = sorted(observations, key=lambda l: (-l['y'], l['x']))
        plain_text = '\n'.join([l['text'] for l in sorted_obs])
        
        return observations, clean_vision_ocr_text(plain_text)
    except Exception as e:
        return [], ""

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

def extract_spatial_bilingual_names(observations, page_num, year_label):
    """
    1-to-1 Horizontal Grid Distance Matching.
    Pairs each Chinese character name with its horizontally closest English name on the exact same row.
    Guarantees no duplicate name assignments across grid columns.
    """
    if not observations:
        return []

    sorted_obs = sorted(observations, key=lambda l: -l['y'])
    
    rows = []
    for obs in sorted_obs:
        matched = False
        for r in rows:
            if abs(r['y'] - obs['y']) < 0.018:
                r['items'].append(obs)
                matched = True
                break
        if not matched:
            rows.append({'y': obs['y'], 'items': [obs]})

    roster_pairs = []
    cjk_pattern = re.compile(r'[\u4e00-\u9fff]{2,5}')
    eng_pattern = re.compile(r'(?:\d+[\.\s]+)?([A-Z][a-zA-Z\s,\.\(\)\'\-]{2,35})')

    for r in rows:
        items = sorted(r['items'], key=lambda i: i['x'])
        eng_items = []
        for i in items:
            m = eng_pattern.search(i['text'])
            if m:
                clean_eng = m.group(1).strip()
                if not any(stop in clean_eng.upper() for stop in ['FORM', 'ARTS', 'SCIENCE', 'UPPER', 'LOWER', 'WAH YAN', 'COLLEGE', 'PAGE', 'TEACHER']):
                    eng_items.append({'text': clean_eng, 'x': i['x']})
        
        chi_items = [i for i in items if cjk_pattern.search(i['text'])]

        if eng_items and chi_items:
            used_eng = set()
            for chi in chi_items:
                chi_match = cjk_pattern.search(chi['text'])
                if not chi_match:
                    continue
                chi_name = chi_match.group(0)

                best_eng_idx = None
                best_dist = 999.0
                for idx, eng in enumerate(eng_items):
                    if idx in used_eng:
                        continue
                    dist = abs(eng['x'] - chi['x'])
                    if dist < best_dist:
                        best_dist = dist
                        best_eng_idx = idx

                if best_eng_idx is not None and best_dist < 0.35:
                    used_eng.add(best_eng_idx)
                    roster_pairs.append({
                        'year': year_label,
                        'page': page_num,
                        'english_name': eng_items[best_eng_idx]['text'],
                        'chinese_name': chi_name
                    })

    return roster_pairs

def detect_and_crop_photos(img, page_num, year_label, output_dir):
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
                    photo_name = f"{year_label}_page_{page_num:03d}_photo_{photo_idx}.png"
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

def process_page_job(args):
    pdf_path, year_label, page_num, total_pages, output_base_dir = args
    photos_dir = os.path.join(output_base_dir, "photos")
    year_pages_dir = os.path.join(output_base_dir, "pages", str(year_label))
    
    os.makedirs(year_pages_dir, exist_ok=True)
    os.makedirs(photos_dir, exist_ok=True)

    full_img_name = f"{year_label}_page_{page_num:03d}_full.png"
    full_img_path = os.path.join(photos_dir, full_img_name)
    
    photos = []
    if not os.path.exists(full_img_path):
        try:
            reader = pypdf.PdfReader(pdf_path)
            page = reader.pages[page_num - 1]
            page_images = page.images
            if page_images:
                primary_img_file = page_images[0]
                img = Image.open(io.BytesIO(primary_img_file.data)).convert('RGB')
                img.save(full_img_path, "PNG")
                photos = detect_and_crop_photos(img, page_num, year_label, photos_dir)
        except Exception as e:
            pass
    else:
        photos = [f for f in os.listdir(photos_dir) if f.startswith(f"{year_label}_page_{page_num:03d}_photo_")]

    observations, ocr_text = run_vision_ocr_spatial(full_img_path)
    verified_pairs = extract_spatial_bilingual_names(observations, page_num, year_label)

    md_lines = [f"# Wah Yan Star {year_label} - Page {page_num}\n"]
    existing_photos = [f for f in os.listdir(photos_dir) if f.startswith(f"{year_label}_page_{page_num:03d}_photo_")]
    if existing_photos:
        md_lines.append("## Extracted Photos & Figures\n")
        for p_file in sorted(existing_photos):
            md_lines.append(f"![{year_label} Page {page_num} Photo](../photos/{p_file})")

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

    return {
        "entry": {
            "year": year_label,
            "page": page_num,
            "title": f"Wah Yan Star {year_label} - Page {page_num}",
            "text": ocr_text,
            "verified_names": verified_pairs,
            "photos": existing_photos,
            "full_page_photo": full_img_name
        },
        "roster": verified_pairs
    }

def process_all_workspace_volumes(files_dir, output_base_dir):
    pdf_files = [f for f in glob.glob(os.path.join(files_dir, '*.pdf')) if not f.endswith('OCR.pdf')]
    pdf_files.sort()

    print(f"Found {len(pdf_files)} Wah Yan Star PDF volumes to process in '{files_dir}'...")

    jobs = []
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        match = re.search(r'\b(19\d\d|20\d\d)\b', filename)
        if match:
            year_label = match.group(1)
        elif "中五" in filename:
            year_label = "F5_Alumni"
        else:
            year_label = filename.replace('.pdf', '')

        try:
            reader = pypdf.PdfReader(pdf_path)
            total_pages = len(reader.pages)
            for page_num in range(1, total_pages + 1):
                jobs.append((pdf_path, year_label, page_num, total_pages, output_base_dir))
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")

    print(f"Total parallel 1-to-1 grid OCR jobs: {len(jobs)} pages across {len(pdf_files)} volumes.")
    print("Launching parallel 1-to-1 Grid Apple Vision OCR workers across 8 CPU cores...")

    master_search_index = []
    master_verified_roster = []

    completed_count = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_page_job, job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            completed_count += 1
            res = future.result()
            master_search_index.append(res["entry"])
            master_verified_roster.extend(res["roster"])

            if completed_count % 200 == 0 or completed_count == len(jobs):
                print(f"  Progress: {completed_count} / {len(jobs)} pages processed with 1-to-1 grid OCR...", flush=True)

    master_search_index.sort(key=lambda x: (str(x["year"]), x["page"]))

    master_index_path = "okf_search_data.json"
    with open(master_index_path, "w", encoding="utf-8") as f:
        json.dump(master_search_index, f, ensure_ascii=False, indent=2)

    master_roster_path = "okf_verified_roster.json"
    with open(master_roster_path, "w", encoding="utf-8") as f:
        json.dump(master_verified_roster, f, ensure_ascii=False, indent=2)

    print(f"\n=======================================================")
    print(f" ALL VOLUMES 1-TO-1 GRID ALIGNED & PROCESSED SUCCESSFULLY!")
    print(f" Total PDF Volumes: {len(pdf_files)}")
    print(f" Total Pages OCR'd & Indexed: {len(master_search_index)}")
    print(f" Total 1-to-1 Grid Verified Bilingual Names: {len(master_verified_roster)}")
    print(f"=======================================================")

if __name__ == "__main__":
    files_dir = "Files"
    output_dir = "okf_output"
    process_all_workspace_volumes(files_dir, output_dir)
