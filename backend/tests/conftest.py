import os
import subprocess
import sys
from pathlib import Path

# Configuración de entorno ANTES de importar la app.
os.environ.setdefault(
    "DATABASE_URL", "mysql+asyncmy://test:test@127.0.0.1:53306/bolsillo_test?charset=utf8mb4"
)
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123456"
os.environ["COOKIE_SECURE"] = "false"
os.environ["INITIAL_USER_EMAIL"] = ""
os.environ["INITIAL_USER_PASSWORD"] = ""
os.environ["DEFAULT_TIMEZONE"] = "America/Bogota"

ROOT = Path(__file__).resolve().parent.parent
