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

### `GET /prompt`

Returns the canonical system prompt for the n8n AI node — no remedies, pure transit interpretation.

```json
{ "system_prompt": "You are a Jyotish (Vedic astrology) expert..." }
```

Use this in your n8n HTTP Request node to keep the prompt version-controlled alongside the API. In your AI node, set the system prompt to the value returned by this endpoint.

### `GET /health`
Returns `{"status": "ok"}`.

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
