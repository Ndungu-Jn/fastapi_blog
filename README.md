# FastAPI Blog

A full-stack blog application built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.x**, **Pydantic**, **JWT authentication**, **Jinja2**, and **vanilla JavaScript**.

This project was built as a practical FastAPI learning project and covers much more than basic CRUD. It includes authentication and authorization, password hashing, password reset, email/background tasks, profile image uploads, pagination, database migrations, API documentation, server-rendered HTML, and JavaScript-driven API interactions.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Application Architecture](#application-architecture)
- [Project Structure](#project-structure)
- [Database Design](#database-design)
- [Authentication and Authorization](#authentication-and-authorization)
- [Profile Image Handling](#profile-image-handling)
- [Password Reset](#password-reset)
- [Pagination](#pagination)
- [API Endpoints](#api-endpoints)
- [Web Pages](#web-pages)
- [API Documentation](#api-documentation)
- [Database Migrations](#database-migrations)
- [Database Seeding](#database-seeding)
- [Installation and Setup](#installation-and-setup)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Testing the API](#testing-the-api)
- [Screenshots](#screenshots)
- [Important Development Notes](#important-development-notes)
- [Security Notes](#security-notes)
- [Known Limitations and Future Improvements](#known-limitations-and-future-improvements)
- [What I Learned](#what-i-learned)
- [Useful Commands](#useful-commands)
- [Git Workflow](#git-workflow-used-during-development)
- [Project Status](#project-status)
- [Author](#author)
- [License](#license)

---

## Project Overview

This project is a blog platform where users can:

- Create an account
- Log in and receive a JWT access token
- View blog posts
- Create posts
- Read individual posts
- Update their own posts
- Delete their own posts
- Update their account information
- Upload and delete profile pictures
- View posts belonging to a specific user
- Change their password
- Request a password reset
- Reset their password using a time-limited token

The application provides both:

1. A **server-rendered web interface** using Jinja2 templates.
2. A **REST API** documented automatically through OpenAPI/Swagger UI.

The database layer uses **PostgreSQL** with **SQLAlchemy's asynchronous API**.

Profile pictures are stored locally under:

```text
media/profile_pics/
```

This version intentionally does **not** require Amazon S3 for profile image storage.

---

## Features

### User Management

- User registration
- Unique username validation
- Unique email validation
- Get current authenticated user
- Get a user by ID
- Update the authenticated user's information
- Delete the authenticated user's account
- Authorization checks to prevent users from modifying other users

### Authentication

- OAuth2 password flow
- JWT access tokens
- Password hashing with Argon2
- Bearer-token authentication
- Token expiration
- Protected endpoints
- FastAPI dependency injection for the current user

### Blog Posts

- Create posts
- Read all posts
- Read one post
- Full updates using `PUT`
- Partial updates using `PATCH`
- Delete posts
- Ownership checks for update/delete operations
- Posts linked to their author through a database relationship
- Newest posts displayed first

### Pagination

The API supports pagination through:

```text
skip
limit
```

Responses include:

- `posts`
- `total`
- `skip`
- `limit`
- `has_more`

The web interface also supports a **Load More Posts** button.

### Profile Pictures

- Upload profile pictures
- Validate uploaded image content
- Maximum upload size configured through settings
- EXIF orientation correction
- Images resized/cropped to 300 × 300
- Images converted to JPEG
- Unique filenames generated with UUIDs
- Old images deleted when replaced
- Profile images stored locally
- Default profile picture used when no image exists

### Password Reset

- Forgot-password endpoint
- Secure random reset tokens
- SHA-256 token hashing before database storage
- Expiration time for reset tokens
- Reset token deletion after use
- Password reset email support
- Background email sending
- Change-password endpoint for authenticated users

### Error Handling

The application distinguishes between API and web requests.

For API routes:

```text
/api/...
```

FastAPI's normal JSON error responses are returned.

For HTML pages, errors are rendered through:

```text
templates/error.html
```

This allows the same application to behave like both a REST API and a web application.

### Automatic API Documentation

FastAPI generates interactive documentation automatically.

Available documentation:

```text
Swagger UI:
http://127.0.0.1:8000/docs

ReDoc:
http://127.0.0.1:8000/redoc

OpenAPI schema:
http://127.0.0.1:8000/openapi.json
```

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12+ | Programming language |
| FastAPI | Web framework and REST API |
| PostgreSQL | Relational database |
| SQLAlchemy 2.x | ORM and database access |
| psycopg | PostgreSQL driver |
| Alembic | Database migrations |
| Pydantic | Data validation and serialization |
| pydantic-settings | Environment-based configuration |
| PyJWT | JWT token creation and validation |
| pwdlib + Argon2 | Password hashing |
| Jinja2 | Server-side HTML templates |
| Pillow | Image processing |
| aiosmtplib | Asynchronous email sending |
| Bootstrap | UI styling |
| Vanilla JavaScript | Browser/API interactions |
| HTTPX | API-based database seeding |
| uv | Python package and environment management |

---

## Application Architecture

The application follows a layered structure:

```text
Browser
   |
   | HTTP requests
   v
FastAPI
   |
   +--------------------+
   |                    |
   v                    v
Jinja2 Templates       REST API
   |                    |
   | JavaScript         |
   | fetch()            |
   |                    |
   +---------+----------+
             |
             v
      Pydantic Schemas
             |
             v
      Authentication
      / Authorization
             |
             v
      SQLAlchemy Async
             |
             v
         PostgreSQL
```

Profile images use a separate local file-storage path:

```text
FastAPI
   |
   v
image_utils.py
   |
   v
Pillow
   |
   v
media/profile_pics/
```

---

## Project Structure

Important project files:

```text
fastapi_blog/
│
├── main.py
├── models.py
├── schemas.py
├── database.py
├── config.py
├── auth.py
├── image_utils.py
├── email_utils.py
├── populate_db.py
│
├── routers/
│   ├── __init__.py
│   ├── users.py
│   └── posts.py
│
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── cd7749d9d0c9_initial_schema.py
│       └── 5714a06fe4f7_add_likes_to_post.py
│
├── templates/
│   ├── layout.html
│   ├── home.html
│   ├── post.html
│   ├── user_posts.html
│   ├── login.html
│   ├── register.html
│   ├── account.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   ├── error.html
│   └── email/
│       └── password_reset.html
│
├── static/
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   ├── auth.js
│   │   └── utils.js
│   └── profile_pics/
│       └── default.jpg
│
├── media/
│   └── profile_pics/
│
├── .env
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── README.md
```

### What the important Python files do

#### `main.py`

The application entry point.

Responsible for:

- Creating the FastAPI application
- Mounting static and media directories
- Registering routers
- Rendering web pages
- Loading posts for the home page
- Rendering individual posts
- Rendering user-post pages
- Registering exception handlers
- Managing the application lifespan

#### `models.py`

Defines SQLAlchemy database models:

- `User`
- `Post`
- `PasswordResetToken`

It also defines relationships between users, posts, and reset tokens.

#### `schemas.py`

Defines Pydantic models used for:

- Request validation
- Response serialization
- User creation/update
- Authentication tokens
- Post creation/update
- Pagination
- Password reset
- Password changes

#### `database.py`

Creates:

- The asynchronous SQLAlchemy engine
- `AsyncSessionLocal`
- The declarative `Base`
- The `get_db` dependency

#### `config.py`

Loads configuration from `.env` using `pydantic-settings`.

#### `auth.py`

Contains authentication/security logic:

- Password hashing
- Password verification
- JWT creation
- JWT verification
- Password reset token generation
- Password reset token hashing
- Current-user dependency

#### `image_utils.py`

Handles local profile-picture processing and deletion.

#### `email_utils.py`

Handles password-reset email construction and sending.

#### `populate_db.py`

Creates development/demo data through the application's API.

#### `routers/users.py`

Contains user-related API endpoints.

#### `routers/posts.py`

Contains post-related API endpoints.

---

## Database Design

The application currently uses three main tables.

### `users`

Stores:

- `id`
- `username`
- `email`
- `password_hash`
- `image_file`

Relationships:

```text
User 1 ---- * Post
User 1 ---- * PasswordResetToken
```

### `posts`

Stores:

- `id`
- `title`
- `content`
- `user_id`
- `date_posted`
- `likes`

The `user_id` field is a foreign key pointing to `users.id`.

### `password_reset_tokens`

Stores:

- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `created_at`

The actual reset token is not stored directly. A hash is stored instead.

---

## Authentication and Authorization

Authentication uses the OAuth2 password flow with JWT bearer tokens.

### Login Flow

```text
User
 |
 | email + password
 v
POST /api/users/token
 |
 v
Verify password
 |
 v
Create JWT
 |
 v
Return access_token
 |
 v
Browser stores token
 |
 v
Authorization: Bearer <token>
```

The token contains:

- user ID (`sub`)
- expiration time (`exp`)

### Protected Routes

Protected routes use the `CurrentUser` dependency.

Conceptually:

```python
current_user: CurrentUser
```

FastAPI then:

1. Reads the Bearer token.
2. Validates the JWT.
3. Extracts the user ID.
4. Looks up the user in PostgreSQL.
5. Injects the authenticated user into the endpoint.

### Authentication vs Authorization

Authentication answers:

> Who are you?

Authorization answers:

> Are you allowed to perform this action?

For example, a user can only update or delete their own posts.

The application checks ownership before allowing these operations.

---

## Profile Image Handling

Profile pictures are intentionally stored locally in:

```text
media/profile_pics/
```

The process is:

```text
UploadFile
    |
    v
Read file bytes
    |
    v
Check maximum size
    |
    v
Pillow opens image
    |
    v
Correct EXIF orientation
    |
    v
Resize/crop to 300x300
    |
    v
Convert to RGB/JPEG
    |
    v
Generate UUID filename
    |
    v
Save to media/profile_pics/
```

The database stores only the filename.

Example:

```text
a8c7d3f5b9e44c8c9f4f1f0e2a123456.jpg
```

The model then exposes a URL such as:

```text
/media/profile_pics/a8c7d3f5b9e44c8c9f4f1f0e2a123456.jpg
```

If a user has no profile picture, the application uses:

```text
/static/profile_pics/default.jpg
```

---

## Password Reset

The password-reset system follows this flow:

```text
1. User submits email
        |
        v
2. Server checks for account
        |
        v
3. Generate secure random token
        |
        v
4. Hash token with SHA-256
        |
        v
5. Store token hash + expiry
        |
        v
6. Send reset email
        |
        v
7. User clicks reset link
        |
        v
8. Server hashes supplied token
        |
        v
9. Compare with database
        |
        v
10. Check expiration
        |
        v
11. Hash new password
        |
        v
12. Delete reset tokens
```

A generic success response is returned for the forgot-password request so the API does not reveal whether an email address is registered.

---

## Pagination

Post listing endpoints support:

```text
?skip=0&limit=10
```

For example:

```text
GET /api/posts?skip=0&limit=10
```

A paginated response looks conceptually like:

```json
{
  "posts": [],
  "total": 45,
  "skip": 0,
  "limit": 10,
  "has_more": true
}
```

The `has_more` field is calculated using the total number of records and the current offset.

The browser also uses the same pagination API for the **Load More Posts** button.

---

## API Endpoints

All API routes are grouped under:

```text
/api/users
/api/posts
```

### Posts

| Method | Endpoint | Authentication | Purpose |
|---|---|---|---|
| GET | `/api/posts` | No | Get paginated posts |
| POST | `/api/posts` | Yes | Create a post |
| GET | `/api/posts/{post_id}` | No | Get one post |
| PUT | `/api/posts/{post_id}` | Yes | Replace a post |
| PATCH | `/api/posts/{post_id}` | Yes | Partially update a post |
| DELETE | `/api/posts/{post_id}` | Yes | Delete a post |

### Users

| Method | Endpoint | Authentication | Purpose |
|---|---|---|---|
| POST | `/api/users` | No | Register a user |
| POST | `/api/users/token` | No | Log in and receive JWT |
| GET | `/api/users/me` | Yes | Get current user |
| POST | `/api/users/forgot-password` | No | Request password reset |
| POST | `/api/users/reset-password` | No | Reset password |
| PATCH | `/api/users/me/password` | Yes | Change password |
| GET | `/api/users/{user_id}` | No | Get a user |
| PATCH | `/api/users/{user_id}` | Yes | Update own user |
| DELETE | `/api/users/{user_id}` | Yes | Delete own user |
| GET | `/api/users/{user_id}/posts` | No | Get user's paginated posts |
| PATCH | `/api/users/{user_id}/picture` | Yes | Upload profile picture |
| DELETE | `/api/users/{user_id}/picture` | Yes | Delete profile picture |

---

## Web Pages

The application also exposes HTML pages.

| URL | Purpose |
|---|---|
| `/` | Home page |
| `/posts` | Blog posts page |
| `/posts/{post_id}` | Individual post page |
| `/users/{user_id}/posts` | User's posts |
| `/login` | Login page |
| `/register` | Registration page |
| `/account` | Account page |
| `/forgot-password` | Password reset request page |
| `/reset-password` | Password reset form |

The HTML pages are rendered using Jinja2 templates.

---

## API Documentation

When the application is running, open:

```text
http://127.0.0.1:8000/docs
```

This opens Swagger UI.

The documentation allows you to:

- See all endpoints
- View request parameters
- View request bodies
- View response schemas
- Authenticate using the Authorize button
- Execute API requests directly from the browser
- Inspect response status codes and JSON responses

Alternative documentation is available at:

```text
http://127.0.0.1:8000/redoc
```

---

## Database Migrations

Alembic manages database schema changes.

### Apply all migrations

```bash
uv run alembic upgrade head
```

### Create a new migration

After changing a SQLAlchemy model:

```bash
uv run alembic revision --autogenerate -m "describe your change"
```

Then inspect the generated migration before applying it.

### Check migration history

```bash
uv run alembic history
```

### Check current database revision

```bash
uv run alembic current
```

### Roll back one migration

```bash
uv run alembic downgrade -1
```

### Current Migration History

The project currently contains an initial schema migration followed by a migration adding the `likes` column to posts:

```text
cd7749d9d0c9  initial_schema
        |
        v
5714a06fe4f7  add_likes_to_post
```

The `likes` field currently exists in the database model/schema migration, but there is not yet a dedicated like/unlike API endpoint.

---

## Database Seeding

The project includes:

```text
populate_db.py
```

The seeder is designed for development/testing.

It:

1. Clears existing posts.
2. Clears existing users.
3. Creates six demo users.
4. Logs in each user to obtain a JWT.
5. Creates 45 demo posts.
6. Assigns posts to different users.
7. Adjusts post dates to make pagination easier to test.

Run it with:

```bash
uv run python populate_db.py
```

Expected final summary:

```text
Database population complete!
Users: 6
Posts: 45
Images: Not used (S3 disabled)
```

### Important Warning

The seeder deletes existing users and posts before recreating them.

**Do not run `populate_db.py` against a production database.**

It is intended for development/demo data only.

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Ndungu-Jn/fastapi_blog.git
cd fastapi_blog
```

### 2. Install Dependencies

This project uses `uv`.

```bash
uv sync
```

If the environment needs to be recreated:

```bash
uv lock
uv sync
```

### 3. Create a PostgreSQL Database

Example:

```sql
CREATE USER fastapi_user WITH PASSWORD 'your_password';
CREATE DATABASE fastapi_blog OWNER fastapi_user;
```

Then make sure PostgreSQL is running.

### 4. Create the `.env` File

Create:

```text
.env
```

in the project root.

Example:

```env
DATABASE_URL=postgresql+psycopg://fastapi_user:your_password@localhost:5432/fastapi_blog

SECRET_KEY=replace-this-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

MAX_UPLOAD_SIZE_BYTES=5242880
POSTS_PER_PAGE=5

RESET_TOKEN_EXPIRE_MINUTES=60

MAIL_SERVER=localhost
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=noreply@example.com
MAIL_USE_TLS=true

FRONTEND_URL=http://localhost:8000
```

Do not commit real secrets to GitHub.

### 5. Create the Local Media Directory

```bash
mkdir -p media/profile_pics
```

### 6. Run Database Migrations

```bash
uv run alembic upgrade head
```

### 7. Populate Development Data

```bash
uv run python populate_db.py
```

### 8. Start the Application

```bash
uv run fastapi dev main.py
```

The application should then be available at:

```text
http://127.0.0.1:8000
```

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Secret used to sign JWT tokens |
| `ALGORITHM` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime |
| `MAX_UPLOAD_SIZE_BYTES` | Maximum profile-image upload size |
| `POSTS_PER_PAGE` | Number of posts initially displayed |
| `RESET_TOKEN_EXPIRE_MINUTES` | Password reset token lifetime |
| `MAIL_SERVER` | SMTP server |
| `MAIL_PORT` | SMTP port |
| `MAIL_USERNAME` | SMTP username |
| `MAIL_PASSWORD` | SMTP password |
| `MAIL_FROM` | Sender email address |
| `MAIL_USE_TLS` | Whether SMTP TLS is enabled |
| `FRONTEND_URL` | Base URL used when generating reset links |

---

## Running the Application

From the project root:

```bash
uv run fastapi dev main.py
```

Then open:

```text
http://127.0.0.1:8000/
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

## Testing the API

### 1. Open Swagger UI

Go to:

```text
http://127.0.0.1:8000/docs
```

### 2. Create a User

Use:

```text
POST /api/users
```

Example:

```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "TestPassword1!"
}
```

### 3. Log In

Use:

```text
POST /api/users/token
```

The OAuth2 form uses:

```text
username = user's email
password = user's password
```

The response contains:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

### 4. Authorize Swagger

Click:

```text
Authorize
```

Enter the credentials/token information requested by Swagger UI.

Once authenticated, protected endpoints can be tested directly from the documentation.

### 5. Create a Post

Use:

```text
POST /api/posts
```

Example:

```json
{
  "title": "My first API post",
  "content": "Learning FastAPI is getting interesting."
}
```

### 6. Test Ownership

Log in as one user and attempt to update/delete another user's post.

The API should reject unauthorized ownership changes with:

```text
403 Forbidden
```

This is an important part of the application's authorization logic.

---

## Screenshots

The screenshots below show the working application and generated API documentation.

### Blog Home Page

![FastAPI Blog Home Page](screenshots/front.png)

The home page demonstrates:

- FastAPI Blog navigation
- Login and registration
- Dark-mode interface
- Blog posts
- Author information
- Post dates
- Load More Posts functionality
- Server-rendered UI

### Posts API

![Posts API Endpoints](screenshots/posts_endpoints.png)

The Swagger UI shows the available post endpoints:

- GET posts
- POST posts
- GET individual post
- PUT post
- PATCH post
- DELETE post

Protected operations display the authentication lock.

### Users API

![Users API Endpoints](screenshots/users_endpoints.png)

The Swagger UI shows the user and authentication endpoints:

- Registration
- Login
- Current-user endpoint
- Forgot password
- Reset password
- Change password
- User retrieval
- User update/delete
- User posts
- Profile picture upload/delete

---

## Important Development Notes

### PostgreSQL Is the Application Database

The current working setup is:

```text
FastAPI
   ↓
SQLAlchemy Async
   ↓
psycopg
   ↓
PostgreSQL
```

The project should not rely on the old SQLite database for normal operation.

### Profile Images Use Local Storage

Profile pictures are stored under:

```text
media/profile_pics/
```

S3 is not required for the current setup.

### Database Schema Changes Use Alembic

Do not manually change PostgreSQL tables when the change should be represented by a migration.

The normal workflow is:

```text
Change model
   ↓
Create migration
   ↓
Review migration
   ↓
Run migration
```

### PUT vs PATCH

`PUT` is used for a full post update:

```text
PUT /api/posts/{post_id}
```

`PATCH` is used for a partial update:

```text
PATCH /api/posts/{post_id}
```

For example, a PATCH can update only the title:

```json
{
  "title": "Updated title"
}
```

### Async Database Access

Database endpoints use:

```python
async def
```

and:

```python
await db.execute(...)
await db.commit()
```

This keeps database operations compatible with FastAPI's asynchronous request handling.

### Relationship Loading

The application uses:

```python
selectinload(models.Post.author)
```

to load post authors efficiently when returning posts.

---

## Security Notes

This project implements several important security concepts:

- Passwords are hashed rather than stored as plain text.
- Argon2 is used for password hashing.
- JWT tokens expire.
- JWT secrets are loaded from environment variables.
- Password reset tokens are generated securely.
- Password reset tokens are hashed before database storage.
- Reset tokens expire.
- Reset tokens are deleted after successful password reset.
- Ownership checks protect user-owned resources.
- API and HTML errors are handled separately.
- `.env` should not be committed to Git.
- File uploads have a configurable size limit.
- Uploaded images are processed rather than served using their original filenames.

---

## Known Limitations and Future Improvements

The project is intentionally still a learning/development project.

Possible future improvements include:

### Automated Testing

Add automated tests using:

- `pytest`
- FastAPI test utilities
- Database fixtures
- Authentication fixtures

### Likes

The database already contains:

```text
posts.likes
```

A future version could add:

```text
POST /api/posts/{post_id}/like
DELETE /api/posts/{post_id}/like
```

and a proper user-to-post likes relationship if individual likes need to be tracked.

### Comments

Add:

```text
comments
```

with relationships between users and posts.

### Search

Add post search by:

- title
- content
- author

### Filtering and Sorting

Allow API clients to request:

```text
/api/posts?author_id=1
/api/posts?sort=oldest
```

### Automated Tests

Create a test suite for:

- registration
- login
- JWT validation
- CRUD
- authorization
- pagination
- password reset
- image upload
- image deletion

### Deployment

The project can eventually be containerized with Docker and deployed with:

- PostgreSQL
- FastAPI
- a production ASGI server
- reverse proxy
- persistent media storage

---

## What I Learned

This project was built as a practical study of FastAPI and modern Python backend development.

The main concepts covered include:

### FastAPI

- Application setup
- Path operations
- Request parameters
- Query parameters
- Request bodies
- Dependencies
- Routers
- Response models
- Exception handlers
- Lifespan management
- Static files
- File uploads
- Background tasks
- OpenAPI documentation

### Pydantic

- `BaseModel`
- `Field`
- Type validation
- Email validation
- Optional fields
- Nested response models
- `ConfigDict(from_attributes=True)`
- `model_dump(exclude_unset=True)`
- Serialization

### SQLAlchemy

- Declarative models
- `Mapped`
- `mapped_column`
- Relationships
- Foreign keys
- `select()`
- `where()`
- `func.count()`
- `selectinload()`
- Async sessions
- Transactions
- Commit/refresh/delete operations

### Authentication

- OAuth2 password flow
- JWT
- Bearer tokens
- Password hashing
- Argon2
- Authentication dependencies
- Authorization/ownership checks

### Database Design

- One-to-many relationships
- Foreign keys
- Unique constraints
- Indexes
- Migration history
- Schema evolution

### Web Development

- Jinja2 templates
- Bootstrap
- JavaScript `fetch()`
- `localStorage`
- `FormData`
- Dynamic HTML
- Client-side validation
- API-driven page updates

### File Handling

- `UploadFile`
- Pillow
- Image validation
- Image resizing
- EXIF orientation
- UUID filenames
- Local media storage

### Security

- Environment variables
- Password hashing
- JWT expiration
- Reset token hashing
- Token expiration
- Ownership authorization
- Safe password reset responses

### Debugging

This project also involved real debugging work, including:

- HTTP 422 validation errors
- HTTP 400/401/403/404 responses
- SQLAlchemy database errors
- Missing database tables
- Jinja route errors
- Import errors
- Async database issues
- SMTP/network problems
- Git rollback and recovery
- Removing an S3 integration without losing the rest of the project

---

## Useful Commands

### Start Development Server

```bash
uv run fastapi dev main.py
```

### Synchronize Dependencies

```bash
uv sync
```

### Update the Lock File

```bash
uv lock
```

### Run Migrations

```bash
uv run alembic upgrade head
```

### Check Migration Status

```bash
uv run alembic current
```

### View Migration History

```bash
uv run alembic history
```

### Create Migration

```bash
uv run alembic revision --autogenerate -m "describe change"
```

### Roll Back One Migration

```bash
uv run alembic downgrade -1
```

### Populate Development Database

```bash
uv run python populate_db.py
```

### Check Git Status

```bash
git status
```

### View Recent Commits

```bash
git log --oneline --decorate --graph -15
```

### Compare Changes

```bash
git diff
```

---

## Git Workflow Used During Development

When a major change causes problems, it is safer to inspect Git history before resetting the entire project.

Useful commands:

```bash
git status
git log --oneline --decorate --graph -15
git show <commit>
git diff <old_commit> <new_commit>
```

For a known-good commit:

```bash
git switch --detach <commit>
```

or create a working branch:

```bash
git switch -c working-version <commit>
```

Avoid using:

```bash
git reset --hard
```

unless you deliberately want to move the current branch backward and discard local changes.

For changes that have already been pushed, `git revert` is often safer than rewriting shared history.

---

## Project Status

The current working version demonstrates a complete learning-oriented FastAPI blog with:

- REST API
- Server-rendered web interface
- PostgreSQL
- Async SQLAlchemy
- Alembic migrations
- Pydantic validation
- JWT authentication
- Argon2 password hashing
- User authorization
- CRUD operations
- Pagination
- Password reset
- Email support
- Background tasks
- Local profile image processing
- Swagger UI
- ReDoc
- Development database seeding

The project is suitable as a portfolio/learning project and as a foundation for adding more advanced features.

---

## Author

**Ndungu**

GitHub: [Ndungu-Jn](https://github.com/Ndungu-Jn)

Repository: [fastapi_blog](https://github.com/Ndungu-Jn/fastapi_blog)

---

## License

No license has been specified for this repository yet.