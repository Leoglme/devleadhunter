"""
Configuration settings for the Prospect Tool API.
"""
import json
from typing import List, Any
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        env: Current environment (development, staging, production)
        debug: Whether debug mode is enabled
        api_version: API version string
        api_prefix: API prefix for routes
        host: Server host address
        port: Server port number
        cors_origins: List of allowed CORS origins
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    env: str = "development"
    debug: bool = True
    api_version: str = "v1"
    api_prefix: str = "/api/v1"
    
    host: str = "0.0.0.0"
    port: int = 8000
    
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173"
    ]
    
    @model_validator(mode="before")
    @classmethod
    def parse_cors_origins_from_env(cls, data: Any) -> Any:
        """
        Parse CORS origins from environment variable if it's a string.
        Allows setting CORS_ORIGINS as a comma-separated string in .env file.
        """
        if isinstance(data, dict) and "cors_origins" in data:
            cors_val = data["cors_origins"]
            if isinstance(cors_val, str):
                # Try to parse as JSON first (if it's a JSON array string)
                try:
                    parsed = json.loads(cors_val)
                    if isinstance(parsed, list):
                        data["cors_origins"] = parsed
                        return data
                except (json.JSONDecodeError, TypeError):
                    pass
                # Split by comma and strip whitespace
                data["cors_origins"] = [origin.strip() for origin in cors_val.split(",") if origin.strip()]
        return data
    
    @property
    def allowed_cors_origins(self) -> List[str]:
        """
        Get allowed CORS origins based on environment.
        
        Returns:
            List of allowed origins for CORS
        """
        origins = self.cors_origins.copy()
        
        # Add production frontend origins if in production
        if self.env.lower() == "production":
            production_origins = [
                "https://devleadhunter.dibodev.fr",
                "https://www.devleadhunter.dibodev.fr"
            ]
            # Only add if not already present
            for origin in production_origins:
                if origin not in origins:
                    origins.append(origin)
        
        return origins


# Global settings instance
settings = Settings()

