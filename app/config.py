# app/config.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter configuration: 20 requests per minute by default
limiter = Limiter(key_func=get_remote_address, default_limits=["20/minute"])
