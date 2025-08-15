# app/config.py
from dataclasses import dataclass
import os

@dataclass
class Settings:
    target_host: str = os.getenv("GIS_TARGET_HOST", "api.dom.gosuslugi.ru")
    stunnel_host: str = os.getenv("GIS_STUNNEL_HOST", "127.0.0.1")
    stunnel_port: int = int(os.getenv("GIS_STUNNEL_PORT", "8080"))
    soap11: bool = bool(int(os.getenv("GIS_SOAP11", "0")))  # 0=SOAP 1.2, 1=SOAP 1.1

settings = Settings()
