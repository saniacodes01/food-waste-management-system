from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import RegisterIn, LoginIn, Token, UserOut, ProfileUpdate
from utils.db import get_db
from utils.auth import hash_password, verify_password, create_token, get_current_user
from services.geo import make_point

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(User).where(User.email == body.email.lower()))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        role=body.role,
        name=body.name,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        phone=body.phone,
        address=body.address,
        city=body.city,
        lat=body.lat,
        lng=body.lng,
        location=make_point(body.lat, body.lng),
        description=body.description,
        vehicle_type=body.vehicle_type,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_token({"sub": user.id, "role": user.role})
    return Token(access_token=token, role=user.role, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_token({"sub": user.id, "role": user.role})
    return Token(access_token=token, role=user.role, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(user, field, value)
    if user.lat is not None and user.lng is not None:
        user.location = make_point(user.lat, user.lng)
    await db.commit()
    await db.refresh(user)
    return user
