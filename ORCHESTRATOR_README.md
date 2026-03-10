# 🦅 BeermannCode Orchestrator v2.0

**24/7 Agent Ecosystem Manager**

---

## Overview

Der neue Orchestrator ist das **Herz** des BeermannCode Systems. Er koordiniert alle 6 Agenten:

```
Architecture Agent (Discovery)
    ↓
Backend/Frontend/Database Agents (Parallel Implementation)
    ↓
Feature Agent (Continuous Proposals)
    ↓
Review Agent (Quality Gate)
    ↓
Auto-Push to Main
    ↓
WhatsApp Summary
```

**Status:** ✅ v2.0 Live  
**Language:** Python 3.9+  
**Agent Spawning:** OpenClaw sub-agents

---

## Quick Start

### 1. Manual Run
```bash
cd /home/shares/beermann/PROJECTS/BeermannCode
python3 orchestrator.py

# Options:
--dry-run              # Simulate without executing
--agent backend        # Run specific agent only
--no-notify            # Disable WhatsApp notifications
--verbose              # Verbose logging
```

### 2. Dry-Run (Test)
```bash
python3 orchestrator.py --dry-run --no-notify
```

### 3. Production Run
```bash
python3 orchestrator.py
# Sends WhatsApp summary, updates task queue, spawns sub-agents
```

---

## How It Works

### Phase 1: Architecture Agent
- **What:** Scans all 10 projects for tasks
- **How:** 
  - Grep for TODOs/FIXMEs
  - Check GitHub Issues
  - Analyze code quality
  - Detect dependencies
- **Output:** 
  - Populates `/home/shares/beermann/tasks/pending.jsonl`
  - WhatsApp: "Discovered X tasks"
- **Timeout:** 10 minutes

### Phase 2: Implementation Agents (Parallel)
```
Backend Agent    ┐
Frontend Agent   ├─ (run in parallel)
Database Agent   ┘
```

Each reads from `pending.jsonl` and:
- Picks up tasks assigned to their domain
- Implements the fix/feature
- Writes tests
- Commits to git
- Updates task status

**Timeout:** 30 minutes per agent

### Phase 3: Feature Agent
- **What:** Runs continuously in background
- **How:** 
  - Analyzes recent code changes
  - Detects code-smells
  - Suggests features
  - Creates TODOs
- **Notification:**
  - ⚡ IMMEDIATE when file changes
  - 📋 HOURLY digest

### Phase 4: Review Agent
- **What:** Validates all implementation
- **How:**
  - Code review (style, security, performance)
  - Test coverage check (>80% required)
  - Issue resolution validation
  - Performance impact analysis
- **Decision:**
  - ✅ APPROVE → Auto-Push to main
  - ❌ REJECT → Send feedback to Implementation Agent
- **Timeout:** 15 minutes

### Phase 5: Auto-Push & Notification
If Review Agent approves:
- ✅ Merge to main branch
- ✅ Send WhatsApp summary
- ✅ Update task status to "done"

---

## Configuration

### agents.json
Located at: `/home/shares/beermann/PROJECTS/BeermannCode/agents.json`

Structure:
```json
{
  "agents": {
    "architecture": { ... },
    "backend": { ... },
    "frontend": { ... },
    "database": { ... },
    "feature": { ... },
    "review": { ... }
  }
}
```

Each agent has:
- `name` — Display name
- `type` — orchestrator, implementation, proposal, quality_gate
- `mode` — continuous_24x7, continuous_loop, reactive
- `model` — Which Claude model to use
- `tasks` — What tasks the agent handles
- `timeout` — How long to run before killing
- `notifications` — WhatsApp settings

### Environment Variables
```bash
# WhatsApp
WHATSAPP_TO="+4917643995085"                    # Target phone
NOTIFY_ENABLED="true"                           # Enable notifications

# Timeouts
AGENT_TIMEOUT_ARCHITECTURE=600                  # 10 min
AGENT_TIMEOUT_IMPLEMENTATION=1800               # 30 min
AGENT_TIMEOUT_REVIEW=900                        # 15 min

# Control
DRY_RUN="false"                                 # Test mode
```

---

## Logs & State

### Logs
Location: `/home/shares/beermann/logs/orchestrator-v2.log`

