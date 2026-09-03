# RAAHI — Tech Stack & Justification

Every choice below was made deliberately, with a stated tradeoff — not defaulted to out of familiarity. Where we evaluated and rejected an alternative, that's noted explicitly.

---

## Backend

### Python + FastAPI
**Why:** Async-native, automatic OpenAPI docs, strong typing via Pydantic, and the best-supported SDK ecosystem for both Razorpay and the data/ML libraries the project needed (pandas, scikit-learn). FastAPI's dependency-injection and route structure also made it straightforward to keep the 5-agent pipeline as plain, explicit function calls rather than framework-managed state.

**Rejected alternative — Node.js/Express:** Would have meant a weaker ML ecosystem (Python's scikit-learn/pandas have no real Node equivalent) and would have split the stack across two languages for no functional benefit, since the frontend already uses JavaScript independently.

### Plain Python orchestration (no LangGraph / agent framework)
**Why:** RAAHI's pipeline is a **fixed, linear sequence** — every record passes through Detection → Diagnosis → Decision → Guardrail → Execution in the same order, with no dynamic branching or looping that would require a graph-based workflow engine. A 10-line orchestrator function is directly auditable by anyone reading it; a graph framework adds an abstraction layer a reviewer would need to trust *in addition to* the underlying logic.

**Explicitly rejected — LangGraph:** Evaluated and rejected specifically because it optimizes for a problem RAAHI doesn't have (dynamic, LLM-directed workflow branching). Since Guardrail must be deterministic and fully auditable, giving an LLM or a graph engine control over *which* rule runs next would weaken — not strengthen — the "bounded and gated" requirement the track explicitly calls for.

### SQLAlchemy + PostgreSQL (via Supabase)
**Why:** SQLAlchemy's ORM gives us portable, typed models that moved cleanly from local SQLite (early development) to production Postgres with a one-line connection-string change — no rewrites. Supabase specifically was chosen over a self-managed Postgres instance because it also provides:
- A managed **Storage** service (used for real generated voice audio files) with the same account/API surface
- A generous free tier sufficient for a full demo dataset (2,000+ synthetic + real records)

**Rejected alternative — raw SQLite for production:** Fine for early local development, but doesn't support concurrent connections well and isn't reachable by a deployed backend on Render without a persistent-disk workaround — Postgres was necessary once we moved beyond local testing.

---

## AI / ML Layer

### Groq (openai/gpt-oss-20b) for LLM inference
**Why:** Groq's inference speed (hundreds of tokens/second) made it practical to run diagnostic reasoning across large synthetic batches without the pipeline stalling. The model itself (`openai/gpt-oss-20b`) was chosen after testing showed the smaller model paired with explicit JSON-output prompting was both faster and, empirically, less prone to truncation issues than the 120B variant in this project's specific reasoning-token consumption pattern.

**Rejected alternative — a larger frontier model (GPT-4-class) for every diagnosis call:** Would have been meaningfully slower and more expensive at batch scale, with no clear accuracy benefit for a task this narrow (root-cause narrative generation with a fixed, small category space) — mitigated further by aggressive caching (see below), which makes the *choice* of model matter less since most records never hit the API at all.

### Redis (Upstash) for LLM response caching
**Why:** Since diagnostic reasoning depends only on `(record_type, failure_reason_code)` — a small, finite set of combinations — caching at that key eliminates redundant LLM calls entirely for repeat categories. This cut real API calls by ~97–99% on large batches, directly reducing cost, latency, and exposure to rate limits. Upstash specifically was chosen for its serverless, connection-less REST API (no persistent connection pool to manage from a stateless backend) and generous free tier.

### scikit-learn (Logistic Regression, calibrated)
**Why:** For the confidence and meta-blend models, interpretability mattered as much as raw predictive power — a logistic regression's coefficients can be directly read and explained ("higher ML confidence increases predicted recovery odds"), which matters for a system whose core requirement is explainability. `CalibratedClassifierCV` was added specifically so the model's output is a genuine probability (validated via Brier score), not just a ranking score.

**Evaluated and rejected — LightGBM:** Directly compared against Logistic Regression using identical preprocessing and 5-fold cross-validation on the same dataset. Logistic Regression won (0.626 vs. 0.569 CV-ROC-AUC) with a tighter variance across folds — consistent with LightGBM's larger-data requirements not being met by our current (~1,700-sample synthetic) dataset. This was a measured decision, not a default; at real production scale with more data, this comparison would likely favor gradient boosting instead, and that's documented as a legitimate future re-evaluation point.

### gTTS (Google Text-to-Speech)
**Why:** For real Hinglish voice message generation, gTTS provides genuine, free, no-API-key text-to-speech with Hindi-language support — enough to produce a real, playable audio artifact proving the "voice recovery" capability without needing a telephony account (Twilio's trial-account restrictions on outbound calling made a live phone-call demo unreliable for this project's timeline; see Known Limitations in the README).

### LLM-based NLP intent extraction (Groq) for Promise-to-Pay, over a rules/regex approach
**Why:** Customer replies arrive as genuinely unstructured free text — "kal tak kar dunga," "I'll pay Friday," "salary aane ke baad, 5 tarikh ko," "already paid, please check," "not interested, stop messaging." A keyword or regex matcher cannot reliably resolve relative dates ("kal," "this Friday," "in 3 days") against the actual calendar, distinguish a genuine commitment from a vague deflection ("maybe next week"), or correctly reject a denial or refusal — all of which the LLM handles correctly in testing, including mixed Hindi-English input. The task was explicitly scoped down to structured JSON extraction (`has_promise`, `promised_date`, `confidence`) rather than open-ended generation, keeping the LLM's role narrow, bounded, and auditable — consistent with how the LLM is used everywhere else in RAAHI (reasoning/extraction only, never given autonomous action authority).

**Design details that came from real testing, not assumption:**
- **IST-aware date resolution.** The extraction prompt anchors "today" to `Asia/Kolkata` time explicitly, not UTC — a genuine bug we caught: using UTC caused incorrect date resolution during the ~5.5 hour window each day where UTC and IST fall on different calendar dates, which would have misresolved "kal" (tomorrow) for a real Indian customer for part of every day.
- **Truncation-safe prompting.** Early prompts asked the LLM to also generate a free-text reasoning sentence, which occasionally pushed responses over the token budget and produced truncated, unparseable JSON — we removed the model-generated reasoning field and now generate that string in code instead, which shortened every response and eliminated the truncation failures we observed in testing.
- **Confidence-gated commit.** A commitment is only logged (and reminders suppressed) above a 0.6 confidence threshold — below that, RAAHI treats the reply as ambiguous and continues normal follow-up rather than silently trusting a low-confidence extraction.

**Rejected alternative — regex/keyword-based date parsing (e.g., matching "friday," "tomorrow," "kal"):** Would break immediately on any phrasing variation, cannot handle relative or conditional commitments ("after salary, on the 5th"), and cannot distinguish "I will pay Friday" from "I already paid" or "stop messaging me" — all three contain payment-related keywords but mean entirely different things. This is precisely the class of problem free-text intent extraction is suited for and pattern matching is not.

---

## Payments Infrastructure

### Razorpay (Test Mode) — Payment Links, Invoices, Subscriptions, Orders
**Why:** This is the mandated platform for the track. Within Razorpay's API surface, we deliberately used the **correct dedicated instrument per record type** rather than a single generic mechanism: Payment Links for one-time payment failures, the real Invoice API for B2B receivables, and real Plan + Subscription objects for subscription failures — because Razorpay's own test-mode dashboard shows genuinely distinct entities for each, which is a stronger, more accurate claim than routing everything through Payment Links alone.

### Webhooks over polling, as the primary recovery-confirmation mechanism
**Why:** This mirrors real production payment architecture — no serious payments system determines "did the customer pay" by repeatedly asking; it reacts to the platform's own push notification. We built a signature-verified webhook receiver covering all 17 relevant events (payment link/invoice/subscription lifecycle plus real-time downtime signals) as the source of truth for `real_verified` outcomes, with a lightweight polling fallback (`link_status_checker.py`) purely as a safety net against a missed webhook — not as the primary mechanism.

**Rejected approach — client-side/browser-automation-driven "fake customer" checkouts (e.g., Playwright) as the primary data-generation method:** Initially explored, then deliberately dropped in favor of the honest, clearly-labeled `training_simulation` outcome-source approach — automating a browser to impersonate hundreds of customers produced fragile, slow, and (most importantly) architecturally confusing results, since it blurred the line between "real infrastructure" and "simulated actor." Real webhook-driven confirmation for actual test payments plus transparently-labeled synthetic training data was judged more honest and more robust than a large-scale fake-customer simulation layer.

---

## Frontend

### React + Vite
**Why:** Fast dev-server iteration (important given how many dashboard panels were built incrementally throughout this project) and a component model that mapped cleanly onto the many independent, real-data-backed panels (cache metrics, comparison, guardrail activity, ML performance, etc.) without needing a heavier framework's routing/state machinery for what is fundamentally a single-page dashboard.

### Tailwind CSS (utility classes, custom dark theme)
**Why:** Fast to iterate on a consistent dark, data-dense dashboard aesthetic across dozens of small components without maintaining a separate stylesheet per component.

### Recharts
**Why:** Lightweight, React-native charting library sufficient for the bar/pie charts needed (root-cause breakdown, channel distribution) without the bundle-size cost of a heavier visualization library.

---

## Infrastructure & Deployment

### Render (Web Service for backend, Static Site for frontend)
**Why:** Zero-configuration GitHub-integrated auto-deploy on every push, free tier sufficient for a demo-scale project, and native support for both a Python web service and a static frontend build under one platform — avoiding the need to manage two separate hosting providers.

**Known tradeoff, stated honestly:** Render's free tier cold-starts after ~15 minutes of inactivity, requiring a warm-up ping before live demos — a real, acknowledged limitation of the free tier, not hidden.

### APScheduler (BackgroundScheduler)
**Why:** Used to run the ML model retraining job on a real cron schedule (Saturday + Sunday at 11 PM IST) without needing a separate task-queue infrastructure like Celery or a managed cron service. APScheduler runs in-process as a background thread — sufficient for a low-frequency, non-critical maintenance job like weekend retraining, where the simplicity of no external broker dependency outweighs the theoretical benefits of a distributed task queue. The scheduler is started via FastAPI's `lifespan` hook so it starts and stops cleanly with the server process.

**Rejected alternative — Celery + Redis as a task queue:** Evaluated and deferred; Celery adds a broker dependency (Redis or RabbitMQ), worker processes, and operational overhead that is disproportionate for a single scheduled job that runs twice a week. APScheduler's in-process model is the right fit here.

### GitHub Actions (CI/CD)
**Why:** A lightweight `.github/workflows/deploy.yml` workflow triggers Render deploy hooks on every push to `main`, reporting deployment status back to GitHub's native Deployments section. Deploy hook URLs are stored as GitHub Secrets — never hardcoded in the workflow file. This gives full deployment visibility (status, history, environment URLs) directly on the GitHub repo page without needing to check Render's dashboard separately.

**Design choice:** Auto-deploy is disabled on Render itself — GitHub Actions is the single deploy trigger, ensuring every deployment is traceable to a specific commit and visible in one place.

### Docker + docker-compose
**Why:** Included for local reproducibility and to demonstrate containerization readiness, even though Render's native Python buildpack (not the Dockerfile) is what actually serves production — this keeps the deployment simple while still providing a genuine, working path to container-based deployment (e.g., a future Kubernetes migration) without needing it today.

**Explicitly not pursued — full Kubernetes deployment:** Evaluated and deliberately deferred; the operational complexity (cluster provisioning, service/ingress configuration, secrets management) would have consumed disproportionate time relative to its judging value for a project whose core differentiators are its real payment integration and ML rigor, not its orchestration infrastructure. Documented as a legitimate next step for genuine production scale, not a gap we're unaware of.

---

## Testing

### pytest
**Why:** The standard, minimal-friction Python testing framework — chosen specifically to build a real, fast (in-memory SQLite, no external dependencies), automated suite covering the Guardrail Agent's rule logic, including boundary conditions and priority ordering between overlapping rules. This exists precisely because manual, one-off verification (which is how most of this project was initially validated) had already let real bugs slip through more than once during development — the automated suite catches exactly that class of regression going forward.

---

## Summary table

| Layer | Choice | Key reason |
|---|---|---|
| Backend framework | FastAPI | Async, typed, strong ML ecosystem access |
| Orchestration | Plain Python | Fixed linear pipeline — no dynamic graph needed |
| Database | PostgreSQL (Supabase) | Managed, portable via SQLAlchemy, includes Storage |
| LLM | Groq (gpt-oss-20b) | Fast, cost-effective, sufficient for narrow task |
| Caching | Redis (Upstash) | ~97% real API call reduction, serverless |
| ML models | scikit-learn, Logistic Regression | Interpretable, empirically outperforms LightGBM on this dataset size |
| Voice | gTTS | Real, free, no telephony account needed |
| Promise-to-Pay NLP | Groq LLM, structured JSON extraction | Free text/Hinglish intent + relative-date resolution regex can't handle |
| Payments | Razorpay (Test Mode) | Track-mandated; correct dedicated instrument per record type |
| Recovery confirmation | Webhooks (signature-verified) | Matches real production architecture, not polling |
| Frontend | React + Vite + Tailwind + Recharts | Fast iteration, sufficient for a data-dense SPA dashboard |
| Scheduling | APScheduler | In-process cron for weekend retraining — no Celery/broker overhead needed |
| CI/CD | GitHub Actions | Commit-triggered deploys via Render hooks, status visible on GitHub repo |
| Deployment | Render + Docker | Zero-config auto-deploy; container-ready without premature K8s complexity |
| Testing | pytest | Fast, real, catches regressions manual testing missed |