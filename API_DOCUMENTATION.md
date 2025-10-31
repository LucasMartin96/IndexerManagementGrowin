# FastAPI ELK Service - API Documentation

This document describes all available endpoints in the FastAPI ELK service for indexing and querying publications.

## Base URL

- **Docker Compose**: `http://fastapi:8000`
- **Local Development**: `http://localhost:8000`

---

## Health Check

### GET `/api/health`

Check if the service is running and healthy.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000000",
  "scheduler_running": true
}
```

**Example:**
```bash
curl http://localhost:8000/api/health
```

---

## Indexer Endpoints

### POST `/api/index-licitacion`

Index a single publication by ID.

**Request Body:**
```json
{
  "publicacion_id": 12345
}
```

**Response:**
```json
{
  "status": "indexed",
  "id": 12345,
  "timestamp": "2024-01-15T10:30:00.000000"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/index-licitacion \
  -H "Content-Type: application/json" \
  -d '{"publicacion_id": 12345}'
```

**Error Responses:**
- `400`: Missing `publicacion_id`
- `404`: Publication not found in MySQL
- `503`: Elasticsearch not available

---

### POST `/api/index-scraper-publications`

Index all publications from a specific scraper updated since a given time. This endpoint is called automatically by the PHP Scraper Manager after a scraper runs.

**Request Body:**
```json
{
  "scraper_id": 5,
  "since": "2024-01-15 10:00:00"
}
```

**Parameters:**
- `scraper_id` (integer, required): ID of the scraper
- `since` (string, required): Datetime in format `YYYY-MM-DD HH:MM:SS` (MySQL datetime format)

**Response:**
```json
{
  "status": "indexed",
  "scraper_id": 5,
  "since": "2024-01-15 10:00:00",
  "indexed": 42,
  "total": 42,
  "failed": 0
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/index-scraper-publications \
  -H "Content-Type: application/json" \
  -d '{
    "scraper_id": 5,
    "since": "2024-01-15 10:00:00"
  }'
```

**Error Responses:**
- `400`: Missing `scraper_id` or `since`
- `503`: Elasticsearch not available (returns error in response, doesn't raise exception)

**Notes:**
- This endpoint is called automatically by `Scraper::trigger_indexer()` after each scraper run
- Processes up to 1000 publications per call
- Non-blocking (timeout: 2 seconds in PHP)

---

### POST `/api/index-bulk`

Initial bulk indexing of all publications. Use this endpoint to index all existing publications for the first time.

**Request Body:**
None (empty JSON object `{}` or no body)

**Response:**
```json
{
  "status": "indexed",
  "total_indexed": 15234,
  "total_failed": 2
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/index-bulk \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Error Responses:**
- `503`: Elasticsearch not available

**Notes:**
- Processes publications in batches of 1000
- This is a long-running operation - may take several minutes depending on data volume
- Use for initial setup only
- Use incremental endpoints (`/api/index-scraper-publications`, `/api/sync-since`) for regular updates

---

### POST `/api/sync-since`

Sync all publications updated since a given date. Useful for catching up after downtime or manual syncs.

**Request Body:**
```json
{
  "since": "2024-01-15 00:00:00"
}
```

**Parameters:**
- `since` (string, required): Datetime in format `YYYY-MM-DD HH:MM:SS`

**Response:**
```json
{
  "status": "synced",
  "since": "2024-01-15 00:00:00",
  "indexed": 156,
  "total": 156,
  "failed": 0
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/sync-since \
  -H "Content-Type: application/json" \
  -d '{
    "since": "2024-01-15 00:00:00"
  }'
```

**Error Responses:**
- `400`: Missing `since` parameter
- `503`: Elasticsearch not available

**Notes:**
- Processes up to 5000 publications per call
- Useful for manual synchronization or catching up after service downtime

---

### POST `/api/trigger-sync`

Manually trigger the scheduled daily sync task. Useful for testing or manual execution.

**Request Body:**
None (empty JSON object `{}` or no body)

**Response:**
```json
{
  "status": "synced",
  "since": "2024-01-14 03:00:00",
  "indexed": 89,
  "failed": 0
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/trigger-sync \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Notes:**
- Runs the same logic as the scheduled daily sync (default: 3:00 AM)
- Syncs publications updated in the last 24 hours
- Processes up to 5000 publications per run

---

## Gateway Endpoints

### POST `/api/search-licitaciones`

Query Elasticsearch for publications. This is the main query endpoint used by the PHP application. It acts as a pure gateway - translating PHP query parameters into Elasticsearch queries.

**Request Body:**
```json
{
  "page": 1,
  "page_size": 15,
  "incluirVencidos": "0",
  "soloVigentes": null,
  "objeto": "contratación",
  "agencia": "ministerio",
  "pais": "5",
  "rubro": "3",
  "apertura_fr": "15/01/2024",
  "apertura_to": "20/01/2024",
  "search": "licitación pública",
  "user_tag_ids": [1, 2, 3],
  "filter_mode": "user_tags"
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 15) |
| `incluirVencidos` | string | No | `"0"` = only vigente, `"1"` = all |
| `soloVigentes` | string | No | `"1"` = only vigente publications |
| `objeto` | string | No | Search in objeto field (wildcard match) |
| `agencia` | string | No | Search in agencia field (wildcard match) |
| `pais` | string/integer | No | Country ID or name (`"all"` to ignore) |
| `rubro` | string/integer | No | Tag/rubro ID (`"all"` to ignore) |
| `apertura_fr` | string | No | Start date in `DD/MM/YYYY` format |
| `apertura_to` | string | No | End date in `DD/MM/YYYY` format |
| `search` | string | No | General search (matches objeto, agencia, oficina, referencia) |
| `user_tag_ids` | array | No | Array of user-selected tag IDs (for filtering by user tags) |
| `filter_mode` | string | No | `"user_tags"` = filter by user tags, `"all"` = show all |

**Response:**
```json
{
  "publicaciones": [
    {
      "id": 12345,
      "scraper": 5,
      "objeto": "Contratación de servicios...",
      "agencia": "Ministerio de Economía",
      "pais": "Argentina",
      "pais_id": 5,
      "tags": [
        {"id": 1, "descripcion": "Servicios"},
        {"id": 3, "descripcion": "Tecnología"}
      ],
      "tag_ids": [1, 3],
      "apertura": "2024-01-20 10:00:00",
      "vigente": true,
      ...
    }
  ],
  "total": 156,
  "pagina": 1,
  "paginas": 11
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/search-licitaciones \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "page_size": 15,
    "pais": "5",
    "rubro": "3",
    "soloVigentes": "1"
  }'
```

**Error Responses:**
- `500`: Elasticsearch query failed or service unavailable
- `503`: Elasticsearch not available

**Notes:**
- All string searches use wildcard matching (`*search*`)
- Date filters support both `DD/MM/YYYY` and `YYYY-MM-DD` formats
- When `filter_mode="user_tags"` and `user_tag_ids` is provided, only publications matching those tags are returned
- Results are sorted by `editado DESC, id DESC` (newest first)
- Empty filters return all visible publications

**PHP Integration:**
This endpoint is called by `Publicaciones::query_elk()` when `use_elk=true` in PHP config. It automatically falls back to MySQL if this endpoint fails.

---

## Scheduled Tasks

The service includes a scheduled task that runs daily to sync all publications updated in the last 24 hours.

### Configuration

Configure the sync time via environment variables in `.env`:
```bash
ELK_SYNC_HOUR=3      # Hour (0-23)
ELK_SYNC_MINUTE=0    # Minute (0-59)
```

Default: 3:00 AM (03:00)

### Manual Trigger

Use the `/api/trigger-sync` endpoint to manually trigger the sync task.

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200`: Success
- `400`: Bad Request (missing or invalid parameters)
- `404`: Resource not found
- `500`: Internal Server Error
- `503`: Service Unavailable (Elasticsearch not available)

Error responses follow this format:
```json
{
  "status": "error",
  "message": "Error description here"
}
```

For HTTP exceptions (400, 404, 503), FastAPI returns standard error format:
```json
{
  "detail": "Error message here"
}
```

---

## Usage Examples

### Initial Setup

1. **Start services:**
   ```bash
   cd elk-service
   docker-compose up -d
   ```

2. **Run initial bulk index:**
   ```bash
   curl -X POST http://localhost:8000/api/index-bulk \
     -H "Content-Type: application/json" \
     -d '{}'
   ```

3. **Verify index:**
   ```bash
   curl http://localhost:9200/growin_licitaciones/_count
   ```

### Daily Operations

Scrapers automatically trigger indexing via `/api/index-scraper-publications` after each run. No manual intervention needed.

### Manual Sync

If you need to manually sync publications:
```bash
curl -X POST http://localhost:8000/api/sync-since \
  -H "Content-Type: application/json" \
  -d '{"since": "2024-01-15 00:00:00"}'
```

### Testing Query Gateway

Test the search endpoint:
```bash
curl -X POST http://localhost:8000/api/search-licitaciones \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "page_size": 5,
    "soloVigentes": "1"
  }'
```

---

## Integration with PHP Application

### Enable ELK

In `aplicacion/.env`:
```bash
USE_ELK=true
FASTAPI_URL=http://localhost:8000
```

### How It Works

1. **Indexing:** After each scraper runs, `Scraper::trigger_indexer()` automatically calls `/api/index-scraper-publications`
2. **Querying:** `Publicaciones::show()` calls `/api/search-licitaciones` if ELK is enabled, falls back to MySQL if it fails

### Fallback Behavior

- If FastAPI/Elasticsearch is unavailable, PHP automatically falls back to MySQL queries
- No errors are shown to users - seamless fallback
- Warnings are logged for monitoring

---

## Monitoring

### Health Check

Monitor service health:
```bash
curl http://localhost:8000/api/health
```

### Logs

View service logs:
```bash
# Docker Compose
docker-compose logs -f fastapi

# Specific container
docker logs -f growin-fastapi
```

### Elasticsearch Status

Check Elasticsearch cluster health:
```bash
curl http://localhost:9200/_cluster/health?pretty
```

### Index Stats

Get index statistics:
```bash
curl http://localhost:9200/growin_licitaciones/_stats?pretty
```

---

## Troubleshooting

### Elasticsearch Not Available

**Symptom:** `503 Service Unavailable` errors

**Solution:**
1. Check if Elasticsearch is running: `docker-compose ps`
2. Check Elasticsearch logs: `docker-compose logs elasticsearch`
3. Wait for health check to pass (30-60 seconds after startup)

### Index Not Created

**Symptom:** Queries return empty results or errors

**Solution:**
1. Run initial bulk index: `POST /api/index-bulk`
2. Verify index exists: `curl http://localhost:9200/_cat/indices`
3. Check mapping: `curl http://localhost:9200/growin_licitaciones/_mapping`

### Slow Queries

**Symptom:** Query endpoint takes too long

**Solution:**
1. Check Elasticsearch cluster health
2. Verify index has reasonable number of shards (currently 1)
3. Check if index needs optimization or reindexing

### MySQL Connection Issues

**Symptom:** Indexing fails with MySQL errors

**Solution:**
1. Verify MySQL connection in `.env` file
2. Ensure MySQL is accessible from FastAPI container
3. Check network connectivity: `docker network inspect elk-service_growin-network`

---

## API Version

Current API version: **v1**

All endpoints are under `/api/` prefix. Future versions may use `/api/v2/` etc.

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs fastapi`
2. Check Elasticsearch: `curl http://localhost:9200/_cluster/health?pretty`
3. Review this documentation

