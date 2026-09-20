from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler
)
from fastapi.exceptions import RequestValidationError

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import Base, engine, get_db
from schemas import PostCreate, PostResponse, PostUpdate, UserCreate, UserResponse, UserUpdate


# Create database tables from our models # this is now the modern way.
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # where the aplication works.
    # Shutdown
    await engine.dispose()


# Create FastAPI app
app = FastAPI()


# Serve CSS, JS, images, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve uploaded/media files
app.mount("/media", StaticFiles(directory="media"), name="media")


# Tell FastAPI where our HTML templates are
templates = Jinja2Templates(directory="templates")


# ============================================================
# HTML PAGE ROUTES
# ============================================================

# Homepage: / or /posts
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Get all posts from the database
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()

    # Render home.html and send posts to the template
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts,
            "title": "Home"
        }
    )


# Display one post: /posts/1
@app.get("/posts/{post_id}", include_in_schema=False, name="get_post")
async def get_post(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find the post by ID
    result = await db.execute(
        select(models.Post).options(selectinload(
            models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if post:
        # Use first 50 characters as page title
        title = post.title[:50]

        # Send post to post.html
        return templates.TemplateResponse(
            request,
            "post.html",
            {
                "post": post,
                "title": title
            }
        )

    # Post doesn't exist
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
    )


# Display all posts belonging to one user
# Example: /users/1/posts
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find the user
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get all posts belonging to the user
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(
            models.Post.user_id == user_id)
    )
    posts = result.scalars().all()

    # Render user_posts.html
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": posts,
            "user": user,
            "title": f"{user.username}'s Posts",
        }
    )


# ============================================================
# USER API ROUTES
# ============================================================

# Create a new user
@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Check if username already exists
    result = await db.execute(
        select(models.User).where(
            models.User.username == user.username
        )
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email already exists
    result = await db.execute(
        select(models.User).where(
            models.User.email == user.email
        )
    )
    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create user database object
    new_user = models.User(
        username=user.username,
        email=user.email,
        password_hash="temporary-not-a-real-hash"
    )

    # Save user to database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# Get one user
# Example: GET /api/users/1
@app.get("/api/users/{user_id}", response_model=UserResponse)
async def api_get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find user by ID
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


# Get all posts belonging to a user
# Example: GET /api/users/1/posts
@app.get(
    "/api/users/{user_id}/posts",
    response_model=list[PostResponse]
)
async def get_user_posts(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Check that the user exists
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get user's posts
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(
            models.Post.user_id == user_id)
    )
    posts = result.scalars().all()

    return posts

# patch for user.


@app.patch("/api/users/{post_id}", response_model=UserResponse)
async def api_update_user_partial(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find post by ID
    result = await db.execute(
        select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(
            select(models.User).where(models.User.username == user_update.username),)
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
        if user_update.email is not None and user_update.email != user.email:
            result = await db.execute(
                select(models.User).where(models.User.username == user_update.username),)
            existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already Registered",
            )
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    await db.commit()
    await db.refresh(user)
    return user


@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find user by ID
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    await db.delete(user)
    await db.commit()


# ============================================================
# POST API ROUTES
# ============================================================

# Get all posts
@app.get("/api/posts", response_model=list[PostResponse])
async def api_get_posts(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Get all posts from database
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)),)
    posts = result.scalars().all()

    return posts


# Create a new post
@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    post: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Make sure the user exists
    result = await db.execute(
        select(models.User).where(
            models.User.id == post.user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Create post database object
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id
    )

    # Save post to database
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])

    return new_post


# Get one post as JSON
# Example: GET /api/posts/1
@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def api_get_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find post by ID
    result = await db.execute(
        select(models.Post).options(selectinload(
            models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if post:
        return post

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
    )


# put endpoint.
@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def api_update_post_full(
    post_id: int,
    post_data: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find post by ID
    result = await db.execute(
        select(models.Post).options(selectinload(
            models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    if post_data.user_id != post.user_id:
        result = await db.execute(select(models.User).where(
            models.User.id == post_data.user_id))
        user = result.scalars().first()
        # CHECKING IF USER.
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

# partial update - that is patch.


@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def api_update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find post by ID
    result = await db.execute(
        select(models.Post).options(selectinload(
            models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

# api end point for deleting


@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Find post by ID
    result = await db.execute(
        select(models.Post).options(selectinload(
            models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    await db.delete(post)
    await db.commit()


# ============================================================
# ERROR HANDLERS
# ============================================================

# Handles HTTP errors such as 404
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException
):

    # API errors return JSON
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

        # Get error message
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    # Website errors return error.html
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code
    )


# Handles validation errors
# Example: /posts/abc when post_id expects an integer
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError
):
    # API validation errors return JSON
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    # Website validation errors return error.html
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )
