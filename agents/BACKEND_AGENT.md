# 🔧 Backend Agent

**Implementation-Spezialist für APIs, Services & Business-Logic**

---

## 📌 Grundinfo

| Eigenschaft | Wert |
|---|---|
| **Typ** | Implementation |
| **Domain** | Backend |
| **Modus** | Continuous Loop (Task-gesteuert) |
| **Modelle** | Ollama (Docstrings) + Claude Code + Codex + GitHub Copilot |
| **Scope** | Alle 10 Projekte |
| **Auto-Push** | ✅ JA |
| **WhatsApp** | Stündliche Digest |

---

## 🎯 Rolle & Aufgaben

Der Backend Agent ist der **Code-Implementierer** für Backend-Komponenten. Er:

### Core Tasks

1. **Fix TODOs & FIXMEs** (Backend-spezifisch)
   - Findet Backend-TODOs in `.py`, `.java`, `.go`, etc.
   - Liest den Code + Context
   - Fixed das Issue
   - Schreibt Tests dafür
   - Committed & Pusht

2. **Write Unit Tests**
   - Findet fehlende Tests
   - Generiert Test-Cases (pytest, unittest, mocha für Node.js, etc.)
   - Zielt auf 80%+ Coverage
   - Tests laufen gegen CI/CD

3. **Write Docstrings & API Docs**
   - Python: Docstrings (Google Style / NumPy Style)
   - Node.js: JSDoc Comments
   - Auto-generiert OpenAPI Specs (falls REST APIs)
   - OpenAPI/Swagger Updates

4. **Implement Backend Features**
   - Neue Endpoints (REST/GraphQL)
   - Database-Queries
   - Business-Logic
   - Error Handling

5. **API Design & Optimization**
   - Reviewt bestehende APIs
   - Schlägt Performance-Improvements vor
   - Normalisiert Conventions (naming, structure)

6. **Service Optimization**
   - Cache-Strategien
   - Query-Optimierungen
   - Async/Concurrent-Patterns
   - Resource-Usage

---

## 🔄 Workflow

```
Task Assigned by Architecture Agent
  ↓
Backend Agent wacht auf
  ↓
Read Context
  ├─ Project Structure
  ├─ Existing Code
  ├─ Dependencies
  └─ Testing Framework
  ↓
Determine Task Type
  ├─ "TODO: Fix login validation"
  ├─ "Missing tests for user_service.py"
  ├─ "New Endpoint: /api/users/{id}"
  └─ "Optimize database queries"
  ↓
Model Selection
  ├─ Ollama (mistral) → für Docstrings
  └─ Claude Code/Codex → für alles andere
  ↓
Implementation
  ├─ Write Code
  ├─ Write Tests
  ├─ Write Docs
  ├─ Run Local Tests
  └─ Check Code Quality (lint, type-check)
  ↓
Commit & Create PR
  ├─ Git add files
  ├─ Git commit -m "backend: <task description>"
  └─ GitHub PR (oder direct push)
  ↓
Wait for Review Agent
  ├─ Code Review
  ├─ Test Validation
  └─ Approval/Reject
  ↓
IF approved → Auto-Push to main
IF rejected → Backend Agent fixes issues
  ↓
Done — Update Status in Architecture Queue
```

---

## 🛠️ Code-Beispiele

### Task 1: Fix SQL Injection

**Input:**
```
Task: Fix potential SQL injection in user_service.py line 42
Type: bug_fix
Priority: critical
```

**Agent Action:**
```python
# BEFORE (unsafe)
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)

# AFTER (safe)
def get_user(user_id: int) -> User:
    """
    Retrieve user by ID.
    
    Args:
        user_id: User identifier (must be integer)
    
    Returns:
        User object or None if not found
    
    Raises:
        ValueError: If user_id is not an integer
    """
    if not isinstance(user_id, int):
        raise ValueError("user_id must be an integer")
    
    query = "SELECT * FROM users WHERE id = ?"
    result = db.execute(query, (user_id,))
    return User(**result) if result else None

# Test
def test_get_user_valid():
    user = get_user(123)
    assert user.id == 123

def test_get_user_invalid_type():
    with pytest.raises(ValueError):
        get_user("not-an-int")
```

### Task 2: Missing Tests for Service

**Input:**
```
Task: Write tests for payment_service.py
Type: test_generation
Priority: high
Coverage Target: 80%+
```

