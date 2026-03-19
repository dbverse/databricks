# Lakeflow Connect → Staging Pipeline: Commit Version as Bookmark

## Overview

This architecture implements an incremental data ingestion pipeline inside Databricks using **Delta Lake's commit version** as a watermark (bookmark) to track ingestion progress. It avoids full table scans on every run and enables reliable, idempotent CDC (Change Data Capture) processing.

---

## Architecture Layers

### Layer 1 — Lakeflow Connect (Gateway Table)

Lakeflow Connect is Databricks' managed ingestion layer. It connects to external sources (databases, SaaS apps, files) and continuously writes incoming records into a **Delta gateway table (databricks streaming table)** using continuous compute.

**Key artifact: `_commit_version`**

Every write to a Delta table generates a monotonically increasing integer version number stored in the Delta transaction log. This version is:

- Strictly ordered — version 43 always comes after version 42
- Unique — no two transactions share the same version
- Immutable — versions are never reassigned or reused

This makes the commit version a reliable ingestion clock, free from the clock skew and duplicates that plague timestamp-based watermarking.

```
External Source
      │
      ▼
Lakeflow Connect (continuous compute)
      │
      ▼
Gateway Table (Delta - Databricks Streaming Table)
  └── _commit_version: 1, 2, 3, 4 ...  ← transaction log
```

---

### Layer 2 — Staging Table with CDF + Custom Watermark

The staging table is a CDF-enabled Delta table that receives upserted records from the gateway table. A custom column — `stage_commit_version` — is stamped on each row during the merge to record which gateway version that row came from.

**Why `stage_commit_version` instead of using CDF's built-in version directly?**

CDF's `_commit_version` lives in the feed metadata, not in the actual table rows. By materialising it as a real column:

- The watermark is **queryable** — `SELECT MAX(stage_commit_version) FROM staging`
- The watermark is **durable** — it survives CDF feed rebuilds or log expiry
- The watermark is **portable** — visible to any tool that can query the table

**CDF on the staging table** means downstream consumers (gold layer, feature store, reporting) can apply the same incremental pattern against staging, creating a chain of efficient CDC processing across layers.

```
Gateway Table (_commit_version: N)
      │
      │  Read versions > MAX(stage_commit_version)
      ▼
Staging Table (Delta, CDF enabled)
  ├── business columns ...
  └── stage_commit_version: N  ← custom watermark column
```

---

### Layer 3 — Databricks Job (Orchestrator)

The Databricks Job is the pipeline brain. On each run it executes the following steps:

1. **Read watermark** — `SELECT MAX(stage_commit_version) FROM staging` → returns last processed gateway version `N`
2. **Compute delta** — query gateway table for all versions between `N+1` and `current_version`
3. **Merge / upsert** — apply the delta records into the staging table (INSERT new rows, UPDATE changed rows)
4. **Advance watermark** — the `stage_commit_version` values written during the merge automatically become the new watermark for the next run

```
Databricks Job
  ├── Step 1: READ  MAX(stage_commit_version) from staging → N
  ├── Step 2: QUERY gateway WHERE _commit_version BETWEEN N+1 AND current
  ├── Step 3: MERGE INTO staging (upsert)
  └── Step 4: watermark advances automatically (stage_commit_version stamped on merged rows)
```

---

## Full Pipeline Flow

```
External Source
      │
      ▼
[Lakeflow Connect — continuous compute]
      │  writes continuously
      ▼
Gateway Table (Delta)
  _commit_version: 1 → 2 → 3 → ... → N+5
                                          │
            ┌─────────────────────────────┘
            │  Databricks Job reads versions > N
            ▼
Staging Table (Delta, CDF enabled)
  stage_commit_version: ... → N → N+1 → N+2 → N+3 → N+4 → N+5
            │
            │  CDF feed available for downstream
            ▼
    Downstream consumers
    (Gold layer, BI, ML feature store)
```

---

## Idempotency

Because the watermark is stored **inside the data itself** (as `stage_commit_version` on each row), the pipeline is naturally idempotent:

- If a job run fails mid-way, `MAX(stage_commit_version)` reflects only what was fully committed
- On retry, the job reads the same watermark and processes the same version range
- Re-running produces the same result with no duplicates or gaps

No external state store, checkpoint file, or job metadata table is required.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Delta commit version as watermark | Strictly ordered, no clock skew, no duplicates |
| Custom `stage_commit_version` column | Makes watermark queryable, durable, and portable |
| CDF on staging table | Enables incremental reads by all downstream consumers |
| Watermark in the data, not job state | Idempotency without external state management |
| Continuous compute on gateway | Near-real-time ingestion from source |

---

## Considerations

**Continuous compute cost**
If source change frequency is low, evaluate whether triggered/scheduled mode on the gateway table is more cost-efficient than always-on continuous compute.

**Watermark reset**
If the staging table is truncated or rebuilt, `MAX(stage_commit_version)` returns NULL. The job should handle this by falling back to version 0 (full load) on a NULL watermark.

**CDF log retention**
Both the gateway and staging tables generate CDF logs. Set `delta.logRetentionDuration` appropriately so the job can always find the version range it needs — especially important if the job runs infrequently.

**Schema evolution**
If the gateway table schema changes (new columns, renamed columns), the merge logic and `stage_commit_version` stamping are unaffected, but the staging table schema and downstream consumers may need updating.
