import os
import json
import re

def build_index(okf_dir, verified_roster_file, output_json):
    pages_dir = os.path.join(okf_dir, "pages")
    photos_dir = os.path.join(okf_dir, "photos")
    manifest_path = os.path.join(okf_dir, "manifest.json")

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # Load ground-truth verified roster mapping (No translation used)
    verified_rosters = []
    if os.path.exists(verified_roster_file):
        with open(verified_roster_file, 'r', encoding='utf-8') as f:
            verified_rosters = json.load(f)

    # Map verified student names by page
    verified_by_page = {}
    for r in verified_rosters:
        p = r["page"]
        if p not in verified_by_page:
            verified_by_page[p] = []
        verified_by_page[p].append(r)

    search_entries = []

    for item in manifest["pages"]:
        page_num = item["page"]
        md_file = os.path.join(okf_dir, item["file"])
        
        text_content = ""
        photos = []

        if os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

                match = re.search(r'```text\n(.*?)\n```', content, re.DOTALL)
                if match:
                    text_content = match.group(1).strip()
                else:
                    text_content = content

                photo_matches = re.findall(r'!\[.*?\]\(\.\./photos/(.*?)\)', content)
                photos = photo_matches

        first_lines = [l.strip() for l in text_content.split('\n') if l.strip() and not l.startswith('#')]
        page_summary = ' '.join(first_lines[:3])[:200] if first_lines else f"Page {page_num} Scanned Document & Photos"

        # Attach ground-truth verified names for this page if available
        page_verified_names = verified_by_page.get(page_num, [])

        search_entries.append({
            "page": page_num,
            "title": f"Page {page_num}",
            "summary": page_summary,
            "text": text_content,
            "verified_names": page_verified_names,
            "photos": photos,
            "full_page_photo": f"page_{page_num:03d}_full.png" if os.path.exists(os.path.join(photos_dir, f"page_{page_num:03d}_full.png")) else None
        })

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(search_entries, f, ensure_ascii=False, indent=2)

    print(f"Search index built with {len(search_entries)} pages and ground-truth verified rosters -> {output_json}")

if __name__ == "__main__":
    build_index("okf_output", "okf_verified_roster.json", "okf_search_data.json")
