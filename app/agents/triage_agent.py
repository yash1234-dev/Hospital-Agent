from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.tools.emergency_tool import EmergencyTool


class TriageAgent(BaseAgent):
    """
    Determines the operational next step for an emergency incident.

    Current version:
        - Deterministic rule-based logic
        - Uses EmergencyTool to retrieve incident information
        - Does not execute hospital actions
        - Produces an AgentResult containing the next decision

    Later:
        - LLM-based triage reasoning can be added
        - Structured LLM output can replace/augment these rules
    """

    HIGH_SEVERITIES = {"HIGH", "CRITICAL"}

    TRIAGED_STATUS = "TRIAGED"

    TRANSPORT_IN_PROGRESS_STATUSES = {
        "AWAITING_TRANSPORT",
        "IN_TRANSIT",
        "ARRIVED",
    }

    def __init__(
        self,
        emergency_tool: EmergencyTool | None = None,
    ) -> None:
        super().__init__(agent_name="TriageAgent")

        self.emergency_tool = emergency_tool or EmergencyTool()

    def process(self, context: AgentContext) -> AgentResult:
        """
        Execute the triage decision process.
        """

        # ---------------------------------------------------------
        # 1. Validate context
        # ---------------------------------------------------------

        if context is None:
            return AgentResult(
                status="FAILED",
                reason="AgentContext cannot be None.",
            )

        if context.incident_id is None:
            return AgentResult(
                status="FAILED",
                reason="Incident ID is required for triage.",
            )

        # ---------------------------------------------------------
        # 2. Retrieve incident using EmergencyTool
        # ---------------------------------------------------------

        incident = self.emergency_tool.run(
            operation="get_emergency_incident",
            incident_id=context.incident_id,
        )

        if not incident:
            return AgentResult(
                status="FAILED",
                reason=(
                    f"Emergency incident "
                    f"{context.incident_id} was not found."
                ),
            )

        # ---------------------------------------------------------
        # 3. Extract incident information
        # ---------------------------------------------------------

        incident_id = incident.get("incident_id")
        patient_id = incident.get("patient_id")
        admission_id = incident.get("admission_id")
        department_id = incident.get("department_id")
        incident_type = incident.get("incident_type")
        severity = incident.get("severity")
        incident_status = incident.get("status")

        # ---------------------------------------------------------
        # 4. Store core identifiers in shared context
        # ---------------------------------------------------------

        context.incident_id = incident_id
        context.patient_id = patient_id
        context.admission_id = admission_id
        context.department_id = department_id

        # ---------------------------------------------------------
        # 5. Store additional incident information in shared data
        # ---------------------------------------------------------

        context.add_data("incident_id", incident_id)
        context.add_data("patient_id", patient_id)
        context.add_data("admission_id", admission_id)
        context.add_data("department_id", department_id)
        context.add_data("incident_type", incident_type)
        context.add_data("severity", severity)
        context.add_data("incident_status", incident_status)

        # ---------------------------------------------------------
        # 6. Validate required incident fields
        # ---------------------------------------------------------

        if severity is None:
            return AgentResult(
                status="FAILED",
                reason="Incident severity is missing.",
                data={
                    "incident_id": incident_id,
                },
            )

        if incident_status is None:
            return AgentResult(
                status="FAILED",
                reason="Incident status is missing.",
                data={
                    "incident_id": incident_id,
                },
            )

        # ---------------------------------------------------------
        # 7. Normalize values
        # ---------------------------------------------------------

        severity = str(severity).upper()
        incident_status = str(incident_status).upper()

        # ---------------------------------------------------------
        # 8. Determine operational decision
        # ---------------------------------------------------------

        if incident_status == self.TRIAGED_STATUS:

            if severity in self.HIGH_SEVERITIES:
                decision = "REQUEST_TRANSPORT"

                reason = (
                    f"Incident {incident_id} is TRIAGED with "
                    f"{severity} severity. Emergency transport "
                    f"is required."
                )

            else:
                decision = "NO_ACTION"

                reason = (
                    f"Incident {incident_id} is TRIAGED with "
                    f"{severity} severity. No transport action "
                    f"is required under the current triage policy."
                )

        elif incident_status in self.TRANSPORT_IN_PROGRESS_STATUSES:

            decision = "NO_ACTION"

            reason = (
                f"Incident {incident_id} already has transport "
                f"status {incident_status}. No additional "
                f"transport request is required."
            )

        else:

            decision = "NO_ACTION"

            reason = (
                f"Incident {incident_id} has status "
                f"{incident_status}. No triage action is required."
            )

        # ---------------------------------------------------------
        # 9. Record decision in shared context
        # ---------------------------------------------------------

       

        # ---------------------------------------------------------
        # 10. Return structured result
        # ---------------------------------------------------------

        return AgentResult(
            status="SUCCESS",
            decision=decision,
            reason=reason,
            data={
                "incident_id": incident_id,
                "patient_id": patient_id,
                "admission_id": admission_id,
                "department_id": department_id,
                "incident_type": incident_type,
                "severity": severity,
                "incident_status": incident_status,
            },
            actions=[],
        )