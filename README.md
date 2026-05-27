# PoC MQTT FastAPI — Collecte d'événements machines

Proof of Concept industriel pour l'ingestion d'événements machines via MQTT, leur historisation dans PostgreSQL, et l'exposition d'un état consolidé via une API REST.

---

## Architecture

```
Machines → MQTT (Mosquitto) → Python Backend → PostgreSQL → FastAPI REST → OT Systems
```

---

## Démarrage rapide

### Prérequis

- [uv](https://docs.astral.sh/uv/) installé
- Docker + Docker Compose

### Démarrage local (dev)

```bash
# 1. Cloner & configurer l'environnement
cp .env.example .env

# 2. Installer les dépendances
uv sync

# 3. Démarrer PostgreSQL et Mosquitto via Docker
docker compose up -d postgres mosquitto

# 4. Lancer le backend
uv run uvicorn app.main:app --reload
```

API disponible sur : http://localhost:8000  
Swagger UI : http://localhost:8000/docs

### Démarrage complet via Docker

```bash
docker compose up -d
```

Avec Grafana :

```bash
docker compose --profile monitoring up -d
```

---

## Commandes uv

| Commande | Description |
|----------|-------------|
| `uv sync` | Installe les dépendances |
| `uv run uvicorn app.main:app --reload` | Lance le serveur en mode dev |
| `uv run pytest` | Lance les tests |
| `uv run ruff check app/` | Lint |
| `uv run ruff format app/` | Formatage |

### Makefile (raccourcis)

```bash
make install       # uv sync
make dev           # démarre le serveur
make docker-up     # docker compose up -d
make docker-down   # docker compose down
make docker-logs   # logs backend
make test          # tests
make lint          # ruff check
make format        # ruff format
make publish-test  # publie des événements de test MQTT
```

---

## Publication MQTT de test

```bash
make publish-test
# ou directement :
uv run python scripts/publish_test.py
```

Exemple de payload publié sur `machines/events` :

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "machine_id": "MACHINE_01",
  "timestamp": "2026-05-27T14:32:10Z",
  "status": "OK"
}
```

Contraintes :
- `status` ∈ `["OK", "NG"]`
- `timestamp` ISO8601 avec timezone (UTC)
- `event_id` UUID unique
- `machine_id` chaîne non vide

---

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/status` | État consolidé des machines |
| `GET` | `/events` | Liste paginée des événements |
| `GET` | `/docs` | Swagger UI |

### GET /health

```json
{"status": "ok"}
```

### GET /status

```json
{
  "global_status": "NG",
  "machines": [
    {"machine_id": "MACHINE_01", "status": "OK", "last_seen": "2026-05-27T14:32:10Z"},
    {"machine_id": "MACHINE_02", "status": "NG", "last_seen": "2026-05-27T14:31:55Z"}
  ]
}
```

Règle : `global_status = NG` si au moins une machine est NG.

### GET /events

```
GET /events?page=1&page_size=50
```

```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 50
}
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://poc:poc@localhost:5432/poc_mqtt` | URL PostgreSQL |
| `MQTT_BROKER_HOST` | `localhost` | Adresse du broker Mosquitto |
| `MQTT_BROKER_PORT` | `1883` | Port MQTT |
| `MQTT_TOPIC` | `machines/events` | Topic souscrit |
| `MQTT_CLIENT_ID` | `poc-backend` | ID client MQTT |
| `MQTT_RECONNECT_DELAY` | `5` | Délai reconnexion (secondes) |
| `LOG_LEVEL` | `INFO` | Niveau de log |

---

## Structure du projet

```
.
├── app/
│   ├── main.py               # Entrypoint FastAPI
│   ├── core/
│   │   ├── config.py         # Configuration (pydantic-settings)
│   │   └── logging.py        # Logging structuré
│   ├── db/
│   │   ├── database.py       # Engine SQLAlchemy async
│   │   └── models.py         # Modèle ORM Event
│   ├── schemas/
│   │   ├── event.py          # Pydantic schemas événements
│   │   └── status.py         # Pydantic schemas statuts
│   ├── api/
│   │   └── routes/
│   │       ├── health.py     # GET /health
│   │       ├── status.py     # GET /status
│   │       └── events.py     # GET /events
│   ├── mqtt/
│   │   └── client.py         # Client MQTT paho v2
│   └── services/
│       ├── event_service.py  # Sauvegarde événements
│       └── status_service.py # Consolidation états
├── scripts/
│   └── publish_test.py       # Publisher MQTT de test
├── tests/
│   ├── test_api.py
│   └── test_services.py
├── mosquitto/config/         # Config Mosquitto
├── postgres/init/            # SQL d'initialisation
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── Makefile
├── AGENT.md
└── README.md
```

---

## TimescaleDB (optionnel)

Pour activer TimescaleDB, décommenter dans `postgres/init/01_init.sql` :

```sql
SELECT create_hypertable('events', 'timestamp', if_not_exists => TRUE);
```

Et utiliser l'image `timescale/timescaledb:latest-pg16` dans `docker-compose.yml`.

---

## Stack technique

- **Python 3.12+** · **FastAPI** · **paho-mqtt v2** · **SQLAlchemy 2.0 async** · **Pydantic v2**
- **PostgreSQL 16** · **Eclipse Mosquitto 2** · **Docker Compose**
- **uv** · **ruff** · **pytest**

