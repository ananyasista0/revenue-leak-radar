from fastapi import APIRouter
from database import get_db

router = APIRouter(prefix="/overview", tags=["Overview"])


@router.get("/{org_id}")
async def get_overview(org_id: str):
    db = get_db()

    # account counts
    total_accounts = await db.accounts.count_documents({"org_id": org_id})
    active_accounts = await db.accounts.count_documents({"org_id": org_id, "status": "active"})
    churned_accounts = await db.accounts.count_documents({"org_id": org_id, "status": "churned"})

    # risk counts from latest drift per account
    pipeline = [
        {"$match": {"org_id": org_id}},
        {"$sort": {"computed_at": -1}},
        {"$group": {
            "_id": "$account_id",
            "latest": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$latest"}}
    ]
    drift_records = await db.drift_metrics.aggregate(pipeline).to_list(1000)

    high_risk = len([r for r in drift_records if r["risk_category"] == "High"])
    medium_risk = len([r for r in drift_records if r["risk_category"] == "Medium"])
    low_risk = len([r for r in drift_records if r["risk_category"] == "Low"])

    # revenue summary from latest churn predictions
    revenue_pipeline = [
        {"$match": {"org_id": org_id}},
        {"$sort": {"computed_at": -1}},
        {"$group": {
            "_id": "$account_id",
            "latest": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$latest"}},
        {"$group": {
            "_id": None,
            "total_mrr": {"$sum": "$mrr"},
            "total_risk": {"$sum": "$revenue_at_risk"}
        }}
    ]
    revenue_result = await db.churn_predictions.aggregate(revenue_pipeline).to_list(1)
    total_mrr = revenue_result[0]["total_mrr"] if revenue_result else 0
    total_risk = revenue_result[0]["total_risk"] if revenue_result else 0

    # top 5 at risk accounts
    top_risk = sorted(drift_records, key=lambda x: x.get("drift_percentage", 0))[:5]
    for r in top_risk:
        r.pop("_id", None)

    return {
        "status": "ok",
        "accounts": {
            "total": total_accounts,
            "active": active_accounts,
            "churned": churned_accounts
        },
        "risk_distribution": {
            "high": high_risk,
            "medium": medium_risk,
            "low": low_risk
        },
        "revenue": {
            "total_mrr": round(total_mrr, 2),
            "revenue_at_risk": round(total_risk, 2),
            "risk_percentage": round((total_risk / total_mrr * 100), 2) if total_mrr > 0 else 0
        },
        "top_risk_accounts": top_risk
    }