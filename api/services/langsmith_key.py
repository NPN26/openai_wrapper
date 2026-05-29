from typing import Optional, Tuple

from langsmith import Client

from api.config import LANGSMITH_BASE_URL


def validate_langsmith_key(api_key: str, api_url: Optional[str] = LANGSMITH_BASE_URL, workspace_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
	"""Validate a LangSmith API key by performing a lightweight list call.

	Returns (True, None) on success, otherwise (False, error_message).
	"""
	try:
		client_kwargs = {"api_key": api_key}
		if api_url:
			client_kwargs["api_url"] = api_url
		if workspace_id:
			client_kwargs["workspace_id"] = workspace_id

		client = Client(**client_kwargs)

		# Try a lightweight list call on known collection endpoints.
		client.list_projects(limit=1)

		return True, None
	except Exception as e:
		return False, str(e)

