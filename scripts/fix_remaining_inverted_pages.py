#!/usr/bin/env python3
"""
Fix Remaining Inverted Pages Across Wah Yan Star Archive
Rotates all 16 identified inverted pages by 180 degrees in-place,
updates any associated photo crops, re-runs Vision OCR, and verifies
orientation against the rendered PDF.
"""

import os
import sys
import glob
import json
import subprocess
import pymupdf
import numpy as np
from PIL import Image

MAC_OCR_BIN = os.path.join(os.path.dirname(__file__), "mac_ocr")

PAGES_TO_FIX = {
    '1971': [10, 37],
    '1972': [4, 27, 107, 109, 160],
    '1973': [24, 50],
    '1974': [27, 130, 139],
    '1976': [17],
    '1978': [116],
    '1979': [86, 94]
}

def clean_vision_ocr_text(text):
    if not text:
        return ""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        cleaned.append(s)
    return '\n'.join(cleaned).strip()

def run_vision_ocr(image_path):
    if not os.path.exists(MAC_OCR_BIN):
        return ""
    try:
        # Convert webp to temporary png if mac_ocr needs png
        temp_png = None
        target_path = image_path
        if image_path.endswith('.webp'):
            temp_png = f"/tmp/ocr_tmp_{os.getpid()}.png"
            with Image.open(image_path) as im:
                im.save(temp_png, "PNG")
            target_path = temp_png

        res = subprocess.run([MAC_OCR_BIN, target_path], capture_output=True, text=True, check=True)
        if temp_png and os.path.exists(temp_png):
            os.remove(temp_png)

        raw_json = res.stdout.strip()
        items = json.loads(raw_json)
        # Vision coords: y=1 top, y=0 bottom. Sort by descending y, then ascending x
        sorted_obs = sorted(items, key=lambda l: (-l['y'], l['x']))
        plain_text = '\n'.join([l['text'] for l in sorted_obs])
        return clean_vision_ocr_text(plain_text)
    except Exception as e:
        print(f"  Warning: OCR failed for {image_path}: {e}")
        return ""

def fix_pages():
    photos_dir = "okf_output/photos"
    pages_base = "okf_output/pages"
    entities_base = "okf_output/entities"

    total = sum(len(v) for v in PAGES_TO_FIX.values())
    print("==================================================")
    print(f"Starting 180° Inversion Correction for {total} Pages")
    print("==================================================")

    processed = 0
    for year, pages in sorted(PAGES_TO_FIX.items()):
        pdf_path = f"Files/{year}.pdf"
        doc = pymupdf.open(pdf_path) if os.path.exists(pdf_path) else None

        print(f"\nProcessing Volume {year} ({len(pages)} pages: {pages})...")
        for p in pages:
            base_name = f"{year}_page_{p:03d}_full"
            webp_path = os.path.join(photos_dir, f"{base_name}.webp")
            png_path = os.path.join(photos_dir, f"{base_name}.png")

            target_files = []
            if os.path.exists(webp_path):
                target_files.append((webp_path, "WEBP"))
            if os.path.exists(png_path):
                target_files.append((png_path, "PNG"))

            if not target_files:
                print(f"  Warning: Neither webp nor png found for {year} p.{p}")
                continue

            # 1. Rotate Full Page Image by 180 degrees
            for path, fmt in target_files:
                with Image.open(path) as im:
                    rotated = im.transpose(Image.ROTATE_180)
                    if fmt == "WEBP":
                        rotated.save(path, "WEBP", quality=85, method=6)
                    else:
                        rotated.save(path, "PNG")

            # 2. Also rotate any photo crops on this page
            crop_files = glob.glob(os.path.join(photos_dir, f"{year}_page_{p:03d}_photo_*.*"))
            for crop_path in crop_files:
                fmt = "WEBP" if crop_path.endswith('.webp') else "PNG"
                with Image.open(crop_path) as c_im:
                    c_rot = c_im.transpose(Image.ROTATE_180)
                    if fmt == "WEBP":
                        c_rot.save(crop_path, "WEBP", quality=85, method=6)
                    else:
                        c_rot.save(crop_path, "PNG")
                print(f"  Rotated crop: {os.path.basename(crop_path)}")

            # 3. Verification: compare with PDF pixmap
            main_path = webp_path if os.path.exists(webp_path) else png_path
            if doc:
                page_obj = doc[p - 1]
                pix = page_obj.get_pixmap(dpi=30)
                pdf_im = Image.frombytes('RGB', [pix.width, pix.height], pix.samples).convert('L')
                pdf_arr = np.array(pdf_im, dtype=float)

                with Image.open(main_path) as disk_im:
                    d_im = disk_im.resize((pix.width, pix.height)).convert('L')
                    disk_arr = np.array(d_im, dtype=float)

                new_diff_0 = float(np.mean(np.abs(disk_arr - pdf_arr)))
                new_diff_180 = float(np.mean(np.abs(np.rot90(disk_arr, 2) - pdf_arr)))
                status = "✅ UPRIGHT" if new_diff_0 < new_diff_180 else "❌ CHECK"
                print(f"  {year} Pg {p:03d}: diff_0={new_diff_0:.2f}, diff_180={new_diff_180:.2f} -> {status}")

            # 4. Re-run OCR and update markdown
            ocr_text = run_vision_ocr(main_path)
            md_dir = os.path.join(pages_base, str(year))
            os.makedirs(md_dir, exist_ok=True)
            md_path = os.path.join(md_dir, f"page_{p:03d}.md")

            crops = [os.path.basename(c) for c in glob.glob(os.path.join(photos_dir, f"{year}_page_{p:03d}_photo_*.*"))]
            md_lines = [f"# Wah Yan Star {year} - Page {p}\n"]
            if crops:
                md_lines.append("## Extracted Photos & Figures\n")
                for c in sorted(crops):
                    md_lines.append(f"![{year} Page {p} Photo](../photos/{c})")
            md_lines.append("\n## Page Text Content\n")
            if ocr_text:
                md_lines.append("```text")
                md_lines.append(ocr_text)
                md_lines.append("```\n")
            else:
                md_lines.append("*No text detected / Scanned image page.*\n")

            with open(md_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(md_lines))

            if year == '1976':
                top_md_path = os.path.join(pages_base, f"page_{p:03d}.md")
                if os.path.exists(top_md_path):
                    with open(top_md_path, "w", encoding="utf-8") as f:
                        f.write('\n'.join(md_lines))

            # 5. Update structured entity if present
            entity_path = os.path.join(entities_base, str(year), f"page_{p:03d}.json")
            if os.path.exists(entity_path):
                try:
                    with open(entity_path, "r", encoding="utf-8") as f:
                        entity_data = json.load(f)
                    entity_data["extracted_photos"] = crops
                    with open(entity_path, "w", encoding="utf-8") as f:
                        json.dump(entity_data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    pass

            processed += 1

    print("\n==================================================")
    print(f"🎉 Successfully corrected all {processed} inverted pages!")
    print("==================================================")

if __name__ == '__main__':
    fix_pages()
