from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI() #Initializing the application.

app.mount("/static", StaticFiles(directory="static"), name="static") # mounting the staic files to this main file.

templates = Jinja2Templates(directory="templates") # Introdeuced the folder where the templates will be.

posts: list[dict] = [
    {
        "id": 1,
        "author": "Corey Schafer",
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "author": "Jane Doe",
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "April 21, 2025",
    },
]

@app.get("/", include_in_schema=False, name="home") #this keeps out the page routes from the API documentation.
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request):
    return templates.TemplateResponse(request, "home_finished.html", {"posts":posts, "title":"Home"},) #changed from the hard coded html to using templates in jinja2 and also passing in thhse into the template.

@app.get("/api/posts")
def get_posts():
    return posts