#!/bin/bash
set -e

YEARS=(1971 1972 1973 1974 1975 1976 1977 1978 1979)

for YR in "${YEARS[@]}"; do
  echo "=== Staging and Committing Year $YR ==="
  git add okf_output/photos/${YR}*
  git commit -m "feat(photos): Add scanned pages for $YR" || echo "Nothing to commit for $YR"
  echo "=== Pushing Year $YR to GitHub ==="
  git push origin main
  echo "=== Year $YR Uploaded Successfully! ==="
done

echo "=== Staging and Committing Remaining Photos (F5, alumni, volume pages) ==="
git add okf_output/photos/F5* okf_output/photos/alumni* okf_output/photos/page*
git commit -m "feat(photos): Add scanned pages for F5 alumni and volume pages" || echo "Nothing to commit"
echo "=== Pushing Final Photos Batch to GitHub ==="
git push origin main
echo "=== ALL ARCHIVE PHOTOS UPLOADED TO GITHUB SUCCESSFULLY! ==="
