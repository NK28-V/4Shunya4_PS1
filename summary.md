# Hackx4.0 — Vibe-Audit Project Summary

**Purpose:** Share this document with Gemini (or any AI) to understand the project structure, architecture, and current progress.

---

## 1. Project Overview

**Vibe-Audit** is a **production-readiness and security audit platform** for AI-generated applications. It provides:

- **Prompt-injection detection** — Multi-layered scanner (regex, YARA, LLM) on user prompts and RAG data; plus in-repo keyword scan in `app/domain/compliance_scanner`.
- **Compliance checks** — SOC 2 (e.g. MFA) and GDPR via `backend/compliance_core`; restrictive-license and prompt-injection keyword checks via `app/domain/compliance_scanner`.
- **Security scanning** — Full-repo scan in `app/domain`: secrets (AWS, RSA, high-entropy), AST sinkholes (eval, os.system, subprocess), hallucinated dependencies; optional dedicated `app/domain/ast_scanner` for dangerous sinks.
- **PII / AST scanning** — Python AST-based PII in `backend/compliance_core`; dangerous-sink AST in `app/domain`.
- **Scoring** — Two paths: (1) **Vibe-to-Value** (root `scoring_algorithm.py` + `constants.py`) for single-file audit; (2) **Risk score + grade** (`app/domain/scoring.RiskScorer`) for worker pipeline (0–100, grade A–F).
- **Remediation** — `app/domain/remediation` maps finding titles to actionable fixes (eval → ast.literal_eval, os.system → subprocess, etc.).
- **Backend API** — FastAPI with projects, scan trigger, and scan status; Celery worker **ingests via git clone** (subprocess + tempfile, no Docker), runs a **unified scanning pipeline** (domain + prompt-injection + compliance core + PII), and persists score, grade, vulnerabilities, violations, and full **ScanReport JSON** (including **dataFlow** for the frontend compliance graph). GET /scans/{id} returns ScanReport-shaped payload.
- **Frontend** — Next.js (vibe-frontend): **Landing** has GitHub Repository URL input; on "Run Production Scan" it calls POST /api/v1/projects/ then POST /api/v1/scans/{project_id}/trigger and navigates to **/dashboard?scanId={scan_id}**. **Dashboard** reads `scanId` from the URL (useSearchParams), polls GET /api/v1/scans/{scanId} every 5s while status is PROCESSING, shows a skeletal loading UI, and displays the supply-chain modal when any vulnerability has **AI_HALLUCINATED** in metadata.

**Tagline:** *From Vibe to Value. Production-grade security for AI-generated applications.*

---

## 2. Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | FastAPI, SQLAlchemy (async + asyncpg), Pydantic, Alembic |
| Task queue | Celery, Redis (broker/backend) |
| DB | PostgreSQL |
| Security / rate limit | slowapi (rate limiting), CORS |
| **Domain scanning** | **app/domain:** security_scanner (secrets, AST sinkholes, hallucinated deps), compliance_scanner (licenses, prompt-injection keywords), ast_scanner (sink visitor), scoring (RiskScorer), remediation |
| Prompt scanner (legacy/CLI) | Python (regex, optional YARA, optional Google Gen AI / Gemini) |
| Compliance engine (legacy/CLI) | backend/compliance_core: SOC2, GDPR, AST PII, PiiAdapter |
| Frontend | Next.js (App Router), React, TypeScript, TanStack Query, Tailwind |
| Repo ingestion | **subprocess + tempfile:** `git clone` into temp dir on host; **cleanup:** `shutil.rmtree` (no Docker). See `app/infrastructure/ingestion.py`. |

---

