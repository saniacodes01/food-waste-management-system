"""Matching logic: nearest NGO for a donation, nearest delivery partner for a pickup."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Donation, DonationEvent
from services.geo import distance_m, within
from utils.config import settings


async def nearest_delivery_partner(
    db: AsyncSession, lat: float, lng: float, radius_km: Optional[float] = None
) -> Optional[User]:
    radius_km = radius_km or settings.match_radius_km
    stmt = (
        select(User)
        .where(
            User.role == "delivery",
            User.is_active.is_(True),
            User.is_approved.is_(True),
            User.is_available.is_(True),
            User.location.isnot(None),
            within(User.location, lat, lng, radius_km),
        )
        .order_by(distance_m(User.location, lat, lng))
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def log_event(
    db: AsyncSession, donation: Donation, status: str,
    actor: Optional[User] = None, note: Optional[str] = None,
):
    db.add(DonationEvent(
        donation_id=donation.id,
        actor_id=actor.id if actor else None,
        actor_role=actor.role if actor else "system",
        status=status,
        note=note,
    ))


async def auto_assign_delivery(db: AsyncSession, donation: Donation) -> Optional[User]:
    """Try to hand a freshly claimed donation to the closest free delivery partner.

    Returns the partner if one was found (donation -> 'assigned'), else None
    (donation stays 'claimed' and shows up in the delivery pool).
    """
    partner = await nearest_delivery_partner(db, donation.lat, donation.lng)
    if partner is None:
        return None
    donation.delivery_by_id = partner.id
    donation.status = "assigned"
    await log_event(db, donation, "assigned", note=f"auto-assigned to {partner.name}")
    return partner


def now() -> datetime:
    return datetime.now(timezone.utc)
