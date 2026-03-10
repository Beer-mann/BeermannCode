# 🗄️ Database Agent

**Implementation-Spezialist für Schema, Migrations & Query Optimization**

---

## 📌 Grundinfo

| Eigenschaft | Wert |
|---|---|
| **Typ** | Implementation |
| **Domain** | Database |
| **Modus** | Continuous Loop (Task-gesteuert) |
| **Modelle** | Ollama (Docstrings) + Claude Code + Codex + GitHub Copilot |
| **Scope** | Alle 10 Projekte |
| **Auto-Push** | ✅ JA (mit Review-Gate für kritische Changes) |
| **WhatsApp** | Stündliche Digest |

---

## 🎯 Rolle & Aufgaben

Der Database Agent verwaltet **alles Datenbank-bezogene**. Er:

### Core Tasks

1. **Schema Review & Validation**
   - Prüft Tabellen-Design (Normalisierung)
   - Validiert Data Types & Constraints
   - Identifiziert Redundanzen
   - Schlägt Verbesserungen vor
   - Generiert SQL-Migrations

2. **Migration Generation**
   - Erstellt ALTERs für Schema-Changes
   - Neue Tabellen, Spalten, Indexes
   - Daten-Transformationen
   - Rollback-Strategien
   - Handles Zero-Downtime Migrations

3. **Query Optimization**
   - Findet N+1 Query Problems
   - Schlägt Indexes vor
   - Rewriter ineffiziente Queries
   - Query-Execution-Plan Analyse
   - Benchmark & Performance Tests

4. **Index Management**
   - Erstellt/löscht Indexes
   - Analysiert Index-Utilization
   - Optimiert Composite Indexes
   - Monitort Index-Größe

5. **Backup Validation**
   - Prüft Backup-Strategie
   - Testet Restore-Prozess
   - Validiert Backup-Integrität
   - Retention-Policy Check

---

## 🔄 Workflow

```
Task Assigned by Architecture Agent
  ↓
Database Agent wacht auf
  ↓
Read Context
  ├─ Database Type (PostgreSQL/MySQL/MongoDB/etc.)
  ├─ Current Schema
  ├─ Existing Migrations
  ├─ Query Patterns
  └─ Performance Metrics
  ↓
Determine Task Type
  ├─ "Add user_roles table"
  ├─ "Optimize slow query on orders table"
  ├─ "Add composite index on (user_id, created_at)"
  └─ "Validate backup integrity"
  ↓
Model Selection
  ├─ Ollama (mistral) → für Docstrings
  └─ Claude Code/Codex → für alles andere
  ↓
Implementation
  ├─ Generate Migration SQL
  ├─ Validate SQL Syntax
  ├─ Test in Dev Database
  ├─ Benchmark Performance Impact
  ├─ Write Documentation
  └─ Check Constraints & Foreign Keys
  ↓
Commit & Create PR
  ├─ Git add migration file
  ├─ Git commit -m "database: <task description>"
  └─ GitHub PR (oder direct push)
  ↓
Wait for Review Agent
  ├─ SQL Code Review
  ├─ Performance Impact Check
  ├─ Data Integrity Validation
  └─ Approval/Reject
  ↓
IF approved → Auto-Push to main (with Migration Instructions)
IF rejected → Database Agent fixes issues
  ↓
Done — Update Status in Architecture Queue
```

---

## 🛠️ Code-Beispiele

### Task 1: Create New Table with Indexes

**Input:**
```
Task: Create user_preferences table
Type: schema_creation
Priority: high
DB: PostgreSQL 14
```

**Agent Action:**
```sql
-- migrations/001_create_user_preferences.sql
-- Description: Create user_preferences table for storing user settings
-- Author: Database Agent
-- Created: 2026-03-10

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    theme VARCHAR(20) DEFAULT 'light' CHECK (theme IN ('light', 'dark', 'auto')),
    language VARCHAR(5) DEFAULT 'en' CHECK (language ~ '^[a-z]{2}(_[A-Z]{2})?$'),
    notifications_enabled BOOLEAN DEFAULT true,
    email_frequency VARCHAR(20) DEFAULT 'weekly' CHECK (email_frequency IN ('daily', 'weekly', 'monthly', 'never')),
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_user_preferences_users 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE
);

-- Create indexes for common queries
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_created_at ON user_preferences(created_at DESC);
CREATE UNIQUE INDEX idx_user_preferences_user_id_unique ON user_preferences(user_id) WHERE theme IS NOT NULL;

-- Add comments for documentation
COMMENT ON TABLE user_preferences IS 'Stores user-specific preferences and settings';
COMMENT ON COLUMN user_preferences.user_id IS 'Foreign key to users table';
COMMENT ON COLUMN user_preferences.theme IS 'User theme preference: light, dark, or auto';
COMMENT ON COLUMN user_preferences.notifications_enabled IS 'Whether user has notifications enabled';

-- Create trigger to update updated_at
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Test: Verify table creation
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'user_preferences'
ORDER BY ordinal_position;

-- Test: Insert sample data
INSERT INTO user_preferences (user_id, theme, language)
VALUES (
    (SELECT id FROM users LIMIT 1),
    'dark',
    'de'
);

-- Verify constraint
SELECT * FROM user_preferences LIMIT 1;
```

