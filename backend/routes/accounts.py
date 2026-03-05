from fastapi import APIRouter
from fastapi.responses import JSONResponse
from database import get_db

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/{org_id}")
async def get_all_accounts(org_id: str):
    db = get_db()
    accounts = await db.accounts.find(
        {"org_id": org_id},
        {"_id": 0}
    ).to_list(1000)
    return {"status": "ok", "count": len(accounts), "accounts": accounts}


@router.get("/{org_id}/{account_id}")
async def get_account_detail(org_id: str, account_id: str):
    db = get_db()

    account = await db.accounts.find_one(
        {"org_id": org_id, "account_id": account_id},
        {"_id": 0}
    )
    if not account:
        return JSONResponse(status_code=404, content={"error": "Account not found"})

    # latest engagement score
    scores = await db.engagement_scores.find(
        {"org_id": org_id, "account_id": account_id},
        {"_id": 0}
    ).sort("computed_at", -1).to_list(10)

    # latest drift
    drift = await db.drift_metrics.find_one(
        {"org_id": org_id, "account_id": account_id},
        {"_id": 0},
        sort=[("computed_at", -1)]
    )

    # latest revenue risk
    revenue = await db.churn_predictions.find_one(
        {"org_id": org_id, "account_id": account_id},
        {"_id": 0},
        sort=[("computed_at", -1)]
    )

    # recent events
    events = await db.events.find(
        {"org_id": org_id, "account_id": account_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(20)

    return {
        "status": "ok",
        "account": account,
        "engagement_history": scores,
        "latest_drift": drift,
        "revenue_risk": revenue,
        "recent_events": events
    }