from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from app.database import get_db

router = APIRouter()

ALLOWED_TABLES = [
    "customers", "sellers", "products",
    "category_translation", "orders",
    "order_items", "order_payments", "order_reviews"
]


def get_info(table_name, db):
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(400, "Invalid table")

    inspector = inspect(db.bind)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    primary_keys = inspector.get_pk_constraint(table_name)["constrained_columns"]

    return columns, primary_keys


@router.get("/{table_name}")
def get_table(table_name: str, db: Session = Depends(get_db)):
    get_info(table_name, db)

    rows = db.execute(
        text(f"SELECT * FROM `{table_name}` LIMIT 100")
    ).mappings().all()

    return {"records": [dict(row) for row in rows]}


@router.get("/{table_name}/columns")
def get_columns(table_name: str, db: Session = Depends(get_db)):
    columns, primary_keys = get_info(table_name, db)

    return {
        "columns": columns,
        "primary_keys": primary_keys
    }


@router.get("/{table_name}/search")
def search_table(table_name: str, q: str, db: Session = Depends(get_db)):
    columns, _ = get_info(table_name, db)

    conditions = " OR ".join(
        f"CAST(`{col}` AS CHAR) LIKE :q" for col in columns
    )

    rows = db.execute(
        text(f"SELECT * FROM `{table_name}` WHERE {conditions} LIMIT 100"),
        {"q": f"%{q}%"}
    ).mappings().all()

    return {"records": [dict(row) for row in rows]}


@router.post("/{table_name}")
def add_record(
    table_name: str,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    columns, _ = get_info(table_name, db)
    values = data.get("values", {})

    if not values or not set(values).issubset(columns):
        raise HTTPException(400, "Invalid or empty values")

    names = list(values.keys())
    sql_columns = ", ".join(f"`{c}`" for c in names)
    placeholders = ", ".join(f":{c}" for c in names)

    try:
        db.execute(
            text(f"INSERT INTO `{table_name}` ({sql_columns}) VALUES ({placeholders})"),
            values
        )
        db.commit()
        return {"message": "Record added successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))


@router.put("/{table_name}")
def update_record(
    table_name: str,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    columns, primary_keys = get_info(table_name, db)

    keys = data.get("primary_key", {})
    values = data.get("values", {})

    if not primary_keys or set(keys) != set(primary_keys):
        raise HTTPException(400, "Provide all primary key values")

    if not values or not set(values).issubset(columns):
        raise HTTPException(400, "Invalid or empty values")

    if set(values).intersection(primary_keys):
        raise HTTPException(400, "Primary keys cannot be changed")

    assignments = ", ".join(f"`{c}` = :v_{c}" for c in values)
    conditions = " AND ".join(f"`{c}` = :k_{c}" for c in primary_keys)

    params = {f"v_{c}": v for c, v in values.items()}
    params.update({f"k_{c}": v for c, v in keys.items()})

    try:
        result = db.execute(
            text(f"UPDATE `{table_name}` SET {assignments} WHERE {conditions}"),
            params
        )
        db.commit()
        return {"message": "Update completed", "rows_affected": result.rowcount}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))


@router.delete("/{table_name}")
def delete_record(
    table_name: str,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    _, primary_keys = get_info(table_name, db)
    keys = data.get("primary_key", {})

    if not primary_keys or set(keys) != set(primary_keys):
        raise HTTPException(400, "Provide all primary key values")

    conditions = " AND ".join(f"`{c}` = :{c}" for c in primary_keys)

    try:
        result = db.execute(
            text(f"DELETE FROM `{table_name}` WHERE {conditions}"),
            keys
        )
        db.commit()
        return {"message": "Delete completed", "rows_affected": result.rowcount}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))