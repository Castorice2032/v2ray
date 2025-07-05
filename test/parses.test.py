

import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from parsers import parse_link

TEST_FILE = Path(__file__).resolve().parent.parent / "data/input/test_links.txt"
OUT_FILE = Path(__file__).resolve().parent / "parses.test.result.json"

def main():
    with open(TEST_FILE, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    results = []
    for line in lines:
        parsed = parse_link(line)
        results.append({
            "input": line,
            "parsed": parsed
        })
    with open(OUT_FILE, "w", encoding="utf-8") as outf:
        json.dump(results, outf, ensure_ascii=False, indent=2)
    print(f"Test results written to {OUT_FILE}")

if __name__ == "__main__":
    main()
