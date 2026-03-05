from datetime import datetime
from database import get_db


def calculate_revenue_at_risk(mrr: float, churn_probability: float) -> float:
    return round(mrr * churn_probability, 2)


def estimate_churn_probability(drift_percentage: float, renewal_days: int) -> float:
    # base probability from drift
    if drift_percentage <= -60:
        base = 0.90
    elif drift_percentage <= -40:
        base = 0.70
    elif drift_percentage <= -30:
        base = 0.55
    elif drift_percentage <= -10:
        base = 0.30
    elif drift_percentage <= 0:
        base = 0.10
    else:
        base = 0.05

    # renewal proximity multiplier
    if renewal_days <= 14:
        multiplier = 1.4
    elif renewal_days <= 30:
        multiplier = 1.2
    else:
        multiplier = 1.0

    probability = min(base * multiplier, 1.0)
    return round(probability, 2)


async def compute_revenue_risk(org_id: str) -> dict:
    db = get_db()

    # get latest drift metric per account
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

    if not drift_records:
        return {"error": "No drift data found. Run /drift/compute first."}

    total_mrr = 0
    total_revenue_at_risk = 0
    account_risks = []

    for record in drift_records:
        mrr = record.get("mrr", 0)
        drift_pct = record.get("drift_percentage", 0)
        renewal_days = record.get("renewal_days_remaining", 365)
        account_id = record.get("account_id")

        churn_prob = estimate_churn_probability(drift_pct, renewal_days)
        revenue_at_risk = calculate_revenue_at_risk(mrr, churn_prob)

        total_mrr += mrr
        total_revenue_at_risk += revenue_at_risk

        risk_record = {
            "org_id": org_id,
            "account_id": account_id,
            "mrr": mrr,
            "drift_percentage": drift_pct,
            "risk_category": record.get("risk_category", "Low"),
            "renewal_days_remaining": renewal_days,
            "churn_probability": churn_prob,
            "revenue_at_risk": revenue_at_risk,
            "flags": record.get("flags", []),
            "computed_at": datetime.utcnow().isoformat()
        }

        # save to churn_predictions collection
        await db.churn_predictions.insert_one(risk_record)
        risk_record.pop("_id", None)
        account_risks.append(risk_record)

    # sort by revenue at risk descending
    account_risks.sort(key=lambda x: x["revenue_at_risk"], reverse=True)

    summary = {
        "org_id": org_id,
        "total_mrr": round(total_mrr, 2),
        "total_revenue_at_risk": round(total_revenue_at_risk, 2),
        "risk_percentage": round((total_revenue_at_risk / total_mrr * 100), 2) if total_mrr > 0 else 0,
        "high_risk_accounts": len([a for a in account_risks if a["risk_category"] == "High"]),
        "accounts": account_risks
    }

    print(f"\nTotal MRR:          ${total_mrr}")
    print(f"Revenue at Risk:    ${round(total_revenue_at_risk, 2)}")
    print(f"Risk %:             {summary['risk_percentage']}%")
    print(f"High risk accounts: {summary['high_risk_accounts']}")

    return summary