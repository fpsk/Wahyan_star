#!/usr/bin/env python3
import os
import sys
import glob
import json
import pymupdf
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor

PDF_MAP = {
    '1969': 'Files/1969.pdf',
    '1970': 'Files/1970.pdf',
    '1971': 'Files/1971.pdf',
    '1972': 'Files/1972.pdf',
    '1973': 'Files/1973.pdf',
    '1974': 'Files/1974.pdf',
    '1975': 'Files/1975.pdf',
    '1976': 'Files/1976.pdf',
    '1977': 'Files/1977.pdf',
    '1978': 'Files/1978.pdf',
    '1979': 'Files/1979.pdf',
    'F5_Alumni': 'Files/華仁中五同學錄.pdf'
}

def scan_volume(year, pdf_path):
    if not os.path.exists(pdf_path):
        return year, []
    
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    inverted = []
    
    for p in range(1, total_pages + 1):
        # Check both webp and png
        webp_path = f'okf_output/photos/{year}_page_{p:03d}_full.webp'
        png_path = f'okf_output/photos/{year}_page_{p:03d}_full.png'
        
        disk_path = webp_path if os.path.exists(webp_path) else (png_path if os.path.exists(png_path) else None)
        if not disk_path:
            continue
            
        try:
            page = doc[p - 1]
            pix = page.get_pixmap(dpi=30)
            pdf_im = Image.frombytes('RGB', [pix.width, pix.height], pix.samples).convert('L')
            pdf_arr = np.array(pdf_im, dtype=float)
            
            with Image.open(disk_path) as disk_raw:
                d_im = disk_raw.resize((pix.width, pix.height)).convert('L')
                disk_arr = np.array(d_im, dtype=float)
                
            diff_0 = float(np.mean(np.abs(disk_arr - pdf_arr)))
            diff_180 = float(np.mean(np.abs(np.rot90(disk_arr, 2) - pdf_arr)))
            
            # If 180 is closer by at least 1.5 units, it's definitely inverted
            if diff_180 + 1.5 < diff_0:
                inverted.append({
                    'year': year,
                    'page': p,
                    'diff_0': round(diff_0, 2),
                    'diff_180': round(diff_180, 2),
                    'delta': round(diff_0 - diff_180, 2),
                    'path': disk_path
                })
        except Exception as e:
            print(f"Error checking {year} p.{p}: {e}", file=sys.stderr)
            
    return year, inverted

def main():
    print("==================================================================")
    print("🔍 Scanning all 12 volumes in parallel for inverted disk images...")
    print("==================================================================")
    
    all_inverted = {}
    with ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as executor:
        futures = [executor.submit(scan_volume, yr, path) for yr, path in sorted(PDF_MAP.items())]
        for f in futures:
            year, inverted = f.result()
            all_inverted[year] = inverted
            pg_list = [item['page'] for item in inverted]
            print(f"Volume {year}: {len(inverted)} inverted pages -> {pg_list}", flush=True)
            
    total_inverted = sum(len(v) for v in all_inverted.values())
    print("==================================================================")
    print(f"Total inverted pages identified across all volumes: {total_inverted}")
    print("==================================================================")
    
    output_json = "/Users/fskpoon/.gemini/antigravity/brain/54ab50fa-0de9-422b-9489-664d331ed843/scratch/all_inverted_pages.json"
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w") as out:
        json.dump(all_inverted, out, indent=2)
    print(f"Saved full report to {output_json}")

if __name__ == '__main__':
    main()
