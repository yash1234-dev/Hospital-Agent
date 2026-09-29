from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.api.routes.health import router as health_router
from app.api.routes.notification_routes import router as notification_router
from app.api.routes.emergency import router as emergency_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.system_health import router as system_health_router
from app.api.routes.beds import router as beds_router
from app.api.routes.staff import router as staff_router
from app.api.routes.lab import router as lab_router
from app.api.routes.pharmacy import router as pharmacy_router
from app.api.routes.admissions import router as admissions_router


settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    description="Hospital Operations Intelligence and Patient Management API",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS CONFIGURATION
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# ROOT ENDPOINT
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "status": "running",
        "version": "1.0.0",
    }


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

app.include_router(health_router)
app.include_router(emergency_router)
app.include_router(dashboard_router)
app.include_router(system_health_router)
app.include_router(beds_router)
app.include_router(staff_router)
app.include_router(lab_router)
app.include_router(pharmacy_router)
app.include_router(admissions_router)
app.include_router(notification_router)