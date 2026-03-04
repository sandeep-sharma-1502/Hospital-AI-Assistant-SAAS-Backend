from pydantic import BaseModel, field_validator
from app.utils.validators import validate_phone_number


class AppointmentCreate(BaseModel):
    patient_name: str
    phone_number: str
    doctor_id: int
    availability_slot_id: int

    email: str | None = None
    age: int | None = None
    gender: str | None = None
    reason_for_visit: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        return validate_phone_number(v)