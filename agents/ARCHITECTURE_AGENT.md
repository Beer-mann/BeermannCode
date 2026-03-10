# 🧠 Architecture Agent

**Orchestrator der gesamten BeermannCode Infrastruktur**

---

## 📌 Grundinfo

| Eigenschaft | Wert |
|---|---|
| **Typ** | Orchestrator |
| **Modus** | Continuous 24/7 |
| **Intervall** | Alle 10 Minuten |
| **Modell** | Claude Code |
| **Scope** | Alle 10 Projekte |
| **WhatsApp** | Stündliche Zusammenfassung |

---

## 🎯 Rolle & Aufgaben

Der Architecture Agent ist das **Gehirn** der Operation. Er:

1. **Task Discovery** — Scannt alle 10 Projekte auf:
   - TODOs & FIXMEs in Sourcecode
   - Fehlende Tests
   - Fehlende Docstrings
   - Alte/veraltete Dependencies
   - Code-Smells
   - Issues auf GitHub/GitLab

2. **Priority Assignment** — Klassifiziert Tasks nach:
   - Dringlichkeit (Critical/High/Medium/Low)
   - Abhängigkeiten (welche müssen zuerst gemacht werden?)
   - Domain (Backend/Frontend/Database/Feature)
   - Komplexität (einfach/mittel/komplex)

3. **Conflict Detection** — Erkennt:
   - Race Conditions (zwei Agenten ändern gleiches File)
   - Breaking Changes (Änderungen, die andere Projekte betreffen)
   - Ungelöste Dependencies

4. **Workload Balancing** — Verteilt Arbeit auf:
   - Backend Agent
   - Frontend Agent
   - Database Agent
   - Feature Agent
   - Nach verfügbarem "Capacity"

5. **Dependency Analysis** — Mapped:
   - Welche Projekte hängen voneinander ab?
   - Welche Changes können parallel laufen?
   - Welche müssen sequenziell erfolgen?

---

## 🔄 Workflow

```
START (alle 10 Min)
  ↓
Scan alle 10 Projekte
  ├─ Git Status
  ├─ Uncommitted Changes
  ├─ TODOs/FIXMEs (grep)
  ├─ GitHub Issues (API)
  └─ Last Commits (git log)
  ↓
Collect Tasks → Task Queue
  ↓
Analyze Dependencies
  ├─ Welche TODOs blockieren andere?
  ├─ Welche Changes sind unabhängig?
  └─ Welche Features sind Priority?
  ↓
Assign Priorities
  ├─ Critical (Bugs, Breaking Changes)
  ├─ High (Features, Tests)
  ├─ Medium (Docstrings, Refactoring)
  └─ Low (Nice-to-have)
  ↓
Distribute Tasks to Agents
  ├─ Backend Tasks → Backend Agent
  ├─ Frontend Tasks → Frontend Agent
  ├─ Database Tasks → Database Agent
  └─ Feature Ideas → Feature Agent
  ↓
Monitor Agent Progress
  ├─ Konflikt-Check (wer ändert was?)
  └─ Capacity-Check (sind die Agenten überlastet?)
  ↓
Compile Hourly Report
  └─ WhatsApp Summary (was wurde gemacht, was kommt next?)
  ↓
END → Nächste Iteration in 10 Min
```

---

## 📊 Task Discovery — Wo schaut der Agent?

### 1. **Git-basiert**
```bash
# Uncommitted Changes
git status --porcelain

# Recent Commits (was wurde die letzte Stunde gemacht?)
git log --since="1 hour ago" --oneline

# TODO/FIXME im Code
grep -r "TODO\|FIXME\|BUG\|HACK" --include="*.py" --include="*.js" --include="*.ts" --include="*.sql"
```

### 2. **GitHub Issues** (falls Public)
```bash
# Offene Issues
gh issue list --state open --limit 50

# Issues mit Label "bug"
gh issue list --label "bug" --state open

# Issues mit Label "enhancement"
gh issue list --label "enhancement" --state open
```

### 3. **Code Quality Checks**
```bash
# Missing Tests
find . -name "*.py" -o -name "*.js" | grep -v test | wc -l

# Missing Docstrings
pylint --disable=all --enable=missing-docstring

# Code Coverage
coverage report
```

### 4. **Dependency Analysis**
```bash
# Veraltete Dependencies
pip list --outdated  # Python
npm outdated        # Node.js
```

---

## 🎭 Task-Klassifikation

Jeder Task wird **auto-klassifiziert**:

```json
{
  "id": "TASK-001",
  "project": "BeermannAI",
  "title": "Fix SQL Injection in login.py",
  "description": "Line 42 has unsanitized user input",
  "domain": "backend",
  "priority": "critical",
  "type": "bug_fix",
  "assigned_to": "backend_agent",
  "estimated_hours": 0.5,
  "blockers": [],
  "blocked_by": [],
  "dependencies": ["TASK-002"],
  "status": "pending"
}
```

### Domains
- **Backend** — APIs, Services, Business-Logic, Security
- **Frontend** — UI, Components, UX, Accessibility
- **Database** — Schema, Migrations, Performance, Backups
- **Feature** — Neue Features, Refactoring, Improvements

### Priorities
- **Critical** — Security, Breaking Bugs, Data Loss Risk
- **High** — Features, Performance, Tests (Coverage <80%)
- **Medium** — Docstrings, Code Style, Minor Refactoring
- **Low** — Nice-to-have, Optimization, Documentation

