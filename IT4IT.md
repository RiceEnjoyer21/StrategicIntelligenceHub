# IT4IT Framework & Reflective Summary

**Project:** AI Business Data Insights Assistant

| Field | Details |
|---|---|
| **Client Type** | Small and Medium Enterprise (SME), B2B |
| **AI Model** | Google Gemini 1.5 Flash (API-based) |
| **ML Engine** | Scikit-learn (Random Forest Regressor) |
| **Deployment** | Streamlit Cloud / Local Testing |
| **Interface** | Web browser – desktop and mobile |

---

## Part 1 — IT4IT Value Stream Mapping

---

### 1. Strategy to Portfolio (S2P) — The Business Problem

#### Problem Statement

Small and medium enterprises generate significant volumes of operational data but lack the internal capability to transform this data into actionable insights. In the Kazakhstan market, SMEs typically suffer from:

- **Data Fragmentation:** Sales, customer activity, and operational metrics are trapped in disconnected CSV files or manual Excel logs.
- **The "Analyst Gap":** Hiring a dedicated data scientist (avg. ₸600,000+ per month) is financially unviable for a business with 10–50 employees.
- **Intuition-Based Decisions:** Owners rely on "gut feeling" for forecasting, leading to over-investment in low-performing areas or missed revenue opportunities during seasonal peaks.

#### Why AI is the Right Investment

Traditional Business Intelligence (BI) tools like Tableau or PowerBI require specialized training. The **AI Business Data Insights Assistant** lowers the barrier to entry by:

- **Translating Math to English/Russian:** It converts complex statistical regressions into natural language business advice.
- **Low-Cost Scalability:** Running on Gemini's free tier or pay-as-you-go pricing, it delivers 24/7 analytical support at a fraction of the cost of a human analyst — though FinOps monitoring is required to avoid unexpected billing at scale.

#### Portfolio Fit

The tool requires almost no setup from the user — upload a CSV, get a report. No dashboards to configure, no queries to write. This makes it practical for business owners who don't have time to learn analytics software.

---

### 2. Requirement to Deploy (R2D) — Architecture & Development

#### Solution Architecture

The system is built as a modular, lightweight Python-based web application:

| Component | Role |
|---|---|
| **Streamlit** | UI/UX framework for rapid, responsive deployment |
| **Pandas / NumPy** | "Deterministic Engine" — data validation, cleaning, and statistical aggregation |
| **Scikit-learn** | Predictive Modeling — Random Forest Regressor for behavior driver analysis |
| **NumPy Polyfit** | Advanced statistical forecasting (3-period projection) |
| **Gemini 1.5 Flash (API-based)** | "Reasoning Layer" — interprets computed metrics and ML drivers into business narratives |

#### Key Architectural Decisions

- **Separation of Concerns:** The AI is not allowed to do math. All calculations happen in Python; Gemini only gets pre-computed numbers to explain. This rule came out of a real failure (see below).
- **JSON Schema Enforcement:** The LLM output is forced into a structured JSON format. This took 3 attempts to stabilize — the first version used free-text output (broke the UI parser), the second used markdown headers (inconsistent keys), and only the third attempt with explicit JSON schema in the system prompt produced reliable, parseable output every time.

#### Development Process — Antigravity Orchestration

The codebase was built through **7 directed architectural sessions** using an AI agent. Not all sessions were productive — Sessions 1, 3, and 6 produced code that required significant refinement or rollback. As the Architect, I defined the system prompts, ML parameters, and modular decomposition, while the agent generated the implementation logic.

> 📁 Full logs are maintained in `logs/antigravity_session_log.md`.

#### Example Architectural Prompt (Session 2)

```
Prompt to Antigravity (Session 2):
"Build a Streamlit app where Pandas computes all statistical metrics
(growth rate, forecast, MoM delta) and returns them as a Python dict.
Pass ONLY this dict as a string to Gemini. The LLM must not perform
any arithmetic — its sole job is to interpret the numbers and generate
a structured JSON report with keys: 'insights', 'predictions', 'actions'."
```

