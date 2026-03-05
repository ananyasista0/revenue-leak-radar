from fastapi import APIRouter
from services.engagement import compute_all_accounts, compute_engagement_score

router = APIRouter(prefix="/engagement", tags=["Engagement"])

@router.post("/compute/{org_id}")
async def compute_org_engagement(org_id: str):
    results = await compute_all_accounts(org_id)
    return {
        "status": "ok",
        "accounts_scored": len(results),
        "results": results
    }

@router.post("/compute/{org_id}/{account_id}")
async def compute_single_account(org_id: str, account_id: str):
    result = await compute_engagement_score(account_id, org_id)
    return {"status": "ok", "result": result}

@router.get("/scores/{org_id}")
async def get_scores(org_id: str):
    from database import get_db
    db = get_db()
    scores = await db.engagement_scores.find(
        {"org_id": org_id},
        {"_id": 0}
    ).sort("engagement_score", 1).to_list(1000)
    return {"status": "ok", "count": len(scores), "scores": scores}