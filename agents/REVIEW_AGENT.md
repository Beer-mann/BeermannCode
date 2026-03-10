# ✅ Review Agent (M.D. Configuration)

**Quality Gate & Final Validator**

---

## 📌 Grundinfo

| Eigenschaft | Wert |
|---|---|
| **Typ** | Quality Gate |
| **Modus** | Reactive (triggered nach Implementation-Agenten) |
| **Modell** | Claude M.D. (benutzerdefiniert — später) |
| **Konfiguration** | M.D. File Format (Markdown-basiert) |
| **Scope** | Alle 10 Projekte |
| **Strict Mode** | ✅ JA — alles muss passen |
| **WhatsApp** | Approval/Reject Status |

---

## 🎯 Rolle & Aufgaben

Der Review Agent ist der **letzte Gate-Keeper** vor Auto-Push. Er:

### Core Validations

1. **Code Review**
   - Prüft Code-Qualität (Style, Best Practices)
   - Sucht nach Bugs oder LogicErrors
   - Prüft auf Security Issues
   - Validiert Error Handling
   - Prüft Performance Impact

2. **Test Validation**
   - Prüft dass alle Tests passen
   - Validiert Test-Coverage (muss >80% sein)
   - Prüft Test-Qualität (echte Tests, keine Dummy-Tests)
   - Verifyft Integration-Tests laufen

3. **Issue Resolution Check**
   - War das Issue WIRKLICH gelöst?
   - Nicht nur oberflächliche Patches
   - Wurden Root-Causes adressiert?
   - Wird das Problem wiederkommen?

4. **Performance Analysis**
   - Keine neuen Performance-Regressions
   - Query-Performance OK?
   - Bundle-Size OK?
   - Response-Times OK?

5. **Security Audit**
   - Secrets nicht hardcoded?
   - Input-Validation vorhanden?
   - Authentication/Authorization OK?
   - OWASP Top 10 Compliance?

6. **Approval/Reject Decision**
   - Approve: → Auto-Push to Main
   - Reject: → Send back to Implementation Agent mit Feedback

---

## 🔄 Workflow

```
Implementation Agent commits change
  ↓
Triggers Review Agent (Pull Request created)
  ↓
Review Agent wacht auf
  ↓
Read PR Content
  ├─ Code changes (diff)
  ├─ Test changes
  ├─ Commit message
  └─ PR description
  ↓
Run Validation Checks (M.D. Configuration)
  ├─ Code Quality Check
  ├─ Test Coverage Check
  ├─ Performance Check
  ├─ Security Check
  └─ Issue Resolution Check
  ↓
Collect Results
  ├─ Pass? → All ✅
  ├─ Fail? → Issues found ❌
  └─ Conditional Pass? → Needs manual review
  ↓
Generate Review Report (M.D. Format)
  ├─ Summary
  ├─ Checklist with results
  ├─ Issues found (if any)
  └─ Recommendations
  ↓
Decision
  ├─ IF all checks pass → Approve ✅
  ├─ IF issues found → Reject ❌ + feedback
  └─ IF unclear → Request manual review
  ↓
Post Result
  ├─ Add comment to PR
  ├─ Send WhatsApp notification
  └─ If Approved: Auto-Push to Main
  ↓
IF Rejected:
  ├─ Implementation Agent gets feedback
  ├─ Agent makes fixes
  ├─ Resubmits for review
  └─ Loop until Approved
```

---

## 📋 M.D. Configuration Format

Die **M.D. (Markdown Descriptor)** Datei definiert alle Validations-Regeln:

### Struktur: `review_agent_config.md`

