"""
seed.py — Idempotent database seed for AgroScan NG.
Safe to run on every container restart: skips inserts where data already exists.
Never exits non-zero (deploy must proceed even if seed errors — tables are in
place either way and users can seed later via admin UI if needed).
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
        # DEFENSIVE: Create any missing tables BEFORE querying.
        # Alembic migrations should have done this, but on SQLite fallback
        # (e.g. DATABASE_URL missing in manual Render services) there is
        # often a path-resolution mismatch between alembic and seed.py
        # that results in "no such table" errors even though migration
        # reported success. create_all() is idempotent.
        try:
            db.create_all()
            db.session.commit()
            print("[seed] db.create_all() OK — all tables guaranteed present.")
        except Exception as e:
            print(f"[seed][WARN] db.create_all() threw: {e!r} — continuing anyway")

        # ── Disease classes & advisories ──────────────────────────────────
        seeded_diseases = 0
        for i, data in enumerate(DISEASES_DATA):
            try:
                exists = DiseaseClass.query.filter_by(
                    crop_name=data['crop'], disease_name=data['disease']
                ).first()
            except Exception as e:
                print(f"[seed][ERROR] DiseaseClass lookup failed for {data['crop']}/{data['disease']}: {e!r}")
                continue
            if exists:
                continue

            try:
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
            except Exception as e:
                print(f"[seed][ERROR] Failed to stage disease_class id={i} ({data['crop']}/{data['disease']}): {e!r}")
                db.session.rollback()
                continue

        # ── Default admin user ────────────────────────────────────────────
        seeded_admin = False
        try:
            if not Admin.query.filter_by(email='admin@agroscan.com').first():
                password = b'admin123'
                hashed = bcrypt.hashpw(password, bcrypt.gensalt())
                admin = Admin(
                    email='admin@agroscan.com',
                    password_hash=hashed.decode('utf-8'),
                )
                db.session.add(admin)
                seeded_admin = True
        except Exception as e:
            print(f"[seed][ERROR] Admin lookup/insert failed: {e!r}")
            db.session.rollback()
            seeded_admin = False

        try:
            db.session.commit()
        except Exception as e:
            print(f"[seed][ERROR] db.session.commit() failed: {e!r}")
            db.session.rollback()
            seeded_diseases = 0
            seeded_admin = False

        if seeded_diseases or seeded_admin:
            print(f"[seed] Inserted {seeded_diseases} disease classes, admin={'yes' if seeded_admin else 'skip'}.")
        else:
            print("[seed] Database already seeded (or skipped seed) — nothing to do.")


if __name__ == '__main__':
    try:
        run_seed()
    except Exception as e:
        # Never propagate — seed failure must not crash the deploy.
        print(f"[seed][FATAL-CAUGHT] run_seed() raised {e!r} — continuing to boot.")
    sys.exit(0)
