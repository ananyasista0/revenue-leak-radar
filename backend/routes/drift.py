from fastapi import APIRouter
from services.drift import compute_all_drift, compute_drift

router = APIRouter(prefix="/drift", tags=["Drift"])

@router.post("/compute/{org_id}")
async def compute_org_drift(org_id: str):
    results = await compute_all_drift(org_id)
    return {
        "status": "ok",
        "total": len(results),
        "high_risk": len([r for r in results if r["risk_category"] == "High"]),
        "medium_risk": len([r for r in results if r["risk_category"] == "Medium"]),
        "low_risk": len([r for r in results if r["risk_category"] == "Low"]),
        "results": results
    }

@router.post("/compute/{org_id}/{account_id}")
async def compute_single_drift(org_id: str, account_id: str):
    result = await compute_drift(account_id, org_id)
    return {"status": "ok", "result": result}

@router.get("/risk/{org_id}")
async def get_risk_accounts(org_id: str, category: str = None):
    from database import get_db
    db = get_db()
    query = {"org_id": org_id}
    if category:
        query["risk_category"] = category
    results = await db.drift_metrics.find(
        query, {"_id": 0}
    ).sort("drift_percentage", 1).to_list(1000)
    return {
        "status": "ok",
        "count": len(results),
        "results": results
    }