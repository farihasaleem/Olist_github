
from pydantic import BaseModel
from typing import List, Dict


# 1. Dashboard summary
class SummaryResponse(BaseModel):
    total_revenue: float
    total_orders: int
    avg_order_value: float
    avg_review_score: float
    pct_late_deliveries: float


# 2. Revenue by month
class ChartResponse(BaseModel):
    labels: List[str]
    values: List[float]


# 3. Review vs delivery
class ReviewDeliveryResponse(BaseModel):
    labels: List[str]
    avg_scores: List[float]
    distribution: Dict[str, List[int]]
