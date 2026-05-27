# Ce fichier est conservé pour compatibilité.
# L'entrypoint réel de l'application est app/main.py
#
# Lancer avec :
#   uv run uvicorn app.main:app --reload

from app.main import app  # noqa: F401
