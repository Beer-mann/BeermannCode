# 🤖 Model Routing & Operations

**Detaillierte Model-Zuordnung für alle 7 Agenten mit Zielzuständen & Operationen**

---

## 📋 Übersicht

Jeder Agent hat eine **Modell-Hierarchie** mit klaren **Zielzuständen** (Target States):

```
Agent
  ├─ Primary Model (Preferred)
  │   └─ Target State: Success Criteria
  ├─ Secondary Model (Fallback 1)
  │   └─ Target State: Success Criteria
  └─ Tertiary Model (Fallback 2)
      └─ Target State: Success Criteria
```

---

## 🎯 Agents & Their Model Operations

### 0️⃣ TASK CREATOR AGENT

**Purpose:** Systematischer TODO/Issue Generator

| Modell | Typ | Zielzustand | Operationen |
|--------|-----|-------------|-------------|
| **Ollama: mistral** | Primary | ✅ Scan alle Projekte, Find alle Gaps | `aider --model ollama:mistral "Scan und erstelle TODOs"` |
| **Claude Haiku** | Secondary | ✅ Falls Ollama timeout | `aider --model claude-haiku "Scan komplexe Gaps"` |
| **Codex (gpt-5.2)** | Tertiary | ✅ Critical Security Issues | `aider --model codex "Security-Scan"` |

**Zielzustand (Target State):**
```json
{
  "status": "complete",
  "tasks_created": ">= 5",
  "critical_issues": "all_found",
  "execution_time": "<= 300s",
  "success_rate": ">= 80%"
}
```

**Operation Flow:**
```
Start
  ↓
Try Ollama (mistral) → 5 Min timeout
  ├─ Success → Mark done, save results
  └─ Timeout/Fail → Fallback to Claude Haiku
       ↓
       Try Claude Haiku → 10 Min timeout
         ├─ Success → Mark done
         └─ Timeout/Fail → Fallback to Codex (Critical only)
              ↓
              Try Codex (Security scan only)
              ├─ Success → Mark critical issues
              └─ Timeout → Log error, continue
```

---

### 1️⃣ ARCHITECTURE AGENT

**Purpose:** Discovery & Prioritization

| Modell | Typ | Zielzustand | Operationen |
|--------|-----|-------------|-------------|
| **Claude Code** | Primary | ✅ Prioritize all tasks | `aider --model claude "Analyze & prioritize"` |
| **Codex (gpt-5.2)** | Secondary | ✅ Falls Claude busy | `aider --model codex "Quick prioritization"` |
| **Ollama: mistral** | Tertiary | ✅ Load not critical | `aider --model ollama:mistral "Basic sorting"` |

**Zielzustand:**
```json
{
  "status": "complete",
  "tasks_analyzed": ">= 10",
  "priorities_assigned": "100%",
  "conflicts_detected": "all",
  "execution_time": "<= 600s",
  "success_rate": ">= 95%"
}
```

**Operation Flow:**
```
Start
  ↓
Try Claude Code → 10 Min timeout
  ├─ Success → Full analysis + prioritization
  └─ Timeout/Fail → Fallback to Codex
       ↓
       Try Codex → 8 Min timeout
         ├─ Success → Quick prioritization
         └─ Timeout/Fail → Fallback to Ollama
              ↓
              Try Ollama → Basic sorting
```

---

### 2️⃣ BACKEND AGENT

**Purpose:** Code Implementation (APIs, Services)

| Modell | Typ | Zielzustand | Operationen |
|--------|-----|-------------|-------------|
| **Claude Code** | Primary | ✅ Complex logic, Design | `aider --model claude "Implement backend feature"` |
| **Codex (gpt-5.2-codex)** | Secondary | ✅ Standard CRUD, APIs | `aider --model codex "Generate CRUD code"` |
| **GitHub Copilot** | Tertiary | ✅ Boilerplate, Tests | `aider --model copilot "Generate tests"` |
| **Ollama: codeqwen** | Quaternary | ✅ Docstrings only | `aider --model ollama:codeqwen "Add docstrings"` |

**Zielzustand:**
```json
{
  "status": "complete",
  "code_quality": ">= 90",
  "test_coverage": ">= 80%",
  "docstrings": "100%",
  "execution_time": "<= 1800s",
  "success_rate": ">= 85%",
  "security_issues": "0"
}
```

