import os
import json

def update_1977_dataset():
    print("=== Updating Master Search Index for Renewed 1977 Volume ===")
    
    search_data_path = 'okf_search_data.json'
    with open(search_data_path, 'r', encoding='utf-8') as f:
        master_data = json.load(f)

    # Keep all volumes except old 1977
    other_entries = [item for item in master_data if str(item.get('year')) != '1977']

    new_1977_entries = []
    pages_dir = 'okf_output/pages/1977'
    photos_dir = 'okf_output/photos'

    if os.path.exists(pages_dir):
        md_files = sorted([f for f in os.listdir(pages_dir) if f.endswith('.md')])
        for fname in md_files:
            p_num = int(fname.replace('page_', '').replace('.md', ''))
            fpath = os.path.join(pages_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            text_content = content
            if '```text' in content:
                parts = content.split('```text')
                if len(parts) > 1:
                    text_content = parts[1].split('```')[0].strip()

            full_img = f"1977_page_{p_num:03d}_full.png"
            photos = sorted([p for p in os.listdir(photos_dir) if p.startswith(f"1977_page_{p_num:03d}_photo_")])

            verified_on_page = []
            if 'poon' in text_content.lower() or '潘' in text_content:
                verified_on_page.append({'year': '1977', 'page': p_num, 'english_name': 'Poon Sek Kwong', 'chinese_name': '潘錫光'})
            if 'yip' in text_content.lower() or '葉' in text_content:
                verified_on_page.append({'year': '1977', 'page': p_num, 'english_name': 'Yip Yau Jim', 'chinese_name': '葉佑沾'})
            if 'law' in text_content.lower() or '羅' in text_content:
                verified_on_page.append({'year': '1977', 'page': p_num, 'english_name': 'Law Sin Kin, Edwin', 'chinese_name': '羅先建'})
            if 'lee chi' in text_content.lower() or '李智' in text_content:
                verified_on_page.append({'year': '1977', 'page': p_num, 'english_name': 'Lee Chi', 'chinese_name': '李智'})
            if 'luk' in text_content.lower() or '陸' in text_content:
                verified_on_page.append({'year': '1977', 'page': p_num, 'english_name': 'Luk Hoi Tak', 'chinese_name': '陸海德'})

            new_1977_entries.append({
                'year': '1977',
                'page': p_num,
                'title': f"Wah Yan Star 1977 - Page {p_num}",
                'text': text_content,
                'photos': photos,
                'full_page_photo': full_img,
                'verified_names': verified_on_page
            })

    print(f"Processed {len(new_1977_entries)} renewed 1977 high-res page entries.")

    combined_data = other_entries + new_1977_entries
    with open(search_data_path, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)

    print(f"Master dataset saved: {len(combined_data)} total pages across all 10 volumes!")

if __name__ == '__main__':
    update_1977_dataset()
