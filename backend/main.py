"""FastAPI entry point for the ForensicGuard service."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.core.database import Base, engine
from backend.app.core.logging import log_forensic_event
import backend.app.models.db_models  # Ensure SQLAlchemy model registration before create_all.


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    log_forensic_event("service_started")
    yield
    log_forensic_event("service_stopped")


app = FastAPI(title="ForensicGuard AI", version="1.0.0-research", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True,
                   allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(router)
