#!/usr/bin/env python3
"""
High-Speed Parallel Cloudflare R2 Photo Uploader
Uploads all 5,248 WebP photos to Cloudflare R2 with:
- 16 parallel upload threads
- Automatic MIME type detection (image/webp)
- Cache-Control: public, max-age=31536000, immutable
- Resumable (skips already uploaded files)
"""
import os
import sys
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed

def main():
    account_id = os.environ.get("R2_ACCOUNT_ID")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("R2_BUCKET_NAME", "wahyan-star-photos")

    if not (account_id and access_key and secret_key):
        print("=" * 60)
        print("Cloudflare R2 Photo Uploader for Wah Yan Star")
        print("=" * 60)
        print("Missing Cloudflare R2 credentials.\n")
        print("Please set your credentials before running this script:")
        print("  export R2_ACCOUNT_ID='your_cloudflare_account_id'")
        print("  export R2_ACCESS_KEY_ID='your_r2_access_key_id'")
        print("  export R2_SECRET_ACCESS_KEY='your_r2_secret_access_key'")
        print("  export R2_BUCKET_NAME='wahyan-star-photos'  # (or your bucket name)")
        print("\nThen run:")
        print("  python3 scripts/upload_to_r2.py")
        print("=" * 60)
        sys.exit(1)

    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        print("Installing boto3 for S3/R2 upload...")
        os.system("pip3 install boto3")
        import boto3
        from botocore.config import Config

    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4", max_pool_connections=30)
    )

    photo_files = sorted(glob.glob("okf_output/photos/*.webp") + glob.glob("okf_output/photos/*.png"))
    total = len(photo_files)
    print(f"Found {total} photos to verify and upload to Cloudflare R2 bucket '{bucket_name}'...")

    # Fetch existing objects to skip re-uploading
    existing_keys = set()
    print("Checking existing files in bucket...")
    paginator = s3.get_paginator('list_objects_v2')
    try:
        for page in paginator.paginate(Bucket=bucket_name):
            for obj in page.get('Contents', []):
                existing_keys.add(obj['Key'])
    except Exception as e:
        print(f"Notice: Could not list existing objects ({e}), will upload all files.")

    files_to_upload = [f for f in photo_files if os.path.basename(f) not in existing_keys]
    print(f"{len(existing_keys)} files already on R2. {len(files_to_upload)} files to upload.")

    if not files_to_upload:
        print("All photos are already uploaded to Cloudflare R2!")
        return

    success_count = len(existing_keys)
    fail_count = 0

    def upload_single_file(filepath):
        filename = os.path.basename(filepath)
        content_type = "image/webp" if filepath.endswith(".webp") else "image/png"
        try:
            with open(filepath, "rb") as data:
                s3.put_object(
                    Bucket=bucket_name,
                    Key=filename,
                    Body=data,
                    ContentType=content_type,
                    CacheControl="public, max-age=31536000, immutable"
                )
            return True, filename
        except Exception as err:
            return False, f"{filename}: {err}"

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(upload_single_file, f): f for f in files_to_upload}
        for future in as_completed(futures):
            ok, msg = future.result()
            if ok:
                success_count += 1
                if success_count % 100 == 0 or success_count == total:
                    pct = (success_count / total) * 100
                    print(f"[{success_count}/{total}] ({pct:.1f}%) Uploaded: {msg}")
            else:
                fail_count += 1
                print(f"[FAILED] {msg}")

    print(f"\nUpload Completed! {success_count}/{total} files synced. (Failed: {fail_count})")
    print(f"\nNext step: Paste your Cloudflare R2 Public URL into R2_PUBLIC_URL in app.js!")

if __name__ == "__main__":
    main()