```markdown
# Review Agent Configuration — M.D. Format

## Overview
- **Agent:** Review Agent
- **Model:** Claude M.D.
- **Purpose:** Validate all code changes before auto-push
- **Strict Mode:** YES (all checks must pass)

---

## 1. Code Quality Checks

### 1.1 Code Style
- **Tool:** eslint (frontend), pylint (backend)
- **Rules:**
  - No warnings allowed (must be 0)
  - Indentation: 2 spaces (JS) / 4 spaces (Python)
  - Line length: max 100 characters (JS), max 88 characters (Python with black)
- **Severity:** WARN (fix requested, not blocking if code runs)

### 1.2 Type Safety
- **Tools:** TypeScript, mypy (Python)
- **Rules:**
  - All functions must have type hints (TypeScript required, Python recommended)
  - No `any` type (unless exception documented)
  - All variables should be typed
- **Severity:** WARN (strongly encouraged, can block if `any` used)

### 1.3 Code Complexity
- **Metrics:**
  - Cyclomatic Complexity: max 10 per function
  - Lines per function: max 50 LOC
  - Nesting depth: max 4 levels
- **Tool:** pylint complexity-check, eslint-complexity
- **Severity:** WARN (refactor suggested)

### 1.4 Security Review
- **Checks:**
  - No hardcoded secrets (API keys, passwords)
  - No SQL injection vulnerabilities
  - Input validation present
  - HTTPS/TLS for external calls
  - CSRF tokens for state changes
- **Tool:** Custom + semgrep
- **Severity:** BLOCK (must fix)

### 1.5 Best Practices
- **Framework-specific:**
  - React: memoization where needed, hooks rules followed
  - FastAPI: proper status codes, error handling
  - SQL: parameterized queries, no N+1 patterns
- **Severity:** WARN (best practice, not strictly required)

---

## 2. Test Validation

### 2.1 Test Coverage
- **Minimum:** 80% code coverage
- **Critical paths:** 100% coverage required
- **Tool:** coverage.py (Python), Jest coverage (JS)
- **Report:** Must be included in PR comment
- **Severity:** BLOCK (if <80%)

### 2.2 Test Quality
- **Rules:**
  - Tests should be meaningful (not dummy passes)
  - Use assertions, not just `assert True`
  - Test both happy path & error cases
  - Mocking external dependencies (APIs, databases)
- **Manual Review:** Sample 3-5 tests for quality
- **Severity:** WARN (auto-check fails, manual review needed)

### 2.3 Test Execution
- **Must Pass:**
  - Unit tests: `pytest . --strict-markers` or `npm test`
  - Integration tests (if exist): `pytest tests/integration/`
  - No flaky tests (run 3x to verify)
- **Timeout:** 5 minutes max for all tests
- **Severity:** BLOCK (if tests fail)

### 2.4 Edge Cases
- **For bug fixes:** Test that reproduces bug + fix verification
- **For features:** Test happy path + 2-3 error cases
- **Examples:**
  - Invalid input
  - Boundary values
  - Concurrency/race conditions (if applicable)
- **Severity:** WARN (recommend, not required)

---

## 3. Issue Resolution Check

### 3.1 Bug Fix Validation
- **Questions:**
  - Is the root cause fixed (not just symptom)?
  - Will this regress in future?
  - Are similar bugs elsewhere in codebase?
- **Verification:**
  - Original failing test now passes
  - No new test failures
  - Code review for similar patterns
- **Severity:** BLOCK (issue must be truly resolved)

### 3.2 Feature Completeness
- **Questions:**
  - Does implementation match description?
  - Are all requirements met?
  - Are edge cases handled?
- **Verification:**
  - PR description matches actual changes
  - Tests cover all stated requirements
- **Severity:** BLOCK (feature must be complete)

---

## 4. Performance Check

### 4.1 Runtime Performance
- **Rules:**
  - No new endpoints with response time >500ms
  - No new queries with execution time >100ms
  - No unbounded loops or recursive calls
- **Verification:**
  - EXPLAIN ANALYZE for new queries
  - Profiling for CPU-intensive code
- **Severity:** WARN (report performance impact)

### 4.2 Bundle Size
- **Frontend Only:**
  - Bundle size should not increase >50KB
  - Report: new vs. old size
  - Tree-shaking enabled
- **Tool:** webpack-bundle-analyzer or similar
- **Severity:** WARN (report, can proceed with explanation)

### 4.3 Database Impact
- **Rules:**
  - No N+1 query patterns
  - New indexes: justified & tested
  - Migrations: zero-downtime or documented downtime
- **Severity:** BLOCK (if N+1 pattern detected)

---

## 5. Documentation

### 5.1 Code Comments
- **Rules:**
  - Complex logic has comments
  - Public APIs have docstrings/JSDoc
  - Why (not what) is documented
- **Severity:** WARN (strongly encouraged)

### 5.2 PR Description
- **Must Include:**
  - What changed?
  - Why?
  - How to test?
  - Any breaking changes?
  - Screenshots (if UI change)
- **Severity:** WARN (good practice)

---

## 6. Compliance & Standards

### 6.1 Git Hygiene
- **Rules:**
  - Meaningful commit messages
  - One commit per logical change
  - No merge commits (use rebase)
- **Severity:** WARN (CI enforces via hooks)

### 6.2 Legal/Compliance
- **Rules:**
  - No GPL code (we use MIT/Apache)
  - No copyrighted content
  - GDPR compliant (no unnecessary data)
- **Severity:** BLOCK (legal must verify)

---

## Review Decision Logic

```
IF all BLOCK-level checks pass:
  AND all tests pass:
    AND code quality WARN-level is acceptable:
      → APPROVE ✅
      → Auto-Push to Main

