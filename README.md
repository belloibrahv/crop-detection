# AgroScan NG — Crop Disease Detection

A web-based AI crop disease detection system for smallholder farmers in Nigeria. Built with React, Flask, and TensorFlow/Keras.

## Current Model Status

| Crop | Classes | Status |
|------|---------|--------|
| Tomato | 8 | ✅ Full data |
| Maize | 4 | ✅ Full data |
| Rice | 1–5 | 🔄 Expanding (download_missing.py) |
| Cassava | 1–5 | 🔄 Expanding (download_missing.py) |
| Yam | 0 | ❌ Requires field collection |

Phase 1 training peaked at **80.9% val accuracy** on 14 classes after 3 epochs. A full run with the improved pipeline is expected to reach **88–93%**.

---

## Project Structure

```
crop-detection/
├── frontend/          # React + Vite PWA (TypeScript)
├── api/               # Flask REST API + PostgreSQL
├── inference/         # FastAPI model server (TF/Keras)
│   ├── serve.py       # Production: loads best_phase2.keras
│   └── serve_simple.py  # Dev mock: no TF needed
├── ml/                # Training & data pipeline
│   ├── train.py         # Full two-phase training (MobileNetV2 or EfficientNetB0)
│   ├── train_colab.py   # Ready-to-run on Colab/Kaggle GPU
│   ├── download_missing.py  # Downloads Cassava + Rice datasets via Kaggle
│   ├── rebuild_splits.py    # Rebuilds stratified 70/15/15 splits
│   ├── balance_dataset.py   # Caps dominant classes at 1,000
│   └── evaluate.py          # 93% accuracy release gate
├── data/
│   ├── raw/           # Raw images per class (Crop/Disease/)
│   └── splits/        # train.csv, val.csv, test.csv + balanced variants
├── docker-compose.yml
└── MODEL_LIMITATIONS.md
```

---

## Quick Start (Local Development)

### Run the full stack with Docker

```bash
docker-compose up --build
```

Then seed the database:

```bash
docker-compose exec api python seed.py
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:5000 |
| Inference (mock) | http://localhost:8501 |

> The inference container uses the real `serve.py`. If `models/v1/best_phase2.keras`
> is not present, `/predict` returns 503. Run `serve_simple.py` locally to bypass
> this during development.

### Run inference mock locally (no Docker, no TF)

```bash
cd inference
pip install fastapi uvicorn pillow
uvicorn serve_simple:app --host 0.0.0.0 --port 8501 --reload
```

---

## Training the Model

### Step 1 — Get the data

```bash
# Download Cassava + Rice datasets from Kaggle (requires ~/.kaggle/kaggle.json)
ml/.venv/bin/python ml/download_missing.py

# Rebuild balanced splits
ml/.venv/bin/python ml/rebuild_splits.py
```

### Step 2 — Train (local CPU, slow)

```bash
ml/.venv/bin/python ml/train.py \
  --train-csv data/splits/train.csv \
  --val-csv   data/splits/val.csv   \
  --output    inference/models/v1
```

### Step 2 — Train (Colab/Kaggle GPU, recommended)

1. Go to [colab.research.google.com](https://colab.research.google.com)
2. Runtime → Change runtime type → **T4 GPU**
3. Upload the repo and run:

```python
# In a Colab cell:
!python ml/train_colab.py \
  --arch efficientnetb0 \
  --output inference/models/v1 \
  --mixed-precision
```

4. Download `inference/models/v1/best_phase2.keras` + `class_indices.json`

### Step 3 — Evaluate & promote

```bash
ml/.venv/bin/python ml/evaluate.py \
  --model-dir  inference/models/v1 \
  --test-csv   data/splits/test.csv \
  --class-indices inference/models/v1/class_indices.json
```

Exit 0 = passes 93% gate → ready for production.

### Architecture options

| Flag | Architecture | Val acc (expected) | Size |
|------|-------------|-------------------|------|
| `--arch mobilenetv2` | MobileNetV2 (default) | 85–90% | 14 MB |
| `--arch efficientnetb0` | EfficientNetB0 | 88–93% | 20 MB |

---

## Deployment (Render)

1. Push to GitHub
2. Create three Web Services on Render:
   - `agroscan-inference` — Docker context `./inference`
   - `agroscan-api` — Docker context `./api`
   - `agroscan-frontend` — Docker context `./frontend` (or Static Site)
3. Create a PostgreSQL database on Render
4. Set environment variables (see `RENDER_ENV_VARS.md`):
   - API: `DATABASE_URL`, `INFERENCE_URL`, `JWT_SECRET`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Query, PWA |
| Backend API | Flask 3, SQLAlchemy, PostgreSQL, Flask-Migrate |
| Inference | FastAPI, TensorFlow 2.15, Keras |
| ML Training | TensorFlow, MobileNetV2 / EfficientNetB0 |
| DevOps | Docker, Docker Compose, GitHub Actions, Render |
