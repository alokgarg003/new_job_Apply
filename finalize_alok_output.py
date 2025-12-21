# finalize_alok_output.py
"""
Helper to rename the latest debug dump to the final CSV if needed.
"""

import os
import glob
from datetime import datetime

def finalize_latest_debug(input_prefix="alok_personalized_debug"):
    pattern = f"{input_prefix}_*.csv"
    files = glob.glob(pattern)
    if not files:
        print("No debug files found.")
        return
    latest = max(files, key=os.path.getctime)
    final_name = "alok_personalized.csv"
    try:
        os.rename(latest, final_name)
        print(f"Renamed {latest} → {final_name}")
    except Exception as e:
        print(f"Failed to rename: {e}")

if __name__ == "__main__":
    finalize_latest_debug()