IF any BLOCK-level check fails:
  → REJECT ❌
  → Request changes
  → Implementation Agent re-submits

IF WARN-level issues (but blocks all pass):
  → CONDITIONAL APPROVE ⚠️
  → Suggest improvements
  → Can auto-push if all BLOCKs pass
```

---

## Approval Template (M.D.)

```markdown
# Review Result: ✅ APPROVED

## Summary
- **PR:** #123 — Fix SQL Injection in login.py
- **Agent:** Backend Agent
- **Reviewed By:** Review Agent (Claude M.D.)
- **Time:** 2026-03-10 14:32:00 UTC

## Checklist

### Code Quality ✅
- [x] No style errors (eslint/pylint passed)
- [x] Type-safe (mypy passed)
- [x] Complexity OK (max 10 per function)
- [x] Security OK (no hardcoded secrets)
- [x] Best practices followed

### Tests ✅
- [x] Coverage: 92% (target: 80%) ✅
- [x] All tests pass (8/8)
- [x] Integration tests pass
- [x] Edge cases covered

### Issue Resolution ✅
- [x] Root cause fixed (parameterized queries)
- [x] Original failing test now passes
- [x] No similar bugs found

### Performance ✅
- [x] No performance regression
- [x] Query time: 5ms (acceptable)
- [x] No N+1 patterns

### Documentation ✅
- [x] Docstring updated
- [x] Security comment added
- [x] Commit message clear

---

## Issues Found: None ❌

---

## Approval
- **Status:** ✅ APPROVED
- **Can Auto-Push:** YES
- **Reason:** All checks passed, excellent code quality

---

## Feedback
Great fix! The parameterized query approach is the right solution.
Consider adding a similar check to password_reset() function
(found similar pattern there).
```

---

## Rejection Template (M.D.)

```markdown
# Review Result: ❌ REJECTED

## Summary
- **PR:** #124 — Implement Payment Processing
- **Agent:** Backend Agent
- **Reviewed By:** Review Agent (Claude M.D.)
- **Time:** 2026-03-10 15:01:00 UTC

## Issues Found

### 🔒 Security Issues (BLOCKING)
1. **Hardcoded API Key**
   - Location: `/home/.../payment_service.py` line 12
   - Issue: Stripe API key in source code
   - Fix: Move to environment variable
   - Severity: CRITICAL

2. **No Input Validation**
   - Location: `/home/.../process_payment()` line 45
   - Issue: Amount not validated (negative values accepted)
   - Fix: Add validation: `assert amount > 0`
   - Severity: HIGH

