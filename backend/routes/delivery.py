from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Donation
from schemas import DonationOut, UserOut, AvailabilityUpdate
from utils.db import get_db
from utils.auth import require_delivery
from utils.config import settings
from services.geo import make_point, distance_m, within
from services.matching import log_event, now
from services.serialize import donation_out, DONATION_LOADS

router = APIRouter(prefix="/api/delivery", tags=["delivery"])


@router.patch("/availability", response_model=UserOut)
async def set_availability(
    body: AvailabilityUpdate,
    user: User = Depends(require_delivery),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    if user.lat is not None and user.lng is not None:
        user.location = make_point(user.lat, user.lng)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/tasks", response_model=List[DonationOut])
async def my_tasks(
    active_only: bool = Query(True),
    user: User = Depends(require_delivery),
    db: AsyncSession = Depends(get_db),
):
    """Donations assigned to this delivery partner."""
    stmt = (
        select(Donation)
        .where(Donation.delivery_by_id == user.id)
        .options(*DONATION_LOADS)
        .order_by(Donation.claimed_at.desc())
    )
    if active_only:
        stmt = stmt.where(Donation.status.in_(("assigned", "picked_up")))
    rows = (await db.execute(stmt)).scalars().all()
    return [donation_out(d) for d in rows]


@router.get("/pool", response_model=List[DonationOut])
async def open_pool(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_km: float = Query(default=None),
    user: User = Depends(require_delivery),
    db: AsyncSession = Depends(get_db),
):
    """Claimed donations that still need a delivery partner, nearest pickup first."""
    lat = lat if lat is not None else user.lat
    lng = lng if lng is not None else user.lng
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="Set your location or pass lat/lng")
    radius_km = radius_km or settings.match_radius_km
    dist = distance_m(Donation.location, lat, lng)
    stmt = (
        select(Donation, dist.label("d"))
        .where(
            Donation.status == "claimed",
            Donation.delivery_by_id.is_(None),
            within(Donation.location, lat, lng, radius_km),
        )
        .options(*DONATION_LOADS)
        .order_by(dist)
    )
    rows = (await db.execute(stmt)).all()
    return [donation_out(d, distance_m=meters) for d, meters in rows]


async def _my_donation(db: AsyncSession, donation_id: int, user: User, allow_unassigned=False) -> Donation:
    result = await db.execute(
        select(Donation).where(Donation.id == donation_id).with_for_update()
    )
    donation = result.scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    mine = donation.delivery_by_id == user.id
    open_to_me = allow_unassigned and donation.delivery_by_id is None
    if not (mine or open_to_me):
        raise HTTPException(status_code=403, detail="This task is not yours")
    return donation


@router.post("/donations/{donation_id}/accept", response_model=DonationOut)
async def accept_task(
    donation_id: int,
    user: User = Depends(require_delivery),
    db: AsyncSession = Depends(get_db),
):
    donation = await _my_donation(db, donation_id, user, allow_unassigned=True)
    if donation.status != "claimed":
        raise HTTPException(status_code=409, detail="This task is not open to accept")
    donation.delivery_by_id = user.id
    donation.status = "assigned"
    await log_event(db, donation, "assigned", actor=user, note=f"accepted by {user.name}")
    await db.commit()
    return await _reload(db, donation_id)


@router.post("/donations/{donation_id}/pickup", response_model=DonationOut)
async def mark_picked_up(
    donation_id: int,
    user: User = Depends(require_delivery),
    db: AsyncSession = Depends(get_db),
):
    donation = await _my_donation(db, donation_id, user)
    if donation.status != "assigned":
        raise HTTPException(status_code=409, detail=f"Cannot pick up a donation that is '{donation.status}'")
    donation.status = "picked_up"
    donation.picked_up_at = now()
    await log_event(db, donation, "picked_up", actor=user, note="collected from restaurant")
    await db.commit()
    return await _reload(db, donation_id)


@router.post("/donations/{donation_id}/deliver", response_model=DonationOut)
async def mark_delivered(
    donation_id: int,
    user: User = Depends(require_delivery),
    db: AsyncSession = Depends(get_db),
):
    donation = await _my_donation(db, donation_id, user)
    if donation.status != "picked_up":
        raise HTTPException(status_code=409, detail=f"Cannot deliver a donation that is '{donation.status}'")
    donation.status = "delivered"
    donation.delivered_at = now()
    await log_event(db, donation, "delivered", actor=user, note="handed over to NGO")
    await db.commit()
    return await _reload(db, donation_id)


@router.post("/donations/{donation_id}/decline", response_model=DonationOut)
async def decline_task(
    donation_id: int,
    user: User = Depends(require_delivery),
    db: AsyncSession = Depends(get_db),
):
    """Drop an assigned task before pickup — back to the pool for another partner."""
    donation = await _my_donation(db, donation_id, user)
    if donation.status != "assigned":
        raise HTTPException(status_code=409, detail=f"Cannot decline a donation that is '{donation.status}'")
    donation.delivery_by_id = None
    donation.status = "claimed"
    await log_event(db, donation, "claimed", actor=user, note=f"declined by {user.name}")
    await db.commit()
    return await _reload(db, donation_id)


async def _reload(db: AsyncSession, donation_id: int) -> DonationOut:
    result = await db.execute(
        select(Donation).where(Donation.id == donation_id).options(*DONATION_LOADS)
    )
    return donation_out(result.scalar_one())
