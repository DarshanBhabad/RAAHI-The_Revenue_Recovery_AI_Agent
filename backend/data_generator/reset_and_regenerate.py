from app.db.database import SessionLocal
from app.models import Transaction, AuditLog, Customer
from data_generator.generate_synthetic_data import generate


def reset_all():
    db = SessionLocal()
    try:
        db.query(AuditLog).delete()
        db.query(Transaction).delete()
        db.query(Customer).delete()
        db.commit()
        print("🗑️  Cleared all existing data.")
    finally:
        db.close()

    generate()


if __name__ == "__main__":
    reset_all()