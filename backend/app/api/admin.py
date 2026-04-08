"""Admin APIs for login, config management, and model discovery."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.storage import create_admin_session, is_admin_session_valid

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class AdminLoginResponse(BaseModel):
    success: bool
    token: str = ""


class ConfigResponse(BaseModel):
    AI_VISION_API_BASE_URL: str
    AI_VISION_MODEL_NAME: str
    AI_TEXT_API_BASE_URL: str
    AI_TEXT_MODEL_NAME: str
    SOLVE_API_BASE_URL: str
    SOLVE_MODEL_NAME: str
    MAX_IMAGE_SIZE_MB: int


class ConfigUpdateRequest(BaseModel):
    AI_VISION_API_KEY: str | None = None
    AI_VISION_API_BASE_URL: str | None = None
    AI_VISION_MODEL_NAME: str | None = None
    AI_TEXT_API_KEY: str | None = None
    AI_TEXT_API_BASE_URL: str | None = None
    AI_TEXT_MODEL_NAME: str | None = None
    SOLVE_API_KEY: str | None = None
    SOLVE_API_BASE_URL: str | None = None
    SOLVE_MODEL_NAME: str | None = None


class ConfigUpdateResponse(BaseModel):
    success: bool
    message: str
    config: ConfigResponse


class ModelListRequest(BaseModel):
    api_key: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)


class ModelInfo(BaseModel):
    id: str
    name: str
    description: str = ""


class ModelListResponse(BaseModel):
    success: bool
    models: list[ModelInfo]
    provider: str = ""
    message: str = ""


COMMON_MODELS = {
    "qwen": [
        ModelInfo(id="qwen-vl-max", name="Qwen VL Max", description="Alibaba Cloud flagship vision model"),
        ModelInfo(id="qwen-vl-plus", name="Qwen VL Plus", description="Alibaba Cloud vision model"),
        ModelInfo(id="qwen-max", name="Qwen Max", description="Alibaba Cloud flagship text model"),
        ModelInfo(id="qwen-plus", name="Qwen Plus", description="Alibaba Cloud general text model"),
        ModelInfo(id="qwen-turbo", name="Qwen Turbo", description="Alibaba Cloud fast text model"),
    ],
    "claude": [
        ModelInfo(id="claude-3-7-sonnet-20250219", name="Claude 3.7 Sonnet", description="Anthropic reasoning model"),
        ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", description="Anthropic balanced model"),
        ModelInfo(id="claude-3-5-haiku-20241022", name="Claude 3.5 Haiku", description="Anthropic fast model"),
        ModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus", description="Anthropic flagship model"),
    ],
    "gemini": [
        ModelInfo(id="gemini-2.5-pro-exp-03-25", name="Gemini 2.5 Pro", description="Google high-end model"),
        ModelInfo(id="gemini-2.0-flash", name="Gemini 2.0 Flash", description="Google fast multimodal model"),
        ModelInfo(id="gemini-2.0-flash-lite", name="Gemini 2.0 Flash Lite", description="Google lightweight model"),
        ModelInfo(id="gemini-1.5-pro", name="Gemini 1.5 Pro", description="Google professional model"),
        ModelInfo(id="gemini-1.5-flash", name="Gemini 1.5 Flash", description="Google fast model"),
    ],
    "openai": [
        ModelInfo(id="gpt-4o", name="GPT-4o", description="OpenAI multimodal model"),
        ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", description="OpenAI cost-efficient model"),
        ModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo", description="OpenAI text model"),
        ModelInfo(id="gpt-3.5-turbo", name="GPT-3.5 Turbo", description="OpenAI fast model"),
    ],
    "deepseek": [
        ModelInfo(id="deepseek-chat", name="DeepSeek Chat", description="DeepSeek conversation model"),
        ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner", description="DeepSeek reasoning model"),
    ],
}


def _ensure_admin_password_configured() -> None:
    if not settings.has_secure_admin_password():
        raise HTTPException(
            status_code=503,
            detail="Admin access is disabled until ADMIN_PASSWORD is configured to a non-default value.",
        )


def _verify_admin_token(token: str | None) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="Missing admin token")
    if not is_admin_session_valid(token):
        raise HTTPException(status_code=401, detail="Admin session is invalid or expired")


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(req: AdminLoginRequest):
    _ensure_admin_password_configured()
    if not settings.verify_admin(req.password):
        raise HTTPException(status_code=401, detail="Password is incorrect")
    return AdminLoginResponse(success=True, token=create_admin_session())


@router.get("/config", response_model=ConfigResponse)
async def get_config(x_admin_token: str = Header(..., description="Admin session token")):
    _verify_admin_token(x_admin_token)
    return ConfigResponse(**settings.get_public_config())


@router.post("/config", response_model=ConfigUpdateResponse)
async def update_config(
    req: ConfigUpdateRequest,
    x_admin_token: str = Header(..., description="Admin session token"),
):
    _verify_admin_token(x_admin_token)

    updates = {
        key: value
        for key, value in req.model_dump().items()
        if value is not None
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No configuration fields were provided")

    try:
        settings.update_config(**updates)
    except Exception as exc:  # pragma: no cover - defensive surface
        raise HTTPException(status_code=500, detail=f"Failed to update config: {exc}") from exc

    return ConfigUpdateResponse(
        success=True,
        message="Configuration updated successfully",
        config=ConfigResponse(**settings.get_public_config()),
    )


def _detect_provider(base_url: str) -> str:
    base_lower = base_url.lower()
    if "dashscope" in base_lower or "aliyun" in base_lower:
        return "qwen"
    if "anthropic" in base_lower:
        return "claude"
    if "google" in base_lower or "generativelanguage" in base_lower:
        return "gemini"
    if "deepseek" in base_lower:
        return "deepseek"
    if "openai" in base_lower or "api.openai.com" in base_lower:
        return "openai"
    return "unknown"


async def _fetch_openai_compatible_models(api_key: str, base_url: str) -> list[ModelInfo]:
    url = f"{base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    models: list[ModelInfo] = []
    for item in data.get("data", []):
        model_id = item.get("id", "")
        if any(
            keyword in model_id.lower()
            for keyword in ["gpt", "claude", "gemini", "qwen", "deepseek", "turbo", "vision", "vl", "chat", "pro", "flash"]
        ):
            models.append(ModelInfo(id=model_id, name=model_id))
    return models


@router.post("/models", response_model=ModelListResponse)
async def get_model_list(
    req: ModelListRequest,
    x_admin_token: str = Header(..., description="Admin session token"),
):
    _verify_admin_token(x_admin_token)

    provider = _detect_provider(req.base_url)
    if provider in COMMON_MODELS:
        return ModelListResponse(
            success=True,
            models=COMMON_MODELS[provider],
            provider=provider,
            message=f"Loaded the common {provider} model list",
        )

    try:
        models = await _fetch_openai_compatible_models(req.api_key, req.base_url)
        if models:
            return ModelListResponse(
                success=True,
                models=models,
                provider="openai_compatible",
                message=f"Loaded {len(models)} models",
            )
        return ModelListResponse(
            success=True,
            models=COMMON_MODELS["openai"],
            provider="unknown",
            message="Fell back to the default OpenAI-compatible model list",
        )
    except httpx.HTTPStatusError as exc:
        return ModelListResponse(
            success=False,
            models=COMMON_MODELS["openai"],
            provider=provider,
            message=f"Model lookup failed ({exc.response.status_code}); check the API key and base URL",
        )
    except Exception as exc:  # pragma: no cover - defensive surface
        return ModelListResponse(
            success=False,
            models=COMMON_MODELS["openai"],
            provider=provider,
            message=f"Model lookup failed: {str(exc)[:100]}",
        )


@router.get("/config/test")
async def test_ai_connection(
    x_admin_token: str = Header(..., description="Admin session token"),
):
    _verify_admin_token(x_admin_token)
    details = {
        "vision": {
            "configured": bool(settings.AI_VISION_API_KEY and settings.AI_VISION_API_BASE_URL),
            "message": settings.AI_VISION_MODEL_NAME or "Not configured",
        },
        "text": {
            "configured": bool(settings.AI_TEXT_API_KEY and settings.AI_TEXT_API_BASE_URL),
            "message": settings.AI_TEXT_MODEL_NAME or "Not configured",
        },
        "solve": {
            "configured": bool(settings.SOLVE_API_KEY and settings.SOLVE_API_BASE_URL and settings.SOLVE_MODEL_NAME),
            "message": settings.SOLVE_MODEL_NAME or "Using the vision model fallback",
        },
    }
    return {
        "configured": details["vision"]["configured"] or details["text"]["configured"],
        "details": details,
        "note": "This endpoint checks whether config values are present. It does not verify the remote credentials.",
    }
