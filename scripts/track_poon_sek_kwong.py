import json

def get_classmates():
    with open('okf_search_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Classmates timeline by year and form
    timeline = {
        "1972 (Form 2A1)": {"form": "Form 2A1", "page": 32, "year": 1972, "classmates": []},
        "1974 (Form 4A1)": {"form": "Form 4A1", "page": 91, "year": 1974, "classmates": []},
        "1975 (Form 5A)": {"form": "Form 5A", "page": 86, "year": 1975, "classmates": []},
        "1976 (Lower 6 Science - L6S)": {"form": "Lower 6 Science (L6S)", "page": 107, "year": 1976, "classmates": []},
        "1977 (Upper 6 Science - U6S)": {"form": "Upper 6 Science (U6S)", "page": 127, "year": 1977, "classmates": []}
    }

    # Extract Page 107 of 1976 (L6S) verified roster
    for item in data:
        if item.get("year") == 1976 and item.get("page") == 107:
            for v in item.get("verified_names", []):
                if "poon" not in v["english_name"].lower():
                    timeline["1976 (Lower 6 Science - L6S)"]["classmates"].append(f"{v['english_name']} ({v['chinese_name']})")

        if item.get("year") == 1977 and item.get("page") == 127:
            for v in item.get("verified_names", []):
                if "poon" not in v["english_name"].lower():
                    timeline["1977 (Upper 6 Science - U6S)"]["classmates"].append(f"{v['english_name']} ({v['chinese_name']})")

    print(json.dumps(timeline, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    get_classmates()
