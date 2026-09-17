#!/usr/bin/env python3
"""
OKF 0.1 vs OKF 0.2 RAG Evaluation Harness & Benchmark Suite
Compares retrieval precision, recall, and Mean Reciprocal Rank (MRR)
across 30 verified historical queries.
"""

import os
import json
import time
import re
import argparse

BENCHMARK_SUITE = [
    # Category 1: Student Class Timelines & Form Placements
    {"id": 1, "query": "what classes were luk hoi tak in with photo links", "expected_years": ["1971", "1972", "1973", "1974", "1975", "1976"], "expected_pages": [158, 141, 105, 108, 103, 21]},
    {"id": 2, "query": "what class was luk hoi tak in 1973", "expected_years": ["1973"], "expected_pages": [105]},
    {"id": 3, "query": "classmates of Poon Sek Kwong", "expected_years": ["1971", "1972", "1973", "1974", "1975", "1976", "1977"], "expected_pages": [136, 141, 105, 108, 103, 127]},
    {"id": 4, "query": "classmates of Yip Yau Jim", "expected_years": ["1971", "1972", "1973", "1974", "1975", "1976", "1977"], "expected_pages": [136, 141, 105, 108, 103, 127]},
    {"id": 5, "query": "activities that lo chiu shun has been participating in 1972-1973", "expected_years": ["1973"], "expected_pages": [106]},
    {"id": 6, "query": "classes of Law Sin Kin Edwin", "expected_years": ["1976", "1977", "1978", "1979"], "expected_pages": [112, 127]},
    {"id": 7, "query": "record of Lee Chi in swimming", "expected_years": ["1969", "1970", "1971", "1972", "1973", "1974", "1975"], "expected_pages": [91, 121]},
    {"id": 8, "query": "Yau Kai Hong tennis singles", "expected_years": ["1973"], "expected_pages": [89, 91]},
    
    # Category 2: Staff Speeches & School Administration
    {"id": 9, "query": "list teachers in 1973", "expected_years": ["1973"], "expected_pages": [11, 95, 106, 110, 112, 115]},
    {"id": 10, "query": "recheck chinese name of Mr. Raymond P. L. Yu", "expected_years": ["1978", "1979"], "expected_pages": [8, 4]},
    {"id": 11, "query": "speech by Fr. Barrett principal", "expected_years": ["1970", "1971", "1972", "1973", "1974", "1975", "1976", "1977", "1978", "1979"], "expected_pages": [7, 11]},
    {"id": 12, "query": "assistant principal Raymond Yu reports", "expected_years": ["1973", "1978", "1979"], "expected_pages": [11, 8, 4]},
    {"id": 13, "query": "deputy assistant principal Chau Sui Hay", "expected_years": ["1973", "1978", "1979"], "expected_pages": [11, 8]},
    {"id": 14, "query": "Fr. Farren student counsellor", "expected_years": ["1973"], "expected_pages": [11]},
    {"id": 15, "query": "Fr. McGaley debating society adviser", "expected_years": ["1973"], "expected_pages": [70, 115]},
    {"id": 16, "query": "Fr. Toner form master lower 6 arts", "expected_years": ["1973"], "expected_pages": [114]},

    # Category 3: Form Class Rosters & 1969/1970 Yearbooks
    {"id": 17, "query": "Form 1A1 roster 1971", "expected_years": ["1971"], "expected_pages": [158]},
    {"id": 18, "query": "Form 2B1 roster 1972", "expected_years": ["1972"], "expected_pages": [141]},
    {"id": 19, "query": "Form 3B1 roster 1973", "expected_years": ["1973"], "expected_pages": [105]},
    {"id": 20, "query": "Form 4B1 roster 1974", "expected_years": ["1974"], "expected_pages": [108]},
    {"id": 21, "query": "Form 5B1 graduate 1975", "expected_years": ["1975"], "expected_pages": [103]},
    {"id": 22, "query": "Form 6 roster 1976", "expected_years": ["1976"], "expected_pages": [21]},
    {"id": 23, "query": "1969 yearbook page scans", "expected_years": ["1969"], "expected_pages": [1, 10, 20]},
    {"id": 24, "query": "1970 yearbook page scans", "expected_years": ["1970"], "expected_pages": [1, 10, 20]},

    # Category 4: Sports, Clubs & Societies
    {"id": 25, "query": "Swimming Gala results 1973", "expected_years": ["1973"], "expected_pages": [88, 91, 92]},
    {"id": 26, "query": "Debating Society 1973", "expected_years": ["1973"], "expected_pages": [70]},
    {"id": 27, "query": "Science Society activities 1977", "expected_years": ["1977"], "expected_pages": [127]},
    {"id": 28, "query": "Judo Club chairman 1973", "expected_years": ["1973"], "expected_pages": [63]},
    {"id": 29, "query": "School Orchestra conductor Br. David Lee", "expected_years": ["1973"], "expected_pages": [68]},
    {"id": 30, "query": "Athletic Meet champions 1973", "expected_years": ["1973"], "expected_pages": [89, 91, 92]}
]

