#!/usr/bin/env python3
"""
align_f5_alumni_bilingual.py
Authoritative bilingual alignment for 1975 Form 5 Alumni Book (華仁中五同學錄).
Cross-references every student profile with the official Wah Yan Star 1975 Form 5 rosters
(Pages 100-103: Forms 5A, 5A1, 5B, 5B1).
"""

import os
import json
import glob

PAGE_STUDENTS = {
    8: [
        {"name_en": "Lee Chi", "name_zh": "李智", "class": "5A", "seat": 17, "role": "主席 (Chairman)"},
        {"name_en": "Pun Wai Sum", "name_zh": "潘偉森", "class": "5B1", "seat": 28, "role": "副主席 (Vice Chairman)", "aliases_en": ["Poon Wai Sum"]},
        {"name_en": "Lui Tai Lok", "name_zh": "呂大樂", "class": "5B", "seat": 19, "role": "文書 (Secretary)"},
        {"name_en": "Leung Wing Fung", "name_zh": "梁永峯", "class": "5A1", "seat": 18, "role": "財政 (Treasurer)"},
        {"name_en": "Chan Yuk Keung", "name_zh": "陳玉強", "class": "5A", "seat": 2, "role": "康樂 (Recreation)", "aliases_zh": ["陳玉强"]},
        {"name_en": "Cheung Yuk Tong", "name_zh": "張玉堂", "class": "5B", "seat": 4, "role": "總務 (General Affairs)"}
    ],
    9: [
        {"name_en": "Chan Man Shun", "name_zh": "陳文信", "class": "5A", "seat": 1},
        {"name_en": "Au Kin Kwok", "name_zh": "區建國", "class": "5B", "seat": 1},
        {"name_en": "Chan Chi Ho", "name_zh": "陳志豪", "class": "5B1", "seat": 1},
        {"name_en": "Chan Pak Chuen", "name_zh": "陳伯傳", "class": "5B1", "seat": 2, "aliases_zh": ["陳伯傅"]}
    ],
    10: [
        {"name_en": "Chan Siu Kau", "name_zh": "陳紹裘", "class": "5A1", "seat": 2},
        {"name_en": "Chan Pui Shing", "name_zh": "陳沛誠", "class": "5A1", "seat": 1},
        {"name_en": "Chan Wai Leung, Valiant", "name_zh": "陳偉亮", "class": "5B", "seat": 2},
        {"name_en": "Chan Sik Pok", "name_zh": "陳皙博", "class": "5B1", "seat": 3, "aliases_zh": ["陳哲博"]}
    ],
    11: [
        {"name_en": "Chan Yin Chuan", "name_zh": "陳燕春", "class": "5B1", "seat": 4},
        {"name_en": "Cheng Kam Fat, James", "name_zh": "鄭金發", "class": "5B", "seat": 3},
        {"name_en": "Chan Yuk Keung", "name_zh": "陳玉強", "class": "5A", "seat": 2, "aliases_zh": ["陳玉强"]},
        {"name_en": "Cheng Kwok Ming", "name_zh": "鄭國明", "class": "5A", "seat": 3}
    ],
    12: [
        {"name_en": "Cheung Wai Yee", "name_zh": "張偉義", "class": "5A", "seat": 4},
        {"name_en": "Cheng Tak Chung", "name_zh": "鄭德忠", "class": "5B1", "seat": 5},
        {"name_en": "Cheung Po Wah", "name_zh": "張寶華", "class": "5B1", "seat": 6},
        {"name_en": "Cheung Yuk Tong", "name_zh": "張玉堂", "class": "5B", "seat": 4}
    ],
    13: [
        {"name_en": "Chiu Schumann, Paul", "name_zh": "趙舒文", "class": "5B", "seat": 5},
        {"name_en": "Chin Po Wah", "name_zh": "錢寶華", "class": "5B1", "seat": 7},
        {"name_en": "Chiu Kwong Wai", "name_zh": "趙光偉", "class": "5A1", "seat": 3},
        {"name_en": "Chiu Tso Mei", "name_zh": "邱松綿", "class": "5A", "seat": 5}
    ],
    14: [
        {"name_en": "Chow Kiang Cheong", "name_zh": "周烱昌", "class": "5A", "seat": 8},
        {"name_en": "Choi Hing Way", "name_zh": "蔡馨偉", "class": "5A", "seat": 6},
        {"name_en": "Chok Kin Ming", "name_zh": "束健銘", "class": "5A", "seat": 7},
        {"name_en": "Chow Yiu Hong", "name_zh": "周耀康", "class": "5B", "seat": 6}
    ],
    15: [
        {"name_en": "Chu Kam Tong", "name_zh": "朱錦棠", "class": "5A1", "seat": 4},
        {"name_en": "Chu Tat Kwong", "name_zh": "朱達光", "class": "5B", "seat": 7},
        {"name_en": "Chu Tai Hang, Henry", "name_zh": "朱大衡", "class": "5A", "seat": 9},
        {"name_en": "Chui Chi Fai", "name_zh": "崔志輝", "class": "5A", "seat": 10}
    ],
    16: [
        {"name_en": "Chung Heung Wing, Lawrence", "name_zh": "鍾向榮", "class": "5B", "seat": 8},
        {"name_en": "Fong Man Hong", "name_zh": "方文康", "class": "5B1", "seat": 9},
        {"name_en": "Fan Man Kwong", "name_zh": "范文廣", "class": "5B1", "seat": 8},
        {"name_en": "Fung Kit Man", "name_zh": "馮傑民", "class": "5A1", "seat": 5}
    ],
    17: [
        {"name_en": "Fung Kwok Kin", "name_zh": "馮國堅", "class": "5A1", "seat": 6},
        {"name_en": "Ho Siu Leung", "name_zh": "何紹良", "class": "5B1", "seat": 11, "aliases_zh": ["何紹長"]},
        {"name_en": "Hui Ying Tat", "name_zh": "許英達", "class": "5A1", "seat": 7},
        {"name_en": "Hau Yuen Shun", "name_zh": "侯元信", "class": "5B1", "seat": 10}
    ],
    18: [
        {"name_en": "Ko Pui Yung", "name_zh": "高培容", "class": "5B", "seat": 10},
        {"name_en": "Hung Chi Ling, Samuel", "name_zh": "洪志凌", "class": "5B", "seat": 9},
        {"name_en": "Kong Chi Hsien, Eugene", "name_zh": "江志賢", "class": "5B", "seat": 11},
        {"name_en": "Keung Shui Cheung", "name_zh": "姜瑞昌", "class": "5A1", "seat": 8}
    ],
    19: [
        {"name_en": "Kong Yu Key", "name_zh": "江禹基", "class": "5A", "seat": 11},
        {"name_en": "Kong Yun Chow", "name_zh": "江潤秋", "class": "5B1", "seat": 12},
        {"name_en": "Kong Yuen Ching", "name_zh": "江遠清", "class": "5A1", "seat": 9},
        {"name_en": "Koo Wai", "name_zh": "顧偉", "class": "5B1", "seat": 13}
    ],
    20: [
        {"name_en": "Kwok Ka Leung", "name_zh": "郭家樑", "class": "5B1", "seat": 14},
        {"name_en": "Lai Fat", "name_zh": "黎發", "class": "5B1", "seat": 15},
        {"name_en": "Lai Chuk Fai", "name_zh": "黎焯輝", "class": "5B", "seat": 12},
        {"name_en": "Lai Ying Kin", "name_zh": "黎應堅", "class": "5A1", "seat": 10}
    ],
    21: [
        {"name_en": "Lam Ching Fung", "name_zh": "林青鋒", "class": "5A", "seat": 12, "aliases_zh": ["林靑鋒"]},
        {"name_en": "Lam Man Pan", "name_zh": "林文彬", "class": "5A", "seat": 14, "aliases_zh": ["林交彬"]},
        {"name_en": "Lam Hang Fung", "name_zh": "林桁峯", "class": "5A", "seat": 13},
        {"name_en": "Lam Puy Chung, Dominic", "name_zh": "林培中", "class": "5B", "seat": 14}
    ],
    22: [
        {"name_en": "Lau Chiu Kit", "name_zh": "劉超傑", "class": "5A1", "seat": 12},
        {"name_en": "Lam Sai Ming, Stephen", "name_zh": "林世明", "class": "5A1", "seat": 11},
        {"name_en": "Lam Wai Nang", "name_zh": "林偉能", "class": "5A", "seat": 15},
        {"name_en": "Lau Kin On", "name_zh": "劉建安", "class": "5A1", "seat": 13}
    ],
    23: [
        {"name_en": "Law Kai Man", "name_zh": "羅啟文", "class": "5A1", "seat": 15},
        {"name_en": "Lau Sik Tim", "name_zh": "劉識添", "class": "5A1", "seat": 14},
        {"name_en": "Law Sin Kin, Edwin", "name_zh": "羅先建", "class": "5A", "seat": 16},
        {"name_en": "Law Pui Lung", "name_zh": "羅培龍", "class": "5B", "seat": 13}
    ],
    24: [
        {"name_en": "Lee Chi", "name_zh": "李智", "class": "5A", "seat": 17},
        {"name_en": "Lee Bing Wah", "name_zh": "李炳華", "class": "5A1", "seat": 16},
        {"name_en": "Lee Chi Keung", "name_zh": "李志強", "class": "5A", "seat": 19, "aliases_zh": ["李志强"]},
        {"name_en": "Lee Hin", "name_zh": "李軒", "class": "5A", "seat": 18}
    ],
    25: [
        {"name_en": "Lee Ka Kit, Tony", "name_zh": "李家傑", "class": "5B", "seat": 15},
        {"name_en": "Lee Yok Shiu, Frederick", "name_zh": "李煜紹", "class": "5A1", "seat": 17},
        {"name_en": "Lee Man Yan", "name_zh": "李文恩", "class": "5B", "seat": 16},
        {"name_en": "Lee Tung Hoi", "name_zh": "李東海", "class": "5B", "seat": 17}
    ],
    26: [
        {"name_en": "Leung Kit Yin", "name_zh": "梁傑賢", "class": "5B1", "seat": 17},
        {"name_en": "Leung Wing Fung", "name_zh": "梁永峯", "class": "5A1", "seat": 18},
        {"name_en": "Lau Tak Yuen", "name_zh": "劉德源", "class": "5B1", "seat": 16},
        {"name_en": "Leung Wai Shing", "name_zh": "梁威成", "class": "5B1", "seat": 18}
    ],
    27: [
        {"name_en": "Li Yuk Ming", "name_zh": "李沃明", "class": "5B", "seat": 18, "aliases_en": ["Lee Yuk Ming"]},
        {"name_en": "Li Ho Ming", "name_zh": "李浩明", "class": "5B1", "seat": 19, "aliases_en": ["Lee Ho Ming"]},
        {"name_en": "Li Man Wah", "name_zh": "李文華", "class": "5A1", "seat": 19, "aliases_en": ["Lee Man Wah"]},
        {"name_en": "Li Yat Kwong", "name_zh": "李日光", "class": "5B1", "seat": 20, "aliases_en": ["Lee Yat Kwong"]}
    ],
    28: [
        {"name_en": "Lui Siu Seck", "name_zh": "呂少碩", "class": "5A", "seat": 20},
        {"name_en": "Ling Ann Sau", "name_zh": "凌安壽", "class": "5B1", "seat": 21},
        {"name_en": "Lo Chi Shun, James", "name_zh": "盧志信", "class": "5A1", "seat": 20},
        {"name_en": "Lui Tai Lok", "name_zh": "呂大樂", "class": "5B", "seat": 19}
    ],
    29: [
        {"name_en": "Ma Chun Hon", "name_zh": "馬鎮漢", "class": "5B1", "seat": 23},
        {"name_en": "Luk Hoi Tak", "name_zh": "陸海德", "class": "5B1", "seat": 22},
        {"name_en": "Mak Chee Fai", "name_zh": "麥志輝", "class": "5A1", "seat": 21},
        {"name_en": "Ma Kin Chung", "name_zh": "馬健忠", "class": "5B1", "seat": 24}
    ],
    30: [
        {"name_en": "Man Po Sheung", "name_zh": "文寶常", "class": "5B", "seat": 20},
        {"name_en": "Ng Chun Hung", "name_zh": "吳俊雄", "class": "5B", "seat": 21},
        {"name_en": "Mok Hing Yim", "name_zh": "莫慶炎", "class": "5A1", "seat": 22},
        {"name_en": "Ng Lai Shun", "name_zh": "吳禮信", "class": "5B1", "seat": 25}
    ],
    31: [
        {"name_en": "Ng Pak Kan", "name_zh": "吳栢芹", "class": "5B", "seat": 22, "aliases_zh": ["吳柏芹"]},
        {"name_en": "Ng Siu Fai", "name_zh": "吳少輝", "class": "5B1", "seat": 26},
        {"name_en": "Ngai Tak Ping", "name_zh": "魏德平", "class": "5A1", "seat": 23},
        {"name_en": "Ng Pak Shing, Simon", "name_zh": "吳百誠", "class": "5B", "seat": 23, "aliases_zh": ["伍百成", "伍百誠"]}
    ],
    32: [
        {"name_en": "Ngan Sau Fung", "name_zh": "顏秀峯", "class": "5A", "seat": 21},
        {"name_en": "Pang Chi Yan, Peter", "name_zh": "彭志仁", "class": "5A", "seat": 23},
        {"name_en": "Pang Che Hong, Tony", "name_zh": "彭賜康", "class": "5A", "seat": 22},
        {"name_en": "Poon Fat Tik", "name_zh": "潘發迪", "class": "5B1", "seat": 27}
    ],
    33: [
        {"name_en": "Poon Sek Kwong", "name_zh": "潘錫光", "class": "5A", "seat": 24, "aliases_en": ["Poon Sek Kong", "Poon Sik Kwong"]},
        {"name_en": "Pun Wai Sum", "name_zh": "潘偉森", "class": "5B1", "seat": 28, "aliases_en": ["Poon Wai Sum"]},
        {"name_en": "Siu Chi Chun", "name_zh": "蕭其雋", "class": "5B1", "seat": 30, "aliases_en": ["Siu Ki Chun"]},
        {"name_en": "See Ching Fai", "name_zh": "施清輝", "class": "5B1", "seat": 29, "aliases_en": ["Sze Ching Fai"]}
    ],
    34: [
        {"name_en": "Tam Kwai Ki, Thomas", "name_zh": "譚瑰琦", "class": "5A", "seat": 26},
        {"name_en": "So Siu Fai", "name_zh": "蘇紹輝", "class": "5B1", "seat": 31},
        {"name_en": "Tam Hon Wing", "name_zh": "譚漢榮", "class": "5A", "seat": 25},
        {"name_en": "Szeto Ping Fai", "name_zh": "司徒炳輝", "class": "5A1", "seat": 24}
    ],
    35: [
        {"name_en": "Tam Laying", "name_zh": "譚乃英", "class": "5A", "seat": 27},
        {"name_en": "Tang Hee Wah", "name_zh": "鄧喜華", "class": "5A", "seat": 28},
        {"name_en": "Tan Chuen Yan, Paul", "name_zh": "譚傳仁", "class": "5B", "seat": 24, "aliases_en": ["T'an Chuen Yan, Paul"], "aliases_zh": ["陳傳仁"]},
        {"name_en": "Tang Kwong Leung", "name_zh": "鄧光亮", "class": "5A", "seat": 29, "aliases_zh": ["鄧廣亮"]}
    ],
    36: [
        {"name_en": "Tong Ping Fai, Vincent", "name_zh": "唐炳輝", "class": "5B", "seat": 25},
        {"name_en": "Tse Yue Kit", "name_zh": "謝以潔", "class": "5B", "seat": 27},
        {"name_en": "Tsang Chung Nin, Tony", "name_zh": "曾松年", "class": "5B", "seat": 26},
        {"name_en": "Tsui Gar Tak", "name_zh": "崔家德", "class": "5B1", "seat": 32, "aliases_zh": ["徐嘉德"]}
    ],
    37: [
        {"name_en": "Wong Chak Kong", "name_zh": "黃澤剛", "class": "5A", "seat": 30},
        {"name_en": "Tung Choi Hing", "name_zh": "董財興", "class": "5B1", "seat": 33},
        {"name_en": "Wong Chun Leong", "name_zh": "黃振亮", "class": "5A1", "seat": 26},
        {"name_en": "Wai Gilbert", "name_zh": "韋嘉華", "class": "5A1", "seat": 25, "aliases_zh": ["韋業嘉"]}
    ],
    38: [
        {"name_en": "Wong Hoi, Henry", "name_zh": "王愷", "class": "5B", "seat": 28},
        {"name_en": "Wong Kwan Pui", "name_zh": "黃均培", "class": "5B", "seat": 30},
        {"name_en": "Wong Kwok Fung", "name_zh": "黃國風", "class": "5A1", "seat": 27, "aliases_zh": ["王國風"]},
        {"name_en": "Wong Kam Fai", "name_zh": "黃錦輝", "class": "5B", "seat": 29}
    ],
    39: [
        {"name_en": "Wong Lap Chun", "name_zh": "黃立俊", "class": "5B", "seat": 31},
        {"name_en": "Wong Wai Ming", "name_zh": "黃偉明", "class": "5A1", "seat": 28},
        {"name_en": "Wong Tak Yee", "name_zh": "黃德輿", "class": "5B1", "seat": 34, "aliases_zh": ["王德義"]},
        {"name_en": "Wong Wai Yeung", "name_zh": "黃偉楊", "class": "5A1", "seat": 29}
    ],
    40: [
        {"name_en": "Wu Lai Chi", "name_zh": "胡禮墀", "class": "5A", "seat": 31},
        {"name_en": "Wu Kwok Kee", "name_zh": "胡國基", "class": "5A1", "seat": 31},
        {"name_en": "Wu Wai Tsuen, Wilson", "name_zh": "胡偉全", "class": "5B", "seat": 33, "aliases_zh": ["伍威全"]},
        {"name_en": "Wong Yiu Tan, Michael", "name_zh": "黃耀丹", "class": "5B", "seat": 32, "aliases_zh": ["黃耀騰"]}
    ],
    41: [
        {"name_en": "Wu Ying Kin", "name_zh": "胡應堅", "class": "5A1", "seat": 32},
        {"name_en": "Wut Kai Hong", "name_zh": "屈啓康", "class": "5B", "seat": 34, "aliases_en": ["Wat Kai Hong"], "aliases_zh": ["屈啟康"]},
        {"name_en": "Yau Kai Hong, Jot", "name_zh": "丘啟康", "class": "5B", "seat": 35, "aliases_zh": ["邱繼康"]},
        {"name_en": "Wu Hon Cheong", "name_zh": "胡漢昌", "class": "5A1", "seat": 30}
    ],
    42: [
        {"name_en": "Yim Pak Keung", "name_zh": "嚴栢强", "class": "5A", "seat": 33, "aliases_zh": ["嚴栢強"]},
        {"name_en": "Yeung Chun Kwok", "name_zh": "楊俊國", "class": "5A", "seat": 32},
        {"name_en": "Yim Ping Chuen, Anthony", "name_zh": "嚴炳泉", "class": "5A", "seat": 34, "aliases_zh": ["嚴秉泉"]},
        {"name_en": "Yeung Tsi Yan", "name_zh": "楊子仁", "class": "5A1", "seat": 33}
    ],
    43: [
        {"name_en": "Yip Yau Jim", "name_zh": "葉佑沾", "class": "5A", "seat": 35, "aliases_en": ["Yip Yuu Jim"]},
        {"name_en": "Yip Tak Chun", "name_zh": "葉德俊", "class": "5A1", "seat": 34},
        {"name_en": "Yu Chi Chak", "name_zh": "余志澤", "class": "5A", "seat": 36, "aliases_zh": ["喻志澤"]},
        {"name_en": "Yiu Hi Cheong", "name_zh": "姚喜昌", "class": "5B", "seat": 36, "aliases_zh": ["姚起昌"]}
    ],
    44: [
        {"name_en": "Yu Hon Kong", "name_zh": "余漢光", "class": "5A", "seat": 37},
        {"name_en": "Yu Chi Sum", "name_zh": "余志深", "class": "5A1", "seat": 35},
        {"name_en": "Yu Wai Kun", "name_zh": "余偉根", "class": "5A", "seat": 38, "aliases_zh": ["俞慧根"]},
        {"name_en": "Yu Ho Ming", "name_zh": "余浩鳴", "class": "5B1", "seat": 35, "aliases_zh": ["余浩明"]}
    ],
    45: [
        {"name_en": "Yuen Chi Hung", "name_zh": "袁志雄", "class": "5A1", "seat": 36},
        {"name_en": "Yung Kwok Hung", "name_zh": "翁國雄", "class": "5A1", "seat": 38},
        {"name_en": "Yuen Wai Kong", "name_zh": "袁偉光", "class": "5A1", "seat": 37, "aliases_zh": ["袁惠光"]},
        {"name_en": "Yung Yip Shing", "name_zh": "翁業成", "class": "5B1", "seat": 36, "aliases_zh": ["容業成"]}
    ]
}