### ⚠️ Test Coverage (BLOCKING)
- Current: 45% (target: 80%)
- Missing tests for:
  - Invalid card scenarios
  - Network error handling
  - Refund process
- Fix: Add 15+ more test cases

### 💡 Code Quality (WARNINGS)
- Function too long: process_payment() has 120 LOC (max 50)
- Recommendation: Extract error handling to separate function

---

## Requested Changes

1. **URGENT:** Move API key to env variable
2. **URGENT:** Add input validation
3. **URGENT:** Add 15+ test cases for 80% coverage
4. **RECOMMENDED:** Refactor process_payment() function

---

## Approval
- **Status:** ❌ REJECTED
- **Can Auto-Push:** NO
- **Reason:** Security issues + insufficient test coverage

---

## Next Steps
1. Fix security issues (1 hour)
2. Add test cases (2 hours)
3. Refactor if time allows
4. Resubmit for review

Please address these items and resubmit. I'll fast-track the re-review.
```

---

## 🔐 M.D. File Path

Der Review Agent sucht seine M.D. Konfiguration hier:

```
/home/shares/beermann/PROJECTS/BeermannCode/agents/review_agent_config.md
```

**Du musst diese Datei später erstellen.** Format:
```
# Review Agent Configuration — M.D. Format

[Your custom rules, checks, severity levels, etc.]
```

---

## 📊 Review Metrics

Review Agent tracked:

| Metrik | Beschreibung |
|--------|---|
| `avg_review_time` | Durchschnittliche Review-Dauer |
| `approval_rate` | % Approved vs. Rejected |
| `common_issues` | Häufige Fehler |
| `security_issues_blocked` | # Security fixes verhindert |
| `test_coverage_avg` | Durchschnittliche Test-Coverage |

Logs → `/home/shares/beermann/logs/review_agent.log`

---

## 🔧 Konfiguration

### Wo du deine M.D. Config erstellst:

```
/home/shares/beermann/PROJECTS/BeermannCode/agents/
├── review_agent_config.md        ← DU ERSTELLST DIESE!
├── REVIEW_AGENT.md               ← Diese Datei (Dokumentation)
└── [andere Agent-Dateien]
```

**Template für deine M.D. Config:**

```markdown
# Review Agent Configuration — M.D. Format

## Overview
[Deine Übersicht]

---

## 1. Code Quality Checks
[Deine Regeln für Code-Qualität]

---

## 2. Test Validation
[Deine Regeln für Tests]

---

## 3. Issue Resolution
[Deine Kriterien für gelöste Issues]

---

## 4. Performance
[Deine Performance-Standards]

---

## 5. Security
[Deine Security-Anforderungen]

---

## Review Decision Logic
[Deine Approval/Rejection Logik]
```

---

## 🎯 Was kommt später

1. **Du erstellst:** `review_agent_config.md` mit deinen M.D. Definitionen
2. **Review Agent** liest diese M.D. Config
3. **Review Agent** validiert alle PRs gegen diese Regeln
4. **Auto-Approval/Rejection** basierend auf M.D.

---

## 📝 Beispiel-Szenarien

### Szenario 1: Security Bypass Detected

```
Implementation Agent: "I need to add a backdoor for debugging"
↓
Review Agent checks: review_agent_config.md rules
↓
M.D. Rule: "No hardcoded credentials OR backdoor access"
↓
Review Agent: "REJECTED — Security violation"
↓
Implementation Agent: "Oh, right... never mind" 🚫
```

### Szenario 2: 95% Test Coverage

```
Implementation Agent: "Complete new feature + 95% tests"
↓
Review Agent checks: Test coverage >80%? ✅
↓
Review Agent: "APPROVED — All checks pass"
↓
Auto-Push to Main ✅
```

---

**Status:** ✅ Template Ready (awaiting M.D. Configuration)  
**Action:** Niklas erstellt `review_agent_config.md` später  
**Letzte Update:** 2026-03-10
