import os
import json
import re

def update_master_dataset():
    print("=== Updating Master Search Index for ALL Volumes (1969 to 1979) ===")
    
    search_data_path = 'okf_search_data.json'
    roster_data_path = 'okf_verified_roster.json'

    # Master entries list
    master_entries = []
    
    # Base directories
    pages_base = 'okf_output/pages'
    photos_dir = 'okf_output/photos'

    if not os.path.exists(pages_base):
        print("Error: okf_output/pages does not exist!")
        return

    year_dirs = sorted([d for d in os.listdir(pages_base) if os.path.isdir(os.path.join(pages_base, d))])
    
    for ydir in year_dirs:
        y_path = os.path.join(pages_base, ydir)
        md_files = sorted([f for f in os.listdir(y_path) if f.endswith('.md')])
        print(f"  Indexing Year '{ydir}': {len(md_files)} pages...")

        for fname in md_files:
            try:
                p_num = int(fname.replace('page_', '').replace('.md', ''))
            except ValueError:
                continue

            fpath = os.path.join(y_path, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            text_content = content
            if '```text' in content:
                parts = content.split('```text')
                if len(parts) > 1:
                    text_content = parts[1].split('```')[0].strip()

            full_img = f"{ydir}_page_{p_num:03d}_full.png"
            photos = sorted([p for p in os.listdir(photos_dir) if p.startswith(f"{ydir}_page_{p_num:03d}_photo_")])

            # Verified student names mapping
            verified_on_page = []
            low_text = text_content.lower()

            if 'poon' in low_text or '潘' in text_content:
                verified_on_page.append({'year': ydir, 'page': p_num, 'english_name': 'Poon Sek Kwong', 'chinese_name': '潘錫光'})
            if 'yip' in low_text or '葉' in text_content:
                verified_on_page.append({'year': ydir, 'page': p_num, 'english_name': 'Yip Yau Jim', 'chinese_name': '葉佑沾'})
            if 'law' in low_text or '羅' in text_content:
                verified_on_page.append({'year': ydir, 'page': p_num, 'english_name': 'Law Sin Kin, Edwin', 'chinese_name': '羅先建'})
            if 'lee chi' in low_text or '李智' in text_content:
                verified_on_page.append({'year': ydir, 'page': p_num, 'english_name': 'Lee Chi', 'chinese_name': '李智'})
            if 'luk' in low_text or '陸' in text_content:
                verified_on_page.append({'year': ydir, 'page': p_num, 'english_name': 'Luk Hoi Tak', 'chinese_name': '陸海德'})

            year_title = f"Wah Yan Star {ydir} - Page {p_num}"
            if ydir == '1975_F5_Alumni':
                year_title = f"1975 Form 5 Alumni Book - Page {p_num}"
            elif ydir == 'Reunion_Gala':
                year_title = f"Alumni Reunion Gala Photo - Page {p_num}"

            master_entries.append({
                'year': ydir,
                'page': p_num,
                'title': year_title,
                'text': text_content,
                'photos': photos,
                'full_page_photo': full_img,
                'verified_names': verified_on_page
            })

    # Save updated okf_search_data.json
    with open(search_data_path, 'w', encoding='utf-8') as f:
        json.dump(master_entries, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Master dataset updated: {len(master_entries)} total pages across ALL volumes!")

if __name__ == '__main__':
    update_master_dataset()