---

## 🔀 Workload Balancing

Der Agent berücksichtigt:

```yaml
backend_agent:
  current_load: 3       # Tasks in Progress
  capacity: 5           # Max concurrent Tasks
  efficiency: 0.95      # % Tasks completed successfully
  availability: 100%

frontend_agent:
  current_load: 2
  capacity: 5
  efficiency: 0.92
  availability: 100%

database_agent:
  current_load: 1
  capacity: 3           # Kleinere Capacity (kritischer)
  efficiency: 0.98
  availability: 100%
```

Wenn ein Agent zu viel hat (load > capacity * 0.8), wird die Queue gepuffert.

---

## 📢 Hourly Report (WhatsApp)

Jede Stunde um HH:00 → WhatsApp Summary:

```
🦅 *Architecture Report — 15:00*

📊 *Tasks verarbeitet:*
• Backend: 3 TODOs fixed, 2 Tests written
• Frontend: 1 Component, 1 Accessibility fix
• Database: 1 Query optimized
• Features: 2 neue Ideen vorgeschlagen

⏳ *Pending (nächste Stunde):*
• Critical: 1 (Security in BeermannAI)
• High: 5 (Tests, Features)
• Medium: 12 (Docstrings)

⚠️ *Blocker:*
Keine.

🚀 *Next Priority:*
Fix SQL Injection in BeermannAI/login.py (Backend Agent)
```

---

## 🔧 Konfiguration

### Config-Dateien
```
/home/shares/beermann/PROJECTS/BeermannCode/
├── agents.json                    # Main Agent Config
├── agents/
│   ├── ARCHITECTURE_AGENT.md      # Diese Datei
│   ├── architecture_config.yaml   # Spezifische Einstellungen
│   └── discovery_patterns.json    # Was soll entdeckt werden?
```

### `discovery_patterns.json`
```json
{
  "code_patterns": {
    "todos": ["TODO", "FIXME", "XXX"],
    "bugs": ["BUG", "HACK"],
    "deprecated": ["deprecated", "obsolete"]
  },
  "file_patterns": {
    "python": ["*.py"],
    "javascript": ["*.js", "*.ts", "*.jsx", "*.tsx"],
    "sql": ["*.sql"],
    "markdown": ["*.md"]
  },
  "ignore_patterns": [
    "node_modules/**",
    "venv/**",
    ".git/**",
    "dist/**",
    "build/**"
  ],
  "priority_keywords": {
    "critical": ["SECURITY", "URGENT", "CRITICAL", "SQL_INJECTION"],
    "high": ["BUG", "FAILING", "REGRESSION"],
    "medium": ["TODO", "FIXME"],
    "low": ["NICE_TO_HAVE", "OPTIMIZATION"]
  }
}
```

---

## 📈 Metriken & Monitoring

Der Architecture Agent tracked:

| Metrik | Beschreibung |
|--------|---|
| `tasks_discovered_per_hour` | Wie viele neue Tasks gefunden? |
| `tasks_completed_per_hour` | Wie viele Tasks geschlossen? |
| `average_task_duration` | Durchschnittliche Bearbeitungszeit |
| `conflict_rate` | % Tasks mit Konflikten |
| `agent_efficiency` | % erfolgreiche Completions |
| `project_health_score` | 0-100 (je höher, desto besser) |

Logs → `/home/shares/beermann/logs/architecture_agent.log`

---

## 🚨 Troubleshooting

### Problem: Agent findet keine Tasks
**Lösung:**
```bash
# Check Git Status
cd /home/shares/beermann/PROJECTS/BCN && git status

# Manual Task Scan
grep -r "TODO\|FIXME" --include="*.py" .

# Check Log
tail -50 /home/shares/beermann/logs/architecture_agent.log
```

### Problem: Zu viele Low-Priority Tasks
**Lösung:**
- Edit `discovery_patterns.json`
- Reduziere TODOs von "medium" zu "low"
- Oder ignoriere bestimmte Patterns

### Problem: Konflikte zwischen Agenten
**Lösung:**
- Architecture Agent erkennt es → verzögert eine Task
- Oder assignt Tasks an verschiedene Time-Slots
- Check: `/home/shares/beermann/logs/conflicts.log`

---

## 🎓 Learnings & Best Practices

1. **Agent braucht gute Git Commits** — ohne saubere History kann er Dependencies nicht erkennen
2. **TODOs sollten beschreibend sein** — `TODO: Fix login` ist besser als `TODO: fix`
3. **Regular Dependency Updates** — alte Libraries werden flagged
4. **Clear Project Structure** — Backend/Frontend/Database sollten trenbar sein

---

## 📝 Beispiel-Session

```
10:00 — Architecture Agent startet
  ├─ Scannt 10 Projekte
  ├─ Findet 47 Tasks
  ├─ Priorisiert
  └─ Verteilt auf Agenten

10:01-10:09 — Agenten arbeiten
  ├─ Backend Agent: 3 Tasks
  ├─ Frontend Agent: 2 Tasks
  ├─ Database Agent: 1 Task
  └─ Feature Agent: continuous

10:00 — Nächste Iteration
```

---

**Status:** ✅ Live & Running  
**Letzte Update:** 2026-03-10  
**Nächster Review:** 2026-03-17
