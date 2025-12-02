from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from datetime import datetime

app = FastAPI()

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    roles: list[str] = Field(default_factory=list)

class UserRead(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

@app.post("/test", response_model=UserRead)
async def test_endpoint():
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "username": "test",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
