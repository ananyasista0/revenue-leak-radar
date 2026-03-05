from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.revenue import compute_revenue_risk

router = APIRouter(prefix="/revenue", tags=["Revenue"])

@router.post("/compute/{org_id}")
async def compute_org_revenue_risk(org_id: str):
    try:
        result = await compute_revenue_risk(org_id)
        if "error" in result:
            return JSONResponse(status_code=400, content=result)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/summary/{org_id}")
async def get_revenue_summary(org_id: str):
    from database import get_db
    db = get_db()

    pipeline = [
        {"$match": {"org_id": org_id}},
        {"$sort": {"computed_at": -1}},
        {"$group": {
            "_id": "$account_id",
            "latest": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$latest"}},
        {"$project": {"_id": 0}},
        {"$sort": {"revenue_at_risk": -1}}
    ]

    accounts = await db.churn_predictions.aggregate(pipeline).to_list(1000)
    total_mrr = sum(a.get("mrr", 0) for a in accounts)
    total_risk = sum(a.get("revenue_at_risk", 0) for a in accounts)

    return {
        "status": "ok",
        "total_mrr": round(total_mrr, 2),
        "total_revenue_at_risk": round(total_risk, 2),
        "risk_percentage": round((total_risk / total_mrr * 100), 2) if total_mrr > 0 else 0,
        "accounts": accounts
    }