**Operation Flow:**
```
Task: "Implement user authentication API"
  ↓
Complex logic? → YES
  ↓
Try Claude Code → 30 Min timeout
  ├─ Success → Full implementation with tests & docs
  └─ Timeout/Fail → Fallback to Codex
       ↓
       Try Codex → 15 Min timeout
         ├─ Success → API implementation
         └─ Timeout/Fail → Fallback to Copilot
              ↓
              Try GitHub Copilot → 10 Min
                ├─ Success → Boilerplate + tests
                └─ Timeout/Fail → Use Ollama for docstrings only
```

**Model Selection by Task Type:**
```
Task: "Write docstring for function X"
  → Ollama (codeqwen) — Schnell, kostenlos

Task: "Write unit tests for module Y"
  → GitHub Copilot — Gut für Tests, kostengünstig

Task: "Generate REST API endpoint /users/:id"
  → Codex (gpt-5.2-codex) — CRUD-spezialisiert

Task: "Refactor payment processing service"
  → Claude Code — Komplex, strategisch
```

---

### 3️⃣ FRONTEND AGENT

**Purpose:** UI/Component Implementation

| Modell | Typ | Zielzustand | Operationen |
|--------|-----|-------------|-------------|
| **Claude Code** | Primary | ✅ Component design, A11y | `aider --model claude "Design component"` |
| **GitHub Copilot** | Secondary | ✅ Component boilerplate | `aider --model copilot "Generate component"` |
| **Codex (gpt-5.2)** | Tertiary | ✅ Styling, CSS | `aider --model codex "Style component"` |
| **Ollama: mistral** | Quaternary | ✅ JSDoc only | `aider --model ollama:mistral "Add docs"` |

**Zielzustand:**
```json
{
  "status": "complete",
  "accessibility": "WCAG AA",
  "test_coverage": ">= 80%",
  "responsive": true,
  "performance": "Lighthouse >= 85",
  "execution_time": "<= 1800s",
  "success_rate": ">= 85%"
}
```

**Operation Flow:**
```
Task: "Create UserProfileCard component"
  ↓
Try Claude Code → 30 Min (Design + A11y)
  ├─ Success → Full component with tests & accessibility
  └─ Fail → Try GitHub Copilot
       ↓
       Try Copilot → 15 Min (Boilerplate)
         ├─ Success → Basic component structure
         └─ Fail → Try Codex for styling
              ↓
              Try Codex → 10 Min (CSS/Tailwind)
              └─ Fallback to Ollama for JSDoc
```

---

### 4️⃣ DATABASE AGENT

**Purpose:** Schema, Migrations, Optimization

| Modell | Typ | Zielzustand | Operationen |
|--------|-----|-------------|-------------|
| **Claude Code** | Primary | ✅ Complex migrations, Schema design | `aider --model claude "Design migration"` |
| **Codex (gpt-5.2-codex)** | Secondary | ✅ SQL queries, Indexes | `aider --model codex "Generate SQL"` |
| **Ollama: mistral** | Tertiary | ✅ Simple migrations, Comments | `aider --model ollama:mistral "Add comments"` |

**Zielzustand:**
```json
{
  "status": "complete",
  "migration_valid": true,
  "zero_downtime": true,
  "performance_impact": "analyzed",
  "rollback_plan": "documented",
  "execution_time": "<= 1200s",
  "success_rate": ">= 95%"
}
```

**Operation Flow:**
```
Task: "Add user_preferences table with migration"
  ↓
Try Claude Code → 20 Min (Full design + zero-downtime)
  ├─ Success → Complete migration with rollback
  └─ Timeout/Fail → Try Codex
       ↓
       Try Codex → 10 Min (SQL generation)
         ├─ Success → SQL queries + indexes
         └─ Fail → Ollama for basic migration
```

---

### 5️⃣ FEATURE AGENT

**Purpose:** Strategic Features & Ideas

| Modell | Typ | Zielzustand | Operationen |
|--------|-----|-------------|-------------|
| **Claude Code** | Primary | ✅ Strategic analysis, Architecture | `aider --model claude "Analyze feature opportunity"` |
| **Codex (gpt-5.2)** | Secondary | ✅ Quick feature sketches | `aider --model codex "Sketch feature idea"` |

**Zielzustand:**
```json
{
  "status": "complete",
  "ideas_generated": ">= 5",
  "roi_calculated": "100%",
  "architecture_impact": "analyzed",
  "execution_time": "<= 3600s",
  "success_rate": ">= 90%"
}
```