Example output:
```
[2026-03-10 14:00:00] 🦅 BeermannCode Orchestration Cycle
[2026-03-10 14:00:00] ================================================================================
[2026-03-10 14:00:00] 📋 Step 1: Architecture Agent (Discovery & Prioritization)
[2026-03-10 14:00:00] ----
[2026-03-10 14:00:05] [AGENT] Architecture Agent      | Status: ✅ SUCCESS  | Duration:   5.23s
[2026-03-10 14:00:05] [ARCH] Discovered 12 pending tasks
[2026-03-10 14:00:05] 🔧 Step 2: Implementation Agents (Parallel)
[2026-03-10 14:00:35] [AGENT] Backend Agent           | Status: ✅ SUCCESS  | Duration:  30.15s
[2026-03-10 14:00:42] [AGENT] Frontend Agent          | Status: ✅ SUCCESS  | Duration:  37.22s
[2026-03-10 14:00:28] [AGENT] Database Agent          | Status: ✅ SUCCESS  | Duration:  23.45s
[2026-03-10 14:00:45] ✅ Orchestration cycle completed
```

### State File
Location: `/home/shares/beermann/logs/orchestrator-state.json`

Tracks:
- `last_run` — When orchestrator last ran
- `last_cycle` — Results from last cycle
- `agent_runs` — Status of each agent

---

## Task Queue

### Format
File: `/home/shares/beermann/tasks/pending.jsonl`

Each line = one task (JSON):
```json
{
  "id": "task-uuid",
  "status": "pending|waiting_review|done|failed",
  "type": "bugfix|feature|refactor|docstring",
  "domain": "backend|frontend|database|feature",
  "project": "BeermannAI",
  "title": "Fix SQL Injection in login.py",
  "description": "...",
  "priority": "critical|high|medium|low",
  "assigned_to": "backend_agent",
  "created_at": "2026-03-10T14:00:00Z",
  "completed_at": null,
  "model_used": null
}
```

### Workflow
```
pending
  ↓ (Architecture Agent assigns)
waiting_implementation
  ↓ (Implementation Agent picks up)
in_progress
  ↓ (Implementation Agent completes)
waiting_review
  ↓ (Review Agent approves/rejects)
done ✅ or failed ❌
```

---

## WhatsApp Notifications

### Message Format

**Architecture Agent (Hourly):**
```
🦅 *Architecture Report — 15:00*

📊 *Tasks discovered:*
• Backend: 3 TODOs, 2 failing tests
• Frontend: 1 component fix
• Database: 1 query optimization

⏳ *Pending:*
Critical: 2 | High: 5 | Medium: 8

🚀 *Next:* Fix SQL Injection in BeermannAI
```

**Implementation Agents (Hourly Digest):**
```
🔧 *Backend Update — 16:00*

✅ *Completed:*
• BeermannAI/user_service.py — Fixed SQL Injection
• BeermannAI/payments.py — Added 6 tests

⏳ *In Progress:*
• Database query optimization

📋 *Pending:*
• 3 more TODOs
```

**Feature Agent (Immediate + Hourly):**
```
⚡ *Code Change — 14:23*
📝 BeermannAI/user_service.py changed
💡 Refactoring opportunity: Extract validation logic
```

**Review Agent (Approval):**
```
✅ *Code Review APPROVED*

PR #123 — Fix SQL Injection
🔧 Backend Agent
✅ All checks passed (92% coverage, 0 security issues)
→ Auto-pushing to main
```

---

## Cron Setup (24/7 Automation)

### Option 1: Using OpenClaw Cron

```bash
# View existing crons
openclaw cron list

# Add new crons
openclaw cron new \
  --name "coding-day" \
  --schedule "*/10 6-22 * * *" \
  --command "cd /home/shares/beermann/PROJECTS/BeermannCode && python3 orchestrator.py"

openclaw cron new \
  --name "coding-night" \
  --schedule "*/15 23-5 * * *" \
  --command "cd /home/shares/beermann/PROJECTS/BeermannCode && python3 orchestrator.py --agent feature"
```

### Option 2: Manual Crontab

```bash
crontab -e

# Add lines:
*/10 6-22 * * * cd /home/shares/beermann/PROJECTS/BeermannCode && python3 orchestrator.py >> /tmp/beermanncode-cron.log 2>&1
*/15 23-5 * * * cd /home/shares/beermann/PROJECTS/BeermannCode && python3 orchestrator.py --agent feature >> /tmp/beermanncode-cron.log 2>&1
```

### Schedule Explanation

| Cron | Time | Frequency | Agents |
|------|------|-----------|--------|
| `coding-day` | 06:00-22:00 | Every 10 min | All (Architecture → Implementation) |
| `coding-night` | 23:00-05:00 | Every 15 min | Feature Agent only (low priority) |

---

## Troubleshooting

