"""
serve_simple.py — Development-only mock inference server (no TensorFlow needed).

PURPOSE
-------
Used during local development when you don't yet have a trained model file.
Returns realistic-looking mock predictions drawn from the real class_indices.json
so the frontend and API behave exactly as they will in production.

PRODUCTION
----------
The production Dockerfile uses serve.py (the real TF model).
Never use this file in production.

STARTUP
-------
From the inference/ directory:
  uvicorn serve_simple:app --host 0.0.0.0 --port 8501 --reload

Or from repo root:
  cd inference && uvicorn serve_simple:app --port 8501 --reload
"""
import hashlib
import io
import json
import logging
import math
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from PIL import Image

# ─── Structured JSON logging ──────────────────────────────────────────────────

class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level':     record.levelname,
            'logger':    record.name,
            'message':   record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith('_'):
                obj[key] = value
        if record.exc_info:
            obj['exc_info'] = self.formatException(record.exc_info)
        import json as _json
        return _json.dumps(obj, default=str)

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_JSONFormatter())
logging.root.handlers = [_handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger('inference.mock')

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title='AgroScan NG Inference Service (MOCK — dev only)',
    description=(
        '⚠️  This is a mock server for local development. '
        'It returns random predictions from real class names — NOT a real model. '
        'For production use serve.py with a trained best_phase2.keras file.'
    ),
)

MODEL_VERSION = os.getenv('MODEL_VERSION', 'v1')

# ─── Class index loading ──────────────────────────────────────────────────────
# Search in multiple locations so it works from both inference/ and repo root.

_SEARCH_PATHS = [
    Path(f'models/{MODEL_VERSION}/class_indices.json'),     # from inference/
    Path(f'inference/models/{MODEL_VERSION}/class_indices.json'),  # from repo root
    Path('models/class_indices.json'),
    Path('inference/models/class_indices.json'),
]

class_indices: dict = {}
class_indices_hash  = ''
_model_file_exists  = False


def _load_resources() -> None:
    global class_indices, class_indices_hash, _model_file_exists

    # Check if a real model file exists (so we can warn the operator)
    model_path_candidates = [
        Path(f'models/{MODEL_VERSION}/best_phase2.keras'),
        Path(f'inference/models/{MODEL_VERSION}/best_phase2.keras'),
    ]
    _model_file_exists = any(p.exists() for p in model_path_candidates)

    # Load class indices
    for path in _SEARCH_PATHS:
        if path.exists():
            raw = path.read_text()
            class_indices.update(json.loads(raw))
            class_indices_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
            logger.info(
                'Class indices loaded',
                extra={'path': str(path), 'num_classes': len(class_indices), 'hash': class_indices_hash},
            )
            break
    else:
        # Hard fallback so the service always starts
        logger.warning(
            'class_indices.json not found in any search path — using built-in fallback',
            extra={'searched': [str(p) for p in _SEARCH_PATHS]},
        )
        fallback = {
            "0":  {"crop": "Cassava", "disease": "Cassava Healthy",                  "is_healthy": True},
            "1":  {"crop": "Maize",   "disease": "Maize Common Rust",                "is_healthy": False},
            "2":  {"crop": "Maize",   "disease": "Maize Healthy",                    "is_healthy": True},
            "3":  {"crop": "Maize",   "disease": "Maize Leaf Blight (Northern)",     "is_healthy": False},
            "4":  {"crop": "Maize",   "disease": "Maize Leaf Spot (Gray)",           "is_healthy": False},
            "5":  {"crop": "Rice",    "disease": "Rice Blast",                       "is_healthy": False},
            "6":  {"crop": "Tomato",  "disease": "Tomato Bacterial Spot",            "is_healthy": False},
            "7":  {"crop": "Tomato",  "disease": "Tomato Early Blight",              "is_healthy": False},
            "8":  {"crop": "Tomato",  "disease": "Tomato Healthy",                   "is_healthy": True},
            "9":  {"crop": "Tomato",  "disease": "Tomato Late Blight",               "is_healthy": False},
            "10": {"crop": "Tomato",  "disease": "Tomato Leaf Mould",                "is_healthy": False},
            "11": {"crop": "Tomato",  "disease": "Tomato Mosaic Virus",              "is_healthy": False},
            "12": {"crop": "Tomato",  "disease": "Tomato Septoria Leaf Spot",        "is_healthy": False},
            "13": {"crop": "Tomato",  "disease": "Tomato Yellow Leaf Curl Virus",    "is_healthy": False},
        }
        class_indices.update(fallback)

    # Print startup banner
    print("\n" + "=" * 62)
    print("  ⚠️  MOCK INFERENCE SERVER — NOT A REAL MODEL")
    print("  Predictions are randomly generated from class names.")
    if _model_file_exists:
        print("  ✓ A trained model file was found. Run serve.py instead.")
        print("    uvicorn serve:app --host 0.0.0.0 --port 8501")
    else:
        print("  ✗ No trained model found. Train one first:")
        print("    ml/.venv/bin/python ml/train.py \\")
        print("      --train-csv data/splits/train.csv \\")
        print("      --val-csv   data/splits/val.csv   \\")
        print("      --output    inference/models/v1")
    print(f"  Classes loaded: {len(class_indices)}")
    print("=" * 62 + "\n")


