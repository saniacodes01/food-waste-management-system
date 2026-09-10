from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Donation, Feedback
from schemas import UserOut, DonationOut, AdminStats, ApprovalUpdate
from utils.db import get_db
from utils.auth import require_admin
from services.matching import log_event, nearest_delivery_partner
from services.serialize import donation_out, DONATION_LOADS

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def stats(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    users_by_role = dict(
        (await db.execute(select(User.role, func.count()).group_by(User.role))).all()
    )
    donations_by_status = dict(
        (await db.execute(select(Donation.status, func.count()).group_by(Donation.status))).all()
    )
    feedback_count = (await db.execute(select(func.count()).select_from(Feedback))).scalar_one()
    return AdminStats(
        users={**{r: 0 for r in ("restaurant", "ngo", "delivery", "admin")}, **users_by_role},
        donations=donations_by_status,
        feedback_count=feedback_count,
    )


@router.get("/users", response_model=List[UserOut])
async def list_users(
    role: Optional[str] = Query(None),
    pending: bool = Query(False, description="only accounts awaiting approval"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc())
    if role:
        stmt = stmt.where(User.role == role)
    if pending:
        stmt = stmt.where(User.is_approved.is_(False))
    return (await db.execute(stmt)).scalars().all()


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: ApprovalUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/donations", response_model=List[DonationOut])
async def list_donations(
    status: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Donation).options(*DONATION_LOADS).order_by(Donation.created_at.desc())
    if status:
        stmt = stmt.where(Donation.status == status)
    if city:
        stmt = stmt.where(Donation.city == city)
    rows = (await db.execute(stmt)).scalars().all()
    return [donation_out(d) for d in rows]


@router.post("/donations/{donation_id}/assign/{delivery_id}", response_model=DonationOut)
async def assign_delivery(
    donation_id: int,
    delivery_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    donation = (await db.execute(select(Donation).where(Donation.id == donation_id))).scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    if donation.status not in ("claimed", "assigned"):
        raise HTTPException(status_code=409, detail=f"Donation is '{donation.status}', cannot assign")
    partner = (await db.execute(
        select(User).where(User.id == delivery_id, User.role == "delivery")
    )).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Delivery partner not found")
    donation.delivery_by_id = partner.id
    donation.status = "assigned"
    await log_event(db, donation, "assigned", note=f"admin assigned {partner.name}")
    await db.commit()
    fresh = await db.execute(
        select(Donation).where(Donation.id == donation_id).options(*DONATION_LOADS)
    )
    return donation_out(fresh.scalar_one())


@router.get("/donations/{donation_id}/nearest-delivery", response_model=Optional[UserOut])
async def suggest_delivery(
    donation_id: int,
    radius_km: float = Query(default=None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    donation = (await db.execute(select(Donation).where(Donation.id == donation_id))).scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    return await nearest_delivery_partner(db, donation.lat, donation.lng, radius_km)
