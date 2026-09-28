from pydantic import BaseModel, Field


class EmergencyTriageRequest(BaseModel):
    """
    Request payload for starting an emergency triage workflow.
    """

    incident_id: int = Field(
        ...,
        gt=0,
        description="Emergency incident ID to process.",
    )