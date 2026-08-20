from sqlalchemy import Column, String, Boolean
from app.db.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    ltv_segment = Column(String, default="standard")   # "high" | "standard" | "low"
    opted_out = Column(Boolean, default=False)