This prompt came after the Session 1 version failed (see below). The key change was the explicit `"must not perform any arithmetic"` constraint — without it, the agent kept generating code where Gemini received raw data.

#### Iteration Log: What Actually Happened

The development was not linear. Here is the honest timeline:

| Session | What was attempted | What went wrong | What survived |
|---|---|---|---|
| **1** | Monolithic app — Gemini receives raw CSV, does everything | LLM computed wrong percentages (~2.5% off); output was free-text, UI couldn't parse it | Basic Streamlit file upload widget |
| **2** | Introduced Pandas "firewall" + JSON schema prompt | JSON output was inconsistent — sometimes returned markdown instead of JSON | Core separation-of-concerns architecture |
| **3** | Added `response_mime_type: application/json` to Gemini config, added forecasting | Statsmodels threw errors on short datasets (<6 rows); agent didn't handle edge case | Forecasting module (after manual edge-case prompt) |
| **4** | Error handling, FinOps token tracking, session state caching | `st.session_state` logic had a race condition — data was re-processed on every click | Token counter, error messages |
| **5** | Bug fixes from Session 4, final UI polish | Minor — mostly CSS alignment issues | Stable release prototype |
| **6** | Added Scikit-learn ML models & PDF export | UI became too complex (tab overload); 404/429 API errors occurred | Random Forest analytics layer |
| **7** | Reverted to "Ideal" UX; added auto-resolve model logic | Initial rollback had API key persistence issues | Final production-safe build |

#### Failure → Recovery: The Arithmetic Hallucination Problem

> **Session 1 failure:** The initial prompt let Gemini compute growth percentages from raw CSV data. During testing, it reported `+14.3% MoM growth` — Python calculated `+11.8%`. A 2.5% gap because LLMs approximate arithmetic from token patterns, they don't actually compute.
>
> **Session 2 attempt:** I told the agent to move all math to Pandas and pass only results to Gemini. This fixed the numbers, but the LLM started returning free-text explanations instead of structured JSON — breaking the frontend parser.
>
> **Session 3 fix:** Added `response_mime_type: "application/json"` to the Gemini API config and rewrote the system prompt with an explicit JSON schema. After this, output was stable. But it took three sessions to get here — the "clean" architecture in the final code hides a lot of trial and error.

---

### 3. Request to Fulfill (R2F) — How the SME Uses the Tool

- **Access Method:** Web browser (desktop/mobile) — no installation or local database setup required.
- **URL:** `Local deployment used for testing (http://localhost:8501)`

#### User Journey

| Step | Action | Description |
|---|---|---|
| 1 | **Ingest** | The owner uploads a CSV file (e.g., `sales_2025.csv`) |
| 2 | **Validate** | The system auto-identifies columns (`Date`, `Revenue`, `Units`) and cleans missing values |
| 3 | **Compute** | The Analytics Layer generates a 6-month forecast and identifies current growth trends |
| 4 | **Interpret** | The user receives a structured report |

**The structured report includes:**
- 💡 **Insights:** *"Your revenue is growing at 12% MoM."*
- 📈 **Predictions:** *"Expect a 15% surge in April based on historical trends."*
- ✅ **Actions:** *"Increase marketing spend on Category X to capitalize on this momentum."*

> **Why this works for SMEs:** The interface is intentionally minimal to reduce cognitive load. Business owners don't want to see "p-values" or "coefficients" — they want to know **what to do next Monday.**

---

### 4. Detect to Correct (D2C) — Monitoring, FinOps & Error Handling

#### LLM Cost Monitoring (FinOps)

- **Token Tracking:** Every request tracks input/output tokens.
- **Cost-per-Insight:** The system calculates the exact cost of each report generated, ensuring the business can scale without *"bill shock."*

#### Hallucination Control

- **Grounding:** The AI is provided with a *"Context Sandbox"* containing only the pre-computed statistical results.
- **Constraint Prompting:** The system prompt includes a strict rule: *"If a number is not in the provided statistics, do not mention it."*

#### Error Handling

