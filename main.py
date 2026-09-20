# asynccontextmanager lets us run code when the FastAPI application
# starts and when it shuts down.
from contextlib import asynccontextmanager

# Annotated allows us to combine a Python type with FastAPI dependencies.
from typing import Annotated


# FastAPI is the main framework.
# Depends is used for dependency injection, such as getting a database session.
# Request gives us access to the incoming HTTP request.
# HTTPException is used when we need to return an HTTP error.
# status provides readable HTTP status codes.
from fastapi import Depends, FastAPI, Request, HTTPException, status


# These are FastAPI's built-in exception handlers.
# We use them for API errors so that API clients receive JSON responses.
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler
)

# RequestValidationError is raised when incoming request data is invalid.
from fastapi.exceptions import RequestValidationError


# StaticFiles allows FastAPI to serve CSS, JavaScript, images, etc.
from fastapi.staticfiles import StaticFiles

# Jinja2Templates allows us to render our HTML templates.
from fastapi.templating import Jinja2Templates


# select is SQLAlchemy's modern way of building SELECT queries.
from sqlalchemy import select

# AsyncSession is the asynchronous SQLAlchemy database session.
from sqlalchemy.ext.asyncio import AsyncSession

# selectinload loads related data efficiently.
# For example, when getting Posts, we can load the Post's author.
from sqlalchemy.orm import selectinload


# Starlette's HTTPException is the base exception used by FastAPI.
# We use it in our general error handler.
from starlette.exceptions import HTTPException as StarletteHTTPException


# These are our own project files.
#
# IMPORTANT:
# The project currently has main.py, models.py, database.py and schemas.py
# directly in the same project directory.
#
# Therefore we use normal/absolute imports here.
# DO NOT change these to "from . import ..." unless the project is converted
# into a Python package and started differently.
import models

from database import Base, engine, get_db

from schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    UserCreate,
    UserResponse,
    UserUpdate
)


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

# The lifespan function controls what happens when FastAPI starts
# and when FastAPI shuts down.
#
# During startup:
#   - Connect to the database.
#   - Create database tables if they do not already exist.
#
# During shutdown:
#   - Close/dispose the database engine.
@asynccontextmanager
async def lifespan(_app: FastAPI):

    # Startup
    async with engine.begin() as conn:

        # Base.metadata.create_all creates the tables defined
        # by our SQLAlchemy models.
        #
        # run_sync is needed because create_all itself is synchronous,
        # while our database connection is asynchronous.
        await conn.run_sync(Base.metadata.create_all)

    # FastAPI now continues running the application.
    yield

    # Shutdown
    # Dispose/close the SQLAlchemy engine when FastAPI stops.
    await engine.dispose()


# ============================================================
# CREATE FASTAPI APPLICATION
# ============================================================

# Connect our lifespan function to FastAPI.
#
# This is important because otherwise the lifespan function above
# would be defined but never actually used.
app = FastAPI(lifespan=lifespan)


# ============================================================
# STATIC AND MEDIA FILES
# ============================================================

# Serve CSS, JavaScript, images, etc. from the static directory.
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# Serve uploaded/media files from the media directory.
app.mount(
    "/media",
    StaticFiles(directory="media"),
    name="media"
)


# Tell FastAPI/Jinja2 where our HTML templates are located.
templates = Jinja2Templates(directory="templates")


# ============================================================
# HTML PAGE ROUTES
# ============================================================


# Homepage:
#
# /       -> homepage
# /posts  -> posts page
#
# Both URLs use the same function.
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Get all posts from the database.
    #
    # selectinload(models.Post.author) tells SQLAlchemy to also
    # load the user/author associated with each post.
    result = await db.execute(
        select(models.Post).options(
            selectinload(models.Post.author)
        )
    )

    # Convert the query result into a list of Post objects.
    posts = result.scalars().all()

    # Render home.html and send the posts to the template.
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts,
            "title": "Home"
        }
    )


# ============================================================
# DISPLAY ONE POST
# ============================================================

# Example:
#
# /posts/1
#
# The number 1 is the post_id.
@app.get(
    "/posts/{post_id}",
    include_in_schema=False,
    name="get_post"
)
async def get_post(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find the post by ID.
    #
    # We also load the author because post.html may need
    # information about the user who created the post.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if post:

        # Use the first 50 characters of the post title
        # as the page title.
        title = post.title[:50]

        # Send the post to post.html.
        return templates.TemplateResponse(
            request,
            "post.html",
            {
                "post": post,
                "title": title
            }
        )

    # The post does not exist.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
    )


