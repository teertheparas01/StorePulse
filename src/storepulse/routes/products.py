"""Product catalog CRUD routes."""

from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from storepulse.database import db_session
from storepulse.models import InventoryTransaction, Product

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


@products_bp.route("", methods=["GET"])
def get_products():
    """List products with search, category filtering, and sorting."""
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()
    sort_by = request.args.get("sort_by", "name")  # name, price, stock, trapped_capital
    order = request.args.get("order", "asc")

    query = db_session.query(Product)

    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.barcode.ilike(f"%{search}%"),
                Product.brand.ilike(f"%{search}%"),
            )
        )

    if category and category.lower() != "all":
        query = query.filter(Product.category.ilike(category))

    if status and status.lower() != "all":
        query = query.filter(Product.status == status)

    products = query.all()

    # In-memory sorting for dynamic properties if needed
    if sort_by == "trapped_capital":
        products.sort(key=lambda p: p.trapped_capital, reverse=(order == "desc"))
    elif sort_by == "margin":
        products.sort(key=lambda p: p.profit_margin, reverse=(order == "desc"))
    elif sort_by == "price":
        products.sort(key=lambda p: p.selling_price, reverse=(order == "desc"))
    elif sort_by == "stock":
        products.sort(key=lambda p: p.stock_quantity, reverse=(order == "desc"))
    else:
        products.sort(key=lambda p: p.name.lower(), reverse=(order == "desc"))

    categories = [c[0] for c in db_session.query(Product.category).distinct().all() if c[0]]

    return jsonify(
        {
            "products": [p.to_dict() for p in products],
            "total": len(products),
            "categories": sorted(categories),
        }
    )


@products_bp.route("/<int:product_id>", methods=["GET"])
def get_product(product_id: int):
    """Retrieve details for a single product."""
    product = db_session.query(Product).get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product.to_dict())


@products_bp.route("", methods=["POST"])
def create_product():
    """Create a new product."""
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    sku = data.get("sku", "").strip()

    if not name or not category:
        return jsonify({"error": "Product name and category are required"}), 400

    # Auto-generate SKU if not provided
    if not sku:
        count = db_session.query(Product).count() + 1
        prefix = category[:3].upper()
        sku = f"{prefix}-{count:03d}"

    # Check unique SKU
    existing = db_session.query(Product).filter(Product.sku == sku).first()
    if existing:
        return jsonify({"error": f"SKU '{sku}' already exists"}), 409

    cost_price = float(data.get("cost_price", 0.0))
    selling_price = float(data.get("selling_price", 0.0))
    stock_quantity = int(data.get("stock_quantity", 0))
    min_stock_alert = int(data.get("min_stock_alert", 10))

    product = Product(
        sku=sku,
        barcode=data.get("barcode", "").strip() or None,
        name=name,
        description=data.get("description", "").strip() or None,
        category=category,
        subcategory=data.get("subcategory", "").strip() or None,
        brand=data.get("brand", "").strip() or None,
        supplier=data.get("supplier", "").strip() or None,
        cost_price=cost_price,
        selling_price=selling_price,
        stock_quantity=stock_quantity,
        min_stock_alert=min_stock_alert,
        status="active",
    )
    db_session.add(product)
    db_session.flush()

    # Log initial inventory transaction if stock > 0
    if stock_quantity > 0:
        tx = InventoryTransaction(
            product_id=product.id,
            transaction_type="restock",
            quantity=stock_quantity,
            balance_after=stock_quantity,
            unit_cost=cost_price,
            notes="Initial stock at product creation",
        )
        db_session.add(tx)

    db_session.commit()
    return jsonify(product.to_dict()), 201


@products_bp.route("/<int:product_id>", methods=["PUT"])
def update_product(product_id: int):
    """Update product information."""
    product = db_session.query(Product).get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json() or {}

    for field in [
        "name",
        "description",
        "category",
        "subcategory",
        "brand",
        "supplier",
        "barcode",
        "status",
    ]:
        if field in data:
            setattr(product, field, data[field])

    if "cost_price" in data:
        product.cost_price = float(data["cost_price"])
    if "selling_price" in data:
        product.selling_price = float(data["selling_price"])
    if "min_stock_alert" in data:
        product.min_stock_alert = int(data["min_stock_alert"])

    db_session.commit()
    return jsonify(product.to_dict())


@products_bp.route("/<int:product_id>", methods=["DELETE"])
def delete_product(product_id: int):
    """Delete a product from the catalog."""
    product = db_session.query(Product).get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    db_session.delete(product)
    db_session.commit()
    return jsonify({"message": f"Product '{product.name}' deleted successfully"})