## 3. Architecture (High Level)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  vibe-frontend (Next.js)                                                 │
│  Landing: GitHub URL input → POST /projects/ → POST /scans/{id}/trigger │
│  → /dashboard?scanId=… → poll GET /scans/{scanId} every 5s if PROCESSING │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Backend API (FastAPI)                                                   │
│  POST /api/v1/projects/     → create project (name, repository_url)      │
│  GET  /api/v1/projects/     → list projects                             │
│  POST /api/v1/scans/{id}/trigger → create Scan, enqueue Celery task      │
│  GET  /api/v1/scans/{scanId} → ScanReport (id, score, vulnerabilities, dataFlow, etc.) │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌──────────────────────────────────────┐
│  Celery Worker                │   │  PostgreSQL                           │
│  scan_codebase(scan_id)       │   │  Project, Scan (score, grade,        │
│  1. Ingest repo (git clone    │   │  report_payload), Vulnerability,     │
│     into temp dir on host)    │   │  ComplianceViolation                  │
│  2. Unified scanners          │   └──────────────────────────────────────┘
│  3. ScanReport + dataFlow     │
│  4. Persist report_payload,   │
│     vulns, violations;        │
│     cleanup (shutil.rmtree)   │
└───────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Unified worker pipeline (app/worker.py)                                │
│  • run_security_scan(repo_path)        → secrets, AST sinkholes, deps  │
│  • run_compliance_scan(repo_path)      → licenses, prompt-injection     │
│  • PromptScanner.scan(content) per .py → prompt injection (L1/L2/L3)   │
│  • ComplianceEngine.evaluate({})      → SOC2/GDPR                     │
│  • scan_python_file + PiiAdapter per .py → PII → violations + dataFlow │
│  • RiskScorer.calculate_risk_score()   → score, grade (A–F)            │
│  • Single ScanReport JSON: vulnerabilities + dataFlow (for frontend)  │
│  • Persist: Scan.report_payload, Vulnerability, ComplianceViolation    │
│  • One failed scanner does not crash task (try/except per scanner)     │
└─────────────────────────────────────────────────────────────────────────┘

Optional / CLI path (single-file):
┌─────────────────────────────────────────────────────────────────────────┐
│  vibe_audit_engine.run_audit(target_python_file)                          │
│  1. PromptScanner.scan(content)     ← prompt_injection_scanner.py        │
│  2. ComplianceEngine.evaluate()    ← backend/compliance_core           │
│  3. AST PII scan + PiiAdapter       ← ast_scanner + pii_adapter          │
│  4. Regex secrets/API keys          │
│  5. build_result_payload(report)   ← scoring_algorithm.py               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. File Structure

Excluding build artifacts (e.g. `.next`, `node_modules`, `__pycache__`, `.git`):

