import asyncio
import random

import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from urllib.parse import urlparse


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Lifecycle manager for handling the open Redis connection on startup and shutdown of the application
    """
    application.state.redis_client = redis.Redis(host="pocket-redis", port=6379, decode_responses=True)
    yield
    await application.state.redis_client.close()


app = FastAPI(lifespan=lifespan)
BASE_URL: str = "http://localhost:8000"
BASE_SIZE: int = 8


def create_short_token(symbols: str = "0123456789abcdefghijklmnopqrstuvwxyz", size: int = BASE_SIZE) -> str:
    """
    Simple algorithm for creating a random short code.
    """
    return ''.join(random.choice(symbols) for _ in range(size))


def create_redis_token_key(token: str) -> str:
    """
    Helper method to decorate Redis key strings shorten token namespace.
    """
    return "shorten_token:" + token


def create_redis_rindex_key(target: str) -> str:
    """
    Helper method to decorate Redis key strings for reverse index.
    """
    return "rindex_key:" + target


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        is_valid = all((result.scheme, result.netloc))
    except ValueError:
        is_valid = False

    return is_valid


class ShortenRequest(BaseModel):
    url: str


@app.post("/url/shorten")
async def url_shorten(shorten_request: ShortenRequest, request: Request):
    """
    Given a URL, generate a short version of the URL that can be later resolved to the originally
    specified URL.
    """
    if not is_valid_url(shorten_request.url):
        # Validate that input is a valid url format.
        raise HTTPException(status_code=400, detail="Invalid URL format.")

    max_token_attempts = 10

    short_size = BASE_SIZE
    if len(shorten_request.url) < short_size:
        # Simple test to keep the short code at least as short as the given url.
        short_size = len(shorten_request.url)

    short_token = create_short_token(size=short_size)
    short_token_key = create_redis_token_key(short_token)
    rindex_key = create_redis_rindex_key(shorten_request.url)

    existing_token = await request.app.state.redis_client.get(rindex_key)
    if existing_token is not None:
        # If we have shortened this URL before, return back the pre-existing token.
        short_token = existing_token
    else:
        token_attempts = 0
        while await request.app.state.redis_client.exists(short_token_key) and token_attempts < max_token_attempts:
            # Try to generate an unused random code, up to a configurable threshold.
            short_token = create_short_token()
            short_token_key = create_redis_token_key(short_token)
            token_attempts += 1
        else:
            if token_attempts < max_token_attempts:
                # Add the token to the datastore, along with the reverse lookup to reduce redundancy.
                await asyncio.gather(
                    request.app.state.redis_client.set(short_token_key, shorten_request.url),
                    request.app.state.redis_client.set(create_redis_rindex_key(shorten_request.url), short_token))

            else:
                # If we were unable to create a new random token, report back and error.
                raise HTTPException(status_code=500, detail="Insufficient token space.")

    return {"short_url": f"{BASE_URL}/r/{short_token}"}


class ResolveRequest(BaseModel):
    short_url: str


@app.get("/r/{short_url}")
async def url_resolve(short_url: str, request: Request):
    """
    Return a redirect response for a valid shortened URL string.
    If the short URL is unknown, return an HTTP 404 response.
    """
    found_url = await request.app.state.redis_client.get(create_redis_token_key(short_url))
    if found_url is None:
        raise HTTPException(status_code=404, detail=f"Unknown short URL {found_url}")

    return RedirectResponse(url=found_url)


@app.get("/")
async def index():
    return "Your URL Shortener is running!"
