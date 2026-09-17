#!/usr/bin/env python3
"""
High-Speed Parallel Multi-Core PNG to WebP Converter for Wah Yan Star Archive
Safely converts 5,248 photos from uncompressed PNG to high-fidelity WebP (quality 82-85).
Verifies each converted image before removing the original PNG.
"""

import os
import sys
import glob
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "okf_output", "photos")

def convert_single_image(png_path):
    """
    Converts a single PNG image to WebP with verification.
    Returns (success: bool, orig_size: int, new_size: int, error_msg: str)
    """
    try:
        webp_path = png_path[:-4] + ".webp"
        orig_size = os.path.getsize(png_path)

        # Full scans get quality=82; cropped photos get quality=85
        is_full = "_full.png" in png_path
        q = 82 if is_full else 85

        with Image.open(png_path) as im:
            # Preserve original colorspace & dimensions
            if im.mode not in ("RGB", "RGBA", "L"):
                im = im.convert("RGB")
            im.save(webp_path, "WEBP", quality=q, method=6)

        # Verification step: ensure newly written WebP can be opened and is non-empty
        new_size = os.path.getsize(webp_path)
        if new_size < 100:
            raise ValueError(f"WebP output suspiciously small ({new_size} bytes)")

        with Image.open(webp_path) as test_im:
            test_im.verify()

        # Safely remove original PNG after verified conversion
        os.remove(png_path)
        return (True, orig_size, new_size, None)

    except Exception as e:
        return (False, 0, 0, f"Error on {png_path}: {e}")

def main():
    if not os.path.exists(PHOTOS_DIR):
        print(f"Error: Directory '{PHOTOS_DIR}' does not exist.")
        sys.exit(1)

    png_files = sorted(glob.glob(os.path.join(PHOTOS_DIR, "*.png")))
    total_files = len(png_files)
    print("==================================================================")
    print(f"🚀 Starting High-Fidelity WebP Conversion: {total_files} PNG images")
    print(f"📁 Target Directory: {PHOTOS_DIR}")
    print("==================================================================")

    if total_files == 0:
        print("No PNG files found to convert. Checking for WebP files...")
        webp_count = len(glob.glob(os.path.join(PHOTOS_DIR, "*.webp")))
        print(f"Found {webp_count} WebP files already present.")
        return

    start_time = time.time()
    total_orig_bytes = 0
    total_new_bytes = 0
    converted_count = 0
    error_count = 0

    # Determine optimal worker count (max 8)
    num_workers = min(8, os.cpu_count() or 4)
    print(f"⚡ Utilizing {num_workers} parallel CPU workers...")

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(convert_single_image, f): f for f in png_files}

        for i, future in enumerate(as_completed(futures), 1):
            success, orig_size, new_size, err = future.result()
            if success:
                converted_count += 1
                total_orig_bytes += orig_size
                total_new_bytes += new_size
            else:
                error_count += 1
                print(f"\n❌ {err}", flush=True)

            if i % 250 == 0 or i == total_files:
                elapsed = time.time() - start_time
                mb_saved = (total_orig_bytes - total_new_bytes) / (1024 * 1024)
                rate = i / elapsed if elapsed > 0 else 0
                pct = (i / total_files) * 100
                print(f"  [{pct:5.1f}%] Converted {i}/{total_files} images ({rate:.1f} img/s) — Reclaimed: {mb_saved/1024:.2f} GB", flush=True)

    elapsed_total = time.time() - start_time
    reclaimed_gb = (total_orig_bytes - total_new_bytes) / (1024 ** 3)
    orig_gb = total_orig_bytes / (1024 ** 3)
    new_gb = total_new_bytes / (1024 ** 3)

    print("\n==================================================================")
    print(f"🎉 Conversion Complete in {elapsed_total:.1f}s!")
    print(f"   • Successfully Converted: {converted_count} / {total_files}")
    print(f"   • Errors: {error_count}")
    print(f"   • Original PNG Space:    {orig_gb:.2f} GB")
    print(f"   • Optimized WebP Space:   {new_gb:.2f} GB")
    print(f"   • Net Space Reclaimed:   {reclaimed_gb:.2f} GB ({(1 - new_gb/orig_gb)*100:.1f}% reduction)")
    print("==================================================================\n")

if __name__ == "__main__":
    main()
