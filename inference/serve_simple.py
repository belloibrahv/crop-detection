"""
serve_simple.py — Simplified inference service without TensorFlow dependency.
This provides mock predictions based on class indices for testing purposes.
"""
import hashlib
import io
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone

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

app = FastAPI(title='AgroScan NG Inference Service (Simple)')

MODEL_VERSION = os.getenv('MODEL_VERSION', 'v1')
MODEL_PATH    = f'/app/models/{MODEL_VERSION}/best_phase2.keras'
CLASS_INDICES_PATH = f'/app/models/{MODEL_VERSION}/class_indices.json'

class_indices: dict = {}
class_indices_hash = ''


def _load_resources() -> None:
    global class_indices, class_indices_hash

    # Try to load class indices from v1 directory
    class_indices_path = 'models/v1/class_indices.json'
    if os.path.exists(class_indices_path):
        with open(class_indices_path) as f:
            raw = f.read()
        class_indices = json.loads(raw)
        class_indices_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        logger.info('Class indices loaded', extra={'num_classes': len(class_indices), 'hash': class_indices_hash})
    else:
        logger.warning('class_indices.json not found', extra={'path': class_indices_path})
        # Create fallback class indices
        class_indices = {
            str(i): {
                'crop': 'Test Crop',
                'disease': f'Test Disease {i}',
                'is_healthy': i % 5 == 0
            }
            for i in range(29)
        }
        logger.info('Using fallback class indices', extra={'num_classes': len(class_indices)})


_load_resources()


def _generate_mock_predictions() -> list:
    """Generate realistic mock predictions with varying confidence levels."""
    num_classes = len(class_indices)
    if num_classes == 0:
        return []
    
    # Generate random confidence scores that sum to 1
    scores = [random.random() for _ in range(num_classes)]
    total = sum(scores)
    scores = [s / total for s in scores]
    
    # Get top 3 indices
    top_indices = sorted(range(num_classes), key=lambda i: scores[i], reverse=True)[:3]
    
    results = []
    for idx in top_indices:
        info = class_indices.get(str(idx), {
            'crop': 'Unknown',
            'disease': f'Class {idx}',
            'is_healthy': False
        })
        results.append({
            'class_id': int(idx),
            'crop': info.get('crop', ''),
            'disease': info.get('disease', ''),
            'is_healthy': info.get('is_healthy', False),
            'confidence': round(scores[idx] * 100, 2),
        })
    
    return results


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
        'model_loaded': True,
        'model_version': MODEL_VERSION,
        'mode': 'simple_mock',
    }


@app.get('/model-info')
async def model_info():
    return {
        'model_version':      MODEL_VERSION,
        'class_indices_hash': class_indices_hash,
        'num_classes':        len(class_indices),
        'class_indices':      class_indices,
        'mode': 'simple_mock',
    }


@app.post('/predict')
async def predict(file: UploadFile = File(...)):
    t_start = time.perf_counter()
    image_data = await file.read()
    input_hash = hashlib.sha256(image_data).hexdigest()[:16]

    try:
        # Validate image
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        image = image.resize((224, 224), Image.LANCZOS)
        
        # Generate mock predictions
        results = _generate_mock_predictions()

    except Exception as exc:
        logger.error('Prediction failed', extra={'input_hash': input_hash, 'error': str(exc)})
        raise HTTPException(status_code=400, detail=f'Error processing image: {exc}')

    latency_ms = round((time.perf_counter() - t_start) * 1000, 1)

    logger.info(
        'prediction',
        extra={
            'input_hash':  input_hash,
            'top_class':   results[0]['disease'] if results else None,
            'confidence':  results[0]['confidence'] if results else None,
            'latency_ms':  latency_ms,
            'mode': 'simple_mock',
        },
    )

    return {'predictions': results}
