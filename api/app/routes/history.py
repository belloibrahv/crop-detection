from flask import Blueprint, request, jsonify
from app import db
from app.models import Farmer, DiagnosisRecord

bp = Blueprint('history', __name__)


@bp.route('/history', methods=['GET'])
def get_history():
    device_id = request.headers.get('X-Device-Id')
    if not device_id:
        return jsonify({'error': 'X-Device-Id header required'}), 400

    farmer = Farmer.query.filter_by(device_identifier=device_id).first()
    if not farmer:
        return jsonify([])

    diagnoses = DiagnosisRecord.query.filter_by(farmer_id=farmer.farmer_id).order_by(
        DiagnosisRecord.created_at.desc()
    ).all()

    return jsonify([
        {
            'diagnosis_id': d.diagnosis_id,
            'predicted_class_id': d.predicted_class_id,
            'confidence_score': d.confidence_score,
            'top3_predictions': d.top3_predictions,
            'created_at': d.created_at.isoformat() + 'Z'
        }
        for d in diagnoses
    ])


@bp.route('/history/<diagnosis_id>', methods=['DELETE'])
def delete_history(diagnosis_id):
    device_id = request.headers.get('X-Device-Id')
    if not device_id:
        return jsonify({'error': 'X-Device-Id header required'}), 400

    farmer = Farmer.query.filter_by(device_identifier=device_id).first()
    if not farmer:
        return jsonify({'error': 'Farmer not found'}), 404

    diagnosis = DiagnosisRecord.query.filter_by(
        diagnosis_id=diagnosis_id,
        farmer_id=farmer.farmer_id
    ).first()

    if not diagnosis:
        return jsonify({'error': 'Diagnosis not found'}), 404

    db.session.delete(diagnosis)
    db.session.commit()

    return jsonify({'status': 'ok'})
