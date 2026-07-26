from flask import Blueprint, request, jsonify, current_app, send_from_directory
from app import db, limiter
from app.models import Farmer, DiagnosisRecord, TreatmentAdvisory
from app.services.image_validator import validate_image, ImageValidationError
from app.services.image_processor import strip_exif, make_thumbnail
import requests
import io
import os

bp = Blueprint('diagnose', __name__)

# 30 diagnoses per hour per IP address (SRS Section 17 security requirement)
_RATE_LIMIT = '30 per hour'

# Supported crops based on current model v2 capabilities (24 classes)
SUPPORTED_CROPS = {'Cassava', 'Maize', 'Rice', 'Tomato'}


@bp.route('/diagnose', methods=['POST'])
@limiter.limit(_RATE_LIMIT)
def diagnose():
    device_id = request.headers.get('X-Device-Id')
    if not device_id:
        return jsonify({'error': 'device_id_missing', 'message': 'X-Device-Id header is required'}), 400

    if 'leaf_image' not in request.files:
        return jsonify({'error': 'image_missing', 'message': 'leaf_image field is required'}), 400

    file = request.files['leaf_image']

    # 1. Validate (type, size, resolution)
    try:
        raw_bytes = validate_image(file)
    except ImageValidationError as exc:
        return jsonify({'error': exc.code, 'message': exc.message}), 422

    crop_hint = request.form.get('crop_hint')
    retrain_consent = request.form.get('retrain_consent') == 'true'

    # Validate crop_hint if provided
    if crop_hint and crop_hint not in SUPPORTED_CROPS:
        return jsonify({
            'error': 'unsupported_crop',
            'message': f'Crop "{crop_hint}" is not currently supported. Supported crops: {", ".join(sorted(SUPPORTED_CROPS))}'
        }), 400

    # 2. Strip EXIF metadata before any storage or forwarding (SRS §17)
    clean_bytes = strip_exif(raw_bytes)

    # 3. Generate thumbnail and get its URL (FR-9)
    try:
        thumbnail_url = make_thumbnail(clean_bytes)
    except Exception as exc:
        current_app.logger.warning(f'Thumbnail generation failed: {exc}')
        thumbnail_url = None

    # 4. Get or create farmer record
    farmer = Farmer.query.filter_by(device_identifier=device_id).first()
    if not farmer:
        farmer = Farmer(device_identifier=device_id)
        db.session.add(farmer)
        db.session.commit()

    # 5. Forward clean image to inference service
    try:
        inference_url = current_app.config['INFERENCE_URL']
        response = requests.post(
            f"{inference_url}/predict",
            files={'file': ('leaf.jpg', io.BytesIO(clean_bytes), 'image/jpeg')},
            timeout=15,
        )
        response.raise_for_status()
        inference_result = response.json()
    except requests.exceptions.Timeout:
        current_app.logger.error('Inference service timed out')
        return jsonify({'error': 'inference_timeout', 'message': 'The analysis took too long. Please try again.'}), 504
    except Exception as exc:
        current_app.logger.error(f'Inference error: {exc}')
        return jsonify({'error': 'inference_error', 'message': 'Failed to process image. Please try again.'}), 500

    predictions = inference_result.get('predictions', [])
    if not predictions:
        return jsonify({'error': 'no_predictions', 'message': 'No predictions returned.'}), 500

    top_prediction = predictions[0]
    low_confidence = top_prediction['confidence'] < 30

    # 6. Fetch treatment advisory (skip for healthy classes)
    advisory = None
    if top_prediction.get('class_id') is not None and not top_prediction.get('is_healthy'):
        advisory = TreatmentAdvisory.query.filter_by(class_id=top_prediction['class_id']).first()

    # 7. Persist diagnosis record
    diagnosis = DiagnosisRecord(
        farmer_id=farmer.farmer_id,
        image_thumbnail_url=thumbnail_url,
        predicted_class_id=top_prediction.get('class_id'),
        confidence_score=top_prediction['confidence'],
        top3_predictions=predictions,
        retrain_consent=retrain_consent,
    )
    db.session.add(diagnosis)
    db.session.commit()

    return jsonify({
        'diagnosis_id': diagnosis.diagnosis_id,
        'results': predictions,
        'thumbnail_url': thumbnail_url,
        'advisory': {
            'recommended_action': advisory.recommended_action,
            'local_treatment_options': advisory.local_treatment_options,
        } if advisory else None,
        'low_confidence': low_confidence,
        'created_at': diagnosis.created_at.isoformat() + 'Z',
    })


# Serve thumbnail images stored on disk
@bp.route('/uploads/thumbnails/<path:filename>')
def serve_thumbnail(filename: str):
    upload_dir = os.getenv('UPLOAD_DIR', '/app/uploads/thumbnails')
    return send_from_directory(upload_dir, filename)
