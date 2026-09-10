from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Feedback, User
from schemas import FeedbackIn, FeedbackOut
from utils.db import get_db
from utils.auth import require_admin

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=201)
async def submit_feedback(body: FeedbackIn, db: AsyncSession = Depends(get_db)):
    fb = Feedback(name=body.name, email=body.email, message=body.message)
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


@router.get("", response_model=List[FeedbackOut])
async def list_feedback(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Feedback).order_by(Feedback.created_at.desc()))).scalars().all()
    return rows
