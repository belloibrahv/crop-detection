# AgroScan NG — Model Status & Improvement Plan

Last updated: July 2026

---

## Current State

### Model v1 — what was trained

Training was cut off at **3 epochs of phase 1** (phase 2 never ran).  
Best val accuracy recorded: **80.9%** on 14 classes.  
Release gate (NFR-2): **93%** weighted accuracy.

### Classes in deployed model (14 / 29 target)

| Crop | Available | Required | Gap |
|------|-----------|----------|-----|
| Tomato | 8 ✅ | 8 | — |
| Maize | 4 | 6 | Streak Virus, Fall Armyworm |
| Rice | 1 | 5 | Bacterial Blight, Brown Spot, Sheath Blight, Healthy |
| Cassava | 1 (Healthy only) | 5 | 4 disease classes |
| Yam | 0 | 5 | All — no public dataset exists |

### Root cause of low accuracy

1. **Training was not completed** — only 3 of 25 planned phase-1 epochs ran.
2. **Severe class imbalance** — Tomato Yellow Leaf Curl had 10,714 images vs Cassava Healthy at 302 (35:1 ratio). Now capped at 8:1 in training splits.
3. **Missing data** — Cassava disease images and several Rice classes were not downloaded during initial setup.

---

## Improvements Made (this sprint)

| # | Change | File(s) |
|---|--------|---------|
| 1 | Rebuilt balanced splits (8:1 max imbalance cap) | `data/splits/train.csv` |
| 2 | Balanced CSVs capping Tomato at 1,000 per class | `data/splits/train_balanced.csv` |
| 3 | Imported 3,224 Rice images (Bacterial Blight, Brown Spot) | `data/raw/Rice/` |
| 4 | Added `download_missing.py` — downloads Cassava + Rice from Kaggle | `ml/download_missing.py` |
| 5 | Upgraded `train.py` — EfficientNetB0 option, cosine LR decay, cutout augmentation | `ml/train.py` |
| 6 | Added `train_colab.py` — self-contained GPU training script | `ml/train_colab.py` |
| 7 | Fixed inference Dockerfile to use `serve.py` (real model) | `inference/Dockerfile` |
| 8 | Rewrote `serve_simple.py` — real class names, startup warning, correct paths | `inference/serve_simple.py` |
| 9 | Fixed low-confidence threshold from 60% → 30% | `api/app/routes/diagnose.py` |
| 10 | Fixed `Farmer` missing import in admin routes | `api/app/routes/admin.py` |

---

## What Still Needs To Happen

### Immediate (required for 88%+ accuracy)

1. **Run `download_missing.py`** to fetch Cassava (5 classes, ~21,000 images) and extra Rice classes from Kaggle. Requires `~/.kaggle/kaggle.json`.

   ```bash
   ml/.venv/bin/python ml/download_missing.py
   ```

2. **Rebuild splits** after download:

   ```bash
   ml/.venv/bin/python ml/rebuild_splits.py
   ```

3. **Run full training on a GPU** — do NOT train on CPU (would take days):

   ```bash
   # Google Colab T4 GPU (free) — see ml/train_colab.py for full setup guide
   python ml/train_colab.py --arch efficientnetb0 --mixed-precision
   ```

4. **Copy trained model files** to `inference/models/v1/`:
   - `best_phase2.keras`
   - `class_indices.json`

5. **Run evaluate.py** to confirm the 93% gate before deploying.

### Short-term (4–8 weeks)

- Collect **Yam disease images** locally (50–100 per class minimum):
  - Yam Anthracnose, Yam Mosaic Virus, Yam Dry Rot, Yam Leaf Spot, Yam Healthy
  - Locations: Ogun State farms, partner with TASUED Agriculture Department
  - Collection guidelines: natural daylight, single leaf, 512×512px minimum

- Add **Maize Streak Virus** and **Fall Armyworm** data from the CCMT Kaggle mirror.

### Long-term (next quarter)

- Train full 29-class model (all 5 crops including Yam)
- Target: ≥ 93% weighted accuracy (NFR-2)
- Remove model limitation warning from frontend
- Deploy `v2` model with EfficientNetB0

---

## Expected Accuracy After Each Stage

| Stage | Classes | Expected Val Acc |
|-------|---------|-----------------|
| Current (3 epochs, phase 1 only) | 14 | ~81% |
| Full training on current 14-class data | 14 | **88–91%** |
| After Cassava + Rice data added | 18–19 | **87–91%** |
| After Yam field collection | 29 | **90–93%** |
| EfficientNetB0 + all data | 29 | **92–95%** |

---

## Yam Data Collection Guidelines

Target classes: Anthracnose, Mosaic Virus, Dry Rot, Leaf Spot, Healthy

- Minimum: 50 real images per class (target: 100+)
- Image quality: ≥ 512×512 px, natural daylight, no heavy shadows
- Subject: single leaf, disease symptoms clearly visible
- Background: plain or blurred preferred
- Format: JPG or PNG
- Partner organisations: IITA (Ibadan), NRCRI (Umudike, Abia State)
