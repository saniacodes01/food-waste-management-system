from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Donation
from schemas import DonationOut
from utils.db import get_db
from utils.auth import require_ngo
from utils.config import settings
from services.geo import distance_m, within
from services.matching import auto_assign_delivery, log_event, now
from services.serialize import donation_out, DONATION_LOADS

router = APIRouter(prefix="/api/ngo", tags=["ngo"])


def _origin(user: User, lat: Optional[float], lng: Optional[float]):
    lat = lat if lat is not None else user.lat
    lng = lng if lng is not None else user.lng
    if lat is None or lng is None:
        raise HTTPException(
            status_code=400,
            detail="No location available. Set your NGO location or pass lat/lng.",
        )
    return lat, lng


@router.get("/donations/available", response_model=List[DonationOut])
async def available_donations(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_km: float = Query(default=None),
    user: User = Depends(require_ngo),
    db: AsyncSession = Depends(get_db),
):
    """Nearby, still-unclaimed donations, closest first."""
    lat, lng = _origin(user, lat, lng)
    radius_km = radius_km or settings.match_radius_km
    dist = distance_m(Donation.location, lat, lng)
    stmt = (
        select(Donation, dist.label("d"))
        .where(Donation.status == "available", within(Donation.location, lat, lng, radius_km))
        .options(*DONATION_LOADS)
        .order_by(dist)
    )
    rows = (await db.execute(stmt)).all()
    return [donation_out(d, distance_m=meters) for d, meters in rows]


@router.get("/donations/claimed", response_model=List[DonationOut])
async def my_claimed(
    status: Optional[str] = Query(None),
    user: User = Depends(require_ngo),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Donation)
        .where(Donation.claimed_by_ngo_id == user.id)
        .options(*DONATION_LOADS)
        .order_by(Donation.claimed_at.desc())
    )
    if status:
        stmt = stmt.where(Donation.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return [donation_out(d) for d in rows]


@router.post("/donations/{donation_id}/claim", response_model=DonationOut)
async def claim_donation(
    donation_id: int,
    user: User = Depends(require_ngo),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Donation).where(Donation.id == donation_id).with_for_update()
    )
    donation = result.scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    if donation.status != "available":
        raise HTTPException(status_code=409, detail="This donation is no longer available")

    donation.status = "claimed"
    donation.claimed_by_ngo_id = user.id
    donation.claimed_at = now()
    await log_event(db, donation, "claimed", actor=user, note=f"claimed by {user.name}")

    await auto_assign_delivery(db, donation)
    await db.commit()

    fresh = await db.execute(
        select(Donation).where(Donation.id == donation_id).options(*DONATION_LOADS)
    )
    return donation_out(fresh.scalar_one())


@router.post("/donations/{donation_id}/confirm-received", response_model=DonationOut)
async def confirm_received(
    donation_id: int,
    user: User = Depends(require_ngo),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Donation).where(Donation.id == donation_id))
    donation = result.scalar_one_or_none()
    if not donation or donation.claimed_by_ngo_id != user.id:
        raise HTTPException(status_code=404, detail="Donation not found")
    if donation.status not in ("assigned", "picked_up", "claimed"):
        raise HTTPException(status_code=409, detail=f"Cannot confirm a donation that is '{donation.status}'")
    donation.status = "delivered"
    donation.delivered_at = now()
    await log_event(db, donation, "delivered", actor=user, note="receipt confirmed by NGO")
    await db.commit()
    fresh = await db.execute(
        select(Donation).where(Donation.id == donation_id).options(*DONATION_LOADS)
    )
    return donation_out(fresh.scalar_one())


@router.post("/donations/{donation_id}/release", response_model=DonationOut)
async def release_claim(
    donation_id: int,
    user: User = Depends(require_ngo),
    db: AsyncSession = Depends(get_db),
):
    """Give a claimed donation back to the pool (e.g. NGO can't take it after all)."""
    result = await db.execute(select(Donation).where(Donation.id == donation_id))
    donation = result.scalar_one_or_none()
    if not donation or donation.claimed_by_ngo_id != user.id:
        raise HTTPException(status_code=404, detail="Donation not found")
    if donation.status not in ("claimed", "assigned"):
        raise HTTPException(status_code=409, detail=f"Cannot release a donation that is '{donation.status}'")
    donation.status = "available"
    donation.claimed_by_ngo_id = None
    donation.delivery_by_id = None
    donation.claimed_at = None
    await log_event(db, donation, "available", actor=user, note="released back to pool by NGO")
    await db.commit()
    fresh = await db.execute(
        select(Donation).where(Donation.id == donation_id).options(*DONATION_LOADS)
    )
    return donation_out(fresh.scalar_one())
