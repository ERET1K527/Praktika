from pydantic import BaseModel


class EmployerCreate(BaseModel):
    company_name: str
    website: str | None = None
    description: str | None = None
    phone: str | None = None


class EmployerUpdate(BaseModel):
    company_name: str | None = None
    website: str | None = None
    description: str | None = None
    phone: str | None = None


class EmployerOut(BaseModel):
    id: int
    user_id: int
    company_name: str
    website: str | None
    description: str | None
    phone: str | None
    verified: bool

    model_config = {"from_attributes": True}
