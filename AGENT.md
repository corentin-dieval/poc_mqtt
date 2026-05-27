# AGENT.md — Conventions & Règles du projet

## Contexte

PoC industriel de collecte et consolidation d'événements machines via MQTT → PostgreSQL → FastAPI REST.

Ce système est un **bus d'événements simple** : il ingère, historise, et expose. Il ne pilote pas les machines.

---

## Stack technique imposée

| Composant        | Technologie                          |
|------------------|--------------------------------------|
| Language         | Python 3.12+                         |
| API              | FastAPI (async)                      |
| MQTT             | paho-mqtt v2 + Eclipse Mosquitto     |
| ORM              | SQLAlchemy 2.0 (async)               |
| Validation       | Pydantic v2                          |
| Base de données  | PostgreSQL 16 (+ TimescaleDB optionnel) |
| Conteneurisation | Docker Compose                       |
| Tooling          | uv, ruff, pytest                     |

---

## Ce que le système fait

- Se connecte à un broker MQTT
- Souscrit à un topic configurable
- Valide et persiste les événements JSON
- Expose un état consolidé via REST
- Expose les événements avec pagination

## Ce que le système NE fait PAS

- Pas de logique métier OT
- Pas de workflow qualité
- Pas de MES
- Pas de pilotage machine
- Pas de gestion de buffers NG

---

## Règles de génération de code

### À faire

- Code simple, lisible, maintenable
- Typage Python moderne (PEP 604, PEP 695)
- SQLAlchemy 2.0 style async (AsyncSession, select(), scalars())
- Pydantic v2 (model_config, ConfigDict, field validators)
- FastAPI async (async def endpoints)
- Configuration via variables d'environnement (pydantic-settings)
- Logs structurés (stdlib logging)
- Séparation claire des responsabilités (routes / services / db / mqtt)

### À ne PAS faire

- Pas de sur-ingénierie
- Pas de CQRS / Event Sourcing
- Pas de microservices
- Pas de Kubernetes
- Pas de Kafka
- Pas d'abstractions prématurées
- Pas de dépendances non demandées

---

## Structure des modules

```
app/
  core/        # config, logging
  db/          # engine, session, models
  schemas/     # pydantic models
  api/routes/  # endpoints FastAPI
  mqtt/        # client MQTT
  services/    # logique métier légère
  main.py      # entrypoint FastAPI
```

---

## Conventions

- Variables d'env préfixées (ex: `MQTT_BROKER_HOST`)
- Fichier `.env` local, `.env.example` committé
- `uv sync` pour installer les dépendances
- `uv run uvicorn app.main:app --reload` pour dev
- Makefile pour les commandes courantes