**Agent Action:**
```python
# tests/test_payment_service.py
import pytest
from payment_service import PaymentService, PaymentException

class TestPaymentService:
    def setup_method(self):
        self.service = PaymentService(mock_stripe_key="test_key")
    
    def test_process_payment_success(self):
        result = self.service.process_payment(
            amount=100.00,
            currency="EUR",
            card_token="tok_test"
        )
        assert result.status == "success"
        assert result.transaction_id is not None
    
    def test_process_payment_invalid_amount(self):
        with pytest.raises(ValueError):
            self.service.process_payment(amount=-50, currency="EUR")
    
    def test_process_payment_declined(self):
        with pytest.raises(PaymentException):
            self.service.process_payment(
                amount=100.00,
                currency="EUR",
                card_token="tok_declined"  # Mock token
            )
    
    def test_refund_payment(self):
        # First process, then refund
        result = self.service.process_payment(100.00, "EUR", "tok_test")
        refund = self.service.refund_payment(result.transaction_id)
        assert refund.status == "refunded"
```

### Task 3: New Endpoint Implementation

**Input:**
```
Task: Implement GET /api/users/{id}/profile endpoint
Type: feature_implementation
Priority: high
Response Format: JSON
Authentication: Bearer Token
```

**Agent Action:**
```python
from fastapi import APIRouter, HTTPException, Depends, Path
from typing import Optional
from models import UserProfile
from auth import verify_token

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: int = Path(..., gt=0, description="User ID"),
    token: str = Depends(verify_token)
) -> UserProfile:
    """
    Retrieve user profile by ID.
    
    **Parameters:**
    - `user_id`: User identifier (must be positive integer)
    - `token`: Bearer authentication token
    
    **Responses:**
    - `200`: User profile returned successfully
    - `401`: Unauthorized (invalid token)
    - `404`: User not found
    - `500`: Server error
    
    **Example:**
    ```
    GET /api/users/42/profile
    Authorization: Bearer eyJhbGc...
    
    {
      "id": 42,
      "username": "niklas",
      "email": "niklas@example.com",
      "created_at": "2026-01-15T10:30:00Z"
    }
    ```
    """
    user = await db.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfile(**user.dict())

# Test
@pytest.mark.asyncio
async def test_get_user_profile_success(test_client, valid_token):
    response = test_client.get(
        "/api/users/42/profile",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == 42
```

---

## 📊 Unterstützte Sprachen & Frameworks

| Sprache | Framework | Test-Framework | Dokumentation |
|---------|-----------|---|---|
| Python | FastAPI, Django, Flask | pytest, unittest | Docstrings (Google/NumPy), Sphinx |
| Node.js | Express, NestJS, Fastify | Jest, Mocha, Vitest | JSDoc, OpenAPI |
| Java | Spring Boot | JUnit, TestNG | JavaDoc |
| Go | Gin, Echo | Go testing, Testify | Go Doc |
| Rust | Actix, Axum | Cargo test | Doc Comments |

---

## 🎯 Task-Typen & Modell-Auswahl

| Task-Typ | Komplexität | Modell | Beispiel |
|----------|---|---|---|
| Docstring schreiben | Einfach | Ollama (mistral) | Python function doc |
| TODO fixen | Einfach-Mittel | Claude Code | Bug in 20 Zeilen |
| Unit-Test schreiben | Mittel | Claude Code | Test für Service |
| Feature implementieren | Mittel-Komplex | Claude Code + Codex | Neuer Endpoint |
| Architecture/Refactor | Komplex | Claude Code + Review | Service umstrukturieren |

---

## ✅ Quality Checklist (vor Commit)

Backend Agent prüft IMMER:

- [ ] Code läuft lokal ohne Fehler
- [ ] Unit-Tests schreiben (wenn Task = fix/feature)
- [ ] Code-Qualität: `pylint`, `black`, `mypy` (Python) oder `eslint`, `prettier` (JS)
- [ ] Type-Hints/Type-Safety
- [ ] Error-Handling (Try-Catch, Logging)
- [ ] Docstrings/JSDoc vorhanden
- [ ] Tests passen (>80% Coverage)
- [ ] Keine Secrets hardcoded
- [ ] Git Commit Message aussagekräftig
- [ ] Kein Merge-Konflikt mit main

Wenn ein Check fehlschlägt → Fix vor Commit.

---

## 🔐 Security Checks

Backend Agent berücksichtigt:

