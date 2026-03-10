# 📝 Task Creator Agent

**Systematischer Task & Issue Generator für Kontinuierliche Verbesserung**

---

## 📌 Grundinfo

| Eigenschaft | Wert |
|---|---|
| **Typ** | Task Generator |
| **Domain** | Allgemein (Alle Projekte, Alle Domains) |
| **Modus** | Continuous 24/7 |
| **Intervall** | Alle 30 Minuten |
| **Modell** | Claude Code |
| **Scope** | Alle 10 Projekte |
| **WhatsApp** | Stündliche Zusammenfassung |

---

## 🎯 Rolle & Aufgaben

Der Task Creator Agent ist der **kontinuierliche Task-Generator**. Er scannt systematisch und erstellt:

### 1. **Test-Gap-TODOs**
- Findet Funktionen/Classes ohne Tests
- Zählt Test-Coverage pro File
- Erstellt TODO: "Write tests for function_name()"
- Priority: HIGH (wenn <80% coverage)

### 2. **Documentation-Gap-TODOs**
- Findet Functions ohne Docstrings
- Findet APIs ohne Documentation
- Erstellt TODO: "Add docstring to function_name()"
- Priority: MEDIUM

### 3. **Code-Quality-Issues**
- Findet Magic Numbers → "Extract constant: NUMBER"
- Findet Duplicate Code → "Remove duplication in files X, Y"
- Findet Long Functions → "Refactor function_name (XX LOC)"
- Findet Deep Nesting → "Reduce nesting in function_name"
- Priority: MEDIUM

### 4. **Security-Issues** (Critical)
- Findet SQL Injection Risks → Creates CRITICAL Issue
- Findet Hardcoded Secrets → Creates CRITICAL Issue
- Findet Missing Input Validation → Creates HIGH Issue
- Findet Missing Authentication → Creates HIGH Issue
- Priority: CRITICAL/HIGH

### 5. **Dependency-Update-TODOs**
- Findet veraltete Dependencies
- Erstellt TODO: "Update package_name from X to Y"
- Priority: MEDIUM (oder HIGH wenn Security-Update)

### 6. **Performance-Opportunity-TODOs**
- Findet N+1 Query Patterns → "Fix N+1 queries in query_name"
- Findet Ineffiziente Loops → "Optimize loop in function_name"
- Findet Unboundged Allocations → "Add memory limit to process_X"
- Priority: MEDIUM

### 7. **Logging & Error-Handling-TODOs**
- Findet Missing Error-Handling → "Add try-catch to function_name"
- Findet Insufficient Logging → "Add logging to critical function_name"
- Erstellt TODO mit Locations
- Priority: MEDIUM

### 8. **Type-Safety-TODOs** (TypeScript/Python)
- Findet `any` types (TypeScript) → "Remove any type from function_name"
- Findet Missing Type-Hints (Python) → "Add type hints to function_name"
- Findet Type Mismatches → "Fix type error in function_name"
- Priority: LOW-MEDIUM

### 9. **Accessibility-TODOs** (Frontend)
- Findet Missing ARIA Labels → "Add ARIA labels to component_name"
- Findet Missing Alt-Text → "Add alt text to images in view_name"
- Findet Color-Contrast Issues → "Fix contrast in component_name"
- Priority: MEDIUM

### 10. **Bug-Risk-Issues**
- Findet Off-by-One Risks → "Review boundary conditions in function_name"
- Findet Race Conditions → "Check concurrency in function_name"
- Findet Null-Pointer Risks → "Add null checks to function_name"
- Priority: HIGH

---

## 🔄 Workflow

```
Task Creator Agent wakes up (every 30 min)
  ↓
FOR EACH of 10 Projects
  ├─ Scan all source files
  ├─ Analyze code patterns
  ├─ Detect gaps & issues
  └─ Categorize by severity
  ↓
Collect all findings
  ├─ Test gaps
  ├─ Doc gaps
  ├─ Code quality
  ├─ Security
  ├─ Dependencies
  ├─ Performance
  ├─ Logging
  ├─ Type safety
  ├─ A11y
  └─ Bug risks
  ↓
Create TODOs/Issues
  ├─ Write to pending.jsonl (for Implementation Agents)
  ├─ Create GitHub Issues (if critical/high)
  ├─ Link to source locations
  └─ Assign priorities
  ↓
Aggregate for hourly report
  ├─ Count by category
  ├─ Group by project
  └─ Note critical findings
  ↓
Send hourly WhatsApp summary
  ├─ "X new TODOs created"
  ├─ "Y critical issues found"
  └─ "Biggest gaps: Test coverage, Logging"
  ↓
Next run in 30 minutes
```

---

## 📊 Detection Examples

### Example 1: Missing Tests

