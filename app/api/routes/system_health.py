from fastapi import APIRouter

from app.database.connection import get_db_connection


router = APIRouter(
    prefix="/api/health",
    tags=["System Health"],
)


def check_database() -> dict:
    """
    Check whether MySQL is reachable and responding.
    """

    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()

            cursor.execute("SELECT 1")

            result = cursor.fetchone()

            cursor.close()

            if result is not None:
                return {
                    "status": "ONLINE",
                    "message": "Database connection is healthy.",
                }

            return {
                "status": "OFFLINE",
                "message": "Database did not return a valid response.",
            }

    except Exception as exc:
        return {
            "status": "OFFLINE",
            "message": str(exc),
        }


def check_orchestrator() -> dict:
    """
    Verify that the agent orchestration layer can be imported
    and initialized.
    """

    try:
        from app.orchestration.orchestrator import Orchestrator

        orchestrator = Orchestrator(
            workflow_name="system_health_check"
        )

        if orchestrator is not None:
            return {
                "status": "READY",
                "message": "Agent orchestrator is available.",
            }

        return {
            "status": "NOT_READY",
            "message": "Agent orchestrator could not be initialized.",
        }

    except Exception as exc:
        return {
            "status": "NOT_READY",
            "message": str(exc),
        }


def check_action_gateway() -> dict:
    """
    Verify that the Action Gateway can be imported
    and initialized.
    """

    try:
        from app.gateway.action_gateway import ActionGateway

        gateway = ActionGateway()

        if gateway is not None:
            return {
                "status": "READY",
                "message": "Action Gateway is available.",
            }

        return {
            "status": "NOT_READY",
            "message": "Action Gateway could not be initialized.",
        }

    except Exception as exc:
        return {
            "status": "NOT_READY",
            "message": str(exc),
        }


@router.get("/system")
def get_system_health():
    """
    Return the operational status of the major
    Hospital AI backend components.
    """

    database = check_database()
    orchestrator = check_orchestrator()
    action_gateway = check_action_gateway()

    return {
        "status": "HEALTHY"
        if (
            database["status"] == "ONLINE"
            and orchestrator["status"] == "READY"
            and action_gateway["status"] == "READY"
        )
        else "DEGRADED",
        "services": {
            "fastapi": {
                "status": "ONLINE",
                "message": "FastAPI API is responding.",
            },
            "mysql": database,
            "orchestrator": orchestrator,
            "action_gateway": action_gateway,
        },
    }