_load_resources()


# ─── Mock prediction generator ────────────────────────────────────────────────

def _softmax(logits: list[float]) -> list[float]:
    """Numerically stable softmax."""
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    s = sum(exps)
    return [e / s for e in exps]


def _generate_mock_predictions() -> list:
    """
    Generates realistic-looking predictions using a softmax distribution.
    One class wins with a high logit (55-85% confidence) so the result
    looks like a real model output rather than uniform noise.
    """
    n = len(class_indices)
    if n == 0:
        return []

    winner = random.randrange(n)
    logits = [random.uniform(-1.0, 1.0) for _ in range(n)]
    logits[winner] = random.uniform(3.0, 6.0)   # dominant class
    scores = _softmax(logits)

    top3 = sorted(range(n), key=lambda i: scores[i], reverse=True)[:3]

    results = []
    for idx in top3:
        info = class_indices.get(str(idx), {
            'crop': 'Unknown', 'disease': f'Class {idx}', 'is_healthy': False
        })
        results.append({
            'class_id':   int(idx),
            'crop':       info.get('crop', ''),
            'disease':    info.get('disease', ''),
            'is_healthy': info.get('is_healthy', False),
            'confidence': round(scores[idx] * 100, 2),
        })
    return results


# ─── Middleware ───────────────────────────────────────────────────────────────

@app.middleware('http')
async def log_requests(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    latency  = round((time.perf_counter() - start) * 1000, 1)
    logger.info('request', extra={
        'method': request.method, 'path': request.url.path,
        'status': response.status_code, 'latency_ms': latency,
    })
    return response


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get('/healthz')
async def healthz():
    return {
        'status':       'ok',
        'model_loaded': False,       # always False — this is a mock
        'model_version': MODEL_VERSION,
        'mode':         'mock',
        'warning':      'This is a development mock. Deploy a trained model for production.',
        'trained_model_found': _model_file_exists,
    }


@app.get('/model-info')
async def model_info():
    return {
        'model_version':      MODEL_VERSION,
        'class_indices_hash': class_indices_hash,
        'num_classes':        len(class_indices),
        'class_indices':      class_indices,
        'mode':               'mock',
        'warning':            'Mock server — predictions are not from a trained model.',
    }


@app.post('/predict')
async def predict(file: UploadFile = File(...)):
    t_start    = time.perf_counter()
    image_data = await file.read()
    input_hash = hashlib.sha256(image_data).hexdigest()[:16]

    try:
        # Validate the image can be opened (same check as production)
        img = Image.open(io.BytesIO(image_data)).convert('RGB')
        img.resize((224, 224), Image.LANCZOS)   # ensure resize works
    except Exception as exc:
        logger.error('Image validation failed', extra={'input_hash': input_hash, 'error': str(exc)})
        raise HTTPException(status_code=400, detail=f'Invalid image: {exc}')

    results    = _generate_mock_predictions()
    latency_ms = round((time.perf_counter() - t_start) * 1000, 1)

    logger.info('prediction', extra={
        'input_hash': input_hash,
        'top_class':  results[0]['disease'] if results else None,
        'confidence': results[0]['confidence'] if results else None,
        'latency_ms': latency_ms,
        'mode':       'mock',
    })

    return {'predictions': results, 'mode': 'mock'}
