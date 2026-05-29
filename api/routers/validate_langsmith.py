from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from api.services.langsmith_key import validate_langsmith_key


router = APIRouter(prefix="/api", tags=["validation"])


class ValidateRequest(BaseModel):
	api_url: Optional[str] = None
	workspace_id: Optional[str] = None


@router.post("/validate-langsmith")
def validate_key(
	payload: ValidateRequest,
	x_langsmith_api_key: str = Header(..., alias="X-LangSmith-Api-Key"),
):
	valid, err = validate_langsmith_key(
		x_langsmith_api_key,
		api_url=payload.api_url,
		workspace_id=payload.workspace_id,
	)
	if not valid:
		raise HTTPException(status_code=401, detail=f"Invalid LangSmith API key: {err}")
	return {"valid": True}