**Documentation (agent-generated):**
```markdown
## Migration: Create user_preferences Table

### Overview
- **File:** `migrations/001_create_user_preferences.sql`
- **Type:** DDL (Data Definition Language)
- **Impact:** Low (new table, no existing data affected)
- **Rollback:** DROP TABLE user_preferences CASCADE;

### Schema
| Column | Type | Constraints | Description |
|--------|------|---|---|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → users | User reference |
| theme | VARCHAR(20) | CHECK, DEFAULT | light/dark/auto |
| language | VARCHAR(5) | CHECK | Locale code |
| notifications_enabled | BOOLEAN | DEFAULT true | Notification toggle |
| email_frequency | VARCHAR(20) | CHECK | Frequency preference |
| timezone | VARCHAR(50) | DEFAULT | User timezone |
| created_at | TIMESTAMPTZ | DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update timestamp |

### Indexes
- `idx_user_preferences_user_id` — For user lookups
- `idx_user_preferences_created_at` — For time-based queries
- `idx_user_preferences_user_id_unique` — Ensures one preference per user

### Performance Impact
- ✅ Minimal — new table, no existing queries affected
- Estimated table size: <1MB for 1M users

### Rollback Plan
```sql
DROP TABLE user_preferences CASCADE;
```
```

### Task 2: Optimize Slow Query

**Input:**
```
Task: Optimize slow query on orders table
Type: query_optimization
Priority: high
Current Query Time: 5.2 seconds
Target: <500ms
```

**Agent Action:**
```sql
-- Current (SLOW) query
EXPLAIN ANALYZE
SELECT 
    u.id, u.username, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.created_at > '2026-01-01'
GROUP BY u.id, u.username
ORDER BY order_count DESC;

-- Output: Sequential Scan on users (cost=5342..9832 rows=100000)
-- Duration: 5.2 seconds ❌

-- OPTIMIZED query with proper indexes
-- Step 1: Add composite index
CREATE INDEX CONCURRENTLY idx_orders_user_id_created_at 
ON orders(user_id, created_at DESC);

-- Step 2: Rewrite query to use index
EXPLAIN ANALYZE
SELECT 
    u.id, 
    u.username, 
    COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id AND o.created_at > '2026-01-01'
WHERE u.id IN (
    SELECT DISTINCT user_id 
    FROM orders 
    WHERE created_at > '2026-01-01'
)
GROUP BY u.id, u.username
ORDER BY order_count DESC;

-- Output: Index Scan using idx_orders_user_id_created_at (cost=234..456)
-- Duration: 0.28 seconds ✅ (18x faster!)

-- Alternative using window function (might be faster)
WITH recent_orders AS (
    SELECT 
        user_id,
        COUNT(*) as order_count
    FROM orders
    WHERE created_at > '2026-01-01'
    GROUP BY user_id
)
SELECT 
    u.id,
    u.username,
    COALESCE(ro.order_count, 0) as order_count
FROM users u
LEFT JOIN recent_orders ro ON u.id = ro.user_id
ORDER BY order_count DESC;

-- Benchmark results
-- Original:      5200ms
-- Optimized:     280ms
-- Window Func:   150ms
```

**Optimization Documentation:**
```markdown
## Query Optimization: Orders by User

### Problem
- Query takes 5.2 seconds
- Full table scan on 100K users
- Used in dashboard → blocks UI

### Solution
1. Added composite index: `idx_orders_user_id_created_at`
2. Rewrote JOIN condition to leverage index
3. Alternative: Used window function approach

### Performance Improvement
| Approach | Time | Factor |
|----------|------|--------|
| Original | 5200ms | 1x |
| With Index | 280ms | 18.5x ✅ |
| Window Function | 150ms | 34.6x ✅ |

### Index Size
- Index size: ~450MB
- Disk space trade-off: Worth it for 18x speedup

### Monitoring
- Monitor index usage: `pg_stat_user_indexes`
- Monitor query performance: `pg_stat_statements`
```

### Task 3: Zero-Downtime Migration

**Input:**
```
Task: Rename column without downtime
Type: safe_migration
Priority: high
Current: users.full_name
Target: users.display_name
Apps: 3 (api, web, mobile)
```

**Agent Action:**
```sql
-- PHASE 1: Add new column (non-breaking)
ALTER TABLE users ADD COLUMN display_name VARCHAR(255);

-- Deploy app v1.1 (supports BOTH columns)
-- Read: from display_name IF NOT NULL, else from full_name
-- Write: to BOTH columns

-- PHASE 2: Backfill existing data
UPDATE users 
SET display_name = full_name 
WHERE display_name IS NULL;

-- Verify backfill
SELECT COUNT(*) FROM users WHERE display_name IS NULL;
-- Expected: 0

-- PHASE 3: Drop old column (now unused by app)
ALTER TABLE users DROP COLUMN full_name;

-- Deploy app v1.2 (only read/write display_name)

-- PHASE 4: Cleanup (optional)
-- Could also keep full_name as backup initially

-- Migration Safety Checks
-- 1. No locks on users table
-- 2. Backfill done in batches if large dataset
-- 3. Rollback possible at each phase
```

