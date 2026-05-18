# NexusIoT Platform 🚀

> Custom IoT Platform — similar to Blynk, built with Python FastAPI.
> Real-time dashboard · Device management · REST API · MQTT · WebSocket

---

## Architecture

```
Devices (ESP32, Raspberry Pi, etc.)
        │
        ├── HTTP POST  →  /api/v1/data/ingest   (REST API)
        └── MQTT pub   →  devices/{id}/data      (MQTT Broker)
                                │
                          [FastAPI Backend]
                                │
                    ┌───────────┴────────────┐
              [SQLite/PostgreSQL]     [WebSocket /ws]
                                            │
                                    [Dashboard + Frontend Apps]
```

---

## Quick Start (Local Dev)

### 1. Install Python dependencies
```bash
cd iot-platform
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 3. Install MQTT broker (optional, for MQTT devices)
```bash
# macOS
brew install mosquitto && brew services start mosquitto

# Ubuntu/Debian
sudo apt install mosquitto mosquitto-clients && sudo systemctl start mosquitto

# Windows: Download from https://mosquitto.org/download/
# Or skip MQTT — set MQTT_ENABLED=false in .env
```

### 4. Start the platform
```bash
python -m app.main
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open dashboard
- Dashboard: http://localhost:8000
- API Docs:  http://localhost:8000/api/docs

### 6. Register & add your first device
1. Open dashboard → Login → Register (use admin@nexusiot.dev / admin123)
2. Add Device → copy the API key
3. Test with the simulator:
```bash
python scripts/simulate_device.py --api-key nxs_your_key_here
```

---

## API Reference

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login → get JWT token |

### Devices (Bearer token required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/devices` | List all devices |
| POST | `/api/v1/devices` | Create device |
| GET | `/api/v1/devices/{id}` | Get device |
| PATCH | `/api/v1/devices/{id}` | Update device |
| DELETE | `/api/v1/devices/{id}` | Delete device |

### Data — Device sends (X-API-Key header)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/data/ingest` | Send single reading |
| POST | `/api/v1/data/ingest/bulk` | Send multiple readings |

### Data — Dashboard queries (Bearer token)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/data/{id}/latest` | Latest value per field |
| GET | `/api/v1/data/{id}/history` | Time-series data |
| GET | `/api/v1/data/{id}/stats` | Min/max/avg stats |

### WebSocket
| URL | Description |
|-----|-------------|
| `ws://host/ws` | All device events |
| `ws://host/ws/{device_id}` | Single device events |

---

## Device Integration

### HTTP (any device)
```python
import requests

headers = {"X-API-Key": "nxs_your_device_api_key"}

# Single reading
requests.post("http://localhost:8000/api/v1/data/ingest",
    json={"field": "temperature", "value": 25.3, "unit": "°C"},
    headers=headers
)

# Bulk readings
requests.post("http://localhost:8000/api/v1/data/ingest/bulk",
    json={"readings": [
        {"field": "temperature", "value": 25.3, "unit": "°C"},
        {"field": "humidity", "value": 60.1, "unit": "%"},
    ]},
    headers=headers
)
```

### MQTT (broker must be running)
```
Topic: devices/{device_id}/data
Payload: {"field": "temperature", "value": 25.3, "unit": "°C"}

# Or bulk:
{"readings": [{"field": "temp", "value": 25}, {"field": "hum", "value": 60}]}

# Status:
Topic: devices/{device_id}/status
Payload: {"status": "online"}  or  {"status": "offline"}
```

### Frontend/Backend calling the API
```javascript
// Get JWT token first
const { access_token } = await fetch("/api/v1/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "user@example.com", password: "password" })
}).then(r => r.json());

// Then query data
const latest = await fetch("/api/v1/data/{device_id}/latest", {
  headers: { "Authorization": `Bearer ${access_token}` }
}).then(r => r.json());

// Subscribe to real-time updates
const ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  // msg.type: "data" | "status" | "alert"
  console.log(msg);
};
```

---

## Deploy to Cloud

### Docker
```bash
# Build image
docker build -t nexusiot .

# Run with PostgreSQL
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db/nexusiot \
  -e SECRET_KEY=your-production-secret \
  nexusiot
```

### Environment variables for production
```env
DEBUG=false
SECRET_KEY=<random 64-char string>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/nexusiot
MQTT_BROKER_HOST=your-mqtt-broker.com
CORS_ORIGINS=["https://your-frontend.com"]
```

---

## Project Structure

```
iot-platform/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   ├── config.py        # Settings (env vars)
│   │   ├── database.py      # Async SQLAlchemy engine
│   │   ├── security.py      # JWT, password hashing, API keys
│   │   └── logger.py        # Logging setup
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── device.py
│   │   ├── sensor_data.py
│   │   └── alert.py
│   ├── schemas/
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── api/v1/
│   │   ├── router.py        # Route aggregator
│   │   ├── deps.py          # Auth dependencies
│   │   └── endpoints/
│   │       ├── auth.py      # Login/register
│   │       ├── devices.py   # Device CRUD
│   │       ├── data.py      # Data ingest & query
│   │       ├── alerts.py    # Alert rules
│   │       └── websocket.py # WS connections
│   ├── services/
│   │   ├── sensor_service.py    # Business logic: ingest, query, stats
│   │   └── websocket_manager.py # WS connection manager & broadcast
│   └── mqtt/
│       └── client.py        # MQTT subscriber + router
├── dashboard/
│   └── templates/
│       └── index.html       # Full real-time dashboard
├── scripts/
│   └── simulate_device.py   # Device simulator for testing
├── docs/
│   └── esp32_example.ino    # Arduino/ESP32 example code
├── requirements.txt
├── .env.example
└── README.md
```
