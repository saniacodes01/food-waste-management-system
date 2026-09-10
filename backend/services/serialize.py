from typing import Optional
from sqlalchemy.orm import selectinload
from models import Donation
from schemas import DonationOut

# relationships to eager-load before serializing a Donation
DONATION_LOADS = (
    selectinload(Donation.restaurant),
    selectinload(Donation.ngo),
    selectinload(Donation.delivery_partner),
    selectinload(Donation.events),
)


def donation_out(donation: Donation, distance_m: Optional[float] = None) -> DonationOut:
    out = DonationOut.model_validate(donation)
    if distance_m is not None:
        out.distance_km = round(distance_m / 1000.0, 2)
    return out