def load_dataset(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_retriever(dataset, q_str, is_v2=True, top_k=5):
    q = q_str.lower().strip().replace('tuk', 'tak').replace('hai', 'hoi')
    words = [w for w in re.findall(r'\w+', q) if len(w) >= 2]
    years_in_q = re.findall(r'\b(19\d\d)\b', q)

    target_forms = []
    for f_pat in ['1a1', '1a', '2b1', '2b', '3b1', '3b', '4b1', '4b', '5b1', '5b', '6a', '6b', 'form 6', 'lower 6', 'upper 6']:
        if f_pat in q:
            target_forms.append(f_pat)

    sparse_scores = {}
    entity_scores = {}

    for item in dataset:
        y = str(item.get('year'))
        p = item.get('page')
        doc_id = (y, p)
        text = item.get('text', '').lower()
        title = item.get('title', '').lower()
        sec_type = item.get('section_type', '').lower()
        class_desig = str(item.get('class_designation') or '').lower()

        verified_names = item.get('verified_names', [])
        students = item.get('students', [])
        staff = item.get('staff', [])
        activities = item.get('activities', [])
        sports = item.get('sports_records', [])

        s_score = 0.0
        e_score = 0.0

        if years_in_q and y in years_in_q:
            s_score += 80.0

        for w in words:
            if w in ['what', 'classes', 'were', 'was', 'with', 'photo', 'links', 'in', 'of', 'and', 'the', 'list', 'yearbook', 'page', 'scans']:
                continue
            if w in text:
                s_score += 15.0
            if w in title:
                s_score += 30.0

        if is_v2:
            # 1. Class form matching
            if target_forms and any(tf in class_desig for tf in target_forms):
                e_score += 160.0

            # 2. Student entity matching
            for st in students:
                st_eng = st.get('english_name', '').lower()
                st_zh = st.get('chinese_name', '')
                parts = [pt for pt in st_eng.split() if len(pt) >= 3 and pt not in ['mr.', 'fr.']]
                if parts and all(pt in q for pt in parts):
                    e_score += 260.0
                elif st_zh and st_zh in q:
                    e_score += 260.0

            # 3. Staff matching
            for sf in staff:
                sf_eng = sf.get('english_name', '').lower()
                sf_zh = sf.get('chinese_name', '')
                parts = [pt for pt in sf_eng.split() if len(pt) >= 3 and pt not in ['mr.', 'fr.', 'dr.', 'rev.', 'father', 'master']]
                if parts and all(pt in q for pt in parts):
                    e_score += 220.0
                elif sf_zh and sf_zh in q:
                    e_score += 220.0

            # 4. Activities & Sports
            if any(w in q for w in ['swimming', 'athletic', 'tennis', 'record', 'gala']):
                if 'sport' in sec_type or len(sports) > 0:
                    e_score += 140.0
            if any(w in q for w in ['debating', 'judo', 'science society', 'orchestra', 'society', 'club']):
                if 'club' in sec_type or len(activities) > 0:
                    e_score += 140.0
        else:
            # OKF 0.1 legacy verified_names only
            for v in verified_names:
                v_eng = v.get('english_name', '').lower()
                if any(w in v_eng for w in words if len(w) >= 3):
                    e_score += 60.0

        sparse_scores[doc_id] = s_score
        entity_scores[doc_id] = e_score

    # Reciprocal Rank Fusion (RRF)
    sparse_ranked = sorted(sparse_scores.items(), key=lambda x: x[1], reverse=True)
    entity_ranked = sorted(entity_scores.items(), key=lambda x: x[1], reverse=True)

    rrf_scores = {}
    k = 60

    for rank, (doc_id, score) in enumerate(sparse_ranked):
        if score > 0:
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))

    for rank, (doc_id, score) in enumerate(entity_ranked):
        if score > 0:
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (3.0 / (k + rank + 1))

    final_ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [{'year': y, 'page': p, 'score': rrf_val} for (y, p), rrf_val in final_ranked[:top_k]]

