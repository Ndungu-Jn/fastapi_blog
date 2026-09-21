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
from routers import posts, users


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


# Register our API routers.
app.include_router(
    users.router,
    prefix="/api/users",
    tags=["users"]
)

app.include_router(
    posts.router,
    prefix="/api/posts",
    tags=["posts"]
)


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
    #
    # IMPORTANT:
    # order_by() belongs to the SELECT query itself.
    # It does NOT belong on selectinload() in this SQLAlchemy setup.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
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
    #
    # The order_by() is applied to the Post query itself.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
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
