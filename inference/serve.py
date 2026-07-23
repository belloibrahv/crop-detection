"""
serve.py — AgroScan NG inference service (FastAPI wrapper around the SavedModel).

Endpoints:
  GET  /healthz      — liveness/readiness probe
  GET  /model-info   — loaded model version + class list hash
  POST /predict      — accepts a multipart image, returns top-3 predictions
"""
import hashlib
import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import tensorflow as tf
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

# ─── Structured JSON logging (NFR-10) ─────────────────────────────────────────

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
logger = logging.getLogger('inference')

# ─── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title='AgroScan NG Inference Service')

MODEL_VERSION = os.getenv('MODEL_VERSION', 'v1')
MODEL_PATH    = f'models/{MODEL_VERSION}/best_phase2.keras'
CLASS_INDICES_PATH = f'models/{MODEL_VERSION}/class_indices.json'

model = None
class_indices: dict = {}
class_indices_hash = ''


def _load_resources() -> None:
    global model, class_indices, class_indices_hash

    if os.path.exists(MODEL_PATH):
        logger.info('Loading SavedModel', extra={'path': MODEL_PATH})
        model = tf.keras.models.load_model(MODEL_PATH)
        logger.info('Model loaded successfully', extra={'model_version': MODEL_VERSION})
    else:
        logger.warning('Model not found — /predict will return 503', extra={'path': MODEL_PATH})

    if os.path.exists(CLASS_INDICES_PATH):
        with open(CLASS_INDICES_PATH) as f:
            raw = f.read()
        class_indices = json.loads(raw)
        class_indices_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        logger.info('Class indices loaded', extra={'num_classes': len(class_indices), 'hash': class_indices_hash})
    else:
        logger.warning('class_indices.json not found', extra={'path': CLASS_INDICES_PATH})


_load_resources()

# ─── Request logging middleware ────────────────────────────────────────────────

@app.middleware('http')
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        'request',
        extra={
            'method':     request.method,
            'path':       request.url.path,
            'status':     response.status_code,
            'latency_ms': latency_ms,
        },
    )
    return response

# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get('/healthz')
async def healthz():
    return {
        'status': 'ok',
        'model_loaded': model is not None,
        'model_version': MODEL_VERSION,
    }


@app.get('/model-info')
async def model_info():
    return {
        'model_version':      MODEL_VERSION,
        'class_indices_hash': class_indices_hash,
        'num_classes':        len(class_indices),
        'class_indices':      class_indices,
    }


@app.post('/predict')
async def predict(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=503, detail='Model not loaded. Check container logs.')

    t_start = time.perf_counter()
    image_data = await file.read()
    input_hash = hashlib.sha256(image_data).hexdigest()[:16]

    try:
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        image = image.resize((224, 224), Image.LANCZOS)
        img_array = tf.keras.preprocessing.image.img_to_array(image)
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
        img_array = np.expand_dims(img_array, axis=0)

        raw_preds = model.predict(img_array, verbose=0)
        top_indices = np.argsort(raw_preds[0])[::-1][:3]

        results = []
        for idx in top_indices:
            info = class_indices.get(str(idx), {})
            results.append({
                'class_id':  int(idx),
                'crop':      info.get('crop', ''),
                'disease':   info.get('disease', ''),
                'is_healthy': info.get('is_healthy', False),
                'confidence': round(float(raw_preds[0][idx]) * 100, 2),
            })

    except Exception as exc:
        logger.error('Prediction failed', extra={'input_hash': input_hash, 'error': str(exc)})
        raise HTTPException(status_code=400, detail=f'Error processing image: {exc}')

    latency_ms = round((time.perf_counter() - t_start) * 1000, 1)

    # FR-21: log every prediction request
    logger.info(
        'prediction',
        extra={
            'input_hash':  input_hash,
            'top_class':   results[0]['disease'] if results else None,
            'confidence':  results[0]['confidence'] if results else None,
            'latency_ms':  latency_ms,
        },
    )

    return {'predictions': results}
