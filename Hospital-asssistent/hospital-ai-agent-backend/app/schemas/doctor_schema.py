from pydantic import BaseModel


class DoctorCreate(BaseModel):
    name: str
    department: str
    specialization: str | None = None


class DoctorResponse(DoctorCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True