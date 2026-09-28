from typing import Any

from app.tools.base_tool import BaseTool
from app.tools.emergency_tools import (
    get_emergency_incident,
    get_available_ambulances,
    get_ambulance_dispatch,
)
from app.gateway.action_gateway import ActionGateway


class EmergencyTool(BaseTool):
    """
    Agent-facing tool for hospital emergency operations.

    Read operations are delegated to emergency_tools.py.

    State-changing operations are delegated to the
    ActionGateway.
    """

    def __init__(
        self,
        action_gateway: ActionGateway | None = None,
    ) -> None:
        super().__init__(
            tool_name="emergency_tool",
            description=(
                "Retrieve emergency incidents, available ambulances, "
                "and ambulance dispatch information."
            ),
        )

        self.action_gateway = (
            action_gateway
            if action_gateway is not None
            else ActionGateway()
        )

    # =========================================================
    # GET EMERGENCY INCIDENT
    # =========================================================

    def get_emergency_incident(
        self,
        incident_id: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve a specific emergency incident.
        """

        return get_emergency_incident(
            incident_id=incident_id,
        )

    # =========================================================
    # GET AVAILABLE AMBULANCES
    # =========================================================

    def get_available_ambulances(
        self,
        ambulance_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve currently available ambulances.

        Optional ambulance type:

            BASIC_LIFE_SUPPORT
            ADVANCED_LIFE_SUPPORT
            PATIENT_TRANSPORT
        """

        return get_available_ambulances(
            ambulance_type=ambulance_type,
        )

    # =========================================================
    # GET AMBULANCE DISPATCH
    # =========================================================

    def get_ambulance_dispatch(
        self,
        dispatch_id: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve a specific ambulance dispatch.
        """

        return get_ambulance_dispatch(
            dispatch_id=dispatch_id,
        )

    # =========================================================
    # REQUEST TRANSPORT
    # =========================================================

    def request_transport(
        self,
        incident_id: int,
        requested_by_agent: str = "TriageAgent",
    ) -> dict[str, Any]:
        """
        Request emergency transportation for an incident.

        The EmergencyTool does not directly modify the
        emergency_incidents table.

        The request is sent through the ActionGateway.
        """

        if incident_id <= 0:
            raise ValueError(
                "incident_id must be a positive integer."
            )

        if not requested_by_agent.strip():
            raise ValueError(
                "requested_by_agent cannot be empty."
            )

        # -----------------------------------------------------
        # Create gateway request
        # -----------------------------------------------------

        gateway_request_id = (
            self.action_gateway.create_request(
                action_type="REQUEST_TRANSPORT",
                requested_by_agent=requested_by_agent,
                request_payload={
                    "incident_id": incident_id,
                },
                incident_id=incident_id,
                target_type="INCIDENT",
                target_id=str(incident_id),
            )
        )

        # -----------------------------------------------------
        # Execute through Action Gateway
        # -----------------------------------------------------

        result = self.action_gateway.execute_action(
            gateway_request_id
        )

        return result

    # =========================================================
    # DISPATCH AMBULANCE
    # =========================================================

    def dispatch_ambulance(
        self,
        incident_id: int,
        ambulance_id: int,
        requested_by_agent: str = "AmbulanceAgent",
    ) -> dict[str, Any]:
        """
        Dispatch an ambulance for an emergency incident.

        The EmergencyTool does not directly modify:

            - ambulances
            - emergency_incidents
            - ambulance_dispatches

        The request is sent through the ActionGateway,
        which performs validation and executes
        dispatch_ambulance_v1.
        """

        if incident_id <= 0:
            raise ValueError(
                "incident_id must be a positive integer."
            )

        if ambulance_id <= 0:
            raise ValueError(
                "ambulance_id must be a positive integer."
            )

        if not requested_by_agent.strip():
            raise ValueError(
                "requested_by_agent cannot be empty."
            )

        # -----------------------------------------------------
        # Create gateway request
        # -----------------------------------------------------

        gateway_request_id = (
            self.action_gateway.create_request(
                action_type="DISPATCH_AMBULANCE",
                requested_by_agent=requested_by_agent,
                request_payload={
                    "incident_id": incident_id,
                    "ambulance_id": ambulance_id,
                },
                incident_id=incident_id,
                target_type="AMBULANCE",
                target_id=str(ambulance_id),
            )
        )

        # -----------------------------------------------------
        # Execute through Action Gateway
        # -----------------------------------------------------

        result = self.action_gateway.execute_action(
            gateway_request_id
        )

        return result

    # =========================================================
    # BASE TOOL EXECUTION INTERFACE
    # =========================================================

    def execute(
        self,
        operation: str,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a supported EmergencyTool operation.

        Supported operations:

            get_emergency_incident
            get_available_ambulances
            get_ambulance_dispatch
            request_transport
            dispatch_ambulance
        """

        # -----------------------------------------------------
        # GET EMERGENCY INCIDENT
        # -----------------------------------------------------

        if operation == "get_emergency_incident":

            if "incident_id" not in kwargs:
                raise ValueError(
                    "incident_id is required for "
                    "get_emergency_incident."
                )

            return self.get_emergency_incident(
                incident_id=int(
                    kwargs["incident_id"]
                )
            )

        # -----------------------------------------------------
        # GET AVAILABLE AMBULANCES
        # -----------------------------------------------------

        if operation == "get_available_ambulances":

            return self.get_available_ambulances(
                ambulance_type=kwargs.get(
                    "ambulance_type"
                )
            )

        # -----------------------------------------------------
        # GET AMBULANCE DISPATCH
        # -----------------------------------------------------

        if operation == "get_ambulance_dispatch":

            if "dispatch_id" not in kwargs:
                raise ValueError(
                    "dispatch_id is required for "
                    "get_ambulance_dispatch."
                )

            return self.get_ambulance_dispatch(
                dispatch_id=int(
                    kwargs["dispatch_id"]
                )
            )

        # -----------------------------------------------------
        # REQUEST TRANSPORT
        # -----------------------------------------------------

        if operation == "request_transport":

            if "incident_id" not in kwargs:
                raise ValueError(
                    "incident_id is required for "
                    "request_transport."
                )

            return self.request_transport(
                incident_id=int(
                    kwargs["incident_id"]
                ),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "TriageAgent",
                ),
            )

        # -----------------------------------------------------
        # DISPATCH AMBULANCE
        # -----------------------------------------------------

        if operation == "dispatch_ambulance":

            if "incident_id" not in kwargs:
                raise ValueError(
                    "incident_id is required for "
                    "dispatch_ambulance."
                )

            if "ambulance_id" not in kwargs:
                raise ValueError(
                    "ambulance_id is required for "
                    "dispatch_ambulance."
                )

            return self.dispatch_ambulance(
                incident_id=int(
                    kwargs["incident_id"]
                ),
                ambulance_id=int(
                    kwargs["ambulance_id"]
                ),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "AmbulanceAgent",
                ),
            )

        # -----------------------------------------------------
        # INVALID OPERATION
        # -----------------------------------------------------

        raise ValueError(
            f"Unsupported EmergencyTool operation: {operation}"
        )