from typing import Any

from app.tools.base_tool import BaseTool
from app.tools.bed_tools import (
    get_available_beds,
    get_eligible_admissions,
)
from app.gateway.action_gateway import ActionGateway


class BedTool(BaseTool):
    """
    Agent-facing tool for hospital bed operations.

    Read operations are delegated to the existing
    bed_tools.py implementation.

    State-changing operations are delegated to the
    ActionGateway.
    """

    def __init__(
        self,
        action_gateway: ActionGateway | None = None,
    ) -> None:
        super().__init__(
            tool_name="bed_tool",
            description=(
                "Retrieve available hospital beds and "
                "perform authorized bed operations."
            ),
        )

        self.action_gateway = (
            action_gateway
            if action_gateway is not None
            else ActionGateway()
        )

    # =========================================================
    # READ OPERATION
    # =========================================================

    def get_available_beds(
        self,
        bed_type: str | None = None,
        room_type: str | None = None,
        department_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve currently available beds.

        Delegates the database read operation to the
        existing bed_tools.py implementation.
        """

        return get_available_beds(
            bed_type=bed_type,
            room_type=room_type,
            department_id=department_id,
        )

    # =========================================================
    # ACTION OPERATION
    # =========================================================

    def reserve_bed(
        self,
        bed_id: int,
        patient_id: str,
        admission_id: int,
        requested_by_agent: str = "BedAgent",
    ) -> dict[str, Any]:
        """
        Reserve a hospital bed for a patient.

        This method NEVER updates the beds table directly.

        It creates an Action Gateway request and allows
        the Action Gateway to perform structural validation
        and execute the authoritative MySQL stored procedure.
        """

        if bed_id <= 0:
            raise ValueError(
                "bed_id must be a positive integer."
            )

        if not patient_id.strip():
            raise ValueError(
                "patient_id cannot be empty."
            )
        if admission_id <= 0:
           raise ValueError(
                 "admission_id must be a positive integer."
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
                action_type="RESERVE_BED",
                requested_by_agent=requested_by_agent,
                request_payload={
                    "bed_id": bed_id,
                    "patient_id": patient_id,
                    "admission_id": admission_id,
                },
                patient_id=patient_id,
                admission_id=admission_id,
                target_type="BED",
                target_id=str(bed_id),
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
        Execute a supported BedTool operation.

        Supported operations:

            get_available_beds
            reserve_bed
        """

        # -----------------------------------------------------
        # GET AVAILABLE BEDS
        # -----------------------------------------------------

        if operation == "get_available_beds":

            return self.get_available_beds(
                bed_type=kwargs.get("bed_type"),
                room_type=kwargs.get("room_type"),
                department_id=kwargs.get("department_id"),
            )

        # -----------------------------------------------------
        # RESERVE BED
        # -----------------------------------------------------

        if operation == "reserve_bed":

            if "bed_id" not in kwargs:
                raise ValueError(
                    "bed_id is required for reserve_bed."
                )

            if "patient_id" not in kwargs:
                raise ValueError(
                    "patient_id is required for reserve_bed."
                )
            if "admission_id" not in kwargs:
                raise ValueError(
                     "admission_id is required for reserve_bed."
             )
            return self.reserve_bed(
                bed_id=int(kwargs["bed_id"]),
                patient_id=str(kwargs["patient_id"]),
                admission_id=int(kwargs["admission_id"]),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "BedAgent",
                ),
            )

        # -----------------------------------------------------
        # INVALID OPERATION
        # -----------------------------------------------------

        raise ValueError(
            f"Unsupported BedTool operation: {operation}"
        )
        
    def get_eligible_admissions(self) -> list[dict[str, Any]]:
        """
        Retrieve admissions that are eligible for bed assignment.
        """

        return get_eligible_admissions()    