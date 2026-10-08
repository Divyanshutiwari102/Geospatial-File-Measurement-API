from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Upload settings
    upload_dir: str = Field(default="uploads", description="Directory to store uploaded files")
    max_upload_size: int = Field(
        default=50 * 1024 * 1024,
        description="Maximum upload size in bytes (default 50 MB)",
    )

    # Database settings
    database_url: str = Field(
        default="sqlite:///./geospatial.db",
        description="Database URL for SQLAlchemy. For PostgreSQL, use postgresql://user:password@host:port/db",
    )

    # Measurement settings
    default_area_unit: str = Field(
        default="square_meters", description="Default unit for area measurements"
    )
    default_length_unit: str = Field(
        default="meters", description="Default unit for length measurements"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
