#!/usr/bin/env python3
"""
OKF 0.2 Master Knowledge Graph & Search Index Builder
Aggregates structured page entities, constructs cross-year student progression timelines,
and builds `okf_search_data_v2.json` & `okf_roster_v2.json`.
"""

import os
import json
import re
from typing import Dict, Any, List

def build_okf_v2_indices():
    print("==================================================================")
    print("🏗️  Building OKF 0.2 Master Knowledge Graph & Universal Roster Index")
    print("==================================================================")

    entities_base = "okf_output/entities"
    pages_base = "okf_output/pages"
    photos_dir = "okf_output/photos"
    out_search_json = "okf_search_data_v2.json"
    out_roster_json = "okf_roster_v2.json"

    if not os.path.exists(pages_base):
        print(f"Error: {pages_base} not found!")
        return

    year_dirs = sorted([d for d in os.listdir(pages_base) if os.path.isdir(os.path.join(pages_base, d))])
    
    master_entries = []
    universal_student_index: Dict[str, Dict[str, Any]] = {}
    universal_staff_index: Dict[str, Dict[str, Any]] = {}

    total_pages = 0
    total_students_extracted = 0

    for ydir in year_dirs:
        y_pages_path = os.path.join(pages_base, ydir)
        y_entities_path = os.path.join(entities_base, ydir) if os.path.exists(entities_base) else None

        md_files = sorted([f for f in os.listdir(y_pages_path) if f.endswith(".md")])
        print(f"  📖 Indexing Volume '{ydir}' ({len(md_files)} pages)...")

        for fname in md_files:
            try:
                p_num = int(fname.replace("page_", "").replace(".md", ""))
            except ValueError:
                continue

            total_pages += 1
            md_path = os.path.join(y_pages_path, fname)
            with open(md_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            text_content = raw_content
            if "```text" in raw_content:
                parts = raw_content.split("```text")
                if len(parts) > 1:
                    text_content = parts[1].split("```")[0].strip()

            full_img_webp = f"{ydir}_page_{p_num:03d}_full.webp"
            full_img = full_img_webp if os.path.exists(os.path.join(photos_dir, full_img_webp)) else f"{ydir}_page_{p_num:03d}_full.png"
            photos = sorted([p for p in os.listdir(photos_dir) if p.startswith(f"{ydir}_page_{p_num:03d}_photo_")])

            # Check if structured OKF 0.2 JSON exists
            entity_json_path = os.path.join(y_entities_path, f"page_{p_num:03d}.json") if y_entities_path else None
            page_data = None
            if entity_json_path and os.path.exists(entity_json_path):
                try:
                    with open(entity_json_path, "r", encoding="utf-8") as ef:
                        page_data = json.load(ef)
                except Exception:
                    page_data = None

            if not page_data:
                # Basic fallback entry
                page_data = {
                    "year": str(ydir),
                    "page": p_num,
                    "section_type": "General",
                    "class_designation": None,
                    "summary": " ".join([l for l in text_content.split("\n") if l.strip() and not l.startswith("#")][:3])[:200],
                    "students": [],
                    "staff": [],
                    "activities": [],
                    "sports_records": []
                }

            students = page_data.get("students", [])
            staff = page_data.get("staff", [])
            activities = page_data.get("activities", [])
            sports_records = page_data.get("sports_records", [])

            entry_year = "1975_F5_Alumni" if ydir in ["1975_F5_Alumni", "F5_Alumni"] else ydir

            # Backwards-compatible verified_names list
            verified_names = list(page_data.get("verified_names", []))
            
            for st in students:
                eng = st.get("english_name", "").strip()
                chi = st.get("chinese_name", "").strip()
                if eng or chi:
                    if not any(v.get("english_name") == eng and v.get("chinese_name") == chi for v in verified_names):
                        verified_names.append({
                            "year": entry_year,
                            "page": p_num,
                            "english_name": eng,
                            "chinese_name": chi,
                            "class": page_data.get("class_designation") or st.get("class_designation") or f"Page {p_num}"
                        })
                    total_students_extracted += 1

                    # Add aliases to verified_names
                    for a_en in st.get("aliases_en", []):
                        if not any(v.get("english_name") == a_en for v in verified_names):
                            verified_names.append({
                                "year": entry_year,
                                "page": p_num,
                                "english_name": a_en,
                                "chinese_name": chi,
                                "class": page_data.get("class_designation") or st.get("class_designation") or f"Page {p_num}"
                            })
                    for a_zh in st.get("aliases_zh", []):
                        if not any(v.get("chinese_name") == a_zh for v in verified_names):
                            verified_names.append({
                                "year": entry_year,
                                "page": p_num,
                                "english_name": eng,
                                "chinese_name": a_zh,
                                "class": page_data.get("class_designation") or st.get("class_designation") or f"Page {p_num}"
                            })

                    # Add to universal student timeline graph
                    primary_key = eng.lower() if eng else chi
                    if primary_key:
                        if primary_key not in universal_student_index:
                            universal_student_index[primary_key] = {
                                "name_en": eng,
                                "name_zh": chi,
                                "appearances": []
                            }
                        if not universal_student_index[primary_key]["name_zh"] and chi:
                            universal_student_index[primary_key]["name_zh"] = chi

                        # Check if appearance already recorded
                        existing_app = next((a for a in universal_student_index[primary_key]["appearances"] if a["year"] == entry_year and a["page"] == p_num), None)
                        if not existing_app:
                            universal_student_index[primary_key]["appearances"].append({
                                "year": entry_year,
                                "page": p_num,
                                "class": page_data.get("class_designation") or st.get("class_designation"),
                                "full_page_photo": full_img if os.path.exists(os.path.join(photos_dir, full_img)) else None
                            })

            year_title = f"Wah Yan Star {entry_year} - Page {p_num}"
            if entry_year == "1975_F5_Alumni":
                year_title = f"1975 Form 5 Alumni Book - Page {p_num}"
            elif entry_year == "Reunion_Gala":
                year_title = f"Alumni Reunion Gala - Page {p_num}"

            master_entries.append({
                "year": entry_year,
                "page": p_num,
                "title": year_title,
                "section_type": page_data.get("section_type", "General"),
                "class_designation": page_data.get("class_designation"),
                "summary": page_data.get("summary", ""),
                "text": text_content,
                "students": students,
                "staff": staff,
                "activities": activities,
                "sports_records": sports_records,
                "verified_names": verified_names,
                "photos": photos,
                "full_page_photo": full_img if os.path.exists(os.path.join(photos_dir, full_img)) else None,
                "is_staff_activity": len(staff) > 0 or "staff" in text_content.lower() or "principal" in text_content.lower()
            })

    # Save OKF 0.2 Master Search Dataset
    with open(out_search_json, "w", encoding="utf-8") as f:
        json.dump(master_entries, f, ensure_ascii=False, indent=2)

    # Save Universal Bilingual Student Roster Directory
    with open(out_roster_json, "w", encoding="utf-8") as f:
        json.dump(list(universal_student_index.values()), f, ensure_ascii=False, indent=2)

    # Also update existing legacy okf_search_data.json and okf_verified_roster.json for full backwards compatibility
    with open("okf_search_data.json", "w", encoding="utf-8") as f:
        json.dump(master_entries, f, ensure_ascii=False, indent=2)

    print(f"\n==================================================================")
    print(f"🎉 OKF 0.2 Build Complete!")
    print(f"   • Total Pages Indexed: {total_pages}")
    print(f"   • Unique Student Records in Knowledge Graph: {len(universal_student_index)}")
    print(f"   • Master Dataset Saved: {out_search_json} & okf_search_data.json")
    print(f"   • Universal Roster Directory: {out_roster_json}")
    print(f"==================================================================\n")

if __name__ == "__main__":
    build_okf_v2_indices()
