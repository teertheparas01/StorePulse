"""Inventory management and stock ledger routes."""

from flask import Blueprint, jsonify, request
from storepulse.database import db_session
from storepulse.models import InventoryTransaction, Product

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")


@inventory_bp.route("", methods=["GET"])
def get_inventory():
    """Retrieve full inventory list with alerts and capital analytics."""
    products = db_session.query(Product).order_by(Product.name).all()

    total_stock_units = sum(p.stock_quantity for p in products)
    total_inventory_value = sum(p.trapped_capital for p in products)

    low_stock_items = [p for p in products if p.stock_quantity <= p.min_stock_alert]
    out_of_stock_items = [p for p in products if p.stock_quantity == 0]

    items_list = []
    for p in products:
        d = p.to_dict()
        d["is_low_stock"] = p.stock_quantity <= p.min_stock_alert
        d["is_out_of_stock"] = p.stock_quantity == 0
        items_list.append(d)

    return jsonify(
        {
            "items": items_list,
            "kpis": {
                "total_skus": len(products),
                "total_units": total_stock_units,
                "total_valuation": round(total_inventory_value, 2),
                "low_stock_count": len(low_stock_items),
                "out_of_stock_count": len(out_of_stock_items),
            },
        }
    )


@inventory_bp.route("/restock", methods=["POST"])
def restock_product():
    """Add incoming stock from supplier."""
    data = request.get_json() or {}

    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 0))
    unit_cost = float(data.get("unit_cost", 0.0))
    reference_id = data.get("reference_id", "").strip()
    notes = data.get("notes", "").strip()

    if not product_id or quantity <= 0:
        return jsonify({"error": "Valid product_id and positive quantity are required"}), 400

    product = db_session.query(Product).get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Update product stock and optionally cost price
    product.stock_quantity += quantity
    if unit_cost > 0:
        product.cost_price = unit_cost

    tx = InventoryTransaction(
        product_id=product.id,
        transaction_type="restock",
        quantity=quantity,
        balance_after=product.stock_quantity,
        unit_cost=unit_cost or product.cost_price,
        reference_id=reference_id or None,
        notes=notes or f"Restocked {quantity} units",
    )
    db_session.add(tx)
    db_session.commit()

    return jsonify(
        {
            "message": f"Successfully added {quantity} units to {product.name}",
            "product": product.to_dict(),
            "transaction": tx.to_dict(),
        }
    )


@inventory_bp.route("/adjust", methods=["POST"])
def adjust_inventory():
    """Manual inventory correction (damaged goods, audit count, write-off)."""
    data = request.get_json() or {}

    product_id = data.get("product_id")
    new_quantity = data.get("new_quantity")
    reason = data.get("reason", "Manual adjustment").strip()
    adj_type = data.get("type", "adjustment")  # adjustment, writeoff, damage

    if product_id is None or new_quantity is None:
        return jsonify({"error": "product_id and new_quantity are required"}), 400

    product = db_session.query(Product).get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    new_quantity = int(new_quantity)
    diff = new_quantity - product.stock_quantity

    product.stock_quantity = new_quantity

    tx = InventoryTransaction(
        product_id=product.id,
        transaction_type=adj_type,
        quantity=diff,
        balance_after=new_quantity,
        unit_cost=product.cost_price,
        notes=reason,
    )
    db_session.add(tx)
    db_session.commit()

    return jsonify(
        {
            "message": f"Updated stock for {product.name} to {new_quantity}",
            "product": product.to_dict(),
            "transaction": tx.to_dict(),
        }
    )


@inventory_bp.route("/transactions", methods=["GET"])
def get_transactions():
    """Retrieve inventory transaction history."""
    limit = int(request.args.get("limit", 50))
    product_id = request.args.get("product_id")

    query = db_session.query(InventoryTransaction)
    if product_id:
        query = query.filter(InventoryTransaction.product_id == int(product_id))

    txs = query.order_by(InventoryTransaction.created_at.desc()).limit(limit).all()
    return jsonify([tx.to_dict() for tx in txs])