```
Hackx4.0/
├── .env                          # Environment (DB, Redis, API keys, etc.)
├── .agent/
│   └── skills/
│       └── dependency-scanner/
│           ├── SKILL.md
│           └── scripts/
│               └── scanner.py
├── alembic.ini                   # Alembic config
├── alembic/
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
│       └── add_report_payload_to_scans.py  # report_payload column on scans
├── app/                          # FastAPI application
│   ├── main.py                    # FastAPI app, CORS, global exception handler
│   ├── worker.py                  # Celery: ingest (git+temp) → unified scanners → ScanReport + persist
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py        # Router aggregation
│   │       └── endpoints/
│   │           ├── projects.py    # Create/list projects
│   │           └── scans.py       # Trigger scan; GET returns ScanReport shape (report_payload or built)
│   ├── core/
│   │   ├── config.py              # Pydantic settings
│   │   ├── logging.py
│   │   ├── security.py            # CORS, rate limiting (slowapi)
│   │   └── validators.py          # GitHub URL, SSRF checks
│   ├── domain/                    # Domain scanning & scoring (used by worker)
│   │   ├── security_scanner.py    # Secrets, AST sinkholes, hallucinated deps
│   │   ├── compliance_scanner.py  # Restrictive licenses, prompt-injection keywords
│   │   ├── ast_scanner.py         # SinkholeVisitor: eval, exec, os.system, subprocess
│   │   ├── scoring.py             # RiskScorer (score 0–100, grade A–F)
│   │   └── remediation.py        # RemediationEngine / get_remediation_tip
│   └── infrastructure/
│       ├── database.py            # Async engine, session, get_db
│       ├── ingestion.py           # git clone via subprocess into temp dir; cleanup_volume = shutil.rmtree
│       └── models.py              # Project, Scan (score, grade, report_payload), Vulnerability, ComplianceViolation
├── backend/
│   └── compliance_core/
│       ├── __init__.py
│       ├── README.md              # Config shape, CLI usage
│       ├── ast_scanner.py         # Python AST PII scan
│       ├── cli.py                 # CLI: --config path/to/config.json
│       ├── config_loader.py
│       ├── engine.py              # ComplianceEngine, evaluate()
│       ├── models.py
│       ├── result.py
│       ├── utils.py
│       ├── adapters/
│       │   └── pii_adapter.py     # AST scan result → compliance violations
│       └── rules/
│           ├── __init__.py
│           ├── gdpr.py
│           └── soc2.py             # e.g. Soc2MfaEnabledRule
├── constants.py                   # Scoring weights (BASE_SCORE, DEDUCT_*, thresholds)
├── prompt_injection_scanner.py    # Layer 1 regex, Layer 2 YARA, Layer 3 Gemini
├── requirements-prompt-scanner.txt  # deps for scanner + API (yara-python, google-genai, etc.)
├── scoring_algorithm.py           # compute_score(), build_result_payload()
├── test_report.json               # Example/sample report output
├── tests/
│   ├── test_infra.py
│   └── test_ingestion.py
├── vibe_audit_engine.py           # run_audit(): orchestrate scanner + compliance + PII + scoring
├── vulnerable_logic.py            # (project-specific helper or test target)
│
└── vibe-frontend/                 # Next.js App Router
    ├── .env.example
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── eslint.config.mjs
    ├── postcss.config.mjs
    ├── next-env.d.ts
    ├── README.md
    ├── app/
    │   ├── favicon.ico
    │   ├── globals.css
    │   ├── layout.tsx
│   ├── page.tsx                # Landing: GitHub URL input; POST project + trigger → /dashboard?scanId=
│   ├── api/
    │   │   └── v1/
    │   │       └── scans/
    │   │           └── [scanId]/
    │   │               └── route.ts # Proxy or direct fetch to backend scan API
    │   ├── dashboard/
│   │   ├── layout.tsx
│   │   └── page.tsx            # Dashboard: scanId from useSearchParams; TanStack Query + 5s poll; skeleton; AI_HALLUCINATED modal
    │   └── hooks/
    │       └── useComplianceGraph.ts
    ├── components/
    │   ├── ComplianceFlow.tsx
    │   ├── ErrorBoundary.tsx
    │   ├── Providers.tsx
    │   └── vibescorecard.tsx
    ├── lib/
    │   ├── mockScans.ts
    │   └── types.ts                # ScanReport, etc.
    └── public/
        └── (static assets)
```

---

## 5. Key Components (for Context)

### 5.1 Domain layer (`app/domain/`) — used by Celery worker

- **security_scanner.py** — `run_security_scan(repo_path)`: walks repo; detects secrets (AWS keys, RSA private key, high-entropy strings), AST sinkholes (eval, os.system), and hallucinated dependencies (imports not in `PYTHON_SAFE_MODULES`). Returns list of findings with severity, title, description, file_path, line_number.
- **compliance_scanner.py** — `run_compliance_scan(repo_path)`: scans LICENSE files for restrictive licenses (GPL, AGPL, etc.); scans code for prompt-injection keywords. Returns list of violations with rule_id, description, severity.
- **ast_scanner.py** — `run_ast_scan(repo_path)`: `SinkholeVisitor` over Python files for dangerous calls (eval, exec, os.system, os.popen, subprocess.run/call/Popen). Returns list of findings. Can be used standalone or is conceptually overlapping with security_scanner’s AST sink logic.
- **scoring.py** — `RiskScorer.calculate_risk_score(findings)`: starts at 100; deducts by severity (CRITICAL 25, HIGH 15, MEDIUM 5, LOW 2); returns (score, grade) with grade A–F.
- **remediation.py** — `get_remediation_tip(title, desc)` / `RemediationEngine.get_fix(title)`: maps finding title/description to fix text (e.g. eval → ast.literal_eval, os.system → subprocess, leaked → env/secrets, prompt injection → sanitize inputs).