# ============================================================
# DISPLAY ALL POSTS BELONGING TO ONE USER
# ============================================================

# Example:
#
# /users/1/posts
@app.get(
    "/users/{user_id}/posts",
    include_in_schema=False,
    name="user_posts"
)
async def user_posts(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find the user first.
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

    # Get all posts belonging to this user.
    #
    # Because we are selecting Post objects, it is valid to use
    # selectinload(models.Post.author) here.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
    )

    posts = result.scalars().all()

    # Render user_posts.html.
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


# Create a new user.
#
# POST /api/users
@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Check whether the username already exists.
    result = await db.execute(
        select(models.User)
        .where(models.User.username == user.username)
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
        .where(models.User.email == user.email)
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
        email=user.email,

        # This is currently a placeholder.
        # It is NOT a real password hashing implementation.
        password_hash="temporary-not-a-real-hash"
    )

    # Add the new user to the database session.
    db.add(new_user)

    # Save the new user.
    await db.commit()

    # Refresh the object so that generated fields such as ID
    # are available.
    await db.refresh(new_user)

    return new_user


# ============================================================
# GET ONE USER
# ============================================================

# Example:
#
# GET /api/users/1
@app.get(
    "/api/users/{user_id}",
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
@app.get(
    "/api/users/{user_id}/posts",
    response_model=list[PostResponse]
)
async def get_user_posts(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # First check that the user exists.
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
@app.patch(
    "/api/users/{user_id}",
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
@app.delete(
    "/api/users/{user_id}",
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


# ============================================================
# POST API ROUTES
# ============================================================


# Get all posts.
#
# GET /api/posts
@app.get(
    "/api/posts",
    response_model=list[PostResponse]
)
async def api_get_posts(
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Get all posts.
    #
    # selectinload loads each post's author.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
    )

    posts = result.scalars().all()

    return posts


# ============================================================
# CREATE POST
# ============================================================

# Create a new post.
#
# POST /api/posts
@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    post: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Make sure the user exists.
    #
    # IMPORTANT:
    # We are selecting a User here.
    #
    # Therefore we must NOT use:
    #
    # selectinload(models.Post.author)
    #
    # because Post.author is a relationship belonging to Post,
    # not the root User entity being selected.
    result = await db.execute(
        select(models.User)
        .where(models.User.id == post.user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Create the Post database object.
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id
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
@app.get(
    "/api/posts/{post_id}",
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
@app.put(
    "/api/posts/{post_id}",
    response_model=PostResponse
)
async def api_update_post_full(
    post_id: int,
    post_data: PostCreate,
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

    # If the post is being assigned to a different user,
    # make sure that user actually exists.
    if post_data.user_id != post.user_id:

        # We are selecting User here.
        #
        # Therefore we do NOT use selectinload(Post.author).
        result = await db.execute(
            select(models.User)
            .where(models.User.id == post_data.user_id)
        )

        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

    # Update the post fields.
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

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
@app.patch(
    "/api/posts/{post_id}",
    response_model=PostResponse
)
async def api_update_post_partial(
    post_id: int,
    post_data: PostUpdate,
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

    # model_dump(exclude_unset=True) returns only the fields
    # that were actually included in the PATCH request.
    #
    # Example:
    #
    # {
    #     "title": "New title"
    # }
    #
    # becomes:
    #
    # {"title": "New title"}
    update_data = post_data.model_dump(
        exclude_unset=True
    )

    # If user_id is being changed, verify that the new user exists.
    if "user_id" in update_data:

        result = await db.execute(
            select(models.User)
            .where(
                models.User.id == update_data["user_id"]
            )
        )

        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
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
@app.delete(
    "/api/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def api_delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    # Find the post by ID.
    #
    # We don't need to load the author because we are only
    # deleting the post.
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

    # Delete the post.
    await db.delete(post)

    # Save the deletion.
    await db.commit()

    # 204 means there is intentionally no response body.


# ============================================================
# ERROR HANDLERS
# ============================================================


# Handles HTTP errors such as 404.
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException
):

    # API errors should return JSON.
    if request.url.path.startswith("/api"):
        return await http_exception_handler(
            request,
            exception
        )

    # Get the error message.
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    # Website errors should render error.html.
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


# ============================================================
# VALIDATION ERROR HANDLER
# ============================================================

# Handles validation errors.
#
# Example:
#
# /posts/abc
#
# when post_id expects an integer.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError
):

    # API validation errors return JSON.
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(
            request,
            exception
        )

    # Website validation errors render error.html.
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": (
                "Invalid request. "
                "Please check your input and try again."
            ),
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )
