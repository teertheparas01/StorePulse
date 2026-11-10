"""Seed script to populate StorePulse with realistic retail store data."""

from datetime import UTC, datetime, timedelta

from storepulse.database import db_session, init_db
from storepulse.models import AIRecommendation, InventoryTransaction, Product, Sale, SaleItem


def seed_data():
    init_db()

    # Clear existing data
    db_session.query(AIRecommendation).delete()
    db_session.query(SaleItem).delete()
    db_session.query(Sale).delete()
    db_session.query(InventoryTransaction).delete()
    db_session.query(Product).delete()
    db_session.commit()

    now = datetime.now(UTC)

    # 1. Products definition
    products_data = [
        # HERO PRODUCTS (Fast-moving, high-margin, reliable)
        {
            "sku": "HERO-101",
            "barcode": "890103001",
            "name": "Dove Deep Moisture Shampoo 340ml",
            "description": "Nourishing daily shampoo with pro-moisture complex",
            "category": "Personal Care",
            "subcategory": "Hair Care",
            "brand": "Dove",
            "supplier": "Unilever Distribution",
            "cost_price": 210.0,
            "selling_price": 299.0,
            "stock_quantity": 42,
            "min_stock_alert": 15,
            "status": "active",
        },
        {
            "sku": "HERO-102",
            "barcode": "890103002",
            "name": "Colgate Total Active Fresh Toothpaste 150g",
            "description": "12-hour antibacterial shield fluoride toothpaste",
            "category": "Personal Care",
            "subcategory": "Oral Care",
            "brand": "Colgate",
            "supplier": "Colgate-Palmolive Ltd",
            "cost_price": 85.0,
            "selling_price": 125.0,
            "stock_quantity": 58,
            "min_stock_alert": 20,
            "status": "active",
        },
        {
            "sku": "HERO-103",
            "barcode": "890103003",
            "name": "Nestle Maggi 2-Minute Masala Noodles 420g Pack",
            "description": "Popular instant wheat noodles with authentic spices",
            "category": "Packaged Food",
            "subcategory": "Instant Meals",
            "brand": "Maggi",
            "supplier": "Nestle Wholesale",
            "cost_price": 88.0,
            "selling_price": 110.0,
            "stock_quantity": 64,
            "min_stock_alert": 25,
            "status": "active",
        },
        {
            "sku": "HERO-104",
            "barcode": "890103004",
            "name": "Fortune Sunlite Refined Sunflower Oil 1L Pouch",
            "description": "Light and healthy cooking oil enriched with vitamins",
            "category": "Grocery",
            "subcategory": "Edible Oils",
            "brand": "Fortune",
            "supplier": "Adani Wilmar Dist.",
            "cost_price": 122.0,
            "selling_price": 145.0,
            "stock_quantity": 30,
            "min_stock_alert": 15,
            "status": "active",
        },
        {
            "sku": "HERO-105",
            "barcode": "890103005",
            "name": "Surf Excel Matic Front Load Detergent Powder 2kg",
            "description": "Tough stain removal powder designed for washing machines",
            "category": "Household",
            "subcategory": "Laundry",
            "brand": "Surf Excel",
            "supplier": "Unilever Distribution",
            "cost_price": 380.0,
            "selling_price": 475.0,
            "stock_quantity": 22,
            "min_stock_alert": 8,
            "status": "active",
        },
        # UNDERPERFORMING / DEAD STOCK PRODUCTS (Trapped Capital Alert candidates!)
        {
            "sku": "DEAD-201",
            "barcode": "890204001",
            "name": "Ex-Vessel Keratin Volume Shampoo 300ml",
            "description": "Salon-style specialty volume shampoo with botanical extracts",
            "category": "Personal Care",
            "subcategory": "Hair Care",
            "brand": "Ex-Vessel",
            "supplier": "Apex Salon Importers",
            "cost_price": 320.0,
            "selling_price": 490.0,
            "stock_quantity": 46,  # 50 originally ordered, only 4 sold in 60 days!
            "min_stock_alert": 10,
            "status": "active",
        },
        {
            "sku": "DEAD-202",
            "barcode": "890204002",
            "name": "UltraGleam Heavy Duty Citrus Floor Wax 1L",
            "description": "Commercial grade solvent floor wax for marble and tile",
            "category": "Household",
            "subcategory": "Surface Care",
            "brand": "UltraGleam",
            "supplier": "Vanguard Chemicals",
            "cost_price": 285.0,
            "selling_price": 420.0,
            "stock_quantity": 38,  # 40 ordered, only 2 sold in 75 days!
            "min_stock_alert": 5,
            "status": "active",
        },
        {
            "sku": "DEAD-203",
            "barcode": "890204003",
            "name": "KetoCrunch Roasted Sacha Inchi Seeds 200g",
            "description": "Exotic high-protein superfood snack with pink Himalayan salt",
            "category": "Packaged Food",
            "subcategory": "Healthy Snacks",
            "brand": "KetoCrunch",
            "supplier": "EcoBounty Direct",
            "cost_price": 340.0,
            "selling_price": 520.0,
            "stock_quantity": 29,  # 30 ordered, only 1 sold in 50 days!
            "min_stock_alert": 5,
            "status": "active",
        },
        # LOW STOCK ALERT PRODUCTS
        {
            "sku": "LOW-301",
            "barcode": "890305001",
            "name": "Amul Pure Cow Ghee 1L Tin",
            "description": "Aromatic traditional clarified butter",
            "category": "Grocery",
            "subcategory": "Dairy & Ghee",
            "brand": "Amul",
            "supplier": "GCMMF Logistics",
            "cost_price": 540.0,
            "selling_price": 630.0,
            "stock_quantity": 4,  # BELOW min_stock_alert (10)
            "min_stock_alert": 10,
            "status": "active",
        },
        {
            "sku": "LOW-302",
            "barcode": "890305002",
            "name": "Tata Tea Gold Premium Black Tea 500g",
            "description": "Assam long leaves with aromatic tea extract",
            "category": "Beverages",
            "subcategory": "Tea",
            "brand": "Tata Tea",
            "supplier": "Tata Consumer Products",
            "cost_price": 240.0,
            "selling_price": 310.0,
            "stock_quantity": 5,  # BELOW min_stock_alert (12)
            "min_stock_alert": 12,
            "status": "active",
        },
        # REGULAR STEADY PRODUCTS
        {
            "sku": "REG-401",
            "barcode": "890406001",
            "name": "Lays India's Magic Masala Chips 90g",
            "description": "Crispy sliced potato chips with spicy Indian masala",
            "category": "Packaged Food",
            "subcategory": "Snacks",
            "brand": "Lays",
            "supplier": "PepsiCo Retail Direct",
            "cost_price": 25.0,
            "selling_price": 35.0,
            "stock_quantity": 50,
            "min_stock_alert": 20,
            "status": "active",
        },
        {
            "sku": "REG-402",
            "barcode": "890406002",
            "name": "Dettol Antiseptic Liquid 250ml",
            "description": "Disinfectant liquid for first aid, surface and personal hygiene",
            "category": "Personal Care",
            "subcategory": "Health & First Aid",
            "brand": "Dettol",
            "supplier": "Reckitt Benckiser",
            "cost_price": 115.0,
            "selling_price": 149.0,
            "stock_quantity": 28,
            "min_stock_alert": 10,
            "status": "active",
        },
    ]

    created_products = {}
    for p_info in products_data:
        p = Product(**p_info)
        db_session.add(p)
        db_session.flush()
        created_products[p.sku] = p

        # Initial Restock transaction
        tx = InventoryTransaction(
            product_id=p.id,
            transaction_type="restock",
            quantity=p.stock_quantity
            + (
                4
                if p.sku == "DEAD-201"
                else (2 if p.sku == "DEAD-202" else (1 if p.sku == "DEAD-203" else 15))
            ),
            balance_after=p.stock_quantity,
            unit_cost=p.cost_price,
            reference_id=f"PO-{p.sku}-INIT",
            notes="Initial stock delivery",
            created_at=now - timedelta(days=60),
        )
        db_session.add(tx)

    db_session.commit()

    # 2. Realistic Recent Sales Transactions (Simulating POS activity)
    # Sales for Hero Products (frequent daily sales)
    hero1 = created_products["HERO-101"]
    hero2 = created_products["HERO-102"]
    hero3 = created_products["HERO-103"]
    dead1 = created_products["DEAD-201"]

    sales_history = [
        # Recent high-volume receipts
        {
            "receipt_no": "REC-202611-001",
            "payment_method": "upi",
            "customer_name": "Rohan Sharma",
            "customer_phone": "9876543210",
            "days_ago": 1,
            "items": [
                {"product": hero1, "qty": 2, "price": hero1.selling_price},
                {"product": hero2, "qty": 1, "price": hero2.selling_price},
            ],
        },
        {
            "receipt_no": "REC-202611-002",
            "payment_method": "cash",
            "customer_name": "Pooja Verma",
            "customer_phone": "9811223344",
            "days_ago": 2,
            "items": [
                {"product": hero3, "qty": 4, "price": hero3.selling_price},
                {"product": created_products["REG-401"], "qty": 3, "price": 35.0},
            ],
        },
        {
            "receipt_no": "REC-202611-003",
            "payment_method": "card",
            "customer_name": "Vikram Malhotra",
            "customer_phone": "9722334455",
            "days_ago": 3,
            "items": [
                {"product": created_products["HERO-104"], "qty": 2, "price": 145.0},
                {"product": created_products["HERO-105"], "qty": 1, "price": 475.0},
            ],
        },
        # Slow-moving shampoo sold 1 unit 25 days ago
        {
            "receipt_no": "REC-202610-098",
            "payment_method": "upi",
            "customer_name": "Ananya Joshi",
            "customer_phone": "9933445566",
            "days_ago": 25,
            "items": [
                {"product": dead1, "qty": 1, "price": dead1.selling_price},
            ],
        },
    ]

    for s_info in sales_history:
        subtotal = sum(it["qty"] * it["price"] for it in s_info["items"])
        tax = round(subtotal * 0.05, 2)  # 5% GST
        total = subtotal + tax

        sale = Sale(
            receipt_no=s_info["receipt_no"],
            subtotal=subtotal,
            tax_amount=tax,
            discount_amount=0.0,
            total_amount=total,
            payment_method=s_info["payment_method"],
            customer_name=s_info["customer_name"],
            customer_phone=s_info["customer_phone"],
            notes="Counter sale",
            created_at=now - timedelta(days=s_info["days_ago"]),
        )
        db_session.add(sale)
        db_session.flush()

        for it in s_info["items"]:
            prod = it["product"]
            item = SaleItem(
                sale_id=sale.id,
                product_id=prod.id,
                quantity=it["qty"],
                unit_price=it["price"],
                unit_cost=prod.cost_price,
                discount=0.0,
                total_price=it["qty"] * it["price"],
                is_bundle=False,
            )
            db_session.add(item)

    # 3. Pre-cached High-Quality AI Replacement Recommendations
    # For DEAD-201 (Ex-Vessel Shampoo with 46 units trapped, cost ₹320, selling ₹490)
    rec1 = AIRecommendation(
        product_id=dead1.id,
        recommended_title="L'Oreal Paris Total Repair 5 Keratin Shampoo 340ml",
        recommended_brand="L'Oreal Paris",
        recommended_price=279.0,
        recommended_rating=4.6,
        review_count=18450,
        value_quality_score=0.91,
        reasoning=(
            "Ex-Vessel sells at ₹490 with low brand trust and only 4 sales in 60 days (₹14,720 trapped capital). "
            "L'Oreal Paris Total Repair 5 addresses the identical hair-repair/keratin need at ₹279 (43% lower price point), "
            "commands 4.6★ across 18,000+ verified customer reviews, and has 3x faster shelf turnover in urban retail."
        ),
        source_url="https://www.lorealparis.co.in/products/hair-care/shampoo/total-repair-5",
        bundle_suggestion="Pair remaining Ex-Vessel stock with Dove Conditioner at 20% combo discount to liquidate trapped ₹14,720 capital.",
        status="pending",
        created_at=now - timedelta(days=2),
    )
    db_session.add(rec1)

    rec2 = AIRecommendation(
        product_id=dead1.id,
        recommended_title="Mamaearth Rosemary Anti-Hair Fall Shampoo 250ml",
        recommended_brand="Mamaearth",
        recommended_price=349.0,
        recommended_rating=4.5,
        review_count=12300,
        value_quality_score=0.88,
        reasoning=(
            "Trending organic/toxin-free formulation. Rosemary extract has +85% search volume growth this quarter. "
            "Wholesale supplier margins offer 32% margin vs 24% on Ex-Vessel."
        ),
        source_url="https://mamaearth.in/product/rosemary-anti-hair-fall-shampoo",
        bundle_suggestion="Promote alongside herbal hair oil in front counter display.",
        status="pending",
        created_at=now - timedelta(days=2),
    )
    db_session.add(rec2)

    db_session.commit()
    print("StorePulse database seeded successfully!")


if __name__ == "__main__":
    seed_data()