### 5.2 Worker (`app/worker.py`)

- Celery task `scan_codebase(scan_id)`.
- **Ingestion:** `ingest_repository(url)` runs `git clone` (subprocess) into a temp directory on the host; returns absolute `local_path`. **cleanup_volume(path)** uses **shutil.rmtree** (no Docker).
- **Unified pipeline:** Runs all scanners with per-scanner try/except so one failure does not crash the task:
  - **app.domain:** `run_security_scan(repo_path)`, `run_compliance_scan(repo_path)`
  - **prompt_injection_scanner:** `PromptScanner.scan(content)` on each `.py` file in the repo
  - **backend/compliance_core:** `ComplianceEngine.default().evaluate({})` (SOC2/GDPR); per-file PII scan + `PiiAdapter`
- **Aggregation:** All findings combined into a single **ScanReport**-shaped payload: `vulnerabilities[]` (id, file, severity, metadata) and **dataFlow[]** (from, to, encrypted, containsPII) for the frontend compliance graph. **RiskScorer** for score/grade; **get_remediation_tip** for each vulnerability.
- **Persistence:** `Scan.score`, `Scan.grade`, **`Scan.report_payload`** (full JSON), `Vulnerability` rows, `ComplianceViolation` rows; then **cleanup_volume(local_path)**.
- Does **not** call `vibe_audit_engine.run_audit`; worker uses the unified pipeline above.

### 5.3 Prompt Injection Scanner (`prompt_injection_scanner.py`)

- **Layer 1:** Regex heuristics — jailbreak phrases, structural anomalies (e.g. forced JSON, ChatML tokens). Score 0–1; threshold 0.25.
- **Layer 2:** YARA rules (optional) — compiled from built-in string rules; match known adversarial payloads.
- **Layer 3:** LLM (optional) — Google Gen AI (`google.genai`), model `gemini-2.5-flash`, JSON response with `score`, `type`, `explanation`. Used only when prior layers are “ambiguous” (configurable).
- **Output:** `ScanResult` dataclass: `is_injection`, `overall_score`, per-layer scores/matches. CLI: stdin or first arg → JSON.

### 5.4 Compliance Engine (`backend/compliance_core/`)

- Loads JSON config (e.g. `logical_access.mfa_enabled`, `data_protection.pii_encrypted`).
- Runs SOC2 and GDPR rules; outputs structured violations.
- AST scanner finds PII in Python files; `PiiAdapter` turns findings into violation objects.

### 5.5 Scoring — two paths

- **Worker path:** `app/domain/scoring.RiskScorer` — score 0–100, grade A–F from combined security + compliance findings.
- **CLI / single-file path:** `scoring_algorithm.py` + `constants.py` — Vibe-to-Value: base 100, deductions for secrets, hallucinated deps, SOC2 MFA, GDPR/PII, low coverage; score &lt; 60 → `DEPLOYMENT_BLOCKED`. `build_result_payload(report)` produces JSON with `vibe_to_value_score` and optional `integrated_report`.

### 5.6 Vibe Audit Engine (`vibe_audit_engine.py`)

- **Input:** Path to a single Python file.
- **Steps:** Read file → PromptScanner on content → ComplianceEngine (empty config) → AST PII scan → PiiAdapter → regex secrets → build integrated report → `build_result_payload()`.
- **Output:** Full payload with score and integrated report. CLI: `python vibe_audit_engine.py <target_python_file>`. **Not used by the worker**; worker uses the unified pipeline (domain + prompt-injection + compliance core + PII) instead.

### 5.7 Frontend (vibe-frontend)

