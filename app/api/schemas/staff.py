from pydantic import BaseModel, Field


class DoctorAssignmentRequest(BaseModel):
    admission_id: int = Field(gt=0)
    doctor_id: int = Field(gt=0)


class NurseAssignmentRequest(BaseModel):
    admission_id: int = Field(gt=0)
    nurse_id: int = Field(gt=0)