# Moussoum Defar

**Data and AI infrastructure for Africa**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0+-green.svg)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-Non--Commercial-blue.svg)](LICENSE)

---

## The Problem

The AI industry has a blind spot: Africa. All the data, benchmarks, and tools are built for Western contexts. Try asking a chatbot about FCFA, Mobile Money, or Wolof — it doesn't know what you're talking about.

**Moussoum Defar** is the missing data layer: a platform where African workers collect real data, clients launch collection campaigns, and AI models get tested against African benchmarks.

---

## What It Does

### Data Collection
Clients create collection campaigns (text, audio, image, video). Workers across Africa get paid to contribute data in their own languages and communities.

### Worker System
Students, linguists, experts earn money contributing to better AI. Scoring system, levels, gamification. The better you are, the more you earn.

### AI Evaluation
Test your AI models against African benchmarks. See if they understand Mobile Money, local languages, and culture.

### Client Dashboard
Full dashboard to manage collections, review submissions, approve/reject contributions, and track spending.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT                                    │
│  - Creates collection campaigns                                  │
│  - Deposits funds into wallet                                    │
│  - Reviews & approves worker submissions                        │
│  - Pays workers automatically on approval                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PLATFORM                                     │
│  - Manages collections, submissions, payments                   │
│  - Calculates quality scores                                    │
│  - Sends notifications                                          │
│  - Tracks worker levels and earnings                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        WORKER                                    │
│  - Browses available collections                                │
│  - Submits data (text, audio, image, video)                     │
│  - Earns money on approval                                      │
│  - Tracks score, level, and balance                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/yourusername/Moussoum_Defar.git
cd Moussoum_Defar

# Setup
cp .env.example .env
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py load_benchmarks
docker compose exec web python manage.py createsuperuser

# Run
docker compose up
```

**Access:**
- Home: http://localhost:8000/templates/index.html
- Admin: http://localhost:8000/admin/
- API Docs (Swagger): http://localhost:8000/api/docs/

**Web Interfaces:**
- Worker Register: http://localhost:8000/templates/worker-register.html
- Worker Login: http://localhost:8000/templates/worker-login.html
- Worker Dashboard: http://localhost:8000/templates/worker-dashboard.html
- Client Register: http://localhost:8000/templates/client-register.html
- Client Login: http://localhost:8000/templates/client-login.html
- Client Dashboard: http://localhost:8000/templates/client-dashboard.html
- Evaluation Lab: http://localhost:8000/templates/evaluation.html

---

## Authentication

All API endpoints (except register/login) require a JWT token.

### Worker Login

```bash
TOKEN=$(curl -s http://localhost:8000/api/v1/workers/auth/login/ \
  -X POST -H 'Content-Type: application/json' \
  -d '{"username":"testworker","password":"testworker123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tokens']['access'])")
```

### Client Login

```bash
TOKEN=$(curl -s http://localhost:8000/api/v1/clients/login/ \
  -X POST -H 'Content-Type: application/json' \
  -d '{"username":"testclient","password":"testclient123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tokens']['access'])")
```

### Use Token

```bash
curl http://localhost:8000/api/v1/workers/collections/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## API Endpoints

### Auth (Public - No Token)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workers/auth/register/` | POST | Register as worker |
| `/api/v1/workers/auth/login/` | POST | Worker login |
| `/api/v1/clients/register/` | POST | Register as client |
| `/api/v1/clients/login/` | POST | Client login |

### Worker

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workers/auth/profile/` | GET | Get worker profile (score, level, balance) |
| `/api/v1/workers/collections/` | GET | List available collections |
| `/api/v1/workers/collections/{id}/submit/` | POST | Submit data (text or file) |
| `/api/v1/workers/annotations/` | GET | List annotation tasks |
| `/api/v1/workers/annotations/{id}/submit_annotation/` | POST | Submit annotation |
| `/api/v1/workers/rlhf/` | GET | List RLHF tasks |
| `/api/v1/workers/rlhf/{id}/submit_feedback/` | POST | Submit RLHF feedback |
| `/api/v1/workers/payments/` | GET | List earnings |
| `/api/v1/workers/notifications/` | GET | List notifications |
| `/api/v1/workers/notifications/{id}/read/` | POST | Mark notification read |

### Client

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/clients/profile/me/` | GET | Get client profile (balance) |
| `/api/v1/clients/profile/deposit/` | POST | Deposit funds (min $10) |
| `/api/v1/clients/data-collections/` | GET/POST | List / Create collections |
| `/api/v1/clients/submissions/` | GET | List worker submissions |
| `/api/v1/clients/submissions/{id}/approve/` | POST | Approve submission (pays worker) |
| `/api/v1/clients/submissions/{id}/reject/` | POST | Reject submission |

