# HACKX 4.0 / Vibe-Audit — Project Summary for Gemini

Use this document to understand the project structure, purpose, and current progress when continuing work or reviewing code.

---

## 1. Project Overview

**Name:** HACKX Backend / Vibe-Audit API  
**Purpose:** A **code security and compliance scanning** backend that:

- Accepts **GitHub repository URLs**, clones them in **isolated Docker volumes**, and runs:
  - **Security scanning:** secrets (AWS keys, RSA keys, high-entropy strings), dangerous sinkholes (`eval`, `os.system`), and unknown/hallucinated dependencies
  - **Compliance scanning:** restrictive licenses (GPL/AGPL) and prompt-injection–style patterns
- Assigns a **risk score (0–100)** and **grade (A–F)** from combined findings
- Provides **remediation tips** per finding type
- Exposes a **REST API** (FastAPI) and runs long scans via **Celery** with **Redis**
- Persists **projects**, **scans**, **vulnerabilities**, and **compliance violations** in **PostgreSQL**
- Is deployable to **Google Cloud Run** via **Terraform** and a **distroless Docker** image

**Entry point:** `main.py` at repo root wires the app and global exception handler; the actual FastAPI app lives in `app/main.py` and is what gets run by uvicorn/Docker.

---

## 2. Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Uvicorn |
| DB | PostgreSQL, SQLAlchemy (async via asyncpg), Alembic |
| Queue / cache | Redis, Celery |
| Isolation / ingestion | Docker (alpine/git clone into ephemeral volumes) |
| Config | pydantic-settings, .env |
| Security | slowapi (rate limiting), CORS in `app.core.security` |
| Deployment | Docker (multi-stage, distroless), Terraform (GCP Cloud Run), deploy.sh (pytest → build → terraform) |
| Tests | pytest |

---

## 3. High-Level Architecture

```
User → FastAPI (/api/v1) → Projects CRUD, Trigger Scan
                ↓
        Celery task (scan_codebase)
                ↓
    validate_github_url → Docker clone → security_scanner + compliance_scanner
                ↓
    RiskScorer + remediation tips → Save to DB (Scan, Vulnerability, ComplianceViolation)
                ↓
        Cleanup Docker volume
```

- **API:** Async FastAPI; DB access via `get_db()` and `SessionLocal` (async).
- **Worker:** Synchronous Celery task that runs an async `run_scan()` via `asyncio.run()`.

---

## 4. File Structure (Project Code Only)

Excluding `venv/`, `.terraform/`, and cache dirs:

