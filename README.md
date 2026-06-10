# Jyotish Transit API

Swiss Ephemeris microservice for real-time Vedic transit calculations.

## Endpoint

### `POST /transits`

**Request body:**
```json
{
  "birth_date": "1990-03-15",
  "birth_time": "14:30:00",
  "birth_lat": 28.6139,
  "birth_lon": 77.2090,
  "birth_tz": 5.5
}
```

**Response:**
```json
{
  "transit_date": "2026-05-25",
  "transit_time_utc": "14:22",
  "natal_positions": {
    "Sun": { "sidereal_longitude": 330.5, "rashi": "Pisces", "rashi_degrees": 0.5, "nakshatra": "Uttara Bhadrapada", "nakshatra_pada": 4 },
    ...
  },
  "transit_positions": { ... },
  "transit_aspects": [
    { "transit_planet": "Saturn", "natal_planet": "Sun", "aspect": "Square", "orb_deg": 2.1, "transit_rashi": "Gemini", "natal_rashi": "Pisces" },
    ...
  ]
}
```

### `POST /transits/context`

Same request body as `/transits`. Returns a pre-formatted plain-text block with all live transit data embedded — pass this directly to your AI node message so the model has the actual positions.

```json
{ "context": "=== LIVE JYOTISH TRANSIT DATA (2026-06-10 08:30 UTC) ===\n\nToday's transit positions:\n  Sun: Taurus 25.40° ..." }
```

### `GET /prompt`

Returns the canonical system prompt for the n8n AI node — no remedies, pure transit interpretation.

```json
{ "system_prompt": "You are a Jyotish (Vedic astrology) expert..." }
```

### `GET /health`
Returns `{"status": "ok"}`.

## n8n Workflow Wiring

The AI node must receive the live transit data or it will refuse to interpret. Correct flow:

```
[Trigger] → [HTTP Request: POST /transits/context] → [AI Node]
                                                          ↑
                                          System prompt: {{ $('HTTP Request (prompt)').item.json.system_prompt }}
                                          User message:  {{ $json.context }}\n\nPlease interpret my transits.
```

1. **Node 1 — Get prompt** `GET <api-url>/prompt` → store `system_prompt`
2. **Node 2 — Get transit context** `POST <api-url>/transits/context` with birth details → store `context`
3. **Node 3 — AI node** — system prompt = output of Node 1, user message = output of Node 2

## Deploy to Railway

1. Push this folder to a GitHub repo
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select the repo — Railway auto-detects `nixpacks.toml`
4. Copy the public URL once deployed
5. Use that URL in the n8n HTTP Request node

## Local testing

```bash
pip install -r requirements.txt
uvicorn app:app --reload
# → http://localhost:8000/docs
```