**Operation Flow:**
```
Continuous scanning
  ↓
Try Claude Code → Analyze architecture, identify opportunities
  ├─ Success → Strategic ideas with ROI + effort estimates
  └─ Busy/Timeout → Try Codex for quick sketches
```

---

### 6️⃣ REVIEW AGENT

**Purpose:** Quality Validation & Approval  
**Config Source:** `agents/REVIEW_AGENT.md` (MD-File basiert — nicht "Claude M.D.")

| Modell | Typ | Zielzustand | Operationen |
|--------|-----|-------------|-------------|
| **Claude Code** | Primary | ✅ Comprehensive review per REVIEW_AGENT.md | `claude "Review per agents/REVIEW_AGENT.md rules"` |
| **Codex** | Secondary | ✅ Basic quality checks | `codex "Quick QA checks"` |

**Zielzustand:**
```json
{
  "status": "approved|rejected",
  "code_quality": ">= 90",
  "test_coverage": ">= 80%",
  "security_ok": true,
  "performance_ok": true,
  "issue_resolved": true,
  "execution_time": "<= 900s"
}
```

**Operation Flow:**
```
PR created by Implementation Agent
  ↓
Load rules from agents/REVIEW_AGENT.md
  ↓
Try Claude Code CLI
  └─ claude "Review gegen Checklist aus REVIEW_AGENT.md"
  ├─ Approved ✅ → Auto-merge to main
  ├─ Rejected ❌ → Send feedback to Implementation Agent
  └─ Timeout → Fallback to Codex
       ↓
       Try Codex CLI
       └─ codex "Quick QA"
```

---

## 🔧 Configuration File: `model_routing.json`

```json
{
  "version": "1.0",
  "agents": {
    "task_creator": {
      "primary": {
        "model": "ollama:mistral",
        "timeout_sec": 300,
        "target_state": {
          "tasks_created_min": 5,
          "execution_time_max": 300,
          "success_rate_min": 0.8
        }
      },
      "secondary": {
        "model": "claude-haiku",
        "timeout_sec": 600,
        "target_state": {
          "tasks_created_min": 3,
          "execution_time_max": 600,
          "success_rate_min": 0.8
        }
      },
      "tertiary": {
        "model": "codex:gpt-5.2-codex",
        "timeout_sec": 600,
        "target_state": {
          "critical_issues_found": true,
          "execution_time_max": 600
        }
      }
    },
    
    "backend": {
      "primary": {
        "model": "claude-code",
        "timeout_sec": 1800,
        "target_state": {
          "code_quality_min": 90,
          "coverage_min": 0.8,
          "security_issues": 0,
          "success_rate_min": 0.85
        }
      },
      "secondary": {
        "model": "codex:gpt-5.2-codex",
        "timeout_sec": 900,
        "target_state": {
          "code_quality_min": 80,
          "coverage_min": 0.75,
          "success_rate_min": 0.8
        }
      },
      "tertiary": {
        "model": "github-copilot",
        "timeout_sec": 600,
        "target_state": {
          "boilerplate_generated": true,
          "tests_generated": true
        }
      },
      "quaternary": {
        "model": "ollama:codeqwen",
        "timeout_sec": 300,
        "target_state": {
          "docstrings_complete": true
        }
      }
    },
    
    "frontend": {
      "primary": {
        "model": "claude-code",
        "timeout_sec": 1800,
        "target_state": {
          "accessibility": "WCAG AA",
          "coverage_min": 0.8,
          "responsive": true,
          "lighthouse_min": 85
        }
      },
      "secondary": {
        "model": "github-copilot",
        "timeout_sec": 900,
        "target_state": {
          "component_generated": true,
          "tests_generated": true
        }
      },
      "tertiary": {
        "model": "codex:gpt-5.2-codex",
        "timeout_sec": 600,
        "target_state": {
          "styling_complete": true
        }
      },
      "quaternary": {
        "model": "ollama:mistral",
        "timeout_sec": 300,
        "target_state": {
          "jsdoc_complete": true
        }
      }
    },

    "database": {
      "primary": {
        "model": "claude-code",
        "timeout_sec": 1200,
        "target_state": {
          "migration_valid": true,
          "zero_downtime": true,
          "rollback_planned": true,
          "success_rate_min": 0.95
        }
      },
      "secondary": {
        "model": "codex:gpt-5.2-codex",
        "timeout_sec": 600,
        "target_state": {
          "sql_valid": true,
          "indexes_analyzed": true
        }
      },
      "tertiary": {
        "model": "ollama:mistral",
        "timeout_sec": 300,
        "target_state": {
          "migration_basic": true,
          "comments_added": true
        }
      }
    },

    "feature": {
      "primary": {
        "model": "claude-code",
        "timeout_sec": 3600,
        "target_state": {
          "ideas_generated_min": 5,
          "roi_calculated": true,
          "architecture_analyzed": true
        }
      },
      "secondary": {
        "model": "codex:gpt-5.2-codex",
        "timeout_sec": 1800,
        "target_state": {
          "ideas_generated_min": 3,
          "quick_sketches": true
        }
      }
    },

    "review": {
      "primary": {
        "model": "claude-m5",
        "timeout_sec": 900,
        "target_state": {
          "comprehensive_review": true,
          "approval_decision": "approve|reject",
          "all_checks_passed": true
        }
      },
      "secondary": {
        "model": "claude-code",
        "timeout_sec": 600,
        "target_state": {
          "code_quality_min": 80,
          "tests_passed": true
        }
      },
      "tertiary": {
        "model": "codex:gpt-5.2-codex",
        "timeout_sec": 600,
        "target_state": {
          "basic_qa_done": true
        }
      }
    }
  },

  "fallback_strategy": {
    "on_timeout": "next_model",
    "on_error": "next_model",
    "max_retries_per_model": 1,
    "max_total_retries": 3,
    "log_failures": true
  },

  "model_info": {
    "ollama": {
      "url": "http://192.168.0.213:11434",
      "cost": "free",
      "speed": "medium",
      "quality": "medium",
      "available_24_7": true
    },
    "claude-code": {
      "provider": "anthropic",
      "cost": "medium",
      "speed": "medium",
      "quality": "high",
      "available_24_7": true
    },
    "claude-haiku": {
      "provider": "anthropic",
      "cost": "low",
      "speed": "fast",
      "quality": "medium",
      "available_24_7": true
    },
    "claude-m5": {
      "provider": "anthropic",
      "cost": "high",
      "speed": "medium",
      "quality": "very_high",
      "available_24_7": true,
      "note": "For Review Agent only (später)"
    },
    "codex": {
      "provider": "openai",
      "model": "gpt-5.2-codex",
      "cost": "low",
      "speed": "fast",
      "quality": "high",
      "available_24_7": true
    },
    "github-copilot": {
      "provider": "github",
      "cost": "low",
      "speed": "medium",
      "quality": "medium",
      "available_24_7": true
    }
  }
}
```