```
HACKX 4.0 - Copy/
├── main.py                    # Root entry: imports app.main, adds global exception handler, mounts API
├── app/
│   ├── main.py                # FastAPI app: CORS, rate limit, /health, /, mounts api v1 router
│   ├── worker.py              # Celery app + scan_codebase task (ingestion → scanners → scoring → DB → cleanup)
│   ├── core/
│   │   ├── config.py          # Settings (DB, Redis, PROJECT_NAME, API_V1_STR)
│   │   ├── logging.py         # setup_logging()
│   │   ├── security.py       # setup_security(app): CORS, slowapi limiter
│   │   └── validators.py     # validate_github_url() — strict HTTPS GitHub URL regex
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py    # Router that includes projects + scans
│   │       └── endpoints/
│   │           ├── projects.py # POST/GET /projects (create/list)
│   │           └── scans.py   # POST /scans/{project_id}/trigger, GET /scans/{scan_id}
│   ├── domain/
│   │   ├── security_scanner.py # run_security_scan: secrets, AST sinkholes (eval/os.system), hallucinated deps
│   │   ├── compliance_scanner.py # run_compliance_scan: restrictive licenses, prompt-injection keywords
│   │   ├── ast_scanner.py    # run_ast_scan (SinkholeVisitor) — not used by security_scanner (duplicate logic)
│   │   ├── scoring.py       # RiskScorer: calculate_risk_score(findings) → (score, grade)
│   │   └── remediation.py   # get_remediation_tip(title, desc), RemediationEngine.get_fix(title)
│   └── infrastructure/
│       ├── database.py       # Async engine, SessionLocal, get_db
│       ├── models.py         # SQLAlchemy: Project, Scan, ScanStatus, Vulnerability, ComplianceViolation
│       └── ingestion.py      # DockerClientSingleton, ingest_repository(repo_url), cleanup_volume()
├── alembic/
│   ├── env.py                # Alembic env, uses app.infrastructure.models.Base and settings
│   ├── alembic.ini           # (at repo root)
│   └── script.py.mako
├── tests/
│   ├── test_ingestion.py     # Pytest: validate_github_url valid/invalid URL parametrization
│   └── test_infra.py        # Manual-style tests: /health, Celery scan_codebase.delay(999)
├── verify_phase4.py          # Standalone script: RiskScorer + RemediationEngine on mock findings
├── requirements.txt
├── Dockerfile                # Multi-stage: python:3.11-slim → gcr.io/distroless/python3, CMD uvicorn app.main
├── deploy.sh                 # Pytest → CI check → docker build → terraform (commented)
├── main.tf                   # GCP Cloud Run (vibe-audit-api), IAM allUsers invoker
├── models.py                 # (Root — likely legacy/duplicate; app uses app/infrastructure/models.py)
├── worker.py                 # (Root — likely legacy; app uses app/worker.py)
└── mock_vibe_code.py         # (Optional/mock file)
```

---

## 5. Key Components

### 5.1 API (app/api/v1)

- **Projects:** `POST /api/v1/projects/` (name, repository_url), `GET /api/v1/projects/`  
  - Validation: `repository_url` must start with `http://` or `https://` (for stricter GitHub-only validation, ingestion uses `validate_github_url`).
- **Scans:**  
  - `POST /api/v1/scans/{project_id}/trigger` → creates `Scan` (PENDING), enqueues `scan_codebase.delay(scan_id)`, returns `scan_id`.  
  - `GET /api/v1/scans/{scan_id}` → returns scan record (status, score, grade, etc.).

### 5.2 Worker (app/worker.py)

- **Celery:** Broker/backend from `settings.celery_broker_url` (Redis).
- **Task `scan_codebase(scan_id)`:**  
  1. Load Scan + Project; set status INGESTING.  
  2. Validate URL with `validate_github_url`.  
  3. `ingest_repository(repo_url)` → Docker volume + clone (alpine/git), returns `container_id` (volume name) and `local_path`.  
  4. Run `run_security_scan(repo_path)` and `run_compliance_scan(repo_path)`; combine findings.  
  5. `RiskScorer(combined_findings).calculate()` → **bug:** `RiskScorer` has no `calculate()` and takes no constructor args; it exposes `calculate_risk_score(findings)`.  
  6. Persist vulnerabilities and compliance violations; set score/grade, status COMPLETED, finished_at.  
  7. `cleanup_volume(container_id)`.  
  - **Bug:** Log line references `all_vulns` which is undefined; should be `security_vulns` (or similar).

### 5.3 Domain

- **security_scanner:** `run_security_scan(repo_path)` walks repo files; for each file: `detect_secrets`, and for `.py`: `detect_ast_sinkholes`, `detect_hallucinated_dependencies`. Uses a whitelist of safe modules for “unknown dependency” checks.
- **compliance_scanner:** `run_compliance_scan(repo_path)` = `detect_restrictive_licenses` + `detect_prompt_injection`.
- **ast_scanner:** `run_ast_scan(repo_path)` with `SinkholeVisitor` — overlaps with `security_scanner` AST logic; currently **not** called by the worker.
- **scoring:** `RiskScorer().calculate_risk_score(findings)` → penalties by severity (CRITICAL/HIGH/MEDIUM/LOW), score 0–100, grade A–F.
- **remediation:** `get_remediation_tip(title, desc)` or `RemediationEngine().get_fix(title)` maps finding types to fix suggestions.

