from pydantic import BaseModel


class ResourceCreate(BaseModel):
    name: str


class ShareRequest(BaseModel):
    user_email: str
    relation: str = "viewer"


class ResourceResponse(BaseModel):
    id: int
    uuid: str
    name: str
    owner: str

    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    email: str
    name: str


class MessageResponse(BaseModel):
    message: str


class ShareResponse(BaseModel):
    message: str
    resource_uuid: str
    shared_with: str
    relation: str


class HealthResponse(BaseModel):
    status: str