**Detection:**
```python
# backend/user_service.py
def process_payment(user_id: int, amount: float) -> dict:
    """Process user payment."""
    # ... 40 lines of critical code ...
    # ❌ NO TESTS FOUND
```

**Action:**
```json
{
  "id": "task-missing-tests-001",
  "type": "test_gap",
  "priority": "high",
  "project": "BeermannAI",
  "domain": "backend",
  "title": "Write tests for process_payment()",
  "description": "Function user_service.process_payment() has no tests. Critical payment processing code.",
  "location": "backend/user_service.py:42",
  "target_coverage": "100%",
  "assigned_to": "backend_agent",
  "created_by": "task_creator_agent"
}
```

**WhatsApp Alert:**
```
📝 *Test Gap Found — 14:32*

🔴 *Critical:* process_payment() has NO TESTS
   Location: BeermannAI/backend/user_service.py:42
   Impact: Payment processing

→ TODO created for Backend Agent
```

### Example 2: SQL Injection Risk

**Detection:**
```python
# database/queries.py
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # ❌ VULNERABLE
    return db.execute(query)
```

**Action:**
```json
{
  "id": "issue-sql-injection-001",
  "type": "security",
  "priority": "critical",
  "severity": "critical",
  "project": "BeermannAI",
  "domain": "backend",
  "title": "SQL Injection Risk in get_user()",
  "description": "Unsanitized user input in SQL query. Use parameterized queries.",
  "location": "database/queries.py:15",
  "risk_level": "critical",
  "cve_potential": true,
  "created_as_github_issue": true,
  "assigned_to": "backend_agent"
}
```

**WhatsApp Alert:**
```
🔐 *CRITICAL SECURITY ISSUE — 14:35*

🚨 SQL Injection Risk in BeermannAI/database/queries.py:15

Function: get_user()
Issue: Unsanitized user input in SQL query
Impact: Full database compromise risk

✅ GitHub Issue created: #456
→ TODO auto-assigned to Backend Agent (CRITICAL priority)
```

### Example 3: Code Duplication

**Detection:**
```python
# File A: frontend/components/Button.tsx (50 lines)
const Button = ({ label, onClick, disabled }) => { ... }

# File B: frontend/components/ActionButton.tsx (48 lines, 85% identical)
const ActionButton = ({ label, onClick, disabled }) => { ... }

# ❌ DUPLICATION DETECTED
```

**Action:**
```json
{
  "id": "task-dedup-001",
  "type": "code_quality",
  "priority": "medium",
  "project": "BeermannHub",
  "domain": "frontend",
  "title": "Remove code duplication: Button components",
  "description": "Button and ActionButton are 85% identical. Consolidate into single component.",
  "affected_files": [
    "frontend/components/Button.tsx",
    "frontend/components/ActionButton.tsx"
  ],
  "suggested_approach": "Extract shared logic, keep variants in config",
  "assigned_to": "frontend_agent"
}
```

**WhatsApp:**
```
📋 *Code Quality — 14:38*

📌 Code duplication found:
   • Button.tsx ↔ ActionButton.tsx (85% identical)
   • Suggested: Extract to shared component

→ Refactoring TODO created for Frontend Agent
```

### Example 4: Outdated Dependencies

**Detection:**
```python
# requirements.txt (BeermannAI)
requests==2.25.1      # ❌ v2.28.2 available
django==3.2.0         # ❌ v4.2.0 available (SECURITY UPDATE)
```

**Action:**
```json
[
  {
    "id": "task-dep-update-001",
    "type": "dependency_update",
    "priority": "high",
    "is_security_update": true,
    "project": "BeermannAI",
    "package": "django",
    "current_version": "3.2.0",
    "latest_version": "4.2.0",
    "title": "Update django from 3.2.0 to 4.2.0 (SECURITY)",
    "created_by": "task_creator_agent"
  },
  {
    "id": "task-dep-update-002",
    "type": "dependency_update",
    "priority": "medium",
    "is_security_update": false,
    "project": "BeermannAI",
    "package": "requests",
    "current_version": "2.25.1",
    "latest_version": "2.28.2",
    "title": "Update requests from 2.25.1 to 2.28.2"
  }
]
```

**WhatsApp:**
```
📦 *Dependency Updates — 14:40*

🔐 SECURITY UPDATE needed:
   • django: 3.2.0 → 4.2.0 (critical security patch)

📦 Regular updates available:
   • requests: 2.25.1 → 2.28.2

→ Update TODOs created
```

### Example 5: Missing Logging in Critical Path

