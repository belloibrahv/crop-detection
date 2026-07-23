"""
train_colab.py — Google Colab / Kaggle Notebook training script for AgroScan NG.

Run this cell-by-cell in a Colab notebook with GPU runtime (T4 or better).
Copy-paste each section into a separate cell.

=============================================================================
CELL 1 — Mount Drive and install deps
=============================================================================
"""

# ── Cell 1 ────────────────────────────────────────────────────────────────────
CELL_1 = """
from google.colab import drive
drive.mount('/content/drive')

# Install the Kaggle CLI
!pip install -q kaggle tqdm

# Upload your kaggle.json here, or run:
# from google.colab import files; files.upload()
import os, json
os.makedirs('/root/.kaggle', exist_ok=True)
# Paste your token values:
token = {"username": "YOUR_KAGGLE_USERNAME", "key": "YOUR_KAGGLE_KEY"}
with open('/root/.kaggle/kaggle.json', 'w') as f:
    json.dump(token, f)
os.chmod('/root/.kaggle/kaggle.json', 0o600)
print("Kaggle configured ✓")
"""

# ── Cell 2 — Download datasets ────────────────────────────────────────────────
CELL_2 = """
import os, zipfile, shutil
from pathlib import Path

RAW = Path('/content/data/raw')
TMP = Path('/content/data/tmp')

# ── PlantVillage ──────────────────────────────────────────────────────────────
PV = TMP / 'plantvillage'
PV.mkdir(parents=True, exist_ok=True)
if not (PV / 'raw').exists():
    !kaggle datasets download -d abdallahalidev/plantvillage-dataset -p {PV} --unzip

# ── Cassava 2020 ──────────────────────────────────────────────────────────────
CASS = TMP / 'cassava2020'
CASS.mkdir(parents=True, exist_ok=True)
if not (CASS / 'train_images').exists():
    !kaggle competitions download -c cassava-leaf-disease-classification -p {CASS}
    for zf in CASS.glob('*.zip'):
        with zipfile.ZipFile(zf) as z: z.extractall(CASS)
        zf.unlink()

# ── Rice ──────────────────────────────────────────────────────────────────────
RICE = TMP / 'rice'
RICE.mkdir(parents=True, exist_ok=True)
if not any(RICE.rglob('*.jpg')):
    !kaggle datasets download -d minhhuy510/rice-leaf-diseases-dataset -p {RICE} --unzip

print("Downloads complete ✓")
"""

# ── Cell 3 — Import into canonical structure ──────────────────────────────────
CELL_3 = """
import sys
sys.path.insert(0, '/content/drive/MyDrive/agroscan-ng')   # adjust to your Drive path

# Run the download script's importers directly
exec(open('/content/drive/MyDrive/agroscan-ng/ml/download_datasets.py').read())

main(
    output_dir='/content/data/raw',
    skip_kaggle=True,    # already downloaded above
    skip_mendeley=False,
)
"""

# ── Cell 4 — Split ────────────────────────────────────────────────────────────
CELL_4 = """
!python /content/drive/MyDrive/agroscan-ng/ml/data_prep.py \\
    --data-dir  /content/data/raw \\
    --output-dir /content/data/splits
"""

# ── Cell 5 — Train ────────────────────────────────────────────────────────────
CELL_5 = """
!python /content/drive/MyDrive/agroscan-ng/ml/train.py \\
    --train-csv  /content/data/splits/train.csv \\
    --val-csv    /content/data/splits/val.csv \\
    --output     /content/drive/MyDrive/agroscan-ng/inference/models/v1 \\
    --epochs-phase1 20 \\
    --epochs-phase2 20 \\
    --batch-size 32 \\
    --mixed-precision
"""

# ── Cell 6 — Evaluate ─────────────────────────────────────────────────────────
CELL_6 = """
!python /content/drive/MyDrive/agroscan-ng/ml/evaluate.py \\
    --model-dir     /content/drive/MyDrive/agroscan-ng/inference/models/v1 \\
    --test-csv      /content/data/splits/test.csv \\
    --class-indices /content/drive/MyDrive/agroscan-ng/inference/models/v1/class_indices.json
"""

# ── Cell 7 — Copy class_indices to inference root ─────────────────────────────
CELL_7 = """
import shutil
shutil.copy(
    '/content/drive/MyDrive/agroscan-ng/inference/models/v1/class_indices.json',
    '/content/drive/MyDrive/agroscan-ng/inference/models/class_indices.json',
)
print("class_indices.json synced ✓")
print("Model saved to Drive — rebuild inference Docker image to deploy.")
"""

if __name__ == '__main__':
    print("This file is a reference script for Google Colab.")
    print("Copy each CELL_N string into a separate Colab cell and run in order.")
    for i, cell in enumerate([CELL_1, CELL_2, CELL_3, CELL_4, CELL_5, CELL_6, CELL_7], 1):
        print(f"\n{'='*60}")
        print(f"CELL {i}")
        print('='*60)
        print(cell.strip())
