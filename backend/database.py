from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client = None
db = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(
        settings.mongo_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    db = client[settings.db_name]
    print(f"Connected to MongoDB: {settings.db_name}")
    await create_indexes()

async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed")

def get_db():
    return db

async def create_indexes():
    print("Creating indexes...")

    await db.organizations.create_index("api_key", unique=True)
    await db.accounts.create_index("org_id")
    await db.accounts.create_index([("org_id", 1), ("status", 1)])
    await db.users.create_index("org_id")
    await db.users.create_index("account_id")
    await db.sessions.create_index("org_id")
    await db.sessions.create_index("account_id")
    await db.sessions.create_index("user_id")
    await db.sessions.create_index("session_start")
    await db.events.create_index("org_id")
    await db.events.create_index("account_id")
    await db.events.create_index("user_id")
    await db.events.create_index("timestamp")
    await db.events.create_index([("account_id", 1), ("timestamp", -1)])
    await db.invoices.create_index("org_id")
    await db.invoices.create_index("account_id")
    await db.invoices.create_index("invoice_date")
    await db.engagement_scores.create_index("org_id")
    await db.engagement_scores.create_index("account_id")
    await db.engagement_scores.create_index([("account_id", 1), ("computed_at", -1)])
    await db.drift_metrics.create_index("org_id")
    await db.drift_metrics.create_index("account_id")
    await db.drift_metrics.create_index("risk_category")
    await db.drift_metrics.create_index([("account_id", 1), ("computed_at", -1)])
    await db.churn_predictions.create_index("org_id")
    await db.churn_predictions.create_index("account_id")
    await db.churn_predictions.create_index([("account_id", 1), ("predicted_at", -1)])

    print("All indexes created")