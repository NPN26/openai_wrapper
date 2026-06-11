from urllib.parse import urlparse

import requests
from api.config import OPENAI_BASE_URL


def _is_azure_endpoint(base_url: str) -> bool:
    try:
        host = urlparse(base_url).netloc.lower()
    except ValueError:
        return False
    return host.endswith(".openai.azure.com") or host.endswith(".services.ai.azure.com")


def _candidate_model_urls(base_url: str) -> list[str]:
    if base_url == OPENAI_BASE_URL:
        return ["https://api.openai.com/v1/models"]

    base = base_url.rstrip("/")
    urls = [f"{base}/models"]

    if not base.endswith("/v1") and not base.endswith("/openai/v1"):
        urls.append(f"{base}/v1/models")

    if base.endswith("/openai/v1"):
        azure_base = base[: -len("/openai/v1")] + "/openai"
        urls.append(f"{azure_base}/models")

    # Additional Azure AI Foundry project patterns
    if ".services.ai.azure.com" in base:
        # If URL contains project path segments, attempt to find the models list at the project root
        if "/openai/v1" in base:
            project_root = base.split("/openai/v1")[0]
            urls.append(f"{project_root}/models")
        elif "/openai" in base:
            project_root = base.split("/openai")[0]
            urls.append(f"{project_root}/models")

    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls

def check_api_key(api_key: str, base_url: str = OPENAI_BASE_URL) -> tuple[bool, str]:
    headers_to_try: list[dict[str, str]]
    if _is_azure_endpoint(base_url):
        # Azure AI Foundry projects can sometimes require Bearer tokens or api-keys
        headers_to_try = [
            {"api-key": api_key},
            {"Authorization": f"Bearer {api_key}"}
        ]
    else:
        headers_to_try = [
            {"Authorization": f"Bearer {api_key}"},
            {"api-key": api_key},
        ]

    status_codes: list[int] = []
    for url in _candidate_model_urls(base_url):
        for headers in headers_to_try:
            try:
                response = requests.get(url, headers=headers, timeout=10)
            except requests.RequestException:
                continue
            status_codes.append(response.status_code)
            if response.status_code == 200:
                return True, "Key is valid for the configured endpoint."

    if not status_codes:
        return False, "Endpoint is unreachable or timed out."

    if all(code in (401, 403) for code in status_codes):
        return False, "Key is invalid for the configured endpoint."

    if all(code >= 500 for code in status_codes):
        return False, "Endpoint error while validating key."

    return True, "Endpoint reachable, but /models validation is not supported."

def validate_key(key: str, base_url: str = OPENAI_BASE_URL) -> tuple[bool, str]:
    try:
        valid, message = check_api_key(key, base_url)
        return valid, message
    except Exception as exc:
        detail = str(exc)
        if "Malformed identifier" in detail:
            detail = (
                f"{detail} Use the Azure deployment name in the Model field and keep the base URL as the resource endpoint, "
                "for example https://YOUR-RESOURCE.openai.azure.com/openai/v1/."
            )
        return False, f"Key validation failed: {detail}"