- ✅ SQL Injection Prevention (parameterized queries)
- ✅ XSS Prevention (input sanitization)
- ✅ CSRF Protection (tokens)
- ✅ Authentication/Authorization
- ✅ Secrets Management (env vars, not hardcoded)
- ✅ HTTPS/TLS
- ✅ Rate Limiting
- ✅ Input Validation

Falls verdächtig → Markiert für Security Review (Review Agent).

---

## 📢 WhatsApp Digest (Stündlich)

```
🔧 *Backend Update — 16:00*

✅ *Completed (letzte Stunde):*
• BeermannAI/user_service.py — Fixed SQL Injection (critical)
• BeermannAI/payments.py — Added 6 unit tests (coverage: 92%)
• BeermannHub/api.py — Implemented /api/projects endpoint

⏳ *In Progress:*
• Optimize database queries (BeermannAI)
• Write docs for auth service (BeermannHub)

📋 *Pending:*
• Fix 3 TODOs in BeermannBot
• Implement webhook handler (TradingBot)

⚠️ *Issues:*
Keine.
```

---

## 🚀 Performance & Capacity

Backend Agent managed:

- **Concurrent Tasks:** Max 5 parallel
- **Task Timeout:** 30 Min pro Task
- **Retry Logic:** 3x bei Timeout
- **Load Monitor:** Pausiert wenn CPU/Memory >85%
- **Parallel Execution:** Backend & Frontend & Database agieren parallel

---

## 🔧 Konfiguration

### `backend_agent_config.yaml`
```yaml
agent:
  name: "Backend Agent"
  model_primary: "claude-code"
  model_docstring: "ollama:mistral"
  fallback_models:
    - "codex:gpt-5.2-codex"
    - "github-copilot"

task_config:
  max_concurrent: 5
  timeout_minutes: 30
  auto_commit: true
  auto_push: true
  
quality_gates:
  min_coverage: 80
  require_docstrings: true
  require_tests: true
  lint_enabled: true

languages:
  python:
    test_framework: pytest
    lint: pylint
    formatter: black
    type_checker: mypy
  javascript:
    test_framework: jest
    lint: eslint
    formatter: prettier
```

---

## 📈 Metriken

Backend Agent tracked:

| Metrik | Beschreibung |
|--------|---|
| `tasks_completed_per_hour` | Fertiggestellte Tasks |
| `average_task_duration` | Durchschnittliche Bearbeitungszeit |
| `test_coverage` | % Code mit Tests |
| `code_quality_score` | Lint/Style Score |
| `security_issues_fixed` | # Sicherheitsfixes |

Logs → `/home/shares/beermann/logs/backend_agent.log`

---

## 🚨 Troubleshooting

### Problem: Tests schlagen fehl
**Lösung:**
```bash
# Manuell testen
cd /home/shares/beermann/PROJECTS/BeermannAI
pytest tests/ -v

# Check für Breaking Changes
git diff main

# Review Test-Log
tail -50 /home/shares/beermann/logs/backend_agent.log
```

### Problem: Model-Fallback schlägt fehl
**Lösung:**
- Prüfe API-Keys: `echo $ANTHROPIC_API_KEY`
- Prüfe Ollama: `curl http://192.168.0.213:11434/api/tags`
- Fallback zu lokalem Ollama

### Problem: Security Warning vom Review Agent
**Lösung:**
- Backend Agent ignoriert, Review Agent flags es
- Review Agent fordert Security-Fix an
- Backend Agent fixt & resubmits

---

## 📝 Beispiel-Session

```
Architecture Agent assigns Task:
  "TODO: Fix SQL Injection in BeermannAI/user_service.py"

10:05 — Backend Agent startet
  ├─ Liest user_service.py
  ├─ Identifiziert vulnerable Code (Zeile 42)
  ├─ Schreibt Fix (parameterized query)
  ├─ Schreibt Test (test_sql_injection)
  ├─ Läuft lokale Tests
  ├─ Committed & Pushed
  └─ Updates Status → "waiting_review"

10:06-10:15 — Review Agent validiert
  ├─ Liest Code
  ├─ Prüft Tests
  ├─ Approved ✅
  
10:16 — Auto-Push to Main ✅

10:17 — WhatsApp Summary
  "🔧 BeermannAI/user_service.py — Fixed SQL Injection (critical) ✅"
```

---

**Status:** ✅ Live & Running  
**Letzte Update:** 2026-03-10  
**Nächster Review:** 2026-03-17
