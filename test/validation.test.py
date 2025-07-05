import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.validation import validate_config

IN_FILE = Path(__file__).resolve().parent / "parses.test.result.json"
OUT_FILE = Path(__file__).resolve().parent / "validation.test.result.json"

def main():
    with open(IN_FILE, encoding="utf-8") as f:
        data = json.load(f)
    results = []
    for item in data:
        parsed = item.get("parsed")
        if not parsed:
            results.append({"input": item.get("input"), "valid": False, "error": "No parsed data"})
            continue
        valid, error = validate_config(parsed)
        results.append({
            "input": item.get("input"),
            "valid": valid,
            "error": error
        })
    with open(OUT_FILE, "w", encoding="utf-8") as outf:
        json.dump(results, outf, ensure_ascii=False, indent=2)
    print(f"Validation results written to {OUT_FILE}")

if __name__ == "__main__":
    main()
