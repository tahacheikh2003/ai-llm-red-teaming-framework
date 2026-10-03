# Local Sales Analytics AI Agent

A university AI security project developed by **Taha El Cheikh**, under the supervision of **Dr. Natasha Alkhatib**.

The application combines a sales dashboard, a local AI assistant, and security demonstrations. It compares three security modes: **Vulnerable**, **Mitigated**, and **Mitigated Final**.

## Features

- Interactive sales dashboard with filters and charts.
- Natural-language questions about synthetic sales data.
- Local model inference through Ollama.
- Six approved read-only analytics tools.
- Three security modes for controlled comparison.
- Agent execution steps showing tool calls and observations.
- Automated tests and Promptfoo evaluation configurations.

## Architecture

User → Streamlit → FastAPI `/chat` → Python Agent → Ollama

The model proposes a tool call. The agent validates it, executes an approved Python function, and retrieves aggregate results from SQLite.

The agent allows a maximum of **three model calls per question**, including tool proposals, correction attempts, and the final response.

Dashboard filters apply to the charts. Users must specify the desired period or product explicitly in chat.

## Technologies

- Python
- FastAPI
- Streamlit
- Ollama
- SQLite
- Pandas and Plotly
- Promptfoo
- Pytest

## Dataset

The project includes **2,400 synthetic sales orders** covering January–December 2025. All monetary values are in USD.

- Products: Laptop, Smartphone, Tablet, Monitor, Headphones, Keyboard and Mouse.
- Categories: Computers, Mobile Devices and Accessories.
- Regions: North, South, East and West.

No real customer data is included. “Best selling product” means the product with the highest number of units sold.

## Security Modes

| Control | Vulnerable | Mitigated | Mitigated Final |
|---|---|---|---|
| System instructions | Basic policy | Stronger policy | Extended policy |
| Input guard | Risk assessed, not enforced | Enforced | Enforced with scope and capability checks |
| Tool allowlist and argument validation | Enforced | Enforced | Enforced |
| Read-only SQLite tools | Yes | Yes | Yes |
| Output disclosure checks | No | Yes | Extended checks |
| False execution-claim checks | No dedicated check | No dedicated check | Yes |
| Final analytics answer | Model-generated | Model-generated with output checks | Built by the application from tool observations |
| Maximum model calls | 3 | 3 | 3 |

All modes use the same six read-only tools. No mode provides arbitrary SQL, shell execution, database deletion, or access to real customer systems.

`DEMO_SECRET_2026` is a public, deliberately fake canary used for reproducible security tests. It is not a real credential.

## Installation

The following commands are for Windows PowerShell.

Install Python 3.11 or later and Ollama. Open PowerShell inside the project folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m database.create_database
ollama pull llama3.2:3b
```

The database command preserves an existing database. To deliberately regenerate the synthetic data:

```powershell
.\.venv\Scripts\python.exe -m database.create_database --force
```

## Run the Application

Start Ollama. If it is not already running, use a separate terminal:

```powershell
$env:OLLAMA_NO_CLOUD = "1"
$env:OLLAMA_HOST = "127.0.0.1:11434"
ollama serve
```

Start the backend from the project folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

Open:

- Dashboard: http://localhost:8501
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Keep the terminals open while using the application.

`Start_Sales_AI.pyw` is an optional Windows launcher. It requires the virtual environment, dependencies and Ollama to be installed first.

## Example Questions

- Which product had the highest revenue in March 2025?
- Compare Laptop revenue between January and February 2025.
- Which region generated the highest total revenue in 2025?
- What was the revenue growth from January to February?
- Show revenue by category.

Each question starts a fresh agent run. Displayed chat history is not sent back to the model.

## Automated Tests

Run the offline regression tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The reviewed version passed **131 automated tests**. These tests use mocked model responses and HTTP interactions. They cover tools, validation, guards, agent control flow, API behavior and dashboard components.

Passing these tests does not establish resistance to every attack or replace live model evaluations.

## Promptfoo Evaluations

Install Node.js compatible with the pinned Promptfoo version, then install the evaluation dependencies:

```powershell
npm.cmd ci --prefix promptfoo --no-audit --no-fund
```

With FastAPI and Ollama running:

```powershell
$env:PROMPTFOO_DISABLE_TELEMETRY = "1"
$env:PROMPTFOO_DISABLE_UPDATE = "1"
$env:PROMPTFOO_DISABLE_REMOTE_GENERATION = "true"
$env:PROMPTFOO_CONFIG_DIR = "$PWD\.promptfoo"
```

Original two-mode evaluation:

```powershell
.\promptfoo\node_modules\.bin\promptfoo.cmd eval -c promptfoo/promptfooconfig.yaml --no-cache --max-concurrency 1
```

Focused Mitigated Final evaluation:

```powershell
.\promptfoo\node_modules\.bin\promptfoo.cmd eval -c promptfoo/mitigated-final.yaml --no-cache --max-concurrency 1
```

The original configuration contains five questions tested in two modes. The retained `promptfoo/results.json` records the initial run of 23 September 2026: **7 passed, 3 failed, 0 errors**.

The separate final-mode configuration contains three attack prompts and four legitimate sales questions. Its result export is not included in this application archive.

These configurations target the application through FastAPI and use deterministic JavaScript assertions.

## Broader Internship Evaluations

The initial application tests are separate from the larger internship campaigns.

The later application exports contain 110 entries per mode:

| Mode | Passed checks | Failed checks |
|---|---:|---:|
| Vulnerable | 82 | 28 |
| Mitigated | 93 | 17 |
| Mitigated Final | 108 | 2 |

These are exported evaluation verdicts, not confirmed compromise counts. The two final-mode failures include a grading-service error and a disputed hallucination verdict. The report explains these cases and the comparison limits.

The broader work also includes Cybersecurity QA, Llama and Mistral red teaming, Base64 campaigns, and a Mistral system-prompt experiment.

The application performs local inference. Some broader Promptfoo campaigns used cloud models for generation or grading, so the complete internship evaluation workflow was not fully offline.

## Project Structure

| Path | Purpose |
|---|---|
| `backend/` | FastAPI, agent loop, Ollama client and demonstration grading |
| `frontend/` | Streamlit dashboard and comparison metrics |
| `security/` | System prompts, input/output guards, tool policy and final-mode controls |
| `tools/` | Six read-only analytics tools |
| `database/` | SQLite database and deterministic generator |
| `data/` | Synthetic sales CSV |
| `tests/` | Automated regression tests |
| `promptfoo/` | Evaluation configurations, dependency files and initial results |
| `scripts/` | Live validation utility |
| `docs/` | Historical validation notes and evidence |
| `.streamlit/` | Interface theme and local server configuration |

## Historical Evidence

The files under `docs/` record different development stages:

- `live-validation-initial.json`: initial analytics checks, including failures.
- `live-validation-before-scope-fix.json`: checks before the scope correction.
- `live-validation.json`: later analytics validation.
- `live-region-summary.json`: regional ranking validation.
- `live-comparison-final.json`: an earlier comparison response in **Mitigated** mode; its filename does not mean Mitigated Final.
- `promptfoo-summary.json`: summary of the initial ten evaluations.
- `VALIDATION.md`: historical validation record.

## Limitations

This is a local educational security lab, not a production-ready service.

The guards use English patterns and heuristics. They can miss unusual attacks or reject legitimate requests. Final-mode answers come from tool observations, but the model can still select an unsuitable tool or incorrect filters.

The tools support a limited set of analytics operations. They do not provide arbitrary queries, forecasting, customer information or database modifications.

Security demonstration verdicts are limited checks. Review responses, selected tools and observations when interpreting results.