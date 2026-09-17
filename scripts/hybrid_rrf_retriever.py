import os
import json
import time
import re
from evaluate_rag_harness import BENCHMARK_SUITE

print("=== Evaluating OKF 0.2 Knowledge Graph Hybrid RRF Retriever ===")

def normalize_query(q_str):
    q = q_str.lower().strip()
    q = q.replace('tuk', 'tak').replace('hai', 'hoi')
    return q

def hybrid_rrf_retrieve_v2(q_str, master_data, top_k=5):
    clean_q = normalize_query(q_str)
    words = [w for w in re.findall(r'\w+', clean_q) if len(w) >= 2]
    years_in_q = re.findall(r'\b(19\d\d)\b', clean_q)

    # Detect class designations in query
    target_forms = []
    for f_pattern in ['1a1', '1a', '2b1', '2b', '3b1', '3b', '4b1', '4b', '5b1', '5b', '6a', '6b', 'form 6', 'lower 6', 'upper 6']:
        if f_pattern in clean_q:
            target_forms.append(f_pattern)

    sparse_scores = {}
    entity_scores = {}

    for idx, item in enumerate(master_data):
        y = str(item.get('year'))
        p = item.get('page')
        doc_id = (y, p)
        text = item.get('text', '').lower()
        title = item.get('title', '').lower()
        sec_type = item.get('section_type', '').lower()
        class_desig = str(item.get('class_designation') or '').lower()
        
        students = item.get('students', [])
        staff = item.get('staff', [])
        activities = item.get('activities', [])
        sports = item.get('sports_records', [])
        verified_names = item.get('verified_names', [])

        s_score = 0.0
        e_score = 0.0

        # Year match boost
        if years_in_q and y in years_in_q:
            s_score += 80.0

        # Class Form Match Boost
        if target_forms and any(tf in class_desig for tf in target_forms):
            e_score += 150.0

        # Section Type Boost
        if 'swimming' in clean_q or 'athletic' in clean_q or 'sports' in clean_q or 'tennis' in clean_q:
            if 'sport' in sec_type or any('swimming' in sp.get('event_name', '').lower() for sp in sports):
                e_score += 120.0

        if 'debating' in clean_q or 'judo' in clean_q or 'science society' in clean_q or 'orchestra' in clean_q:
            if 'club' in sec_type or any(act.get('club_name', '').lower() in clean_q for act in activities):
                e_score += 120.0

        if 'teacher' in clean_q or 'principal' in clean_q or 'rector' in clean_q or 'counsellor' in clean_q or 'adviser' in clean_q or 'form master' in clean_q:
            if 'staff' in sec_type or len(staff) > 0:
                e_score += 100.0

        # Word match scoring
        for w in words:
            if w in ['what', 'classes', 'were', 'was', 'with', 'photo', 'links', 'in', 'of', 'and', 'the', 'list', 'yearbook', 'page', 'scans', 'roster', 'activities']:
                continue
            if w in text:
                s_score += 15.0
            if w in title:
                s_score += 30.0

        # Student Name Entity Matching across OKF 0.2 Universal Graph
        for st in students:
            st_eng = st.get('english_name', '').lower()
            st_zh = st.get('chinese_name', '')
            if st_eng and (st_eng in clean_q or any(p in clean_q for p in st_eng.split() if len(p) >= 4)):
                e_score += 180.0
            elif st_zh and st_zh in clean_q:
                e_score += 200.0

        # Staff Matching
        for sf in staff:
            sf_eng = sf.get('english_name', '').lower()
            sf_zh = sf.get('chinese_name', '')
            if sf_eng and any(p in clean_q for p in sf_eng.split() if len(p) >= 3 and p not in ['mr.', 'fr.', 'dr.', 'rev.']):
                e_score += 140.0
            elif sf_zh and sf_zh in clean_q:
                e_score += 160.0

        # Legacy verified_names backup
        for v in verified_names:
            v_eng = v.get('english_name', '').lower()
            v_chi = v.get('chinese_name', '').strip()
            if v_eng and (v_eng in clean_q or any(p in clean_q for p in v_eng.split() if len(p) >= 4)):
                e_score += 150.0
            elif v_chi and v_chi in clean_q:
                e_score += 180.0

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
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (2.5 / (k + rank + 1))

    final_ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [{'year': y, 'page': p, 'score': rrf_val} for (y, p), rrf_val in final_ranked[:top_k]]

def evaluate_retriever():
    with open('okf_search_data_v2.json', 'r', encoding='utf-8') as f:
        master_data = json.load(f)

    total_queries = len(BENCHMARK_SUITE)
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    mrr_sum = 0.0
    start_time = time.time()

    print(f"\nEvaluating Upgraded OKF 0.2 Retriever across {total_queries} Benchmark Questions...")
    print("-" * 75)

    for test_case in BENCHMARK_SUITE:
        q_id = test_case["id"]
        q_str = test_case["query"]
        expected_years = [str(y) for y in test_case["expected_years"]]
        expected_pages = test_case["expected_pages"]

        top_5 = hybrid_rrf_retrieve_v2(q_str, master_data, top_k=5)

        hit_rank = 0
        for idx, res in enumerate(top_5):
            if res['year'] in expected_years and (not expected_pages or res['page'] in expected_pages):
                hit_rank = idx + 1
                break

        if hit_rank == 1:
            hits_at_1 += 1
        if 1 <= hit_rank <= 3:
            hits_at_3 += 1
        if 1 <= hit_rank <= 5:
            hits_at_5 += 1

        if hit_rank > 0:
            mrr_sum += (1.0 / hit_rank)

        status_symbol = "✅" if hit_rank > 0 else "❌"
        print(f"Test #{q_id:02d} [{status_symbol} Hit Rank: {hit_rank if hit_rank > 0 else 'FAIL'}] Query: \"{test_case['query']}\"")

    elapsed = time.time() - start_time
    avg_latency_ms = (elapsed / total_queries) * 1000

    hit_rate_1 = (hits_at_1 / total_queries) * 100
    hit_rate_3 = (hits_at_3 / total_queries) * 100
    hit_rate_5 = (hits_at_5 / total_queries) * 100
    mrr = mrr_sum / total_queries

    print("\n" + "=" * 75)
    print("🚀 UPGRADED OKF 0.2 HYBRID RRF RETRIEVAL BENCHMARK RESULTS")
    print("=" * 75)
    print(f"  • Total Evaluation Test Cases: {total_queries}")
    print(f"  • Hit Rate @ 1 (Top-1 Precision): {hit_rate_1:.2f}% ({hits_at_1}/{total_queries})")
    print(f"  • Hit Rate @ 3 (Top-3 Precision): {hit_rate_3:.2f}% ({hits_at_3}/{total_queries})")
    print(f"  • Hit Rate @ 5 (Top-5 Recall):    {hit_rate_5:.2f}% ({hits_at_5}/{total_queries})")
    print(f"  • Mean Reciprocal Rank (MRR):     {mrr:.4f}")
    print(f"  • Average Retrieval Latency:      {avg_latency_ms:.2f} ms / query")
    print("=" * 75 + "\n")

if __name__ == '__main__':
    evaluate_retriever()