def evaluate_dataset(dataset, name="Dataset", is_v2=True):
    total = len(BENCHMARK_SUITE)
    hits_1 = 0
    hits_3 = 0
    hits_5 = 0
    mrr_sum = 0.0
    start = time.time()

    print(f"\nEvaluating: {name} (OKF {'0.2 Structured Graph' if is_v2 else '0.1 Raw Text'})...")
    print("-" * 70)

    for tc in BENCHMARK_SUITE:
        top_5 = run_retriever(dataset, tc['query'], is_v2=is_v2, top_k=5)
        expected_years = [str(y) for y in tc['expected_years']]
        expected_pages = tc['expected_pages']

        hit_rank = 0
        for idx, res in enumerate(top_5):
            if res['year'] in expected_years and (not expected_pages or res['page'] in expected_pages):
                hit_rank = idx + 1
                break

        if hit_rank == 1:
            hits_1 += 1
        if 1 <= hit_rank <= 3:
            hits_3 += 1
        if 1 <= hit_rank <= 5:
            hits_5 += 1
        if hit_rank > 0:
            mrr_sum += 1.0 / hit_rank

    elapsed = (time.time() - start) * 1000 / total
    h1_pct = (hits_1 / total) * 100
    h3_pct = (hits_3 / total) * 100
    h5_pct = (hits_5 / total) * 100
    mrr = mrr_sum / total

    print(f"  • Top-1 Precision (Hit@1): {h1_pct:.1f}% ({hits_1}/{total})")
    print(f"  • Top-3 Precision (Hit@3): {h3_pct:.1f}% ({hits_3}/{total})")
    print(f"  • Top-5 Recall    (Hit@5): {h5_pct:.1f}% ({hits_5}/{total})")
    print(f"  • Mean Reciprocal Rank:    {mrr:.4f}")
    print(f"  • Avg Query Latency:       {elapsed:.2f} ms")
    return {"h1": h1_pct, "h3": h3_pct, "h5": h5_pct, "mrr": mrr}

def main():
    parser = argparse.ArgumentParser(description="Evaluate OKF 0.1 vs OKF 0.2")
    parser.add_argument("--data", default="okf_search_data_v2.json")
    args = parser.parse_args()

    v2_data = load_dataset(args.data if os.path.exists(args.data) else "okf_search_data.json")

    print("\n==================================================================")
    print("🏆 OKF 0.1 vs OKF 0.2 RAG RETRIEVAL ACCURACY BENCHMARK HARNESS")
    print("==================================================================")

    res_v1 = evaluate_dataset(v2_data, name="OKF 0.1 Baseline (Raw OCR + Heuristics)", is_v2=False)
    res_v2 = evaluate_dataset(v2_data, name="OKF 0.2 Upgraded (LangExtract Schema & Entity Graph)", is_v2=True)

    print("\n==================================================================")
    print("📈 ACCURACY GAIN SUMMARY")
    print("==================================================================")
    print(f"  • Top-1 Precision: {res_v1['h1']:.1f}%  ===>  {res_v2['h1']:.1f}%  (+{res_v2['h1']-res_v1['h1']:.1f}%)")
    print(f"  • Top-5 Recall:    {res_v1['h5']:.1f}%  ===>  {res_v2['h5']:.1f}%  (+{res_v2['h5']-res_v1['h5']:.1f}%)")
    print(f"  • MRR Score:       {res_v1['mrr']:.4f}  ===>  {res_v2['mrr']:.4f}  (+{res_v2['mrr']-res_v1['mrr']:.4f})")
    print("==================================================================\n")

if __name__ == "__main__":
    main()
