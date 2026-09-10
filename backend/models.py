from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geography
from utils.db import Base


# Roles anyone can self-register as. "admin" is seeded, never self-registered.
SELF_SIGNUP_ROLES = ("restaurant", "ngo", "delivery")
ALL_ROLES = SELF_SIGNUP_ROLES + ("admin",)

# Donation lifecycle
DONATION_STATUSES = (
    "available",   # posted by a restaurant, visible to nearby NGOs
    "claimed",     # an NGO claimed it; waiting for a delivery partner
    "assigned",    # a delivery partner accepted / was auto-assigned
    "picked_up",   # collected from the restaurant
    "delivered",   # handed over to the NGO
    "cancelled",   # withdrawn by the restaurant or NGO
    "expired",     # passed its best-before time before pickup
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    role = Column(String, nullable=False)  # restaurant | ngo | delivery | admin

    name = Column(String, nullable=False)          # org name or person name
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    phone = Column(String, nullable=True)

    address = Column(Text, nullable=True)
    city = Column(String, nullable=True, index=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    location = Column(Geography("POINT", srid=4326), nullable=True)

    # role-specific extras
    description = Column(Text, nullable=True)       # ngo: who they serve / restaurant note
    vehicle_type = Column(String, nullable=True)    # delivery: bike / car / van
    is_available = Column(Boolean, default=True)    # delivery: accepting tasks right now

    is_approved = Column(Boolean, default=True)     # admin can gate accounts
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    donations = relationship(
        "Donation", back_populates="restaurant",
        foreign_keys="Donation.restaurant_id",
    )


class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True)

    restaurant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    claimed_by_ngo_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    delivery_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    food_name = Column(String, nullable=False)
    meal_type = Column(String, nullable=True)       # veg | non-veg
    category = Column(String, nullable=True)        # raw-food | cooked-food | packed-food
    quantity = Column(String, nullable=True)        # free text: "20 people" / "5 kg"
    notes = Column(Text, nullable=True)

    contact_name = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)

    pickup_address = Column(Text, nullable=False)
    city = Column(String, nullable=True, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    location = Column(Geography("POINT", srid=4326), nullable=False)

    best_before = Column(DateTime(timezone=True), nullable=True)

    status = Column(String, nullable=False, default="available", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    restaurant = relationship("User", back_populates="donations", foreign_keys=[restaurant_id])
    ngo = relationship("User", foreign_keys=[claimed_by_ngo_id])
    delivery_partner = relationship("User", foreign_keys=[delivery_by_id])
    events = relationship(
        "DonationEvent", back_populates="donation",
        order_by="DonationEvent.created_at", cascade="all, delete-orphan",
    )


class DonationEvent(Base):
    """Append-only timeline for a donation — who did what, when."""
    __tablename__ = "donation_events"

    id = Column(Integer, primary_key=True)
    donation_id = Column(Integer, ForeignKey("donations.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_role = Column(String, nullable=True)
    status = Column(String, nullable=False)         # the status the donation moved to
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    donation = relationship("Donation", back_populates="events")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
