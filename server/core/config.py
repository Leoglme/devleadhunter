"""
Configuration settings for the Prospect Tool API.
"""
from typing import List
from pydantic import field_validator
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
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """
        Parse CORS origins from environment variable if it's a string.
        Allows setting CORS_ORIGINS as a comma-separated string in .env file.
        """
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
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