- **Landing (app/page.tsx):** Text input for **GitHub Repository URL**. On "Run Production Scan": (a) POST **/api/v1/projects/** with `{ name: "Dynamic Project", repository_url }` → capture project `id`; (b) POST **/api/v1/scans/{project_id}/trigger** → capture `scan_id`; then navigate to **/dashboard?scanId={scan_id}**. Uses `NEXT_PUBLIC_SCAN_API_BASE`. Loading and error states; no hardcoded scan ID.
- **Dashboard (app/dashboard/page.tsx):** Reads **scanId** from URL via **useSearchParams**; TanStack Query with `queryKey: ["scan", scanId]` and **refetchInterval: 5000** when `status === "PROCESSING"`. Non-blocking **skeletal UI** (ProcessingSkeleton) during loading. **Supply-chain modal** when any vulnerability has **CRITICAL** severity and **AI_HALLUCINATED** in `metadata`. Score gauge, VibeScorecard, Compliance Data Flow from `dataFlow`. GO/NO-GO by score &lt; 60.

---

## 6. Current Progress (Summary)

- **Done:** Prompt injection scanner (3 layers), backend/compliance_core (SOC2/GDPR + AST PII + PiiAdapter), root scoring_algorithm + constants, **app.domain** (security, compliance, ast_scanner, scoring, remediation), FastAPI app with projects and scans endpoints, **unified Celery worker** (git-based ingestion into temp dir, no Docker; domain + prompt-injection + compliance core + PII; single ScanReport with **dataFlow**; **report_payload** on Scan), DB models including **Vulnerability** (remediation_tip) and Scan **score**/**grade**/**report_payload**, **GET /scans/{id}** returns **ScanReport** shape, Alembic migration for report_payload, vibe-frontend landing and dashboard.
- **Two pipelines:** (1) **Worker:** ingest (subprocess + tempfile) → unified scanners (domain + prompt_injection_scanner + compliance_core + PII) → aggregate → RiskScorer → persist report_payload + Vulnerability + ComplianceViolation + cleanup with shutil.rmtree. (2) **CLI/single-file:** vibe_audit_engine.run_audit → prompt_injection_scanner + backend/compliance_core + scoring_algorithm.
- **Frontend (Phase 2):** No hardcoded scan ID. Landing collects GitHub URL, creates project and triggers scan via API, then redirects to **/dashboard?scanId=…**. Dashboard reads **scanId** from query params, polls GET /scans/{scanId} every 5s while PROCESSING, shows skeletal loading UI, and triggers the supply-chain modal when **AI_HALLUCINATED** appears in vulnerability metadata.
- **Repro:** Backend needs PostgreSQL and Redis; worker needs **git on PATH** and same DB/Redis (no Docker). Frontend needs `NEXT_PUBLIC_SCAN_API_BASE` pointing at backend.

---

## 7. How to Run (Quick Reference)

- **Backend:** From repo root, `uvicorn app.main:app --reload` (or `python -m app.main`). Requires `.env` with DB and Redis.
- **Worker:** `celery -A app.worker worker -l info` (broker/backend from settings). Worker **ingests via git clone into a temp dir** (requires **git on PATH**), runs **unified scanners** (domain + prompt-injection + compliance core + PII), builds ScanReport with dataFlow, persists report_payload and vulns/violations, then removes temp dir with shutil.rmtree.
- **Migrations:** `alembic upgrade head` (adds `report_payload` to scans if not already applied).
- **Prompt scanner only:** `pip install -r requirements-prompt-scanner.txt`, set `GOOGLE_API_KEY` or `GEMINI_API_KEY` for Layer 3; `python prompt_injection_scanner.py "text to scan"` or pipe stdin.
- **Single-file audit:** `python vibe_audit_engine.py path/to/file.py`.
- **Compliance CLI:** `python backend/compliance_core/cli.py --config path/to/config.json --pretty`.
- **Frontend:** `cd vibe-frontend && npm install && npm run dev`; set `NEXT_PUBLIC_SCAN_API_BASE` to backend URL (e.g. `http://localhost:8000`).

---

Use this summary with Gemini (or any assistant) by pasting it and then asking specific questions about code, flows, or next steps.
