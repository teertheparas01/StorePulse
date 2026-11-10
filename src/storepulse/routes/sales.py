"""Sales and POS billing routes with atomic inventory deduction."""

from datetime import UTC, datetime

from flask import Blueprint, jsonify, request
from storepulse.database import db_session
from storepulse.models import InventoryTransaction, Product, Sale, SaleItem

sales_bp = Blueprint("sales", __name__, url_prefix="/api/sales")


def generate_receipt_no() -> str:
    """Generate a unique sequential receipt number formatted REC-YYYYMM-XXXX."""
    now = datetime.now(UTC)
    prefix = now.strftime("REC-%Y%m")
    count = db_session.query(Sale).filter(Sale.receipt_no.like(f"{prefix}-%")).count() + 1
    return f"{prefix}-{count:04d}"


@sales_bp.route("", methods=["POST"])
def create_sale():
    """Create a new sale from the POS cart and atomically deduct stock."""
    data = request.get_json() or {}
    items_data = data.get("items", [])

    if not items_data:
        return jsonify({"error": "Cart cannot be empty"}), 400

    payment_method = data.get("payment_method", "cash")
    customer_name = data.get("customer_name", "").strip() or None
    customer_phone = data.get("customer_phone", "").strip() or None
    notes = data.get("notes", "").strip() or None

    # Step 1: Pre-validate stock for all items
    products_to_update = []
    subtotal = 0.0
    discount_total = 0.0

    for item in items_data:
        product_id = item.get("product_id")
        qty = int(item.get("quantity", 1))

        if qty <= 0:
            return jsonify({"error": f"Invalid quantity {qty} for product ID {product_id}"}), 400

        product = db_session.query(Product).get(product_id)
        if not product:
            return jsonify({"error": f"Product with ID {product_id} not found"}), 404

        if product.stock_quantity < qty:
            return (
                jsonify(
                    {
                        "error": f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}, requested: {qty}"
                    }
                ),
                400,
            )

        unit_price = float(item.get("unit_price", product.selling_price))
        discount = float(item.get("discount", 0.0))
        is_bundle = bool(item.get("is_bundle", False))

        line_subtotal = (qty * unit_price) - discount
        subtotal += qty * unit_price
        discount_total += discount

        products_to_update.append(
            {
                "product": product,
                "quantity": qty,
                "unit_price": unit_price,
                "discount": discount,
                "total_price": line_subtotal,
                "is_bundle": is_bundle,
            }
        )

    # Step 2: Calculate tax (e.g. 5% GST) and final total
    tax_rate = float(data.get("tax_rate", 0.05))
    tax_amount = round((subtotal - discount_total) * tax_rate, 2)
    total_amount = round((subtotal - discount_total) + tax_amount, 2)

    receipt_no = generate_receipt_no()

    sale = Sale(
        receipt_no=receipt_no,
        subtotal=round(subtotal, 2),
        tax_amount=tax_amount,
        discount_amount=round(discount_total, 2),
        total_amount=total_amount,
        payment_method=payment_method,
        customer_name=customer_name,
        customer_phone=customer_phone,
        notes=notes,
    )
    db_session.add(sale)
    db_session.flush()

    # Step 3: Atomic stock deduction and transaction recording
    for item_info in products_to_update:
        prod = item_info["product"]
        qty = item_info["quantity"]

        # Deduct inventory
        prod.stock_quantity -= qty

        # Add SaleItem
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=prod.id,
            quantity=qty,
            unit_price=item_info["unit_price"],
            unit_cost=prod.cost_price,
            discount=item_info["discount"],
            total_price=item_info["total_price"],
            is_bundle=item_info["is_bundle"],
        )
        db_session.add(sale_item)

        # Record Inventory Transaction audit trail
        tx = InventoryTransaction(
            product_id=prod.id,
            transaction_type="sale",
            quantity=-qty,
            balance_after=prod.stock_quantity,
            unit_cost=prod.cost_price,
            reference_id=sale.receipt_no,
            notes=f"POS Sale {sale.receipt_no}",
        )
        db_session.add(tx)

    db_session.commit()

    return (
        jsonify(
            {
                "message": "Sale completed successfully",
                "sale": sale.to_dict(),
            }
        ),
        201,
    )


@sales_bp.route("", methods=["GET"])
def get_sales():
    """List past sales with optional date filtering."""
    limit = int(request.args.get("limit", 50))
    payment = request.args.get("payment_method")

    query = db_session.query(Sale)
    if payment and payment.lower() != "all":
        query = query.filter(Sale.payment_method == payment.lower())

    sales = query.order_by(Sale.created_at.desc()).limit(limit).all()
    return jsonify(
        {
            "sales": [s.to_dict() for s in sales],
            "total": len(sales),
        }
    )


@sales_bp.route("/<int:sale_id>", methods=["GET"])
def get_sale(sale_id: int):
    """Retrieve full itemized receipt details for a sale."""
    sale = db_session.query(Sale).get(sale_id)
    if not sale:
        return jsonify({"error": "Sale not found"}), 404
    return jsonify(sale.to_dict())
