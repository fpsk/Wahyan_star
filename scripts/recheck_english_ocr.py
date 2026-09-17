import json
import re

def clean_english_ocr_text(text):
    if not text:
        return ""

    # 1. Honorific & Title Spacing
    text = re.sub(r'\bFr\.([A-Z])', r'Fr. \1', text)
    text = re.sub(r'\bRev\.Fr\.', 'Rev. Fr. ', text)
    text = re.sub(r'\bMr\.([A-Z])', r'Mr. \1', text)
    text = re.sub(r'\bDr\.([A-Z])', r'Dr. \1', text)

    # 2. Form & Class Designation Corrections
    text = re.sub(r'\bL65\b', 'L6S', text)
    text = re.sub(r'\bU65\b', 'U6S', text)
    text = re.sub(r'\b5AI\b', '5A', text)
    text = re.sub(r'\b4AI\b', '4A', text)
    text = re.sub(r'\b3AI\b', '3A', text)
    text = re.sub(r'\b2AI\b', '2A', text)
    text = re.sub(r'\b1AI\b', '1A', text)
    text = re.sub(r'\bForm(\d)\b', r'Form \1', text)

    # 3. Common OCR Typo Word Fixes
    text = re.sub(r'\bIst\b', '1st', text)
    text = re.sub(r'\bI st\b', '1st', text)
    text = re.sub(r'\b2 nd\b', '2nd', text)
    text = re.sub(r'\b3 rd\b', '3rd', text)
    text = re.sub(r'\bVlce\b', 'Vice', text)
    text = re.sub(r'\bV1ce\b', 'Vice', text)
    text = re.sub(r'\bCommitte\b', 'Committee', text)
    text = re.sub(r'\bExecutiv\b', 'Executive', text)
    text = re.sub(r'\bKwonig\b', 'Kwong', text)
    text = re.sub(r'\bPuy\b', 'Pui', text)

    # 4. Clean noise trailing punctuation/symbols
    text = re.sub(r'[~“^\|\*]+', '', text)
    
    # 5. Fix double spaces
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()

def clean_student_name(name):
    if not name:
        return ""
    # Strip leading numbers
    name = re.sub(r'^\d+[\.\s]+', '', name)
    # Strip trailing numbers or noise
    name = re.sub(r'[0-9~“^\|\*]+$', '', name)
    
    # Common name typos
    name = name.replace('Kwonig', 'Kwong')
    name = name.replace('Puy', 'Pui')
    name = name.replace('James,', 'James ')
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def run_english_ocr_recheck():
    with open('okf_search_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open('okf_verified_roster.json', 'r', encoding='utf-8') as f:
        rosters = json.load(f)

    cleaned_entries = 0
    cleaned_names = 0

    for item in data:
        orig_text = item.get('text', '')
        new_text = clean_english_ocr_text(orig_text)
        if orig_text != new_text:
            item['text'] = new_text
            cleaned_entries += 1

        v_names = item.get('verified_names', [])
        for v in v_names:
            orig_eng = v.get('english_name', '')
            new_eng = clean_student_name(orig_eng)
            if orig_eng != new_eng:
                v['english_name'] = new_eng
                cleaned_names += 1

    for r in rosters:
        orig_eng = r.get('english_name', '')
        new_eng = clean_student_name(orig_eng)
        if orig_eng != new_eng:
            r['english_name'] = new_eng

    # Save cleaned Master Search Index
    with open('okf_search_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Save cleaned Master Roster
    with open('okf_verified_roster.json', 'w', encoding='utf-8') as f:
        json.dump(rosters, f, ensure_ascii=False, indent=2)

    print(f"=======================================================")
    print(f" ENGLISH OCR RECHECK & CORRECTION COMPLETED!")
    print(f" Corrected Text Entries: {cleaned_entries} pages")
    print(f" Corrected English Names: {cleaned_names} names")
    print(f"=======================================================")

if __name__ == "__main__":
    run_english_ocr_recheck()
