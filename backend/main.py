from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.config import settings
from utils.db import init_db
from routes import auth, donations, ngo, delivery, admin, feedback


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Food Waste Management API",
    version="2.0.0",
    description=(
        "Restaurants post leftover food, nearby NGOs claim it for the people they "
        "serve, and the nearest delivery partner moves it from the restaurant to the NGO."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, donations, ngo, delivery, admin, feedback):
    app.include_router(module.router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
