# Personalized Video Feed API - Prototype

A production-grade FastAPI prototype demonstrating rule-based video feed personalization with proper software engineering practices.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Layer (Routers)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │   Feed Router   │  │  Health Router  │  │  Exception Handlers │ │
│  └────────┬────────┘  └─────────────────┘  └─────────────────────┘ │
│           │                                                          │
│           ▼ Dependency Injection                                     │
├─────────────────────────────────────────────────────────────────────┤
│                       Service Layer                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │   FeedService   │  │  RankingEngine  │  │ FeatureFlagService  │ │
│  │ (Orchestrator)  │  │ (Strategy Pattn)│  │   (Kill Switch)     │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────────┘ │
│           │                    │                                     │
│           ▼                    ▼                                     │
├─────────────────────────────────────────────────────────────────────┤
│                    Core Infrastructure                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ CircuitBreaker  │  │  CacheInterface │  │    Exceptions       │ │
│  │  (Resilience)   │  │   (Abstraction) │  │    (Hierarchy)      │ │
│  └─────────────────┘  └────────┬────────┘  └─────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
├─────────────────────────────────────────────────────────────────────┤
│                      Repository Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │UserSignalRepo   │  │ CandidateRepo   │  │ TenantConfigRepo    │ │
│  │  (Protocol)     │  │   (Protocol)    │  │    (Protocol)       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Design Patterns Used

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Strategy** | `RankingEngine` | Pluggable scoring algorithms (Recency, Affinity) |
| **Repository** | `repositories/` | Abstract data access, swap Redis/Memory easily |
| **Circuit Breaker** | `core/circuit_breaker.py` | Prevent cascading failures |
| **Dependency Injection** | `api/dependencies.py` | Loose coupling, testability |
| **Factory** | `create_app()` | Application configuration |
| **Singleton** | `@lru_cache()` | Shared service instances |

## Resilience Patterns

1. **Graceful Degradation**: If personalization fails → return fallback feed
2. **Circuit Breaker**: Stop calling failing services after threshold
3. **Feature Flag Kill Switch**: Instantly disable personalization
4. **Timeout Budgets**: Configured per-dependency (see `config/settings.py`)

## Quick Start

```bash
# 1. Navigate to Personalized-Video-Feed-API directory
cd Personalized-Video-Feed-API-

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python -m uvicorn app.main:app --reload --port 8000
```

# 5. Run Tests
python -m pytest tests
```

# 6. Get Test Coverage
python -m pytest --cov=app --cov-report=term-missing tests
```

## API Endpoints

### GET /v1/feed
Get personalized video feed.

```bash
# Sports fan (personalized)
Invoke-RestMethod -Uri "http://localhost:8000/v1/feed?user_hash=user_sporty&limit=5" `
  -Headers @{"X-Tenant-ID"="tenant_sports"} | ConvertTo-Json -Depth 5

# Cold start user (fallback to popularity)
Invoke-RestMethod -Uri "http://localhost:8000/v1/feed?user_hash=user_new&limit=5" `
  -Headers @{"X-Tenant-ID"="tenant_sports"} | ConvertTo-Json -Depth 5
```

### GET /health
Basic health check.

### GET /health/ready
Readiness check with circuit breaker status.

## Project Structure

```
prototype/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   │
│   ├── api/                    # API Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py     # Dependency injection container
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── feed.py         # GET /v1/feed
│   │       └── health.py       # Health checks
│   │
│   ├── config/                 # Configuration
│   │   ├── __init__.py
│   │   └── settings.py         # Pydantic BaseSettings
│   │
│   ├── core/                   # Core Infrastructure
│   │   ├── __init__.py
│   │   ├── cache.py            # CacheInterface + InMemoryCache
│   │   ├── circuit_breaker.py  # CircuitBreaker pattern
│   │   └── exceptions.py       # Custom exception hierarchy
│   │
│   ├── models/                 # Domain Models
│   │   ├── __init__.py
│   │   ├── interfaces.py       # Repository protocols
│   │   └── schemas.py          # Pydantic models
│   │
│   ├── repositories/           # Data Access Layer
│   │   ├── __init__.py
│   │   └── memory.py           # In-memory implementations
│   │
│   └── services/               # Business Logic Layer
│       ├── __init__.py
│       ├── feature_flags.py    # Feature flag evaluation
│       ├── feed.py             # Feed orchestration
│       └── ranking.py          # Ranking engine
│
└── requirements.txt
```

## Configuration

All configuration via environment variables (12-factor app):

```bash
# Feature Flags
PERSONALIZATION_ENABLED=true
KILL_SWITCH_ACTIVE=false

# Timeouts (ms)
RANKING_TIMEOUT_MS=20
CACHE_TIMEOUT_MS=5

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SEC=30
```

## What This Demonstrates

### Software Engineering Best Practices
- ✅ **Layered Architecture**: API → Service → Repository
- ✅ **SOLID Principles**: Single responsibility, Interface segregation
- ✅ **Type Annotations**: Full typing with Pydantic models
- ✅ **Dependency Injection**: Loose coupling via FastAPI Depends
- ✅ **Centralized Config**: Pydantic BaseSettings
- ✅ **Custom Exceptions**: Mapped to HTTP status codes
- ✅ **Async by Default**: All endpoints are async

### Resilience Patterns
- ✅ **Circuit Breaker**: Prevents cascading failures
- ✅ **Graceful Degradation**: Fallback to trending feed
- ✅ **Kill Switch**: Instant personalization disable
- ✅ **Structured Logging**: JSON format for production

### Personalization Logic
- ✅ **Rule-Based Ranking**: Configurable weights
- ✅ **User Affinity Boosting**: Based on watch history
- ✅ **Recency Decay**: Fresh content ranked higher
- ✅ **Watch History Filtering**: Remove already-seen
- ✅ **Multi-Tenant Support**: Per-tenant configuration
