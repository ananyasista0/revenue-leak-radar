import pandas as pd
import random
from datetime import datetime, timedelta

random.seed(42)

ORG_ID = "org_001"
NUM_ACCOUNTS = 20
NUM_USERS_PER_ACCOUNT = 3

# ── accounts ──────────────────────────────────────────────
plans = [("starter", 99), ("pro", 299), ("enterprise", 799)]
accounts = []
for i in range(1, NUM_ACCOUNTS + 1):
    plan, price = random.choice(plans)
    signup = datetime(2024, random.randint(1, 6), random.randint(1, 28))
    accounts.append({
        "account_id": f"acc_{i:03d}",
        "org_id": ORG_ID,
        "organization_name": f"Company {i}",
        "plan_type": plan,
        "monthly_price": price,
        "billing_cycle": "monthly",
        "signup_date": signup.strftime("%Y-%m-%d"),
        "renewal_date": (signup + timedelta(days=365)).strftime("%Y-%m-%d"),
        "status": random.choice(["active", "active", "active", "churned"])
    })

pd.DataFrame(accounts).to_csv("data/accounts.csv", index=False)
print(f"accounts.csv — {len(accounts)} rows")

# ── users ─────────────────────────────────────────────────
users = []
for acc in accounts:
    for j in range(1, NUM_USERS_PER_ACCOUNT + 1):
        users.append({
            "user_id": f"usr_{acc['account_id']}_{j}",
            "org_id": ORG_ID,
            "account_id": acc["account_id"],
            "email": f"user{j}@{acc['organization_name'].lower().replace(' ', '')}.com",
            "created_at": acc["signup_date"]
        })

pd.DataFrame(users).to_csv("data/users.csv", index=False)
print(f"users.csv — {len(users)} rows")

# ── sessions ──────────────────────────────────────────────
features = ["dashboard_view", "export_report", "integration_enabled",
            "api_call", "settings_update", "report_view"]

sessions = []
events = []
event_id = 1

for acc in accounts:
    # churned accounts get low activity in last 30 days
    is_churning = acc["status"] == "churned" or random.random() < 0.3

    for user in [u for u in users if u["account_id"] == acc["account_id"]]:
        # last 60 days of sessions
        for day_offset in range(60, 0, -1):
            date = datetime.now() - timedelta(days=day_offset)

            # churning accounts drop off after day 30
            if is_churning and day_offset < 30:
                if random.random() < 0.85:
                    continue

            if random.random() < 0.6:
                start = date.replace(
                    hour=random.randint(8, 18),
                    minute=random.randint(0, 59)
                )
                duration = random.randint(5, 90)
                end = start + timedelta(minutes=duration)

                sessions.append({
                    "session_id": f"sess_{acc['account_id']}_{user['user_id']}_{day_offset}",
                    "org_id": ORG_ID,
                    "account_id": acc["account_id"],
                    "user_id": user["user_id"],
                    "session_start": start.isoformat(),
                    "session_end": end.isoformat(),
                    "duration_minutes": duration
                })

                # 1-4 events per session
                for _ in range(random.randint(1, 4)):
                    events.append({
                        "event_id": f"evt_{event_id:06d}",
                        "org_id": ORG_ID,
                        "account_id": acc["account_id"],
                        "user_id": user["user_id"],
                        "feature_name": random.choice(features),
                        "event_type": "click",
                        "timestamp": start.isoformat()
                    })
                    event_id += 1

pd.DataFrame(sessions).to_csv("data/sessions.csv", index=False)
pd.DataFrame(events).to_csv("data/events.csv", index=False)
print(f"sessions.csv — {len(sessions)} rows")
print(f"events.csv   — {len(events)} rows")

# ── invoices ──────────────────────────────────────────────
invoices = []
for acc in accounts:
    for month_offset in range(6, 0, -1):
        invoice_date = datetime.now() - timedelta(days=30 * month_offset)
        churned_this_month = acc["status"] == "churned" and month_offset == 1
        invoices.append({
            "invoice_id": f"inv_{acc['account_id']}_{month_offset}",
            "org_id": ORG_ID,
            "account_id": acc["account_id"],
            "invoice_date": invoice_date.strftime("%Y-%m-%d"),
            "mrr": 0 if churned_this_month else acc["monthly_price"],
            "downgrade_flag": False,
            "upgrade_flag": False,
            "churn_flag": churned_this_month
        })

pd.DataFrame(invoices).to_csv("data/invoices.csv", index=False)
print(f"invoices.csv — {len(invoices)} rows")

print("\nSample data generation complete.")