import os
import sys
import json
import time
from pathlib import Path
from tqdm import tqdm

TMP_DIR = Path(__file__).resolve().parent.parent / "data/tmp"
INPUT_DIR = Path(__file__).resolve().parent.parent / "data/input"
LOG_DIR = Path(__file__).resolve().parent.parent / "data/logs"
TMP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

all_nodes_path = TMP_DIR / "all_nodes.jsonl"
duplicate_log_path = LOG_DIR / "duplicate_all_nodes.log"

def main():
    seen_raws = set()
    total = 0
    # Count total lines for progress bar (from temp/*.jsonl) and print per-file stats
    TEMP_DIR = Path(__file__).resolve().parent.parent / "data/tmp"
    temp_files = list(TEMP_DIR.glob("*.jsonl"))
    file_counts = {}
    for temp_file in temp_files:
        with open(temp_file, encoding="utf-8") as f:
            count = sum(1 for _ in f)
            file_counts[temp_file.name] = count
            total += count
    print("Node count per file:")
    for fname, count in file_counts.items():
        print(f"  {fname}: {count}")
    print(f"Total nodes in all files: {total}\n")
    valid = 0
    duplicates = 0
    with open(all_nodes_path, "w", encoding="utf-8") as outf, \
         open(duplicate_log_path, "w", encoding="utf-8") as logf:
        with tqdm(total=total, desc="all_nodes", ncols=80, leave=True, dynamic_ncols=True, colour='green') as pbar:
            for temp_file in temp_files:
                with open(temp_file, encoding="utf-8") as f:
                    for idx, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            pbar.update(1)
                            continue
                        try:
                            node = json.loads(line)
                        except Exception:
                            pbar.update(1)
                            continue
                        raw = node.get("raw")
                        # نرمالایز کردن: حذف فاصله و کاراکترهای نامرئی و تبدیل به lowercase
                        if raw is not None:
                            norm_raw = ''.join(c for c in raw.strip().lower() if c.isprintable())
                        else:
                            norm_raw = None
                        if not norm_raw:
                            pbar.update(1)
                            continue
                        if norm_raw in seen_raws:
                            logf.write(json.dumps({"raw": raw, "reason": "duplicate"}, ensure_ascii=False) + "\n")
                            duplicates += 1
                        else:
                            outf.write(json.dumps(node, ensure_ascii=False) + "\n")
                            seen_raws.add(norm_raw)
                            valid += 1
                        pbar.set_postfix(valid=valid, dup=duplicates)
                        pbar.update(1)
    print(f"\n✅ Done: {valid} unique nodes, {duplicates} duplicates.\nAll unique nodes: {all_nodes_path}\nDuplicates log: {duplicate_log_path}")

if __name__ == "__main__":
    main()
