from datetime import timedelta

# Annotated allows us to combine a Python type with FastAPI dependencies.
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
# select is SQLAlchemy's modern way of building SELECT queries.
from sqlalchemy import select

# AsyncSession is the asynchronous SQLAlchemy database session.
from sqlalchemy.ext.asyncio import AsyncSession

# selectinload loads related data efficiently.
# For example, when getting Posts, we can load the Post's author.
from sqlalchemy.orm import selectinload
import models

from auth import (
    create_access_token,
    hash_password,
    oauth2_scheme,
    verify_access_token,
    verify_password,
)
from config import settings
from database import get_db

from schemas import (
    PostResponse,
    Token,
    UserCreate,
    UserPublic,
    UserPrivate,
    UserUpdate
)


router = APIRouter()

# POST /api/users

# Only the decorater and the route have changed when transfering this from the main.py file.


@router.post(
    "",
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Check whether the username already exists.
    result = await db.execute(
        select(models.User)
        .where(func.lower(models.User.username) == user.username.lower())
    )

    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check whether the email already exists.
    result = await db.execute(
        select(models.User)
        .where(func.lower(models.User.email) == user.email.lower())
    )

    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create the SQLAlchemy User object.
    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password)
    )

    # Add the new user to the database session.
    db.add(new_user)

    # Save the new user.
    await db.commit()

    # Refresh the object so that generated fields such as ID
    # are available.
    await db.refresh(new_user)

    return new_user


# log in fro access token
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Look up user by email (case-insensitive)
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower(),
        ),
    )
    user = result.scalars().first()

    # Verify user exists and password is correct
    # Don't reveal which one failed (security best practice)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token_expires = timedelta(
        minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)
async def get_current_user(current_user: CurrentUser):
    return current_user


# ============================================================
# GET ONE USER
# ============================================================

# Example:
#
# GET /api/users/1
@router.get(
    "/{user_id}",
    response_model=UserResponse
)
async def api_get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find the user by ID.
    result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if user:
        return user

    # User does not exist.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


# ============================================================
# GET ALL POSTS BELONGING TO A USER
# ============================================================

# Example:
#
# GET /api/users/1/posts
@router.get(
    "/{user_id}/posts",
    response_model=list[PostResponse]
)
async def get_user_posts(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # First check that the user exists.
    result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id).order_by(
            models.Post.date_posted.desc()),
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get all posts belonging to the user.
    #
    # We are selecting Post objects here, so loading Post.author
    # is correct.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
    )

    posts = result.scalars().all()

    return posts


# ============================================================
# PARTIAL UPDATE USER
# ============================================================

# PATCH allows us to update only the fields we provide.
#
# Example:
#
# PATCH /api/users/1
#
# {
#     "username": "newname"
# }
#
# We do not have to send every user field.
@router.patch(
    "/{user_id}",
    response_model=UserResponse
)
async def api_update_user_partial(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find the user by ID.
    result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # --------------------------------------------------------
    # CHECK USERNAME
    # --------------------------------------------------------

    # Only check for duplicate username if the username is
    # actually being changed.
    if (
        user_update.username is not None
        and user_update.username != user.username
    ):

        result = await db.execute(
            select(models.User)
            .where(
                models.User.username == user_update.username
            )
        )

        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )

    # --------------------------------------------------------
    # CHECK EMAIL
    # --------------------------------------------------------

    # Email must be checked separately from username.
    #
    # The old version incorrectly placed this check inside
    # the username condition and searched the username column.
    if (
        user_update.email is not None
        and user_update.email != user.email
    ):

        result = await db.execute(
            select(models.User)
            .where(
                models.User.email == user_update.email
            )
        )

        existing_email = result.scalars().first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

    # --------------------------------------------------------
    # APPLY THE CHANGES
    # --------------------------------------------------------

    if user_update.username is not None:
        user.username = user_update.username

    if user_update.email is not None:
        user.email = user_update.email

    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    # Save changes.
    await db.commit()

    # Refresh the user from the database.
    await db.refresh(user)

    return user


# ============================================================
# DELETE USER
# ============================================================

# DELETE /api/users/1
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def api_delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find user by ID.
    result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Delete the user.
    await db.delete(user)

    # Save the deletion.
    await db.commit()

    # 204 means successful deletion with no response body.
