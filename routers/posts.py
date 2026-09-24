# Annotated allows us to combine a Python type with FastAPI dependencies.
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
# select is SQLAlchemy's modern way of building SELECT queries.
from sqlalchemy import select, func

# AsyncSession is the asynchronous SQLAlchemy database session.
from sqlalchemy.ext.asyncio import AsyncSession

# selectinload loads related data efficiently.
# For example, when getting Posts, we can load the Post's author.
from sqlalchemy.orm import selectinload
import models

from auth import CurrentUser

from database import get_db

from schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    PaginatedPostsResponse

)

router = APIRouter()


# GET /api/posts
@router.get(
    "",
    response_model=PaginatedPostsResponse
)
async def api_get_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):

    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0

    # Get all posts.
    #
    # selectinload loads each post's author.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author)).order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit),
    )

    posts = result.scalars().all()

    has_more = skip + len(posts) < total

    return PaginatedPostsResponse(
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


# ============================================================
# CREATE POST
# ============================================================

# Create a new post.
#
# POST /api/posts
@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    post: PostCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Create the Post database object.
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id,
    )

    # Add the post to the database session.
    db.add(new_post)

    # Save it.
    await db.commit()

    # Refresh the post and load its author.
    await db.refresh(
        new_post,
        attribute_names=["author"]
    )

    return new_post


# ============================================================
# GET ONE POST AS JSON
# ============================================================

# Example:
#
# GET /api/posts/1
@router.get(
    "/{post_id}",
    response_model=PostResponse
)
async def api_get_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find post by ID.
    #
    # Because we are selecting Post, loading Post.author
    # is valid here.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if post:
        return post

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
    )


# ============================================================
# PUT POST
# ============================================================

# PUT replaces the full post.
#
# Therefore PostCreate is used here because title, content and
# user_id are all expected.
#
# Example:
#
# PUT /api/posts/1
#
# {
#     "title": "New title",
#     "content": "New content",
#     "user_id": 2
# }
@router.put(
    "/{post_id}",
    response_model=PostResponse
)
async def api_update_post_full(
    post_id: int,
    post_data: PostCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find the existing post.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    # Update the post fields.
    post.title = post_data.title
    post.content = post_data.content

    # Save changes.
    await db.commit()

    # Refresh the post and load the new author relationship.
    await db.refresh(
        post,
        attribute_names=["author"]
    )

    return post


# ============================================================
# PATCH POST
# ============================================================

# PATCH performs a partial update.
#
# Unlike PUT, we do not have to provide every field.
#
# For example, this is valid:
#
# PATCH /api/posts/1
#
# {
#     "title": "Only change the title"
# }
@router.patch(
    "/{post_id}",
    response_model=PostResponse
)
async def api_update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find the existing post.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    update_data = post_data.model_dump(
        exclude_unset=True
    )
    # Apply each supplied field to the existing post.
    for field, value in update_data.items():
        setattr(post, field, value)

    # Save changes.
    await db.commit()

    # Refresh the post and its author.
    await db.refresh(
        post,
        attribute_names=["author"]
    )

    return post


# ============================================================
# DELETE POST
# ============================================================

# DELETE /api/posts/1
@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def api_delete_post(
    post_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    result = await db.execute(
        select(models.Post)
        .where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )

    # Delete the post.
    await db.delete(post)

    # Save the deletion.
    await db.commit()

    # 204 means there is intentionally no response body.
