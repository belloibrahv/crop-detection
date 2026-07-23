from app import db
from datetime import datetime
import uuid


class Farmer(db.Model):
    __tablename__ = 'farmer'
    farmer_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_identifier = db.Column(db.String(128), nullable=False, unique=True)
    phone_number = db.Column(db.String(20), nullable=True)
    preferred_language = db.Column(db.String(20), default='en')
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    diagnoses = db.relationship('DiagnosisRecord', backref='farmer', lazy=True)


class DiseaseClass(db.Model):
    __tablename__ = 'disease_class'
    class_id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(50), nullable=False)
    disease_name = db.Column(db.String(100), nullable=False)
    is_healthy = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=True)
    advisory = db.relationship('TreatmentAdvisory', backref='disease_class', uselist=False, cascade='all, delete-orphan')
    diagnoses = db.relationship('DiagnosisRecord', backref='disease_class', lazy=True)
    __table_args__ = (db.UniqueConstraint('crop_name', 'disease_name', name='_crop_disease_uc'),)


class TreatmentAdvisory(db.Model):
    __tablename__ = 'treatment_advisory'
    advisory_id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('disease_class.class_id'), nullable=False, unique=True)
    recommended_action = db.Column(db.Text, nullable=False)
    local_treatment_options = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class DiagnosisRecord(db.Model):
    __tablename__ = 'diagnosis_record'
    diagnosis_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmer.farmer_id'), nullable=False)
    image_thumbnail_url = db.Column(db.String(255), nullable=True)
    predicted_class_id = db.Column(db.Integer, db.ForeignKey('disease_class.class_id'), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    top3_predictions = db.Column(db.JSON, nullable=True)
    retrain_consent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_diagnosis_farmer', 'farmer_id', 'created_at'),
    )


class Admin(db.Model):
    __tablename__ = 'admin'
    admin_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default='admin')
    audit_logs = db.relationship('AuditLog', backref='admin', lazy=True)


class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    log_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = db.Column(db.String(36), db.ForeignKey('admin.admin_id'), nullable=True)
    action = db.Column(db.String(50), nullable=True)
    target_table = db.Column(db.String(50), nullable=True)
    diff = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
