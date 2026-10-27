import os, csv, sys

sys.stdout.reconfigure(encoding='utf-8')

for fname in os.listdir("special_tournaments"):
    if not fname.endswith(".csv"):
        continue
    fpath = os.path.join("special_tournaments", fname)
    print(f"\n==================== {fname} ====================")
    with open(fpath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        print(f"Total rows: {len(rows)}")
        for i, row in enumerate(rows[:20]):
            non_empty = [f"c{c_idx}:{val.strip()}" for c_idx, val in enumerate(row) if val.strip()]
            if non_empty:
                print(f"R{i}: " + " | ".join(non_empty)[:140])
