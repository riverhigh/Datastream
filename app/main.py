from fastapi import FastAPI, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import limiter  # Import limiter from config
from app.routes import analytics

app = FastAPI(
    title="DataStream API",
    description="A super cool data analytics API built by a 16-year-old! Now with even more features 🚀",
    version="1.0.0"
)

# Set up rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# API Key Authentication
API_KEY = "my-test-key-123"  # Change this for security!
api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

# Include routes with authentication
app.include_router(analytics.router, dependencies=[Security(get_api_key)])

@app.get("/")
async def root():
    return {"message": "Welcome to DataStream API! Built by a teen coder—upload data, analyze, and have fun!"}