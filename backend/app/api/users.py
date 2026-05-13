from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_active_superuser
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, UserListResponse, UserAdminCreate, UserAdminUpdate, PasswordResetResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_update.nickname is not None:
        current_user.nickname = user_update.nickname

    if user_update.password is not None:
        from app.core.security import get_password_hash
        current_user.password_hash = get_password_hash(user_update.password)

    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 20,
    search: str = "",
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    count_query = select(func.count(User.id))

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_pattern)) | (User.nickname.ilike(search_pattern))
        )
        count_query = count_query.where(
            (User.email.ilike(search_pattern)) | (User.nickname.ilike(search_pattern))
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    result = await db.execute(query.order_by(User.id).offset(skip).limit(limit))
    users = result.scalars().all()

    return UserListResponse(total=total, items=[UserResponse.model_validate(u) for u in users])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserAdminCreate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    existing = await service.get_by_email(user_in.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = await service.admin_create(user_in)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserAdminUpdate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_update.email_verified is False and user.is_superuser:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot unverify superuser")

    updated_user = await service.admin_update(user, user_update)
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await service.delete(user)


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_user_password(
    user_id: int,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reset your own password via admin")

    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    import secrets
    new_password = secrets.token_urlsafe(12)
    await service.reset_password(user, new_password)

    return PasswordResetResponse(message=f"Password reset successfully. New password: {new_password}")
