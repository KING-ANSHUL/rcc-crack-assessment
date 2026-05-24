"""
Downloads remaining batch images with very long delays to avoid Wikimedia rate limits.
Run this script and leave it running — it will take ~15 minutes to download all remaining images.

Usage:  python download_remaining.py
"""
import os, sys, time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\college_project")
from image_processor import process_image
import json

BATCH_DIR     = r"C:\college_project\batch_test_results"
ORIGINALS_DIR = os.path.join(BATCH_DIR, "originals")
OVERLAYS_DIR  = os.path.join(BATCH_DIR, "overlays")
os.makedirs(ORIGINALS_DIR, exist_ok=True)
os.makedirs(OVERLAYS_DIR,  exist_ok=True)

HEADERS = {
    "User-Agent": "RCC-CrackAssessmentBatch/1.0 (educational; DTU-Civil-2026)",
    "Accept": "image/jpeg,image/png,image/*;q=0.9",
}
DELAY = 30   # 30 seconds per image — polite to Wikimedia

# Only the remaining images that still need downloading
REMAINING = [
    ("crack_07.jpg", "Zig-zagging crack in masonry wall",
     "https://upload.wikimedia.org/wikipedia/commons/9/9d/Zig-zagging_crack_-_geograph.org.uk_-_2963733.jpg"),
    ("crack_11.jpg", "Concrete crack measurement — engineering photo",
     "https://upload.wikimedia.org/wikipedia/commons/a/a2/23_0065602_Convair_Negative_Image_-_Concrete_crack_measurement_%2854137555361%29.jpg"),
    ("crack_12.jpg", "Wide crack in wall — severe",
     "https://upload.wikimedia.org/wikipedia/commons/4/43/Nasty_crack_-_geograph.org.uk_-_4798756.jpg"),
    ("crack_13.jpg", "Cracks in concrete surface — Hogg Lane",
     "https://upload.wikimedia.org/wikipedia/commons/c/cc/Cracks_in_concrete%2C_Hogg_Lane_-_geograph.org.uk_-_3476983.jpg"),
    ("crack_14.jpg", "Surface cracks in concrete slab",
     "https://upload.wikimedia.org/wikipedia/commons/0/00/Cracks_in_concrete_-_geograph.org.uk_-_706423.jpg"),
    ("crack_15.jpg", "Cracks forming mountainscape pattern",
     "https://upload.wikimedia.org/wikipedia/commons/5/5a/Cracks_in_wall_form_mountainscape.jpg"),
    ("crack_17.jpg", "Crack in masonry wall — Newbridge on Usk",
     "https://upload.wikimedia.org/wikipedia/commons/1/1d/A_crack_in_the_wall%2C_Newbridge_on_Usk_-_geograph.org.uk_-_1253041.jpg"),
    ("crack_18.jpg", "Crack in brick wall — geograph",
     "https://upload.wikimedia.org/wikipedia/commons/1/1f/Crack_in_the_wall_-_geograph.org.uk_-_1643346.jpg"),
    ("crack_19.jpg", "Willowbank building crack — view 1",
     "https://upload.wikimedia.org/wikipedia/commons/e/e3/Willowbank_crack_1.jpg"),
    ("crack_20.jpg", "Willowbank building crack — view 2",
     "https://upload.wikimedia.org/wikipedia/commons/a/a4/Willowbank_crack_2.jpg"),
]

print(f"Downloading {len(REMAINING)} remaining images with {DELAY}s delays...")
print(f"Estimated time: ~{len(REMAINING)*DELAY//60} minutes\n")

done = []
for fname, label, url in REMAINING:
    path = os.path.join(ORIGINALS_DIR, fname)
    if os.path.exists(path) and os.path.getsize(path) > 3000:
        print(f"  [SKIP]  {fname} already exists")
        continue

    print(f"  Downloading {fname}: {label}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        size_kb = len(data) // 1024

        with open(path, "rb") as f:
            raw = f.read()
        res = process_image(raw)
        over_path = os.path.join(OVERLAYS_DIR, fname)
        with open(over_path, "wb") as f:
            f.write(res["overlay_bytes"])
        status = "CRACK" if res["crack_detected"] else "NO_CRACK"
        print(f"    -> {status}  type={res['crack_type']}  conf={res['confidence']:.0%}  ({size_kb}KB)")
        done.append(fname)
    except Exception as e:
        print(f"    -> FAILED: {e}")

    print(f"  Waiting {DELAY}s...")
    time.sleep(DELAY)

print(f"\nDone. Downloaded {len(done)} new images.")
print("Re-run batch_test.py to see the updated full results.")
