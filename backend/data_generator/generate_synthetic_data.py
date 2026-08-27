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

PAYMENT_FAILURE_REASONS = [
    "insufficient_funds",
    "issuer_unavailable",
    "authentication_failed",
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


def random_phone():
    first_digit = random.choice(['6', '7', '8', '9'])
    rest = ''.join(random.choices('0123456789', k=9))
    while len(set(rest)) < 4:
        rest = ''.join(random.choices('0123456789', k=9))
    return f"+91{first_digit}{rest}"


def random_customer_id():
    return f"cust_{uuid.uuid4().hex[:10]}"


def random_txn_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def create_customer(db):
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    customer = Customer(
        id=random_customer_id(),
        name=name,
        phone=random_phone(),
        email=f"{name.split()[0].lower()}{random.randint(1,999)}@example.com",
        ltv_segment=random.choices(LTV_SEGMENTS, weights=[0.2, 0.6, 0.2])[0],
        opted_out=random.random() < 0.05,
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


def create_checkout_abandonment(db, merchant):
    customer = create_customer(db)
    amount = round(random.uniform(0.3, 2.0) * merchant["avg_order_value"], 2)
    txn = Transaction(
        id=random_txn_id("cart"),
        merchant_id=merchant["merchant_id"],
        customer_id=customer.id,
        record_type="payment",
        amount=amount,
        status="at_risk",
        failure_reason_code="checkout_abandoned",
        max_attempts=2,
        created_at=datetime.utcnow() - timedelta(minutes=random.randint(15, 90)),
    )
    db.add(txn)


def inject_edge_cases(db, merchant):
    customer = create_customer(db)
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


def generate(num_records_per_merchant=160, merchant_suffix="", include_edge_cases=True):
    db = SessionLocal()
    merchants = load_merchants()
    BATCH_COMMIT_SIZE = 50

    try:
        records_since_commit = 0

        for merchant in merchants:
            merchant_copy = dict(merchant)
            merchant_copy["merchant_id"] = merchant["merchant_id"] + merchant_suffix

            for i in range(num_records_per_merchant):
                record_type = random.choices(
                    ["payment", "checkout_abandoned", "subscription", "invoice"],
                    weights=[0.4, 0.15, 0.25, 0.2],
                )[0]

                if record_type == "payment":
                    create_payment_failure(db, merchant_copy)
                elif record_type == "checkout_abandoned":
                    create_checkout_abandonment(db, merchant_copy)
                elif record_type == "subscription":
                    create_subscription_failure(db, merchant_copy)
                else:
                    create_overdue_invoice(db, merchant_copy)

                records_since_commit += 1
                if records_since_commit >= BATCH_COMMIT_SIZE:
                    db.commit()
                    print(f"⏳ Progress: {i + 1}/{num_records_per_merchant} for {merchant_copy['merchant_id']}...", flush=True)
                    records_since_commit = 0

            if include_edge_cases:
                inject_edge_cases(db, merchant_copy)

            db.commit()  # commit after each merchant's edge cases too
            records_since_commit = 0

        total = db.query(Transaction).filter(
            Transaction.merchant_id.like(f"%{merchant_suffix}") if merchant_suffix else True
        ).count()
        print(f"✅ Generated batch (suffix='{merchant_suffix}') — {total} transactions across {len(merchants)} merchants.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error generating data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    generate(num_records_per_merchant=160)