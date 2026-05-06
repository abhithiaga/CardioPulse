from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "CardioAI"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-in-production"

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    DYNAMODB_TABLE_PATIENTS: str = "cardioai-patients"
    DYNAMODB_TABLE_ECG: str = "cardioai-ecg-records"
    S3_BUCKET_ECG: str = "cardioai-ecg-files"

    # ML model config
    MODEL_PATH: str = "models/ecg_classifier.pkl"
    RISK_THRESHOLD_HIGH: float = 0.75
    RISK_THRESHOLD_MEDIUM: float = 0.45

    # Optional: external AI inference endpoint
    INFERENCE_ENDPOINT: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
