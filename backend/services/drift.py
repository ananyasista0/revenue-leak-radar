from datetime import datetime, timedelta
from database import get_db


def calculate_drift(current_score: float, previous_score: float) -> dict:
    if previous_score == 0:
        return {
            "drift_percentage": 0.0,
            "drift_velocity": 0.0,
            "risk_category": "Low"
        }

    drift_pct = ((current_score - previous_score) / previous_score) * 100
    drift_pct = round(drift_pct, 2)
    drift_velocity = round(drift_pct / 4, 2)

    if drift_pct <= -30:
        risk = "High"
    elif drift_pct <= -10:
        risk = "Medium"
    else:
        risk = "Low"

    return {
        "drift_percentage": drift_pct,
        "drift_velocity": drift_velocity,
        "risk_category": risk
    }


def get_drift_flags(current: dict, prev: dict, renewal_days: int) -> list:
    flags = []

    prev_sessions = prev.get("current_sessions", 0)
    if prev_sessions > 0:
        session_drop = ((current.get("current_sessions", 0) - prev_sessions) / prev_sessions) * 100
        if session_drop <= -40:
            flags.append("severe_session_drop")
        elif session_drop <= -20:
            flags.append("session_decline")

    prev_events = prev.get("current_events", 0)
    if prev_events > 0:
        event_drop = ((current.get("current_events", 0) - prev_events) / prev_events) * 100
        if event_drop <= -40:
            flags.append("feature_abandonment")
        elif event_drop <= -20:
            flags.append("reduced_feature_usage")

    prev_users = prev.get("active_user_count", 0)
    if prev_users > 0:
        user_drop = ((current.get("active_user_count", 0) - prev_users) / prev_users) * 100
        if user_drop <= -50:
            flags.append("active_user_drop")

    if renewal_days <= 14:
        flags.append("renewal_critical")
    elif renewal_days <= 30:
        flags.append("renewal_imminent")

    return flags


async def compute_drift(account_id: str, org_id: str) -> dict:
    db = get_db()
    now = datetime.utcnow()

    all_scores = await db.engagement_scores.find(
        {"account_id": account_id, "org_id": org_id},
        {"_id": 0}
    ).to_list(1000)

    if not all_scores:
        return {"error": f"No engagement scores found for {account_id}"}

    all_scores.sort(key=lambda x: str(x.get("computed_at", "")), reverse=True)

    current = all_scores[0]
    current_score = current.get("engagement_score", 0)

    prev_sessions = current.get("prev_sessions", 0)
    prev_events = current.get("prev_events", 0)

    max_sessions = 90
    max_events = 300

    ps = min(prev_sessions / max_sessions, 1.0) * 40
    pe = min(prev_events / max_events, 1.0) * 40
    prev_score_val = round(ps + pe, 2)

    synthetic_prev = {
        "current_sessions": prev_sessions,
        "current_events": prev_events,
        "active_user_count": current.get("active_user_count", 1),
        "engagement_score": prev_score_val
    }

    account = await db.accounts.find_one(
        {"account_id": account_id, "org_id": org_id}
    )

    if not account:
        return {"error": f"Account {account_id} not found"}

    try:
        renewal_date = datetime.strptime(str(account["renewal_date"]), "%Y-%m-%d")
    except Exception:
        renewal_date = now + timedelta(days=365)

    renewal_days = max((renewal_date - now).days, 0)

    drift_data = calculate_drift(current_score, prev_score_val)
    flags = get_drift_flags(current, synthetic_prev, renewal_days)

    record = {
        "org_id": org_id,
        "account_id": account_id,
        "computed_at": now.isoformat(),
        "current_score": current_score,
        "previous_score": prev_score_val,
        "drift_percentage": drift_data["drift_percentage"],
        "drift_velocity": drift_data["drift_velocity"],
        "risk_category": drift_data["risk_category"],
        "renewal_days_remaining": renewal_days,
        "flags": flags,
        "mrr": account.get("monthly_price", 0)
    }

    await db.drift_metrics.insert_one(record)
    record.pop("_id", None)
    return record


async def compute_all_drift(org_id: str) -> list:
    db = get_db()

    try:
        accounts = await db.accounts.find(
            {"org_id": org_id, "status": "active"}
        ).to_list(1000)

        print(f"Found {len(accounts)} active accounts for {org_id}")

        if not accounts:
            print("No active accounts found - check org_id and status field")
            return []

        results = []
        for acc in accounts:
            try:
                result = await compute_drift(acc["account_id"], org_id)
                if "error" not in result:
                    results.append(result)
                    print(
                        f"{acc['account_id']} | "
                        f"score: {result['current_score']} | "
                        f"drift: {result['drift_percentage']}% | "
                        f"risk: {result['risk_category']}"
                    )
                else:
                    print(f"SKIP {acc['account_id']}: {result['error']}")
            except Exception as e:
                print(f"ERROR on {acc['account_id']}: {str(e)}")
                import traceback
                traceback.print_exc()

        high = [r for r in results if r["risk_category"] == "High"]
        med  = [r for r in results if r["risk_category"] == "Medium"]
        print(f"\nHigh: {len(high)} | Medium: {len(med)} | Total: {len(results)}")
        return results

    except Exception as e:
        print(f"FATAL ERROR in compute_all_drift: {str(e)}")
        import traceback
        traceback.print_exc()
        return []