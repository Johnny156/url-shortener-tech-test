import random

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from urllib.parse import urlparse

redis_client = redis.Redis(host="pocket-redis", port=6379, decode_responses=True)
app = FastAPI()
BASE_URL: str = "http://locahost:8000"
BASE_SIZE: int = 8


class ShortenRequest(BaseModel):
    url: str


def create_short_token(symbols: str = "0123456789abcdefghijklmnopqrstuvwxyz", size: int = BASE_SIZE) -> str:
    return ''.join(random.choice(symbols) for _ in range(size))


def create_redis_token_key(token: str) -> str:
    return "shorten_token:" + token


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        is_valid = all((result.scheme, result.netloc))
    except ValueError:
        is_valid = False

    return is_valid


@app.post("/url/shorten")
async def url_shorten(request: ShortenRequest):
    """
    Given a URL, generate a short version of the URL that can be later resolved to the originally
    specified URL.
    """
    if not is_valid_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid URL format.")

    max_token_attempts = 10

    short_size = BASE_SIZE
    if len(request.url) < short_size:
        short_size = len(request.url)

    short_token = create_short_token(size=short_size)
    short_token_key = create_redis_token_key(short_token)

    token_attempts = 0
    while await redis_client.exists(short_token_key) and token_attempts < max_token_attempts:
        short_token = create_short_token()
        short_token_key = create_redis_token_key(short_token)
        token_attempts += 1
    else:
        if token_attempts < max_token_attempts:
            await redis_client.set(short_token_key, request.url)
        else:
            raise HTTPException(status_code=500, detail="Insufficient token space.")

    return {"short_url": f"{BASE_URL}/r/{short_token}"}


class ResolveRequest(BaseModel):
    short_url: str


@app.get("/r/{short_url}")
async def url_resolve(short_url: str):
    """
    Return a redirect response for a valid shortened URL string.
    If the short URL is unknown, return an HTTP 404 response.
    """
    found_url = await redis_client.get(create_redis_token_key(short_url))
    if found_url is None:
        raise HTTPException(status_code=404, detail=f"Unknown short URL {found_url}")

    return RedirectResponse(url=found_url)


@app.get("/")
async def index():
    return "Your URL Shortener is running!"
