# Deployment (local)

## Auth Token
- Stored locally only (do not commit). See `.env.local`.

## Run (HTTP API)
```
export MOLT_REDIS_URL=redis://localhost:6379/0
export MOLT_OFFICE_TOKEN="<your-token>"

.venv/bin/uvicorn molt_office.api:create_app --factory --host 0.0.0.0 --port 8099
```

## Notes
- Token required for all endpoints.
- Header: `Authorization: Bearer <token>`
