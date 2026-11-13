"""Analytics summary routes for store KPIs."""

from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from storepulse.database import db_session
from storepulse.models import Product, Sale, SaleItem

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/summary", methods=["GET"])
def get_analytics_summary():
    """Return comprehensive store analytics summary."""
    days = int(request.args.get("days", 30))
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Revenue overview
    sales_query = db_session.query(Sale).filter(Sale.created_at >= cutoff)
    sales = sales_query.all()

    total_revenue = sum(s.total_amount for s in sales)
    total_tax = sum(s.tax_amount for s in sales)
    total_discount = sum(s.discount_amount for s in sales)
    total_subtotal = sum(s.subtotal for s in sales)

    # Profit margins (overall + per category)
    sale_items = (
        db_session.query(SaleItem)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(Sale.created_at >= cutoff)
        .all()
    )

    total_cost = sum(item.unit_cost * item.quantity for item in sale_items)
    total_revenue_items = sum(item.total_price for item in sale_items)
    overall_margin = (
        ((total_revenue_items - total_cost) / total_revenue_items * 100)
        if total_revenue_items > 0
        else 0
    )

    # Per-category margins
    category_stats = {}
    for item in sale_items:
        if item.product:
            cat = item.product.category
            if cat not in category_stats:
                category_stats[cat] = {"revenue": 0.0, "cost": 0.0, "units": 0}
            category_stats[cat]["revenue"] += item.total_price
            category_stats[cat]["cost"] += item.unit_cost * item.quantity
            category_stats[cat]["units"] += item.quantity

    category_margins = {
        cat: {
            "margin_pct": round(
                (
                    ((stats["revenue"] - stats["cost"]) / stats["revenue"] * 100)
                    if stats["revenue"] > 0
                    else 0
                ),
                2,
            ),
            "revenue": round(stats["revenue"], 2),
            "units_sold": stats["units"],
        }
        for cat, stats in category_stats.items()
    }

    # Capital health
    products = db_session.query(Product).all()
    total_inventory_capital = sum(p.trapped_capital for p in products)
    total_units_on_hand = sum(p.stock_quantity for p in products)

    # Dead stock capital (velocity < 0.20)
    dead_stock_capital = 0.0
    dead_stock_items = []
    for p in products:
        if p.stock_quantity > 0:
            sold_qty = (
                db_session.query(func.coalesce(func.sum(SaleItem.quantity), 0))
                .join(Sale, SaleItem.sale_id == Sale.id)
                .filter(SaleItem.product_id == p.id, Sale.created_at >= cutoff)
                .scalar()
            ) or 0
            total_pool = p.stock_quantity + sold_qty
            velocity = (sold_qty / total_pool) if total_pool > 0 else 0.0
            if velocity < 0.20:
                dead_stock_capital += p.trapped_capital
                dead_stock_items.append(
                    {
                        "product_id": p.id,
                        "name": p.name,
                        "trapped_capital": p.trapped_capital,
                        "velocity": round(velocity, 4),
                    }
                )

    dead_stock_items.sort(key=lambda x: x["trapped_capital"], reverse=True)

    free_working_capital = total_inventory_capital - dead_stock_capital

    # Top sellers (by revenue)
    product_revenue = {}
    for item in sale_items:
        if item.product:
            pid = item.product.id
            if pid not in product_revenue:
                product_revenue[pid] = {
                    "name": item.product.name,
                    "sku": item.product.sku,
                    "category": item.product.category,
                    "revenue": 0.0,
                    "units": 0,
                }
            product_revenue[pid]["revenue"] += item.total_price
            product_revenue[pid]["units"] += item.quantity

    top_sellers_by_revenue = sorted(
        product_revenue.values(), key=lambda x: x["revenue"], reverse=True
    )[:5]
    top_sellers_by_volume = sorted(
        product_revenue.values(), key=lambda x: x["units"], reverse=True
    )[:5]

    # Dead stock (bottom 5 by velocity with trapped capital > 0)
    dead_stock_sorted = sorted(dead_stock_items, key=lambda x: x["trapped_capital"], reverse=True)[
        :5
    ]

    # Revenue by period for charts
    period_revenue = {}
    for sale in sales:
        day_key = sale.created_at.date().isoformat()
        period_revenue[day_key] = period_revenue.get(day_key, 0) + sale.total_amount

    revenue_overview = {
        f"last_{days}_days": {
            "total_revenue": round(total_revenue, 2),
            "total_tax": round(total_tax, 2),
            "total_discount": round(total_discount, 2),
            "total_subtotal": round(total_subtotal, 2),
            "bill_count": len(sales),
        },
        "daily_breakdown": [
            {"date": k, "revenue": round(v, 2)} for k, v in sorted(period_revenue.items())
        ],
    }

    return jsonify(
        {
            "revenue_overview": revenue_overview,
            "profit_margins": {
                "overall_margin_pct": round(overall_margin, 2),
                "by_category": category_margins,
            },
            "capital_health": {
                "total_inventory_capital": round(total_inventory_capital, 2),
                "free_working_capital": round(free_working_capital, 2),
                "trapped_dead_stock_capital": round(dead_stock_capital, 2),
                "total_units_on_hand": total_units_on_hand,
                "capital_at_risk_pct": round(
                    (
                        (dead_stock_capital / total_inventory_capital * 100)
                        if total_inventory_capital > 0
                        else 0
                    ),
                    2,
                ),
            },
            "top_sellers": {
                "by_revenue": [
                    {**s, "revenue": round(s["revenue"], 2)} for s in top_sellers_by_revenue
                ],
                "by_volume": top_sellers_by_volume,
            },
            "dead_stock": dead_stock_sorted,
        }
    )