def main():
    entities_dir = "okf_output/entities/F5_Alumni"
    os.makedirs(entities_dir, exist_ok=True)
    
    bilingual_dict = {
        "en_to_zh": {},
        "zh_to_en": {}
    }

    total_injected = 0
    pages_updated = 0

    for page_num, students in PAGE_STUDENTS.items():
        json_path = os.path.join(entities_dir, f"page_{page_num:03d}.json")
        
        # Load existing entity JSON if present
        page_entity = {}
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    page_entity = json.load(f)
                except Exception:
                    page_entity = {}
        
        page_entity["year"] = "1975_F5_Alumni"
        page_entity["page"] = page_num
        page_entity["section_type"] = "Graduation Roster / Alumni Profile" if page_num >= 9 else "Class Association Committee"
        page_entity["full_page_photo"] = f"F5_Alumni_page_{page_num:03d}_full.webp"
        
        # Prepare structured students array
        student_entities = []
        verified_names = []
        
        for st in students:
            en_name = st["name_en"]
            zh_name = st["name_zh"]
            cls_name = f"Form {st['class']} (1974-75)"
            
            student_obj = {
                "english_name": en_name,
                "chinese_name": zh_name,
                "class_designation": cls_name,
                "seat_number": st.get("seat"),
                "is_prefect": False,
                "is_graduate": True,
                "role": st.get("role")
            }
            if st.get("aliases_en"):
                student_obj["aliases_en"] = st["aliases_en"]
            if st.get("aliases_zh"):
                student_obj["aliases_zh"] = st["aliases_zh"]
                
            student_entities.append(student_obj)
            
            # Verified name record
            v_record = {
                "year": "1975_F5_Alumni",
                "page": page_num,
                "english_name": en_name,
                "chinese_name": zh_name,
                "class": f"Form {st['class']}"
            }
            verified_names.append(v_record)
            
            # Also register aliases into verified_names for search
            for a_en in st.get("aliases_en", []):
                verified_names.append({
                    "year": "1975_F5_Alumni",
                    "page": page_num,
                    "english_name": a_en,
                    "chinese_name": zh_name,
                    "class": f"Form {st['class']}"
                })
            for a_zh in st.get("aliases_zh", []):
                verified_names.append({
                    "year": "1975_F5_Alumni",
                    "page": page_num,
                    "english_name": en_name,
                    "chinese_name": a_zh,
                    "class": f"Form {st['class']}"
                })

            # Add to bilingual dictionary
            en_keys = [en_name.lower()] + [a.lower() for a in st.get("aliases_en", [])]
            zh_keys = [zh_name] + st.get("aliases_zh", [])
            
            for ek in en_keys:
                if ek not in bilingual_dict["en_to_zh"]:
                    bilingual_dict["en_to_zh"][ek] = []
                for zk in zh_keys:
                    if zk not in bilingual_dict["en_to_zh"][ek]:
                        bilingual_dict["en_to_zh"][ek].append(zk)

            for zk in zh_keys:
                if zk not in bilingual_dict["zh_to_en"]:
                    bilingual_dict["zh_to_en"][zk] = []
                for ek_orig in [en_name] + st.get("aliases_en", []):
                    if ek_orig not in bilingual_dict["zh_to_en"][zk]:
                        bilingual_dict["zh_to_en"][zk].append(ek_orig)

            total_injected += 1

        page_entity["students"] = student_entities
        page_entity["verified_names"] = verified_names
        
        # Summary
        summary_names = " • ".join(f"{s['name_en']} ({s['name_zh']})" for s in students)
        page_entity["summary"] = f"Form 5 Alumni Profiles: {summary_names}"
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(page_entity, f, ensure_ascii=False, indent=2)
            
        pages_updated += 1

    # Save bilingual dictionary
    with open("okf_bilingual_dictionary.json", "w", encoding="utf-8") as f:
        json.dump(bilingual_dict, f, ensure_ascii=False, indent=2)

    print(f"Successfully updated {pages_updated} F5 Alumni entity JSON files.")
    print(f"Injected {total_injected} bilingual student records.")
    print(f"Generated okf_bilingual_dictionary.json with {len(bilingual_dict['en_to_zh'])} English terms and {len(bilingual_dict['zh_to_en'])} Chinese terms.")

if __name__ == "__main__":
    main()