### Problem: Orchestrator doesn't start
```bash
# Check lock file
ls -la /tmp/beermanncode-orchestrator.lock

# Remove stale lock (if needed)
rm /tmp/beermanncode-orchestrator.lock

# Run with verbose logging
python3 orchestrator.py --verbose
```

### Problem: Tasks not being discovered
```bash
# Check Architecture Agent directly
cd /home/shares/beermann/PROJECTS/BeermannCode
python3 orchestrator.py --agent architecture --verbose

# Check task queue
cat /home/shares/beermann/tasks/pending.jsonl | head -20

# Check for TODOs manually
cd /home/shares/beermann/PROJECTS/BCN
grep -r "TODO\|FIXME" --include="*.py" .
```

### Problem: WhatsApp notifications not sending
```bash
# Check environment
echo $WHATSAPP_TO
echo $NOTIFY_ENABLED

# Test manually
openclaw message send \
  --channel whatsapp \
  --target "+4917643995085" \
  --message "Test message"

# Check logs
tail -50 /home/shares/beermann/logs/orchestrator-v2.log
```

### Problem: Agent timed out
```bash
# Check which agent failed
tail -20 /home/shares/beermann/logs/orchestrator-v2.log | grep TIMEOUT

# Increase timeout
export AGENT_TIMEOUT_IMPLEMENTATION=2400  # 40 min instead of 30

python3 orchestrator.py
```

---

## Advanced Usage

### Run Specific Agent Only
```bash
python3 orchestrator.py --agent backend
# Only runs Backend Agent (useful for testing)
```

### Test Cycle Without Notifications
```bash
python3 orchestrator.py --dry-run --no-notify
# Simulates full cycle without actually spawning agents or sending messages
```

### Monitor in Real-Time
```bash
tail -f /home/shares/beermann/logs/orchestrator-v2.log
# Live monitoring of orchestrator

# Or with colors
tail -f /home/shares/beermann/logs/orchestrator-v2.log | grep --color=always "✅\|❌\|⏱️"
```

### Debug Task Queue
```bash
# View pending tasks
cat /home/shares/beermann/tasks/pending.jsonl | jq '. | select(.status == "pending")'

# View done tasks
cat /home/shares/beermann/tasks/pending.jsonl | jq '. | select(.status == "done")'

# Count by status
cat /home/shares/beermann/tasks/pending.jsonl | jq '.status' | sort | uniq -c
```

---

## Performance Metrics

Orchestrator tracks these metrics in state file:

```json
{
  "last_cycle": {
    "cycle_start": "2026-03-10T14:00:00",
    "cycle_duration": 125.4,
    "tasks_discovered": 12,
    "tasks_completed": 8,
    "tasks_failed": 2,
    "agents_run": {
      "architecture": { "success": true, ... },
      "backend": { "success": true, ... },
      "frontend": { "success": true, ... },
      "database": { "success": true, ... },
      "feature": { "success": true, ... },
      "review": { "success": false, ... }
    }
  }
}
```

---

## Next Steps

1. ✅ Orchestrator v2.0 deployed
2. ⏳ Setup cron jobs (see above)
3. ⏳ Create `review_agent_config.md` (M.D. configuration)
4. ⏳ Test with `--dry-run` first
5. ⏳ Go live! 🚀

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    BeermannCode Orchestrator                │
│                         (Main Loop)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼────┐   ┌────▼────┐   ┌───▼────┐
    │Architecture  │Backend  │   │Feature │
    │   Agent   │  │ Agent   │   │ Agent  │
    └────┬────┘   └────┬────┘   └───┬────┘
         │             │             │
    discovers       implements    proposes
    tasks           code          ideas
         │             │             │
         └─────────┬───┴─────────────┘
                   │
           ┌───────▼────────┐
           │  Frontend Agent│ (parallel with Backend)
           └───────┬────────┘
                   │
           ┌───────▼────────┐
           │ Database Agent │ (parallel with Backend)
           └───────┬────────┘
                   │
                   ▼
           ┌───────────────┐
           │ Review Agent  │ (Quality Gate)
           └───────┬───────┘
                   │
             ✅ Approved?
             /           \
          YES             NO
           │               │
           ▼               ▼
      Auto-Push      Send Feedback
      to main        (back to impl)
           │               │
           └───┬───────────┘
               │
               ▼
        ┌─────────────┐
        │WhatsApp     │
        │Summary      │
        └─────────────┘
```

---

**Status:** ✅ Live  
**Version:** 2.0  
**Last Updated:** 2026-03-10