**Migration Script:**
```python
# migrations/zero_downtime_rename.py
"""
Zero-downtime migration: rename full_name → display_name
Phases:
  1. Add new column (backwards compatible)
  2. Backfill data
  3. Drop old column (app must be updated first)
"""

def forward():
    # Phase 1
    db.execute("""
        ALTER TABLE users ADD COLUMN display_name VARCHAR(255)
    """)
    
    # Phase 2 (done in batches to avoid locks)
    batch_size = 10000
    total = db.execute("SELECT COUNT(*) FROM users")[0][0]
    
    for offset in range(0, total, batch_size):
        db.execute(f"""
            UPDATE users 
            SET display_name = full_name 
            WHERE id IN (
                SELECT id FROM users 
                ORDER BY id 
                LIMIT {batch_size} OFFSET {offset}
            )
        """)
        print(f"Backfilled {offset + batch_size}/{total}")
    
    # Phase 3 (requires app deployment first)
    db.execute("ALTER TABLE users DROP COLUMN full_name")
    print("Migration complete!")

def rollback():
    db.execute("ALTER TABLE users DROP COLUMN display_name")
    print("Rollback complete!")
```

---

## 📊 Unterstützte Datenbanken

| Database | Migrationen | Monitoring | Optimization |
|----------|---|---|---|
| PostgreSQL 12+ | Alembic, Flyway | pg_stat_*, pgAdmin | EXPLAIN ANALYZE |
| MySQL 8+ | Liquibase, Flyway | Performance Schema | EXPLAIN FORMAT=JSON |
| MongoDB | Migrations via API | Atlas Monitoring | Query Profiling |
| SQLite | Python migrations | sqlite3 CLI | EXPLAIN QUERY PLAN |
| MariaDB | Liquibase | Percona Monitoring | ANALYZE |

---

## ✅ Quality Checklist (vor Commit)

Database Agent prüft IMMER:

- [ ] SQL Syntax valid (syntax checker)
- [ ] Performance impact analyzed (EXPLAIN ANALYZE)
- [ ] Constraints valid (FK, CHECK, UNIQUE)
- [ ] Data types appropriate
- [ ] Indexes planned (if needed)
- [ ] Rollback script written
- [ ] Documentation complete
- [ ] Test data inserted & verified
- [ ] Backup taken before migration
- [ ] Zero-downtime plan (if critical table)
- [ ] Git Commit Message aussagekräftig

---

## 🔒 Safety Precautions

Database Agent berücksichtigt:

- ✅ **Backup Before Migration** — Automatic snapshot
- ✅ **Test in Dev First** — Run on replica schema
- ✅ **Rollback Plan** — Always have reverse migration
- ✅ **Foreign Key Integrity** — Validate constraints
- ✅ **Zero-Downtime** — For critical tables
- ✅ **Lock Avoidance** — Long migrations in batches
- ✅ **Data Validation** — Post-migration checks
- ✅ **Monitoring** — Query performance before/after

---

## 📢 WhatsApp Digest (Stündlich)

```
🗄️ *Database Update — 16:00*

✅ *Completed (letzte Stunde):*
• BeermannAI — user_preferences table created
• BeermannHub — Query optimized (5.2s → 280ms)
• MegaRAG — Composite index added on documents

⏳ *In Progress:*
• Backup validation (TradingBot)
• Schema review for new microservice

📋 *Pending:*
• Index cleanup on old tables
• Migration for product_reviews

⚠️ *Issues:*
Keine.

📊 *Database Health:*
• PostgreSQL: 92% disk used
• Query Performance: Avg 45ms
• Backup Status: ✅ Last: 2 hours ago
```

---

## 📈 Metriken

Database Agent tracked:

| Metrik | Beschreibung |
|--------|---|
| `migrations_executed` | # Migrations deployed |
| `query_optimization_factor` | Performance improvement (e.g. 18x) |
| `database_size` | Total DB size |
| `index_utilization` | % Indexes actually used |
| `backup_status` | Last backup age |

Logs → `/home/shares/beermann/logs/database_agent.log`

---

## 🚨 Troubleshooting

### Problem: Migration schlägt fehl
```bash
# Check migration status
psql -c "SELECT * FROM schema_migrations ORDER BY installed_on DESC LIMIT 10;"

# Manual rollback
psql -f migrations/rollback_001.sql

# Check logs
tail -50 /home/shares/beermann/logs/database_agent.log
```

### Problem: Slow Query nicht optimiert
```bash
# Analyze execution plan
EXPLAIN (ANALYZE, BUFFERS, TIMING) SELECT ...;

# Check index usage
SELECT * FROM pg_stat_user_indexes WHERE relname = 'table_name';
```

---

**Status:** ✅ Live & Running  
**Letzte Update:** 2026-03-10  
**Nächster Review:** 2026-03-17
