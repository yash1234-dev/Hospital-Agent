from fastapi import APIRouter

from app.database.connection import get_db_connection


router = APIRouter(
    prefix="/api/health",
    tags=["Health"],
)


@router.get("")
def health_check():
    """
    Basic health check for the Hospital AI backend.
    """

    return {
        "status": "ok",
        "service": "Hospital AI Backend",
    }


@router.get("/database")
def database_health_check():
    """
    Check connectivity between the API and MySQL database.
    """

    try:
        with get_db_connection() as connection:
            if connection.is_connected():
                return {
                    "status": "ok",
                    "database": "connected",
                }

            return {
                "status": "error",
                "database": "disconnected",
            }

    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
        }