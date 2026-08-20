from app.db.database import Base, engine
from app.models import customer, transaction, audit_log  # noqa: F401 (ensures models register)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ RAAHI database initialized.")


if __name__ == "__main__":
    init_db()