- **Graceful Degradation:** If the LLM API is down, the system still displays the deterministic charts and tables, ensuring the tool isn't useless during a network failure.
- **Data Validation:** If a user uploads a corrupted CSV, a clear, non-technical error message explains exactly which column is missing.

---

## Part 2 — Reflective Summary

---

### Managing an AI Agent vs. Writing Code

The hardest part of this project was **not** the AI tool itself — it was managing the agent that built it. When I wrote vague prompts like *"add error handling,"* the agent produced superficial try/except blocks that caught nothing useful. When I wrote overly specific prompts, it followed them too literally and broke other parts of the code.

The real skill I developed was learning to write **constraint-oriented prompts** — not telling the agent *how* to code, but defining what the code *must not* do. For example, instead of "compute growth rate," I learned to say: "Pandas computes growth rate. Gemini must never see raw numbers. Pass only the final dict."

I also learned that AI agents don't remember context between sessions. Every new session, I had to re-explain the architecture from scratch, or the agent would drift back to its default patterns (like letting the LLM do math).

---

### Hardest Architectural Bottlenecks

#### 1. The Calculation / Interpretation Split

This was the biggest problem and it took 3 sessions to fully solve:

- **Session 1:** LLM did all the math → wrong numbers (2.5% drift)
- **Session 2:** Moved math to Pandas, but LLM still sometimes "corrected" the numbers in its output when it disagreed with them
- **Session 3:** Added explicit constraint in system prompt: *"All numbers below are final and verified. Do not recalculate, round, or adjust any figure. Only explain."* — this finally stopped the behaviour

| | Session 1 | Session 2 | Session 3 (final) |
|---|---|---|---|
| **Who computes?** | Gemini | Pandas | Pandas |
| **LLM behaviour** | Computed freely | Sometimes "corrected" results | Explained only |
| **Accuracy** | ~97–98% | ~99% (occasional override) | no mismatches observed (tested on 15 datasets) |

#### 2. Structuring the Output Format

The first version returned a wall of text like a chatbot response — unusable in a UI. I tried 3 approaches:

1. **Free text with markdown headers** → inconsistent key names, UI parser broke randomly
2. **Asking for JSON in the user prompt** → worked 70% of the time, other 30% it returned markdown anyway
3. **`response_mime_type: application/json` + JSON schema in system prompt** → stable

Even after fixing the format, the *content* was too generic. I had to add a Structured Prompt Template forcing the model to categorize output into `"observations"`, `"causes"`, and `"recommendations"` — otherwise it just wrote vague summaries.

#### 3. Maintaining State in Streamlit

Because Streamlit reruns the entire script on every interaction, keeping the uploaded data *"alive"* without re-processing it (and wasting API tokens) required a deep understanding of `st.session_state`. I had to direct the AI agent specifically on how to cache these dataframes.

---

### Proof of Architecture Execution

This project strictly follows the Zero Manual Coding Rule.

All core application logic was generated by an AI coding agent
The student acted exclusively as Product Architect
Responsibilities included:
defining system architecture
designing prompt constraints
identifying and correcting failures
guiding iterative refinement across sessions

# 📁 Evidence:
Full session logs are provided in:

logs/antigravity_session_log.md

# These logs demonstrate:

initial system design prompts
failure cases (arithmetic hallucination, JSON instability)
corrective architectural decisions
step-by-step evolution from prototype to stable system
Production Considerations (Enterprise Readiness)

# While this project is delivered as a Streamlit MVP, the architecture is designed for extension:

Can be integrated with BI tools or internal dashboards
LLM layer can be replaced without affecting analytics engine
Deterministic layer ensures auditability of all metrics
FinOps tracking enables cost control at scale

## Conclusion

The final product works, but getting here was not clean. About 40% of the code generated across sessions was discarded or rewritten. The main lesson: building with an AI agent is fast for the first 70%, but the last 30% — edge cases, output stability, state management — takes just as long as traditional development.

Using the IT4IT framework helped me treat this as a real product instead of a demo. Without the D2C thinking (cost tracking, error handling), I would have shipped something that breaks on the first unusual CSV upload. The framework forced me to ask "what happens when this fails?" — which is the question that turned a prototype into something actually usable.

