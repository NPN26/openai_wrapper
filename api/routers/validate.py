from fastapi import APIRouter
from pydantic import BaseModel
from api.services.api_key import validate_key
from api.config import OPENAI_BASE_URL

router = APIRouter(prefix="/api", tags=["validation"])

class ValidationRequest(BaseModel):
    api_key: str
    base_url: str = OPENAI_BASE_URL
    
class ValidationResponse(BaseModel):
    valid: bool
    message: str
    
@router.post("/validate", response_model=ValidationResponse)
def validate(request: ValidationRequest):
    valid, message = validate_key(request.api_key, request.base_url)
    return ValidationResponse(valid=valid, message=message)