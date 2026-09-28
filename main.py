# Runs code when FastAPI starts and shuts down.
from contextlib import asynccontextmanager

# Combines a type with a FastAPI dependency.
from typing import Annotated

# FastAPI tools used for routes, dependencies, requests, and HTTP errors.
from fastapi import Depends, FastAPI, Request, HTTPException, status

# Built-in handlers used to return appropriate API error responses.
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler
)

# Raised when incoming request data fails validation.
from fastapi.exceptions import RequestValidationError

# Serves static files such as CSS, JavaScript, and images.
from fastapi.staticfiles import StaticFiles

# Renders Jinja2 HTML templates.
from fastapi.templating import Jinja2Templates

# Builds SQL queries using SQLAlchemy.
from sqlalchemy import select, func

# Asynchronous database session.
from sqlalchemy.ext.asyncio import AsyncSession

# Loads related records efficiently.
from sqlalchemy.orm import selectinload

# Starlette HTTPException is used by our general error handler.
from starlette.exceptions import HTTPException as StarletteHTTPException

# Project files.
import models
from database import engine, get_db
from routers import posts, users
from config import settings


# Create tables at startup and close the database engine at shutdown.
@asynccontextmanager
async def lifespan(_app: FastAPI):

    # FastAPI runs the application between startup and shutdown.
    yield

    await engine.dispose()


# Attach the startup/shutdown lifecycle to the FastAPI app.
app = FastAPI(lifespan=lifespan)


# Serve files from the static directory.
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# Tell Jinja2 where the HTML templates are located.
templates = Jinja2Templates(directory="templates")


# Register the users API routes.
app.include_router(
    users.router,
    prefix="/api/users",
    tags=["users"]
)


# Register the posts API routes.
app.include_router(
    posts.router,
    prefix="/api/posts",
    tags=["posts"]
)


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
# Display the latest posts on the home page.
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .limit(settings.posts_per_page),
    )

    posts = result.scalars().all()

    has_more = len(posts) < total

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts,
            "title": "Home",
            "limit": settings.posts_per_page,
            "has_more": has_more,
        },
    )


@app.get(
    "/posts/{post_id}",
    include_in_schema=False,
    name="get_post"
)
# Display one post by its ID.
async def get_post(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    result = await db.execute(
        # Load the author together with the post to avoid an extra query later.
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if post:

        # Use part of the title as the page title.
        title = post.title[:50]

        return templates.TemplateResponse(
            request,
            "post.html",
            {
                "post": post,
                "title": title
            }
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
    )


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
# Display all posts belonging to a specific user.
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    count_result = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user_id),
    )

    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
        .limit(settings.posts_per_page),
    )

    posts = result.scalars().all()

    has_more = len(posts) < total

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": posts,
            "user": user,
            "title": f"{user.username}'s Posts",
            "limit": settings.posts_per_page,
            "has_more": has_more,
        },
    )


@app.get("/login", include_in_schema=False)
# Render the login page.
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Login"},
    )


@app.get("/register", include_in_schema=False)
# Render the registration page.
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {"title": "Register"},
    )


@app.get("/account", include_in_schema=False)
# Render the account page.
async def account_page(request: Request):
    return templates.TemplateResponse(
        request,
        "account.html",
        {"title": "Account"},
    )


@app.get("/forgot-password", include_in_schema=False)
# Render the forgot-password page.
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"title": "Forgot Password"},
    )


@app.get("/reset-password", include_in_schema=False)
# Render the reset-password page.
async def reset_password_page(request: Request):
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        {"title": "Reset Password"},
    )

    response.headers["Referrer-Policy"] = "no-referrer"

    return response


# Return JSON for API errors and an HTML page for website errors.
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException
):

    if request.url.path.startswith("/api"):
        return await http_exception_handler(
            request,
            exception
        )

    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

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


# Handle invalid request data differently for APIs and HTML pages.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError
):

    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(
            request,
            exception
        )

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
