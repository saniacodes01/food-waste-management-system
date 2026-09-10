from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Donation
from schemas import DonationCreate, DonationUpdate, DonationOut
from utils.db import get_db
from utils.auth import get_current_user, require_restaurant
from services.geo import make_point
from services.matching import log_event, now
from services.serialize import donation_out, DONATION_LOADS

router = APIRouter(prefix="/api/donations", tags=["donations"])

# statuses a restaurant is still allowed to edit / cancel
_EDITABLE = {"available"}
_CANCELLABLE = {"available", "claimed", "assigned"}


async def _load(db: AsyncSession, donation_id: int) -> Donation:
    result = await db.execute(
        select(Donation).where(Donation.id == donation_id).options(*DONATION_LOADS)
    )
    donation = result.scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    return donation


@router.post("", response_model=DonationOut, status_code=201)
async def create_donation(
    body: DonationCreate,
    user: User = Depends(require_restaurant),
    db: AsyncSession = Depends(get_db),
):
    donation = Donation(
        restaurant_id=user.id,
        location=make_point(body.lat, body.lng),
        contact_name=body.contact_name or user.name,
        contact_phone=body.contact_phone or user.phone,
        **body.model_dump(exclude={"contact_name", "contact_phone"}),
    )
    db.add(donation)
    await db.flush()
    await log_event(db, donation, "available", actor=user, note="donation posted")
    await db.commit()
    return donation_out(await _load(db, donation.id))


@router.get("/mine", response_model=List[DonationOut])
async def my_donations(
    status: Optional[str] = Query(None),
    user: User = Depends(require_restaurant),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Donation)
        .where(Donation.restaurant_id == user.id)
        .options(*DONATION_LOADS)
        .order_by(Donation.created_at.desc())
    )
    if status:
        stmt = stmt.where(Donation.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return [donation_out(d) for d in rows]


@router.get("/{donation_id}", response_model=DonationOut)
async def get_donation(
    donation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    donation = await _load(db, donation_id)
    involved = {donation.restaurant_id, donation.claimed_by_ngo_id, donation.delivery_by_id}
    if user.role != "admin" and user.id not in involved and donation.status != "available":
        raise HTTPException(status_code=403, detail="Not your donation")
    return donation_out(donation)


@router.patch("/{donation_id}", response_model=DonationOut)
async def update_donation(
    donation_id: int,
    body: DonationUpdate,
    user: User = Depends(require_restaurant),
    db: AsyncSession = Depends(get_db),
):
    donation = await _load(db, donation_id)
    if donation.restaurant_id != user.id:
        raise HTTPException(status_code=403, detail="Not your donation")
    if donation.status not in _EDITABLE:
        raise HTTPException(status_code=409, detail=f"Cannot edit a donation that is '{donation.status}'")

    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(donation, field, value)
    if donation.lat is not None and donation.lng is not None:
        donation.location = make_point(donation.lat, donation.lng)
    await db.commit()
    return donation_out(await _load(db, donation_id))


@router.post("/{donation_id}/cancel", response_model=DonationOut)
async def cancel_donation(
    donation_id: int,
    user: User = Depends(require_restaurant),
    db: AsyncSession = Depends(get_db),
):
    donation = await _load(db, donation_id)
    if donation.restaurant_id != user.id:
        raise HTTPException(status_code=403, detail="Not your donation")
    if donation.status not in _CANCELLABLE:
        raise HTTPException(status_code=409, detail=f"Cannot cancel a donation that is '{donation.status}'")
    donation.status = "cancelled"
    await log_event(db, donation, "cancelled", actor=user, note="cancelled by restaurant")
    await db.commit()
    return donation_out(await _load(db, donation_id))
