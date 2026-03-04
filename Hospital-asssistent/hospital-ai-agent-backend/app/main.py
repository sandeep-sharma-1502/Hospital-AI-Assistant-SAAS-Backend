from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
import time
import asyncio
import traceback

# Logging
from app.core.logging import setup_logging, get_logger

# DB
from app.db.database import engine

# Routers
from app.api.v1.webrtc import router as webrtc_router
from app.api.v1.admin.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.admin.doctors import router as doctor_router
from app.api.v1.admin.schedule import router as schedule_router
from app.api.v1.public.slots import router as public_slot_router
from app.api.v1.admin.slots import router as admin_slot_router
from app.api.v1.admin.appointments import router as appointment_router

# Settings
from app.core.config import settings


# =========================================================
# 1️⃣ Initialize Logging
# =========================================================
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Hospital AI Admin API",
    version="1.0.0"
)

# =========================================================
# 2️⃣ CAPTURE ASYNC BACKGROUND ERRORS (VERY IMPORTANT)
# =========================================================
def handle_async_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.error("🔥 Async Background Error", exc_info=msg)

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_async_exception)


# =========================================================
# 3️⃣ SECURITY HEADERS MIDDLEWARE
# =========================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "no-referrer"

        return response


app.add_middleware(SecurityHeadersMiddleware)


# =========================================================
# 4️⃣ CORS CONFIGURATION
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# =========================================================
# 5️⃣ REQUEST LOGGING (SAFE VERSION)
# =========================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception("🔥 Request crashed")
        raise

    process_time = round((time.time() - start_time) * 1000, 2)

    logger.info(
        f"{request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Time: {process_time}ms"
    )

    return response


# =========================================================
# 6️⃣ GLOBAL EXCEPTION HANDLER (FULL STACK TRACE)
# =========================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("🔥 Unhandled Global Exception")

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# =========================================================
# 7️⃣ INCLUDE ROUTERS
# =========================================================

app.include_router(health_router, prefix="/api/v1")
app.include_router(webrtc_router, prefix="/api/v1/webrtc")
app.include_router(auth_router, prefix="/api/v1/auth")

app.include_router(doctor_router, prefix="/api/v1/admin")
app.include_router(schedule_router, prefix="/api/v1/admin")
app.include_router(admin_slot_router, prefix="/api/v1/admin")
app.include_router(appointment_router, prefix="/api/v1/admin")

app.include_router(public_slot_router, prefix="/api/v1")


# =========================================================
# 8️⃣ STARTUP EVENT
# =========================================================
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Application is starting up...")


# =========================================================
# 9️⃣ HEALTH CHECK
# =========================================================
@app.get("/health")
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        return {"status": "ok", "db": "connected"}

    except Exception:
        logger.exception("❌ Health check failed")
        return {
            "status": "error",
            "db": "not connected",
            "details": "Check server logs"
        }