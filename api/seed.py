"""
seed.py — Idempotent database seed for AgroScan NG.
Safe to run on every container restart: skips inserts where data already exists.
"""
import sys
from app import create_app, db
from app.models import DiseaseClass, TreatmentAdvisory, Admin
import bcrypt

DISEASES_DATA = [
    # class_id 0
    {'crop': 'Cassava', 'disease': 'Cassava Healthy', 'is_healthy': True},
    # class_id 1
    {'crop': 'Maize', 'disease': 'Maize Common Rust', 'is_healthy': False,
     'advisory': 'Use resistant varieties.',
     'local': 'Plant early to escape severe infection.'},
    # class_id 2
    {'crop': 'Maize', 'disease': 'Maize Healthy', 'is_healthy': True},
    # class_id 3
    {'crop': 'Maize', 'disease': 'Maize Leaf Blight (Northern)', 'is_healthy': False,
     'advisory': 'Use resistant varieties. Crop rotation. Fungicide if needed.',
     'local': 'Remove crop debris after harvest.'},
    # class_id 4
    {'crop': 'Maize', 'disease': 'Maize Leaf Spot (Gray)', 'is_healthy': False,
     'advisory': 'Use resistant varieties. Ensure good air circulation.',
     'local': 'Avoid dense planting.'},
    # class_id 5
    {'crop': 'Rice', 'disease': 'Rice Blast', 'is_healthy': False,
     'advisory': 'Use resistant varieties. Apply fungicide if needed.',
     'local': 'Avoid excessive nitrogen fertilizer.'},
    # class_id 6
    {'crop': 'Tomato', 'disease': 'Tomato Bacterial Spot', 'is_healthy': False,
     'advisory': 'Use disease-free seed. Copper sprays.',
     'local': 'Practice crop rotation.'},
    # class_id 7
    {'crop': 'Tomato', 'disease': 'Tomato Early Blight', 'is_healthy': False,
     'advisory': 'Remove lower leaves. Use copper fungicides.',
     'local': 'Apply compost tea as a foliar spray.'},
    # class_id 8
    {'crop': 'Tomato', 'disease': 'Tomato Healthy', 'is_healthy': True},
    # class_id 9
    {'crop': 'Tomato', 'disease': 'Tomato Late Blight', 'is_healthy': False,
     'advisory': 'Use resistant varieties. Apply fungicide preventively.',
     'local': 'Ensure good air circulation.'},
    # class_id 10
    {'crop': 'Tomato', 'disease': 'Tomato Leaf Mould', 'is_healthy': False,
     'advisory': 'Improve air circulation. Reduce humidity.',
     'local': 'Space plants properly.'},
    # class_id 11
    {'crop': 'Tomato', 'disease': 'Tomato Mosaic Virus', 'is_healthy': False,
     'advisory': 'Use disease-free seed. Wash hands between plants.',
     'local': 'Avoid smoking near plants.'},
    # class_id 12
    {'crop': 'Tomato', 'disease': 'Tomato Septoria Leaf Spot', 'is_healthy': False,
     'advisory': 'Remove infected leaves. Crop rotation.',
     'local': 'Mulch to prevent soil splash.'},
    # class_id 13
    {'crop': 'Tomato', 'disease': 'Tomato Yellow Leaf Curl Virus', 'is_healthy': False,
     'advisory': 'Use resistant varieties. Control whiteflies.',
     'local': 'Use reflective mulches.'},
]


def run_seed():
    app = create_app()
    with app.app_context():
        # ── Disease classes & advisories ──────────────────────────────────
        seeded_diseases = 0
        for i, data in enumerate(DISEASES_DATA):
            exists = DiseaseClass.query.filter_by(
                crop_name=data['crop'], disease_name=data['disease']
            ).first()
            if exists:
                continue

            disease = DiseaseClass(
                class_id=i,
                crop_name=data['crop'],
                disease_name=data['disease'],
                is_healthy=data['is_healthy'],
                description=f"{data['crop']} — {data['disease']}",
            )
            db.session.add(disease)

            if not data['is_healthy']:
                advisory = TreatmentAdvisory(
                    class_id=i,
                    recommended_action=data['advisory'],
                    local_treatment_options=data.get('local'),
                )
                db.session.add(advisory)

            seeded_diseases += 1

        # ── Default admin user ────────────────────────────────────────────
        seeded_admin = False
        if not Admin.query.filter_by(email='admin@agroscan.com').first():
            password = b'admin123'
            hashed = bcrypt.hashpw(password, bcrypt.gensalt())
            admin = Admin(
                email='admin@agroscan.com',
                password_hash=hashed.decode('utf-8'),
            )
            db.session.add(admin)
            seeded_admin = True

        db.session.commit()

        if seeded_diseases or seeded_admin:
            print(f"[seed] Inserted {seeded_diseases} disease classes, admin={'yes' if seeded_admin else 'skip'}.")
        else:
            print("[seed] Database already seeded — nothing to do.")


if __name__ == '__main__':
    run_seed()
