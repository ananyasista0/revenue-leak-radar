from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import connect_db, close_db
from routes.engagement import router as engagement_router
from routes.drift import router as drift_router
from routes.revenue import router as revenue_router
from routes.accounts import router as accounts_router
from routes.overview import router as overview_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(
    title="Revenue Leak Radar",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engagement_router)
app.include_router(drift_router)
app.include_router(revenue_router)
app.include_router(accounts_router)
app.include_router(overview_router)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Revenue Leak Radar is running"}