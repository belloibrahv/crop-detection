from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import DiseaseClass, TreatmentAdvisory, Admin, AuditLog, DiagnosisRecord, Farmer
import jwt
from functools import wraps

bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            token = token.split(' ')[1]
            payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
            admin = Admin.query.filter_by(admin_id=payload['admin_id']).first()
            if not admin:
                return jsonify({'error': 'Unauthorized'}), 401
        except Exception as e:
            return jsonify({'error': 'Unauthorized'}), 401

        return f(admin, *args, **kwargs)
    return decorated_function


@bp.route('/diseases', methods=['POST'])
@admin_required
def create_disease(admin):
    data = request.get_json()
    disease = DiseaseClass(
        crop_name=data['crop_name'],
        disease_name=data['disease_name'],
        is_healthy=data.get('is_healthy', False),
        description=data.get('description')
    )
    db.session.add(disease)
    db.session.commit()

    audit = AuditLog(
        admin_id=admin.admin_id,
        action='create',
        target_table='disease_class',
        diff={'class_id': disease.class_id, 'data': data}
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'class_id': disease.class_id}), 201


@bp.route('/diseases/<int:class_id>', methods=['PUT'])
@admin_required
def update_disease(admin, class_id):
    disease = DiseaseClass.query.get_or_404(class_id)
    data = request.get_json()
    for key, value in data.items():
        if hasattr(disease, key):
            setattr(disease, key, value)
    db.session.commit()

    audit = AuditLog(
        admin_id=admin.admin_id,
        action='update',
        target_table='disease_class',
        diff={'class_id': class_id, 'data': data}
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'status': 'ok'})


@bp.route('/advisory/<int:class_id>', methods=['PUT'])
@admin_required
def update_advisory(admin, class_id):
    advisory = TreatmentAdvisory.query.filter_by(class_id=class_id).first()
    data = request.get_json()
    if not advisory:
        advisory = TreatmentAdvisory(class_id=class_id)
        db.session.add(advisory)

    advisory.recommended_action = data['recommended_action']
    advisory.local_treatment_options = data.get('local_treatment_options')
    db.session.commit()

    audit = AuditLog(
        admin_id=admin.admin_id,
        action='update',
        target_table='treatment_advisory',
        diff={'class_id': class_id, 'data': data}
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'status': 'ok'})


@bp.route('/analytics/summary', methods=['GET'])
@admin_required
def get_analytics(admin):
    total_diagnoses = DiagnosisRecord.query.count()
    low_confidence = DiagnosisRecord.query.filter(DiagnosisRecord.confidence_score < 30).count()

    from sqlalchemy import func
    crop_stats = db.session.query(
        DiseaseClass.crop_name,
        func.count(DiagnosisRecord.diagnosis_id)
    ).join(DiagnosisRecord, DiseaseClass.class_id == DiagnosisRecord.predicted_class_id).group_by(
        DiseaseClass.crop_name
    ).all()

    return jsonify({
        'total_diagnoses': total_diagnoses,
        'low_confidence_count': low_confidence,
        'crop_stats': [{'crop': crop, 'count': count} for crop, count in crop_stats]
    })


@bp.route('/diseases/<int:class_id>', methods=['DELETE'])
@admin_required
def delete_disease(admin, class_id):
    disease = DiseaseClass.query.get_or_404(class_id)
    
    # Check if disease has associated diagnoses
    has_diagnoses = DiagnosisRecord.query.filter_by(predicted_class_id=class_id).first()
    if has_diagnoses:
        return jsonify({'error': 'Cannot delete disease with associated diagnosis records'}), 400
    
    db.session.delete(disease)
    db.session.commit()

    audit = AuditLog(
        admin_id=admin.admin_id,
        action='delete',
        target_table='disease_class',
        diff={'class_id': class_id}
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'status': 'ok'})


@bp.route('/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs(admin):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page
    )
    
    return jsonify({
        'logs': [
            {
                'log_id': log.log_id,
                'admin_id': log.admin_id,
                'action': log.action,
                'target_table': log.target_table,
                'diff': log.diff,
                'created_at': log.created_at.isoformat() + 'Z'
            }
            for log in logs.items
        ],
        'total': logs.total,
        'pages': logs.pages,
        'current_page': page
    })


@bp.route('/farmers', methods=['GET'])
@admin_required
def get_farmers(admin):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    farmers = Farmer.query.order_by(Farmer.registration_date.desc()).paginate(
        page=page, per_page=per_page
    )
    
    return jsonify({
        'farmers': [
            {
                'farmer_id': f.farmer_id,
                'device_identifier': f.device_identifier,
                'phone_number': f.phone_number,
                'preferred_language': f.preferred_language,
                'registration_date': f.registration_date.isoformat() + 'Z',
                'diagnosis_count': len(f.diagnoses)
            }
            for f in farmers.items
        ],
        'total': farmers.total,
        'pages': farmers.pages,
        'current_page': page
    })


@bp.route('/farmers/<farmer_id>', methods=['GET'])
@admin_required
def get_farmer_detail(admin, farmer_id):
    farmer = Farmer.query.get_or_404(farmer_id)
    
    diagnoses = DiagnosisRecord.query.filter_by(farmer_id=farmer_id).order_by(
        DiagnosisRecord.created_at.desc()
    ).all()
    
    return jsonify({
        'farmer_id': farmer.farmer_id,
        'device_identifier': farmer.device_identifier,
        'phone_number': farmer.phone_number,
        'preferred_language': farmer.preferred_language,
        'registration_date': farmer.registration_date.isoformat() + 'Z',
        'diagnoses': [
            {
                'diagnosis_id': d.diagnosis_id,
                'predicted_class_id': d.predicted_class_id,
                'confidence_score': d.confidence_score,
                'created_at': d.created_at.isoformat() + 'Z'
            }
            for d in diagnoses
        ]
    })
