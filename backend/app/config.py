from __future__ import annotations

import os
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    AI_VISION_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("AI_VISION_API_KEY", "AI_API_KEY"),
    )
    AI_VISION_API_BASE_URL: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias=AliasChoices("AI_VISION_API_BASE_URL", "AI_API_BASE_URL"),
    )
    AI_VISION_MODEL_NAME: str = Field(
        default="qwen-vl-max",
        validation_alias=AliasChoices("AI_VISION_MODEL_NAME", "AI_MODEL_NAME"),
    )

    AI_TEXT_API_KEY: str = ""
    AI_TEXT_API_BASE_URL: str = ""
    AI_TEXT_MODEL_NAME: str = ""

    SOLVE_API_KEY: str = ""
    SOLVE_API_BASE_URL: str = ""
    SOLVE_MODEL_NAME: str = ""

    MAX_IMAGE_SIZE_MB: int = 5

    DATABASE_URL: str = "sqlite:///./data/app.db"
    OSS_ACCESS_KEY: str = ""
    OSS_SECRET_KEY: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_ENDPOINT: str = ""

    ADMIN_PASSWORD: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        if not self.AI_TEXT_API_KEY:
            self.AI_TEXT_API_KEY = self.AI_VISION_API_KEY
        if not self.AI_TEXT_API_BASE_URL:
            self.AI_TEXT_API_BASE_URL = self.AI_VISION_API_BASE_URL
        if not self.AI_TEXT_MODEL_NAME:
            self.AI_TEXT_MODEL_NAME = self.AI_VISION_MODEL_NAME

        if not self.DATABASE_URL:
            self.DATABASE_URL = "sqlite:///./data/app.db"

    def update_config(self, **kwargs) -> bool:
        """Update in-memory settings and persist them to `.env`."""
        env_file_path = Path(self.model_config.get("env_file", ".env")).resolve()
        env_file_path.parent.mkdir(parents=True, exist_ok=True)

        env_vars: dict[str, str] = {}
        if env_file_path.exists():
            with env_file_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                env_vars[key] = str(value)

        self.model_post_init(None)

        lines = [
            "# AI homework service configuration",
            "# Managed by the admin console",
            "",
            "# Vision model",
            f"AI_VISION_API_KEY={env_vars.get('AI_VISION_API_KEY', self.AI_VISION_API_KEY)}",
            f"AI_VISION_API_BASE_URL={env_vars.get('AI_VISION_API_BASE_URL', self.AI_VISION_API_BASE_URL)}",
            f"AI_VISION_MODEL_NAME={env_vars.get('AI_VISION_MODEL_NAME', self.AI_VISION_MODEL_NAME)}",
            "",
            "# Text model",
            f"AI_TEXT_API_KEY={env_vars.get('AI_TEXT_API_KEY', self.AI_TEXT_API_KEY)}",
            f"AI_TEXT_API_BASE_URL={env_vars.get('AI_TEXT_API_BASE_URL', self.AI_TEXT_API_BASE_URL)}",
            f"AI_TEXT_MODEL_NAME={env_vars.get('AI_TEXT_MODEL_NAME', self.AI_TEXT_MODEL_NAME)}",
            "",
            "# Solve model",
            f"SOLVE_API_KEY={env_vars.get('SOLVE_API_KEY', self.SOLVE_API_KEY)}",
            f"SOLVE_API_BASE_URL={env_vars.get('SOLVE_API_BASE_URL', self.SOLVE_API_BASE_URL)}",
            f"SOLVE_MODEL_NAME={env_vars.get('SOLVE_MODEL_NAME', self.SOLVE_MODEL_NAME)}",
            "",
            "# Limits",
            f"MAX_IMAGE_SIZE_MB={env_vars.get('MAX_IMAGE_SIZE_MB', self.MAX_IMAGE_SIZE_MB)}",
            "",
            "# Admin",
            f"ADMIN_PASSWORD={env_vars.get('ADMIN_PASSWORD', self.ADMIN_PASSWORD)}",
            "",
            "# Storage",
            f"DATABASE_URL={env_vars.get('DATABASE_URL', self.DATABASE_URL)}",
            "",
        ]

        with env_file_path.open("w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

        return True

    def get_public_config(self) -> dict[str, object]:
        return {
            "AI_VISION_API_BASE_URL": self.AI_VISION_API_BASE_URL,
            "AI_VISION_MODEL_NAME": self.AI_VISION_MODEL_NAME,
            "AI_TEXT_API_BASE_URL": self.AI_TEXT_API_BASE_URL,
            "AI_TEXT_MODEL_NAME": self.AI_TEXT_MODEL_NAME,
            "SOLVE_API_BASE_URL": self.SOLVE_API_BASE_URL,
            "SOLVE_MODEL_NAME": self.SOLVE_MODEL_NAME,
            "MAX_IMAGE_SIZE_MB": self.MAX_IMAGE_SIZE_MB,
        }

    def has_secure_admin_password(self) -> bool:
        return bool(self.ADMIN_PASSWORD and self.ADMIN_PASSWORD != "admin123")

    def verify_admin(self, password: str) -> bool:
        return self.has_secure_admin_password() and password == self.ADMIN_PASSWORD

    @property
    def database_path(self) -> Path:
        if self.DATABASE_URL.startswith("sqlite:///"):
            raw_path = self.DATABASE_URL.removeprefix("sqlite:///")
            path = Path(raw_path)
            if not path.is_absolute():
                path = Path(os.getcwd()) / path
            return path.resolve()
        raise ValueError("Only sqlite DATABASE_URL values are supported in this project")


settings = Settings()
MAX_IMAGE_SIZE_MB = settings.MAX_IMAGE_SIZE_MB
