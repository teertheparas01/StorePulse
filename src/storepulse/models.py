"""SQLAlchemy ORM models for StorePulse Retail System."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from storepulse.database import Base


def utc_now():
    return datetime.now(UTC)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    barcode = Column(String(64), index=True, nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)
    brand = Column(String(100), nullable=True)
    supplier = Column(String(100), nullable=True)
    cost_price = Column(Float, default=0.0, nullable=False)
    selling_price = Column(Float, default=0.0, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    min_stock_alert = Column(Integer, default=10, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active, clearance, discontinued
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    transactions = relationship(
        "InventoryTransaction", back_populates="product", cascade="all, delete-orphan"
    )
    sale_items = relationship("SaleItem", back_populates="product")
    recommendations = relationship(
        "AIRecommendation", back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def profit_margin(self) -> float:
        if self.selling_price > 0:
            return round(((self.selling_price - self.cost_price) / self.selling_price) * 100, 2)
        return 0.0

    @property
    def trapped_capital(self) -> float:
        return round(self.stock_quantity * self.cost_price, 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sku": self.sku,
            "barcode": self.barcode or "",
            "name": self.name,
            "description": self.description or "",
            "category": self.category,
            "subcategory": self.subcategory or "",
            "brand": self.brand or "",
            "supplier": self.supplier or "",
            "cost_price": self.cost_price,
            "selling_price": self.selling_price,
            "stock_quantity": self.stock_quantity,
            "min_stock_alert": self.min_stock_alert,
            "status": self.status,
            "profit_margin": self.profit_margin,
            "trapped_capital": self.trapped_capital,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    transaction_type = Column(
        String(30), nullable=False
    )  # restock, sale, adjustment, return, writeoff
    quantity = Column(Integer, nullable=False)  # + for addition, - for reduction
    balance_after = Column(Integer, nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)
    reference_id = Column(String(64), nullable=True)  # receipt_no, PO#, etc.
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    product = relationship("Product", back_populates="transactions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_sku": self.product.sku if self.product else None,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "balance_after": self.balance_after,
            "unit_cost": self.unit_cost,
            "reference_id": self.reference_id or "",
            "notes": self.notes or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_no = Column(String(64), unique=True, nullable=False, index=True)
    subtotal = Column(Float, default=0.0, nullable=False)
    tax_amount = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    payment_method = Column(String(30), default="cash", nullable=False)  # cash, card, upi, split
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "receipt_no": self.receipt_no,
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount,
            "payment_method": self.payment_method,
            "customer_name": self.customer_name or "",
            "customer_phone": self.customer_phone or "",
            "notes": self.notes or "",
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    total_price = Column(Float, nullable=False)
    is_bundle = Column(Boolean, default=False, nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sale_id": self.sale_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_sku": self.product.sku if self.product else None,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "unit_cost": self.unit_cost,
            "discount": self.discount,
            "total_price": self.total_price,
            "is_bundle": self.is_bundle,
        }


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    recommended_title = Column(String(255), nullable=False)
    recommended_brand = Column(String(100), nullable=True)
    recommended_price = Column(Float, nullable=True)
    recommended_rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
    value_quality_score = Column(Float, default=0.0)
    reasoning = Column(Text, nullable=True)
    source_url = Column(String(500), nullable=True)
    bundle_suggestion = Column(Text, nullable=True)
    status = Column(String(30), default="pending", nullable=False)  # pending, accepted, dismissed
    created_at = Column(DateTime, default=utc_now, nullable=False)

    product = relationship("Product", back_populates="recommendations")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_sku": self.product.sku if self.product else None,
            "product_category": self.product.category if self.product else None,
            "current_price": self.product.selling_price if self.product else None,
            "current_cost": self.product.cost_price if self.product else None,
            "current_stock": self.product.stock_quantity if self.product else 0,
            "trapped_capital": self.product.trapped_capital if self.product else 0,
            "recommended_title": self.recommended_title,
            "recommended_brand": self.recommended_brand or "",
            "recommended_price": self.recommended_price,
            "recommended_rating": self.recommended_rating,
            "review_count": self.review_count,
            "value_quality_score": self.value_quality_score,
            "reasoning": self.reasoning or "",
            "source_url": self.source_url or "",
            "bundle_suggestion": self.bundle_suggestion or "",
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
