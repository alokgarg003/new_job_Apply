"""Small utility to remove Bayt rows from jobs.csv and write jobs_no_bayt.csv
Run: python scripts/remove_bayt_from_csv.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "jobs.csv"
OUTPUT = ROOT / "jobs_no_bayt.csv"

with INPUT.open("r", encoding="utf-8") as inf, OUTPUT.open("w", encoding="utf-8", newline="") as outf:
    reader = csv.reader(inf)
    writer = csv.writer(outf)
    header = next(reader)
    writer.writerow(header)
    removed = 0
    for row in reader:
        # site column is 2nd column per current CSV layout
        site = row[1].strip().lower() if len(row) > 1 else ""
        if site == "bayt":
            removed += 1
            continue
        writer.writerow(row)

print(f"Wrote {OUTPUT} (removed {removed} Bayt rows)")
