import pandas as pd
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Fix: correct path to .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "revenue_leak_radar")

print(f"Connecting to: {MONGO_URI[:30]}...")  # shows first 30 chars to verify

async def load():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    collections = ["accounts", "users", "sessions", "events", "invoices"]

    for name in collections:
        df = pd.read_csv(f"data/{name}.csv")
        records = df.to_dict("records")

        await db[name].delete_many({})
        await db[name].insert_many(records)
        print(f"Loaded {len(records)} records into '{name}'")

    client.close()
    print("\nAll data loaded into MongoDB.")

asyncio.run(load())