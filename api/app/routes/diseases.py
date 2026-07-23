from flask import Blueprint, jsonify
from app.models import DiseaseClass, TreatmentAdvisory

bp = Blueprint('diseases', __name__)


@bp.route('/diseases', methods=['GET'])
def get_diseases():
    diseases = DiseaseClass.query.all()
    return jsonify([
        {
            'class_id': d.class_id,
            'crop_name': d.crop_name,
            'disease_name': d.disease_name,
            'is_healthy': d.is_healthy,
            'description': d.description
        }
        for d in diseases
    ])


@bp.route('/diseases/<int:class_id>/advisory', methods=['GET'])
def get_advisory(class_id):
    advisory = TreatmentAdvisory.query.filter_by(class_id=class_id).first()
    if not advisory:
        return jsonify({'error': 'Advisory not found'}), 404
    return jsonify({
        'recommended_action': advisory.recommended_action,
        'local_treatment_options': advisory.local_treatment_options
    })