---

## 🚀 Usage in Orchestrator

```python
# Load routing config
routing = json.load(open("agents/model_routing.json"))

# For each agent
agent_routing = routing["agents"]["backend"]

# Try models in order
for priority in ["primary", "secondary", "tertiary", "quaternary"]:
    model_config = agent_routing.get(priority)
    if not model_config:
        continue
    
    model = model_config["model"]
    timeout = model_config["timeout_sec"]
    target_state = model_config["target_state"]
    
    # Determine which CLI to use
    if "ollama" in model:
        # Use AIDER for local Ollama models
        cmd = f"aider --model {model} --ask '{task}'"
        result = subprocess.run(cmd, timeout=timeout)
    
    elif "claude" in model:
        # Use Claude CLI
        cmd = f"claude '{task}'"
        result = subprocess.run(cmd, timeout=timeout)
    
    elif "codex" in model:
        # Use Codex CLI
        cmd = f"codex exec '{task}'"
        result = subprocess.run(cmd, timeout=timeout)
    
    elif "copilot" in model:
        # Use GitHub Copilot CLI
        cmd = f"gh copilot suggest '{task}'"
        result = subprocess.run(cmd, timeout=timeout)
    
    # Check target state
    if check_target_state(result, target_state):
        return result  # Success!
    else:
        continue  # Try next model
```

**CLI Mapping:**
- **Ollama** → `aider --model ollama:mistral`
- **Claude** → `claude` (CLI)
- **Codex** → `codex exec` (CLI)
- **Copilot** → `gh copilot suggest` (CLI)

---

**Status:** ✅ Dokumentiert & Ready  
**Implementierung:** Orchestrator umbauen auf Model-Routing  
**Letzte Update:** 2026-03-10
