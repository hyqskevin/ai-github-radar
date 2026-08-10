# A3 数据库设计 — ai-github-radar

> 阶段一用 SQLite 单文件存储。所有表见 SPEC.md §6。

## 文件位置

- 默认：`./data/radar.db`
- 环境变量覆盖：`RADAR_DB_PATH`

## ORM

- SQLAlchemy 2.0（同步即可，阶段一无高并发）
- Alembic 做 schema 迁移（首版用 `Base.metadata.create_all()` 即可，schema 稳定后切 alembic）

## 表 DDL

### `stars`

存已 star 仓库的快照。**只读**，每次 init 时全量刷新。

```sql
CREATE TABLE stars (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id      INTEGER UNIQUE NOT NULL,    -- GitHub repo id
  owner        TEXT NOT NULL,
  name         TEXT NOT NULL,
  full_name    TEXT NOT NULL,              -- owner/name
  description  TEXT,
  language     TEXT,
  topics       TEXT,                       -- JSON array string
  homepage     TEXT,
  stargazers_count INTEGER,
  pushed_at    TEXT,                       -- ISO 8601
  starred_at   TEXT,                       -- ISO 8601 (从 /user/starred 拿)
  fetched_at   TEXT NOT NULL,              -- ISO 8601 (本地拉取时间)
  archived     INTEGER DEFAULT 0           -- 0/1
);

CREATE INDEX idx_stars_lang ON stars(language);
CREATE INDEX idx_stars_fetched ON stars(fetched_at);
```

### `keywords`

关键字订阅表。`source` 区分自动 / 手动。

```sql
CREATE TABLE keywords (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  term        TEXT UNIQUE NOT NULL,        -- "agent" / "claude code" / "MCP"
  weight      REAL DEFAULT 1.0,            -- 匹配权重，> 1 优先
  source      TEXT NOT NULL,               -- "auto" | "manual"
  enabled     INTEGER DEFAULT 1,           -- 0/1
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

CREATE INDEX idx_keywords_enabled ON keywords(enabled);
```

### `trending_snapshots`

trending 历史。每条 trending 仓库一条。

```sql
CREATE TABLE trending_snapshots (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id       INTEGER NOT NULL,
  snapshot_date TEXT NOT NULL,             -- YYYY-MM-DD
  rank          INTEGER NOT NULL,          -- trending 当日排名
  stars_today   INTEGER,                   -- 当日新增 star
  language      TEXT,
  description   TEXT,
  fetched_at    TEXT NOT NULL,
  UNIQUE(repo_id, snapshot_date)
);

CREATE INDEX idx_trending_date ON trending_snapshots(snapshot_date);
```

### `recommendations`

已推送的推荐记录。`pushed_at` 用于去重（同一 repo 7 天内不重复推）。

```sql
CREATE TABLE recommendations (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id         INTEGER NOT NULL,
  score           REAL NOT NULL,           -- 匹配分数 0-10
  matched_keywords TEXT,                   -- JSON array string
  channel         TEXT NOT NULL,           -- "local" | "feishu" | "email"
  pushed_at       TEXT NOT NULL,
  UNIQUE(repo_id, pushed_at)
);

CREATE INDEX idx_rec_pushed ON recommendations(pushed_at);
CREATE INDEX idx_rec_repo ON recommendations(repo_id);
```

## 数据生命周期

| 表 | 写入时机 | 保留策略 |
|---|---|---|
| `stars` | init 时全量刷 | 永远（snapshot） |
| `keywords` | init 时 upsert，keyword add/del/toggle 立即生效 | 永远 |
| `trending_snapshots` | scan 时新增 | 保留 90 天 |
| `recommendations` | scan push 时新增 | 保留 365 天 |

定期清理：`scan --cleanup` 可加 `--cleanup-older-than 90d` 删旧 trending。

## 测试覆盖

- [ ] `tests/db/test_models.py` — 建表 + 4 张表的 CRUD + 唯一约束
- [ ] `tests/db/test_migrations.py` — Alembic 升降级
- [ ] `tests/db/test_lifecycle.py` — 清理任务不误删用户 keyword