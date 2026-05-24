"""
Bulk test on Kaggle SDNET-style dataset:
  - ALL cracked images from Decks / Pavements / Walls
  - Equal number of non-cracked images (random sample)
Saves overlays + JSON summary.  Run: python batch_test.py
"""
import os, sys, json, random, traceback
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\college_project")
from image_processor import process_image

KAGGLE_DIR    = r"C:\college_project\kaggle_data"
BATCH_DIR     = r"C:\college_project\batch_test_results"
OVERLAYS_DIR  = os.path.join(BATCH_DIR, "overlays")
os.makedirs(OVERLAYS_DIR, exist_ok=True)

random.seed(42)

# ── Collect all cracked images ────────────────────────────────────────────────
cracked_images = []
for surface in ("Decks", "Pavements", "Walls"):
    folder = Path(KAGGLE_DIR) / surface / "Cracked"
    if folder.exists():
        imgs = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
        for p in imgs:
            cracked_images.append({"path": str(p), "surface": surface, "label": "Cracked"})

# ── Equal number of non-cracked images (random sample) ───────────────────────
n_cracked = len(cracked_images)
noncracked_pool = []
for surface in ("Decks", "Pavements", "Walls"):
    folder = Path(KAGGLE_DIR) / surface / "Non-cracked"
    if folder.exists():
        imgs = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
        for p in imgs:
            noncracked_pool.append({"path": str(p), "surface": surface, "label": "Non-cracked"})

noncracked_sample = random.sample(noncracked_pool, min(n_cracked, len(noncracked_pool)))

all_images = cracked_images + noncracked_sample
random.shuffle(all_images)

print("=" * 68)
print("  RCC Crack Risk Assessment — Kaggle Dataset Bulk Test")
print("=" * 68)
print(f"  Cracked images      : {n_cracked}")
print(f"  Non-cracked images  : {len(noncracked_sample)}")
print(f"  Total to process    : {len(all_images)}")
print(f"  Output              : {BATCH_DIR}\n")

# ── Process ───────────────────────────────────────────────────────────────────
results = []
PRINT_EVERY = 200

for idx, item in enumerate(all_images, 1):
    path = item["path"]
    fname = f"overlay_{idx:05d}.jpg"
    over_path = os.path.join(OVERLAYS_DIR, fname)

    try:
        with open(path, "rb") as f:
            raw = f.read()
        res = process_image(raw)

        # Save overlay only for cracked images (saves disk space)
        if item["label"] == "Cracked" and res["crack_detected"]:
            with open(over_path, "wb") as f:
                f.write(res["overlay_bytes"])

        results.append({
            "id": idx,
            "file": os.path.basename(path),
            "surface": item["surface"],
            "true_label": item["label"],
            "detected": res["crack_detected"],
            "crack_type": res["crack_type"],
            "orientation": res["orientation"],
            "width_class": res["width_class"],
            "confidence": res["confidence"],
            "overlay": fname if (item["label"] == "Cracked" and res["crack_detected"]) else None,
        })

        if idx % PRINT_EVERY == 0 or idx == len(all_images):
            tp = sum(1 for r in results if r["true_label"]=="Cracked"    and r["detected"])
            tn = sum(1 for r in results if r["true_label"]=="Non-cracked" and not r["detected"])
            fp = sum(1 for r in results if r["true_label"]=="Non-cracked" and r["detected"])
            fn = sum(1 for r in results if r["true_label"]=="Cracked"    and not r["detected"])
            acc = (tp + tn) / idx * 100
            print(f"  [{idx:>5}/{len(all_images)}]  TP={tp} TN={tn} FP={fp} FN={fn}  Acc={acc:.1f}%")

    except Exception as e:
        results.append({
            "id": idx, "file": os.path.basename(path),
            "surface": item["surface"], "true_label": item["label"],
            "detected": None, "error": str(e),
        })
        if idx % PRINT_EVERY == 0:
            print(f"  [{idx:>5}/{len(all_images)}]  (some errors — continuing)")

# ── Save full results JSON ────────────────────────────────────────────────────
summary_path = os.path.join(BATCH_DIR, "batch_results.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# ── Metrics ───────────────────────────────────────────────────────────────────
processed = [r for r in results if r.get("detected") is not None]
tp = sum(1 for r in processed if r["true_label"]=="Cracked"    and r["detected"])
tn = sum(1 for r in processed if r["true_label"]=="Non-cracked" and not r["detected"])
fp = sum(1 for r in processed if r["true_label"]=="Non-cracked" and r["detected"])
fn = sum(1 for r in processed if r["true_label"]=="Cracked"    and not r["detected"])
errors = len(results) - len(processed)

precision = tp / (tp + fp) if (tp + fp) else 0
recall    = tp / (tp + fn) if (tp + fn) else 0
f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
accuracy  = (tp + tn) / len(processed) * 100 if processed else 0

from collections import Counter
type_dist = Counter(r["crack_type"]  for r in processed if r.get("crack_type") and r["detected"])
ori_dist  = Counter(r["orientation"] for r in processed if r.get("orientation") and r["detected"])
wid_dist  = Counter(r["width_class"] for r in processed if r.get("width_class") and r["detected"])

# Per-surface breakdown
surface_stats = {}
for surface in ("Decks", "Pavements", "Walls"):
    rows = [r for r in processed if r["surface"] == surface]
    s_tp = sum(1 for r in rows if r["true_label"]=="Cracked"    and r["detected"])
    s_tn = sum(1 for r in rows if r["true_label"]=="Non-cracked" and not r["detected"])
    s_fp = sum(1 for r in rows if r["true_label"]=="Non-cracked" and r["detected"])
    s_fn = sum(1 for r in rows if r["true_label"]=="Cracked"    and not r["detected"])
    s_acc = (s_tp + s_tn) / len(rows) * 100 if rows else 0
    surface_stats[surface] = {"tp": s_tp, "tn": s_tn, "fp": s_fp, "fn": s_fn,
                               "acc": round(s_acc, 1), "n": len(rows)}

print("\n" + "=" * 68)
print("  FINAL RESULTS")
print("=" * 68)
print(f"  Total processed    : {len(processed):,}")
print(f"  Errors             : {errors}")
print(f"\n  Confusion Matrix:")
print(f"    True Positive  (cracked, detected)     : {tp:>6,}")
print(f"    True Negative  (no crack, not detected): {tn:>6,}")
print(f"    False Positive (no crack, but detected): {fp:>6,}")
print(f"    False Negative (cracked, not detected) : {fn:>6,}")
print(f"\n  Accuracy   : {accuracy:.1f}%")
print(f"  Precision  : {precision:.1%}")
print(f"  Recall     : {recall:.1%}")
print(f"  F1 Score   : {f1:.1%}")

print(f"\n  Per-Surface Accuracy:")
for s, st in surface_stats.items():
    print(f"    {s:<12}  acc={st['acc']:>5.1f}%  TP={st['tp']} TN={st['tn']} FP={st['fp']} FN={st['fn']}  (n={st['n']})")

print(f"\n  Detected Crack Type Distribution:")
for k, v in type_dist.most_common():
    print(f"    {k:<28}  {v:>5,}")

print(f"\n  Detected Orientation Distribution:")
for k, v in ori_dist.most_common():
    print(f"    {k:<28}  {v:>5,}")

print(f"\n  Detected Width Class Distribution:")
for k, v in wid_dist.most_common():
    print(f"    {k:<28}  {v:>5,}")

print(f"\n  JSON   : {summary_path}")
print(f"  Overlays saved for TP images: {OVERLAYS_DIR}")
print("=" * 68)