### 5.4 Infrastructure

- **ingestion:** Docker SDK; create volume, run `alpine/git` clone into volume, return volume name and path; `cleanup_volume` removes volume.
- **models:** Project, Scan (with status, container_id, local_path, score, grade), Vulnerability, ComplianceViolation; relationships set up for Scan.

---

## 6. Current Progress Summary

| Area | Status |
|------|--------|
| FastAPI app + /health, /api/v1 | Done |
| Projects CRUD (create, list) | Done |
| Scan trigger + status by ID | Done |
| URL validation (GitHub HTTPS only) | Done, tested in test_ingestion.py |
| Docker-based ingestion (clone in volume) | Done |
| Security scan (secrets, AST sinkholes, unknown deps) | Done |
| Compliance scan (licenses, prompt-injection) | Done |
| Risk scoring and grading | Done (verify_phase4.py validates flow) |
| Remediation mapping | Done |
| Persisting vulnerabilities and compliance violations | Done |
| Celery task orchestration | Implemented; has bugs (see below) |
| Alembic + shared models | Configured |
| Tests | test_ingestion (unit), test_infra (integration-style, assumes running API/worker) |
| Docker (distroless) + Terraform (Cloud Run) | Present; deploy.sh references pytest and terraform (steps commented) |

---

## 7. Known Issues / To Fix

1. **Worker – RiskScorer:** Worker calls `scorer = RiskScorer(combined_findings)` and `scorer.calculate()`. In code, `RiskScorer()` takes no arguments and only has `calculate_risk_score(self, findings)`. Fix: e.g. `scorer = RiskScorer()` then `score, grade = scorer.calculate_risk_score(combined_findings)`.
2. **Worker – undefined variable:** Log line uses `all_vulns`; should be `security_vulns` (and optionally include compliance count in message).
3. **scans endpoint:** `app/api/v1/endpoints/scans.py` uses `Project` in `select(Project).where(...)` but does not import `Project`; add `from app.infrastructure.models import Project` (or equivalent).
4. **Duplicate AST logic:** `ast_scanner.run_ast_scan` and `security_scanner.detect_ast_sinkholes` overlap; consider using one place or clearly splitting responsibilities.
5. **Ingestion path:** `ingest_repository` returns `local_path: "/data/repo"` (path inside the container). The worker uses this as `repo_path` for file scanning. If the worker runs on the host, it cannot read that path; it needs to either run the scan inside a container that mounts the volume or have ingestion copy the repo to a host path. Current design suggests the worker is expected to run in an environment where `/data/repo` is available (e.g. same container or volume-mounted path). Clarify deployment model (e.g. worker in Docker with volume mount) or change ingestion to expose a host path.

---

## 8. How to Run (for Gemini / future you)

- **API:** From repo root, `uvicorn app.main:app --host 0.0.0.0 --port 8000` (or `python main.py` if root main.py is used).
- **Worker:** Celery worker with app from `app.worker`: e.g. `celery -A app.worker worker -l info`.
- **Redis:** Required for Celery.
- **PostgreSQL:** Required; run Alembic migrations as needed.
- **Docker:** Required for ingestion (clone step).
- **Tests:** `pytest tests/ -v` (unit tests); test_infra assumes API and worker are up for full flow.

---

## 9. One-Liner for Gemini

**HACKX/Vibe-Audit** is a FastAPI + Celery backend that clones GitHub repos in Docker, runs security (secrets, eval/os.system, unknown deps) and compliance (licenses, prompt-injection) scans, scores results, stores them in PostgreSQL, and exposes projects and scans via REST. Fix the worker’s `RiskScorer` call and `all_vulns` reference, add the missing `Project` import in scans, and clarify where the worker runs relative to the ingestion volume so `local_path` is valid.