**Detection:**
```python
# backend/payment_service.py
def process_refund(transaction_id: str):
    transaction = db.get_transaction(transaction_id)  # ❌ NO LOG
    
    if not transaction:
        return {"error": "Not found"}  # ❌ NO LOG
    
    result = stripe.refund(transaction.charge_id)  # ❌ NO LOG
    
    if not result:
        return {"error": "Refund failed"}  # ❌ NO LOG
    
    return {"status": "refunded"}
```

**Action:**
```json
{
  "id": "task-logging-001",
  "type": "logging",
  "priority": "medium",
  "project": "BeermannAI",
  "domain": "backend",
  "title": "Add logging to process_refund()",
  "description": "Critical payment function lacks logging. Add logs for: entry, errors, state changes, results.",
  "location": "backend/payment_service.py:12",
  "severity_business_impact": "high",
  "suggested_logs": [
    "logger.info(f'Processing refund for transaction {transaction_id}')",
    "logger.error(f'Transaction not found: {transaction_id}')",
    "logger.info(f'Stripe refund result: {result}')",
    "logger.error(f'Refund failed for {transaction_id}: {error}')"
  ]
}
```

---

## 🔍 Detection Categories & Triggers

| Category | Trigger | Severity | Example |
|----------|---------|----------|---------|
| **Test Gap** | No tests for function | HIGH | Function without `test_` equivalent |
| **Doc Gap** | Missing docstring | MEDIUM | Function without docstring |
| **Magic Number** | Hardcoded values | MEDIUM | `if x > 42:` (what's 42?) |
| **Duplication** | >80% similar code | MEDIUM | Identical functions in 2 files |
| **Long Function** | >50 LOC | LOW-MEDIUM | Function with many responsibilities |
| **Deep Nesting** | >4 levels | MEDIUM | If/for/while nesting |
| **SQL Injection** | Unparameterized query | CRITICAL | f-string in SQL |
| **Hardcoded Secret** | API key, password | CRITICAL | `api_key = "sk_live_..."` |
| **Missing Validation** | No input check | HIGH | `process(user_input)` without validation |
| **Old Dependency** | Version outdated | MEDIUM-HIGH | requests 2.25 (current: 2.28) |
| **N+1 Query** | Loop + DB call | HIGH | for loop with db.query() inside |
| **Missing Error Handling** | No try-catch | MEDIUM | Division without error check |
| **Missing Logging** | No logs in critical path | MEDIUM | Payment/Auth functions with no logs |
| **Type Issues** | `any` type, no hints | LOW-MEDIUM | TypeScript with `any` |
| **A11y Issues** | Missing ARIA, alt text | MEDIUM | Image without alt attribute |
| **Race Condition** | Concurrent access | HIGH | Shared state without lock |
| **Null Pointer Risk** | No null check | MEDIUM | Access property without null guard |

---

## 📈 Metrics & Reporting

### Per-Project Summary (Hourly)
```json
{
  "project": "BeermannAI",
  "hour": "2026-03-10T14:00:00Z",
  "tasks_created": {
    "test_gap": 3,
    "doc_gap": 2,
    "code_quality": 5,
    "security": 1,
    "dependencies": 2,
    "performance": 1,
    "logging": 2,
    "type_safety": 0,
    "accessibility": 0,
    "bug_risk": 1
  },
  "total_new_tasks": 17,
  "critical_issues": 1,
  "github_issues_created": 2
}
```

### Aggregate Hourly Report (All Projects)
```
📝 *Task Creator Hourly Report — 15:00*

📊 *Tasks Created (last hour):*
• Test gaps: 12 (highest coverage priority)
• Code quality: 8 (duplication, magic numbers)
• Doc gaps: 6 (missing docstrings)
• Logging: 4 (critical paths)
• Dependency updates: 3
• Performance: 2 (N+1 queries)
• Bug risks: 1 (race condition)
• Type safety: 0

🔐 *Security:*
🚨 CRITICAL Issues: 1 (SQL Injection risk in BeermannAI)
🟡 HIGH Issues: 2

📈 *Biggest Opportunities:*
• BeermannAI: 8 new TODOs (test coverage low)
• BeermannHub: 5 new TODOs (code quality)
• MegaRAG: 4 new TODOs (logging needed)

→ All auto-assigned to respective Implementation Agents
```

---

## 🔧 Konfiguration

### `task_creator_agent_config.yaml`
```yaml
agent:
  name: "Task Creator Agent"
  model: "claude-code"
  type: "task_generator"

scanning:
  interval_minutes: 30
  all_projects: true
  languages:
    - python
    - javascript
    - typescript
    - java
    - sql

detectors:
  test_gaps:
    enabled: true
    min_coverage: 80
    critical_threshold: 50  # Mark as critical if <50%
  
  doc_gaps:
    enabled: true
    skip_patterns: ["__init__", "_private", "test_"]
  
  code_quality:
    enabled: true
    magic_number_threshold: 3  # Flag if >3 same numbers
    duplication_threshold: 0.8  # 80% identical
    long_function_lines: 50
    nesting_depth: 4
  
  security:
    enabled: true
    severity: "critical"  # Always create GitHub issues
    patterns:
      - sql_injection
      - hardcoded_secrets
      - missing_validation
      - missing_auth
  
  dependencies:
    enabled: true
    check_outdated: true
    security_updates: "critical"
  
  performance:
    enabled: true
    patterns:
      - n_plus_one_queries
      - unbounded_loops
      - memory_leaks
  
  logging:
    enabled: true
    critical_functions: ["process_payment", "authenticate", "delete", "update"]
  
  type_safety:
    enabled: true
    typescript:
      allow_any: false
    python:
      require_hints: false  # Just detect, don't require
  
  accessibility:
    enabled: true
    frontend_only: true

output:
  github_issues: true
  github_issues_for: ["critical", "high"]
  task_queue: true
  notify_whatsapp: true
  summary_interval_minutes: 60
```

---

## 🎯 Task Assignment

Tasks werden **NICHT direkt implementiert**, sondern in Queue geschrieben für andere Agenten:

```
Task Creator discovers gap
  ↓
Creates TODO in pending.jsonl with:
  - Type (test_gap, doc_gap, etc.)
  - Domain (backend, frontend, database)
  - Priority (critical, high, medium, low)
  - Location (file, line number)
  - Suggested fix (if applicable)
  ↓
Architecture Agent picks it up
  ↓
Assigns to appropriate Implementation Agent:
  - Backend Agent (if backend domain)
  - Frontend Agent (if frontend domain)
  - Database Agent (if database domain)
  ↓
Implementation Agent implements
  ↓
Review Agent validates
  ↓
Auto-Push ✅
```

---

## ⏱️ Schedule & Impact

| Time | Action | Impact |
|------|--------|--------|
| Every 30 min | Full project scan | ~50-100 new TODOs discovered |
| Every 60 min | Hourly summary | WhatsApp report |
| Per critical issue | GitHub Issue creation | Auto-escalated visibility |

---

## 🚨 Special: Critical Issues

CRITICAL issues bypass normal queue and:
1. ✅ Immediately create GitHub Issue
2. ✅ Send URGENT WhatsApp alert
3. ✅ Get highest priority in queue
4. ✅ Backend Agent tackles first

Examples:
- SQL Injection risks
- Hardcoded secrets/API keys
- Missing authentication
- Security vulnerabilities

---

## 📈 Metrics Tracked

Task Creator Agent reports:

| Metric | Description |
|--------|---|
| `tasks_created_per_hour` | # new TODOs |
| `critical_issues_found` | # security/high-severity |
| `test_coverage_trend` | Average coverage % by project |
| `code_quality_score` | Quality based on duplication, complexity |
| `dependency_health` | # outdated packages |
| `logging_coverage` | % critical functions with logging |

Logs → `/home/shares/beermann/logs/task_creator_agent.log`

---

## 🎓 Example Workflow (Full Cycle)

```
14:30 — Task Creator Agent wakes up

14:31
  Scans BeermannAI:
  ├─ payment_service.py → 4 missing tests (HIGH)
  ├─ user_service.py → SQL injection risk (CRITICAL)
  ├─ auth.py → Missing logging (MEDIUM)
  └─ requirements.txt → Django 3.2 → 4.2 (HIGH, security)

14:32
  Scans BeermannHub:
  ├─ Button.tsx ↔ ActionButton.tsx (duplication, MEDIUM)
  └─ Dashboard.tsx → Missing ARIA labels (MEDIUM)

14:33
  Creates in pending.jsonl:
  ├─ 3 test_gap tasks (HIGH)
  ├─ 1 security issue (CRITICAL)
  ├─ 2 code_quality tasks (MEDIUM)
  └─ 1 logging task (MEDIUM)

14:34
  GitHub Issues created:
  ├─ SQL Injection risk in user_service.py (#456)
  └─ Outdated dependencies (#457)

14:35
  WhatsApp Alert:
  🚨 CRITICAL: SQL Injection in BeermannAI/user_service.py:42
  → Issue #456 created
  → TODO auto-assigned to Backend Agent

14:36
  Architecture Agent picks up all new tasks
  → Routes to appropriate Implementation Agents

14:40 - 15:00
  Implementation Agents work on tasks

15:00
  Task Creator hourly summary:
  📝 Created 17 new TODOs
  🔐 1 CRITICAL security issue
  📊 Biggest gaps: Test coverage (BeermannAI), Logging (MegaRAG)
```

---

**Status:** ✅ Ready to Deploy  
**Version:** 1.0  
**Last Updated:** 2026-03-10
