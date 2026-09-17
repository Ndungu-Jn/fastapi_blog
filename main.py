from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError #return validation error i.e when string is passed insteed of int
from fastapi.responses import JSONResponse #to return JSON 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException#fastapi is built on top of starlette.
from schemas import PostCreate, PostResponse


app = FastAPI()  # Initializing the application.

app.mount("/static", StaticFiles(directory="static"), name="static")  # mounting the static files to this main file.

templates = Jinja2Templates(directory="templates")  # Introduced the folder where the templates will be.

posts: list[dict] = [
    {
        "id": 1,
        "user_id": 1,
        "author": "Corey Schafer",
        "image_path": "/static/profile_pics/default.jpg",
        
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "user_id": 2,
        "author": "Jane Doe",
        "image_path": "/static/profile_pics/default.jpg",
        
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "April 21, 2025",
    },
]


@app.get("/", include_in_schema=False, name="home")  # this keeps out the page routes from the API documentation.
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})

"""
    Page route: renders the full HTML page for a single post (post.html),
    including the post's title/content/author baked into the markup.
    This is what a user's browser hits when they click a post link.
    Hidden from the auto-generated API docs since it's a page, not an API.
    """
@app.get("/posts/{post_id}", include_in_schema=False, name="get_posts")
def get_posts(request: Request, post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            title = post["title"][:50]
            return templates.TemplateResponse(
                request, "post.html", {"post": post, "title": title}
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

"""
    API endpoint: returns ALL posts as raw JSON (a list of post dicts).
    Used by frontend JS or external clients that need the full post list
    """
@app.get("/api/posts", response_model=list[PostResponse])
def api_get_posts():
    return posts

@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(post: PostCreate):
    new_id = max(p["id"] for p in posts) + 1 if posts else 1
    new_post = {
        "id": new_id,
        "author": post.author,
        "title": post.title,
        "content": post.content,
        "date_posted": "April 23, 2026" , 
    }
    posts.append(new_post)
    return new_post





"""
    API endpoint: returns a single post as raw JSON, given its ID.
    Used by frontend JS (fetch calls) or any external client.
    Not meant to be visited directly in a browser as a page.
    """
@app.get("/api/posts/{post_id}",response_model=PostResponse)
def api_get_post(post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

"""
    Global handler for any HTTPException raised anywhere in the app
    (e.g. your 404 'Post not found' raises).

    Behaves differently depending on which "half" of the app the error
    came from:
      - If the request was to an /api/... route: return the error as
        JSON, since API clients (JS fetch, React, etc.) expect JSON,
        not an HTML page.
      - Otherwise (a normal page route): render error.html, a proper
        styled error page for a human browsing the site.

    Falls back to a generic message if exception.detail is empty.
    """
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
):
    message = (
            exception.detail
            if exception.detail
            else "An error occurred. Please check your request and try again."
        )
    
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message}
        )


    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )

"""
    Global handler specifically for FastAPI's automatic input validation
    failures — e.g. hitting /posts/John%20Doe when the route expects
    post_id: int. FastAPI raises this BEFORE the route function runs,
    since the data doesn't even match the expected type/shape.

    Same API-vs-page branching as the general HTTP exception handler:
      - /api/... requests get JSON back, including FastAPI's detailed
        list of what failed validation (exception.errors()).
      - Page requests get a rendered error.html with a simple,
        human-readable message instead of raw validation internals.
    """
@app.exception_handler(RequestValidationError)
def validation_exception_handler(request:Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail":exception.errors()},
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title":status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. PLease check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )