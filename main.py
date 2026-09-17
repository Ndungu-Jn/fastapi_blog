from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError #return validation error i.e when string is passed insteed of int
from fastapi.responses import JSONResponse #to return JSON 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException#fastapi is built on top of starlette.



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


@app.get("/posts/{post_id}", include_in_schema=False, name="get_posts")
def get_posts(request: Request, post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            title = post["title"][:50]
            return templates.TemplateResponse(
                request, "post.html", {"post": post, "title": title}
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/api/posts")
def api_get_posts():
    return posts


@app.get("/api/posts/{post_id}")
def api_get_post(post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

#Error handling
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
#validation_exception_handler
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