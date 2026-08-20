import random
import uuid
from datetime import datetime, timedelta
import json
import os

from app.db.database import SessionLocal
from app.models.customer import Customer
from app.models.transaction import Transaction

FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "merchant_profiles.json")

FIRST_NAMES = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Karan",
               "Divya", "Arjun", "Neha", "Rahul", "Pooja", "Sanjay", "Meera"]
LAST_NAMES = ["Sharma", "Patel", "Reddy", "Iyer", "Singh", "Gupta", "Nair", "Rao"]

# Realistic failure reason codes per record type
PAYMENT_FAILURE_REASONS = [
    "insufficient_funds",
    "issuer_unavailable",
    "authentication_failed",   # OTP/3DS failure
    "card_declined",
    "card_expired",
    "network_timeout",
]

SUBSCRIPTION_FAILURE_REASONS = [
    "insufficient_funds",
    "mandate_not_active",
    "issuer_unavailable",
    "card_expired",
]

INVOICE_STATUSES = ["overdue_7d", "overdue_15d", "overdue_30d"]

LTV_SEGMENTS = ["high", "standard", "low"]


def load_merchants():
    with open(FIXTURES_PATH, "r") as f:
        return json.load(f)


def random_customer_id():
    return f"cust_{uuid.uuid4().hex[:10]}"


def random_txn_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def create_customer(db):
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    customer = Customer(
        id=random_customer_id(),
        name=name,
        phone=f"+91{random.randint(6000000000, 9999999999)}",
        email=f"{name.split()[0].lower()}{random.randint(1,999)}@example.com",
        ltv_segment=random.choices(LTV_SEGMENTS, weights=[0.2, 0.6, 0.2])[0],
        opted_out=random.random() < 0.05,   # 5% opted out of comms
    )
    db.add(customer)
    return customer


def create_payment_failure(db, merchant):
    customer = create_customer(db)
    amount = round(random.uniform(0.3, 2.5) * merchant["avg_order_value"], 2)
    txn = Transaction(
        id=random_txn_id("pay"),
        merchant_id=merchant["merchant_id"],
        customer_id=customer.id,
        record_type="payment",
        amount=amount,
        status="at_risk",
        failure_reason_code=random.choice(PAYMENT_FAILURE_REASONS),
        max_attempts=3,
        created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
    )
    db.add(txn)


def create_subscription_failure(db, merchant):
    customer = create_customer(db)
    amount = round(merchant["avg_order_value"] * random.uniform(0.8, 1.2), 2)
    txn = Transaction(
        id=random_txn_id("sub"),
        merchant_id=merchant["merchant_id"],
        customer_id=customer.id,
        record_type="subscription",
        amount=amount,
        status="at_risk",
        failure_reason_code=random.choice(SUBSCRIPTION_FAILURE_REASONS),
        max_attempts=3,
        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 5)),
    )
    db.add(txn)


def create_overdue_invoice(db, merchant):
    customer = create_customer(db)
    amount = round(merchant["avg_order_value"] * random.uniform(1.0, 4.0), 2)
    overdue_status = random.choice(INVOICE_STATUSES)
    days_overdue = int(overdue_status.split("_")[1].replace("d", ""))
    txn = Transaction(
        id=random_txn_id("inv"),
        merchant_id=merchant["merchant_id"],
        customer_id=customer.id,
        record_type="invoice",
        amount=amount,
        status="at_risk",
        failure_reason_code=overdue_status,
        max_attempts=4,
        due_date=datetime.utcnow() - timedelta(days=days_overdue),
        created_at=datetime.utcnow() - timedelta(days=days_overdue + 5),
    )
    db.add(txn)


def inject_edge_cases(db, merchant):
    """Guarantees our test_cases.json scenarios are represented in the batch."""
    customer = create_customer(db)

    # Edge case: very small amount
    db.add(Transaction(
        id=random_txn_id("edge_small"),
        merchant_id=merchant["merchant_id"],
        customer_id=customer.id,
        record_type="payment",
        amount=10.0,
        status="at_risk",
        failure_reason_code="insufficient_funds",
        max_attempts=3,
    ))

    # Edge case: very large amount
    customer2 = create_customer(db)
    db.add(Transaction(
        id=random_txn_id("edge_large"),
        merchant_id=merchant["merchant_id"],
        customer_id=customer2.id,
        record_type="invoice",
        amount=500000.0,
        status="at_risk",
        failure_reason_code="overdue_30d",
        due_date=datetime.utcnow() - timedelta(days=30),
        max_attempts=4,
    ))

    # Edge case: already exhausted retries (should route to exception)
    customer3 = create_customer(db)
    db.add(Transaction(
        id=random_txn_id("edge_exhausted"),
        merchant_id=merchant["merchant_id"],
        customer_id=customer3.id,
        record_type="payment",
        amount=999.0,
        status="at_risk",
        failure_reason_code="card_declined",
        attempts_made=3,
        max_attempts=3,
    ))

    # Edge case: opted-out customer (must never be contacted)
    customer4 = create_customer(db)
    customer4.opted_out = True
    db.add(Transaction(
        id=random_txn_id("edge_optedout"),
        merchant_id=merchant["merchant_id"],
        customer_id=customer4.id,
        record_type="invoice",
        amount=15000.0,
        status="at_risk",
        failure_reason_code="overdue_15d",
        due_date=datetime.utcnow() - timedelta(days=15),
        max_attempts=4,
    ))


def generate(num_records_per_merchant=25):
    db = SessionLocal()
    merchants = load_merchants()

    try:
        for merchant in merchants:
            for _ in range(num_records_per_merchant):
                record_type = random.choices(
                    ["payment", "subscription", "invoice"],
                    weights=[0.5, 0.3, 0.2],
                )[0]

                if record_type == "payment":
                    create_payment_failure(db, merchant)
                elif record_type == "subscription":
                    create_subscription_failure(db, merchant)
                else:
                    create_overdue_invoice(db, merchant)

            inject_edge_cases(db, merchant)

        db.commit()
        total = db.query(Transaction).count()
        print(f"✅ Generated synthetic batch — {total} transactions across {len(merchants)} merchants.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error generating data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate()