import requests
from config import OPENAI_BASE_URL

def check_api_key(api_key: str, base_url: str = OPENAI_BASE_URL) -> bool:
    try:
        if base_url != OPENAI_BASE_URL:
            # Ensure we are hitting a valid endpoint like /models for validation
            response = requests.get(
                f"{base_url.rstrip('/')}/models",
                headers={"api-key": api_key},
                timeout=10
            )
        else:
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10
            )
        return response.status_code == 200
    except requests.RequestException:
        return False

def validate_key(key: str, base_url: str = OPENAI_BASE_URL) -> tuple[bool, str]:
    try:
        if check_api_key(key, base_url):
            return True, "Key is valid for the configured endpoint."
        return False, "Key is invalid or the configured endpoint is unreachable."
    except Exception as exc:
        detail = str(exc)
        if "Malformed identifier" in detail:
            detail = (
                f"{detail} Use the Azure deployment name in the Model field and keep the base URL as the resource endpoint, "
                "for example https://YOUR-RESOURCE.openai.azure.com/openai/v1/."
            )
        return False, f"Key validation failed: {detail}"