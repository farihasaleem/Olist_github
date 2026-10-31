
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime, timedelta
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

# Common filters for order-based analytics
def get_filters(start_date, end_date, state):
    conditions = [
        "o.order_status NOT IN ('canceled', 'unavailable')"
    ]
    params = {}

    if start_date:
        conditions.append("o.order_purchase_timestamp >= :start_date")
        params["start_date"] = start_date

    if end_date:
        conditions.append("o.order_purchase_timestamp < :end_date")
        params["end_date"] = end_date + timedelta(days=1)

    if state:
        conditions.append("c.customer_state = :state")
        params["state"] = state.upper()

    return " AND ".join(conditions), params


def filters_params(
    start_date: date = None,
    end_date: date = None,
    state: str = None
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "Start date must not exceed end date")

    if state and len(state) != 2:
        raise HTTPException(422, "State must contain 2 letters")

    return get_filters(start_date, end_date, state)


# 1. Dashboard Summary
@router.get("/summary")
def summary(
    start_date: date = None,
    end_date: date = None,
    state: str = None,
    db: Session = Depends(get_db)
):
    where, params = filters_params(start_date, end_date, state)

    revenue = db.execute(text(f"""
        SELECT COALESCE(SUM(i.price), 0)
        FROM order_items i
        JOIN orders o ON i.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where}
    """), params).scalar()

    orders = db.execute(text(f"""
        SELECT COUNT(DISTINCT o.order_id)
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where}
    """), params).scalar()

    avg_review = db.execute(text(f"""
        SELECT COALESCE(AVG(r.avg_score), 0)
        FROM (
            SELECT order_id, AVG(review_score) AS avg_score
            FROM order_reviews
            GROUP BY order_id
        ) r
        JOIN orders o ON r.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where}
    """), params).scalar()

    delivery = db.execute(text(f"""
        SELECT
            COUNT(CASE
                WHEN o.order_delivered_customer_date >
                     o.order_estimated_delivery_date
                THEN 1 END),
            COUNT(*)
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where}
        AND o.order_status = 'delivered'
        AND o.order_delivered_customer_date IS NOT NULL
    """), params).fetchone()

    late_pct = (delivery[0] / delivery[1] * 100) if delivery[1] else 0

    return {
        "total_revenue": float(revenue or 0),
        "total_orders": int(orders or 0),
        "avg_order_value": float(revenue / orders) if orders else 0,
        "avg_review_score": float(avg_review or 0),
        "pct_late_deliveries": round(late_pct, 2)
    }


# 2. Revenue by Month
@router.get("/revenue-by-month")
def revenue_by_month(
    start_date: date = None,
    end_date: date = None,
    state: str = None,
    db: Session = Depends(get_db)
):
    where, params = filters_params(start_date, end_date, state)

    rows = db.execute(text(f"""
        SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month,
               SUM(i.price) AS revenue
        FROM order_items i
        JOIN orders o ON i.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where}
        GROUP BY month
        ORDER BY month
    """), params).fetchall()

    return {
        "labels": [str(r[0]) for r in rows],
        "values": [float(r[1]) for r in rows]
    }


# 3. Top Product Categories
@router.get("/top-categories")
def top_categories(
    limit: int = Query(10, ge=1, le=30),
    start_date: date = None,
    end_date: date = None,
    state: str = None,
    db: Session = Depends(get_db)
):
    where, params = filters_params(start_date, end_date, state)
    params["limit"] = limit

    rows = db.execute(text(f"""
        SELECT COALESCE(ct.product_category_name_english, 'unknown') AS category,
               SUM(i.price) AS revenue
        FROM order_items i
        JOIN orders o ON i.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN products p ON i.product_id = p.product_id
        LEFT JOIN category_translation ct
            ON p.product_category_name = ct.product_category_name
        WHERE {where}
        GROUP BY category
        ORDER BY revenue DESC
        LIMIT :limit
    """), params).fetchall()

    return {
        "labels": [r[0] for r in rows],
        "values": [float(r[1]) for r in rows]
    }


# 4. Orders by State
@router.get("/orders-by-state")
def orders_by_state(
    start_date: date = None,
    end_date: date = None,
    state: str = None,
    db: Session = Depends(get_db)
):
    where, params = filters_params(start_date, end_date, state)

    rows = db.execute(text(f"""
        SELECT c.customer_state, COUNT(DISTINCT o.order_id) AS total
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where}
        GROUP BY c.customer_state
        ORDER BY total DESC
    """), params).fetchall()

    return {
        "labels": [r[0] for r in rows],
        "values": [int(r[1]) for r in rows]
    }


# 5. Payment Types
@router.get("/payment-types")
def payment_types(
    start_date: date = None,
    end_date: date = None,
    state: str = None,
    db: Session = Depends(get_db)
):
    where, params = filters_params(start_date, end_date, state)

    rows = db.execute(text(f"""
        SELECT p.payment_type, COUNT(*) AS total
        FROM order_payments p
        JOIN orders o ON p.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where}
        GROUP BY p.payment_type
        ORDER BY total DESC
    """), params).fetchall()

    return {
        "labels": [r[0] for r in rows],
        "values": [int(r[1]) for r in rows]
    }


# 6. Review Score vs Delivery
@router.get("/review-vs-delivery")
def review_vs_delivery(
    start_date: date = None,
    end_date: date = None,
    state: str = None,
    db: Session = Depends(get_db)
):
    where, params = filters_params(start_date, end_date, state)

    rows = db.execute(text(f"""
        SELECT
            CASE
                WHEN o.order_delivered_customer_date >
                     o.order_estimated_delivery_date
                THEN 'Late'
                ELSE 'On time'
            END AS delivery_group,
            ROUND(AVG(r.avg_score), 2) AS avg_score,
            ROUND(r.avg_score) AS score,
            COUNT(*) AS total
        FROM (
            SELECT order_id, AVG(review_score) AS avg_score
            FROM order_reviews
            GROUP BY order_id
        ) r
        JOIN orders o ON r.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where}
        AND o.order_status = 'delivered'
        AND o.order_delivered_customer_date IS NOT NULL
        AND o.order_estimated_delivery_date IS NOT NULL
        GROUP BY delivery_group, score
    """), params).fetchall()

    distribution = {
        "on_time": [0, 0, 0, 0, 0],
        "late": [0, 0, 0, 0, 0]
    }

    averages = {"On time": [], "Late": []}

    for group, avg, score, count in rows:
        if score is not None and 1 <= int(score) <= 5:
            key = "late" if group == "Late" else "on_time"
            distribution[key][int(score) - 1] += int(count)

        averages[group].append((float(avg), int(count)))

    avg_scores = []
    for group in ["On time", "Late"]:
        values = averages[group]
        total = sum(count for _, count in values)
        average = (
            sum(avg * count for avg, count in values) / total
            if total else 0
        )
        avg_scores.append(round(average, 2))

    return {
        "labels": ["On time", "Late"],
        "avg_scores": avg_scores,
        "distribution": distribution
    }