### Benchmarks & Evaluation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/benchmarks/` | GET | List African benchmarks |
| `/api/v1/benchmarks/{id}/tests/` | GET | Get test cases |
| `/api/v1/evaluations/test_quick/` | POST | Quick model evaluation |

---

## API Examples

### Register Worker

```bash
curl -X POST http://localhost:8000/api/v1/workers/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "amine_worker",
    "email": "amine@example.com",
    "password": "securepass123",
    "password2": "securepass123",
    "phone": "+221771234567",
    "country": "Senegal",
    "languages": ["Wolof", "French"],
    "bio": "Linguist specializing in Wolof"
  }'
```

### Register Client

```bash
curl -X POST http://localhost:8000/api/v1/clients/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "mycompany",
    "email": "contact@mycompany.com",
    "password": "securepass123",
    "company_name": "My Company SARL",
    "company_description": "AI chatbot for banking"
  }'
```

### Deposit Funds

```bash
curl -X POST http://localhost:8000/api/v1/clients/profile/deposit/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CLIENT_TOKEN" \
  -d '{"amount": 50}'
```

### Create Collection

```bash
curl -X POST http://localhost:8000/api/v1/clients/data-collections/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CLIENT_TOKEN" \
  -d '{
    "title": "Wolof Voice Commands",
    "description": "Collect Wolof voice commands for AI training",
    "data_type": "audio",
    "language": "Wolof",
    "country": "Senegal",
    "target_count": 100,
    "price_per_item": 0.50,
    "instructions": "Speak clearly in Wolof. Record common phrases."
  }'
```

### Submit Data (Text)

```bash
curl -X POST http://localhost:8000/api/v1/workers/collections/1/submit/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -d '{"transcription": "Nanga def, ca va?", "metadata": {}}'
```

### Submit Data (Audio File)

```bash
curl -X POST http://localhost:8000/api/v1/workers/collections/1/submit/ \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -F "transcription=Voice recording" \
  -F "file=@recording.webm"
```

### Approve Submission (Pays Worker)

```bash
curl -X POST http://localhost:8000/api/v1/clients/submissions/1/approve/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CLIENT_TOKEN" \
  -d '{"notes": "Great quality", "quality_score": 0.95}'
```

---

## Data Collection Flow

1. **Client deposits funds** → `POST /api/v1/clients/profile/deposit/`
2. **Client creates collection** → `POST /api/v1/clients/data-collections/`
3. **Worker browses collections** → `GET /api/v1/workers/collections/`
4. **Worker submits data** → `POST /api/v1/workers/collections/{id}/submit/`
5. **Client reviews submission** → `GET /api/v1/clients/submissions/`
6. **Client approves** → `POST /api/v1/clients/submissions/{id}/approve/`
7. **Worker gets paid** → Balance increases, quality score recalculated

---

## Worker Quality Score

Score is calculated on a 0-100 scale:

```
accuracy_score    = accuracy × 50      (50% weight)
volume_score      = min(tasks/100, 1) × 25  (25% weight)
consistency_score = consistency × 25   (25% weight)
total             = accuracy_score + volume_score + consistency_score
```

---

## Benchmarks

| Country | Tests | Categories |
|---------|-------|------------|
| Senegal | 22 | Mobile Money, Wolof, Culture, Admin |
| Nigeria | 19 | Fintech, Pidgin, Culture, Security |
| Kenya | 21 | M-Pesa, Sheng, Culture, Health |

---

## Tech Stack

- **Backend:** Django 5 + DRF
- **Database:** PostgreSQL 16
- **Cache:** Redis
- **Tasks:** Celery
- **Storage:** MinIO (S3-compatible)
- **Container:** Docker
- **API Docs:** drf-spectacular (Swagger/OpenAPI)

---

## Roadmap

- [x] Worker registration and dashboard
- [x] Client dashboard with collection management
- [x] Audio/video/image upload support
- [x] Submission approval with automatic payment
- [x] Quality scoring system
- [x] Notification system
- [x] Client wallet (deposit/balance)
- [ ] Mobile Money integration (Orange Money, Wave, M-Pesa)
- [ ] Real-time WebSocket notifications
- [ ] Mobile app for workers
- [ ] More African countries (Ghana, Tanzania, Ethiopia...)

---

## License

**Non-Commercial License** - Free for learning, research, and open-source contribution.

Commercial use requires written permission from Moussoum Defar.

See [LICENSE](LICENSE) for full details.

To request commercial license: malickoseme@gmail.com

---

## Support

- API Docs: http://localhost:8000/api/docs/
- Issues: GitHub Issues
- Email: malickoseme@gmail.com

---

**Made in Africa, for Africa.**
