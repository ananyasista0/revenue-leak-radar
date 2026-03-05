from datetime import datetime, timedelta
from database import get_db

async def compute_engagement_score(account_id: str, org_id: str) -> dict:
    db = get_db()
    now = datetime.utcnow()

    window_30_start = now - timedelta(days=30)
    window_60_start = now - timedelta(days=60)

    # ── Current 30 days ───────────────────────────────────
    current_sessions = await db.sessions.count_documents({
        "account_id": account_id,
        "org_id": org_id,
        "session_start": {"$gte": window_30_start.isoformat()}
    })

    current_events = await db.events.count_documents({
        "account_id": account_id,
        "org_id": org_id,
        "timestamp": {"$gte": window_30_start.isoformat()}
    })

    # avg session duration (current 30d)
    pipeline_duration = [
        {"$match": {
            "account_id": account_id,
            "org_id": org_id,
            "session_start": {"$gte": window_30_start.isoformat()}
        }},
        {"$group": {
            "_id": None,
            "avg_duration": {"$avg": "$duration_minutes"}
        }}
    ]
    duration_result = await db.sessions.aggregate(pipeline_duration).to_list(1)
    avg_duration = duration_result[0]["avg_duration"] if duration_result else 0

    # active users (current 30d)
    active_users = await db.sessions.distinct("user_id", {
        "account_id": account_id,
        "org_id": org_id,
        "session_start": {"$gte": window_30_start.isoformat()}
    })
    active_user_count = len(active_users)

    # ── Previous 30 days (days 60→30) ─────────────────────
    prev_sessions = await db.sessions.count_documents({
        "account_id": account_id,
        "org_id": org_id,
        "session_start": {
            "$gte": window_60_start.isoformat(),
            "$lt": window_30_start.isoformat()
        }
    })

    prev_events = await db.events.count_documents({
        "account_id": account_id,
        "org_id": org_id,
        "timestamp": {
            "$gte": window_60_start.isoformat(),
            "$lt": window_30_start.isoformat()
        }
    })

    # ── Engagement Score Formula ───────────────────────────
    # Weighted: sessions 40%, events 40%, avg duration 20%
    # Normalized to 0-100
    max_sessions = 90   # expected max in 30 days
    max_events = 300
    max_duration = 60   # minutes

    session_score  = min(current_sessions / max_sessions, 1.0) * 40
    event_score    = min(current_events / max_events, 1.0) * 40
    duration_score = min(avg_duration / max_duration, 1.0) * 20

    engagement_score = round(session_score + event_score + duration_score, 2)

    # ── Save to MongoDB ────────────────────────────────────
    record = {
        "org_id": org_id,
        "account_id": account_id,
        "computed_at": now.isoformat(),
        "window_days": 30,
        "current_sessions": current_sessions,
        "current_events": current_events,
        "prev_sessions": prev_sessions,
        "prev_events": prev_events,
        "avg_session_duration": round(avg_duration, 2),
        "active_user_count": active_user_count,
        "engagement_score": engagement_score
    }

    await db.engagement_scores.insert_one(record)
    return record


async def compute_all_accounts(org_id: str):
    db = get_db()
    accounts = await db.accounts.find(
        {"org_id": org_id, "status": "active"}
    ).to_list(1000)

    results = []
    for acc in accounts:
        result = await compute_engagement_score(acc["account_id"], org_id)
        results.append(result)
        print(f"Scored: {acc['account_id']} → {result['engagement_score']}")

    print(f"\nScored {len(results)} accounts")
    return results