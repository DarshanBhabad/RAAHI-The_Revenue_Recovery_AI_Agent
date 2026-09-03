<div align="center">

# RAAHI — The Revenue Recovery AI Agent

*Detects revenue at risk, diagnoses why, decides the right intervention, and recovers it — every action explainable, bounded, and audited.*

![RAAHI System Architecture](./docs/IMAGES/Raahi_system_architecture.png)

<!-- PLACEHOLDER: demo video link -->
**🎥 Demo Video:** [link here]

<!-- PLACEHOLDER: live demo link -->
**🚀 Live Demo:** [link here] · **📊 Backend API:** [link here]



</div>

---

## Table of Contents

- [The Problem](#the-problem)
- [What RAAHI Actually Does](#what-raahi-actually-does)
- [Architecture](#architecture)
- [The Five Agents](#the-five-agents)
- [What's Genuinely Real vs. What's Modeled](#whats-genuinely-real-vs-whats-modeled)
- [Machine Learning Components](#machine-learning-components)
- [Compliance & Guardrails](#compliance--guardrails)
- [RAAHI vs. Naive Baseline](#raahi-vs-naive-baseline)
- [Tech Stack](#tech-stack)
- [Setup & Reproduction](#setup--reproduction)
- [Testing](#testing)
- [Dashboard Features](#dashboard-features)
- [Known Limitations & What's Next](#known-limitations--whats-next)
- [Project Structure](#project-structure)

---

## The Problem

Revenue loss rarely happens in one clean step. A payment degrades, a checkout gets abandoned, a subscription fails, or an invoice goes overdue — each needs a different diagnosis and a different response. Most businesses handle this with the same generic reminder sent to everyone, on a fixed schedule, with no way to tell whether a customer opted out, already promised to pay, or has simply exhausted every reasonable retry.

RAAHI closes this loop: **detect → diagnose → decide → gate → recover**, with every decision logged, explainable, and bounded by deterministic safety rules.

## What RAAHI Actually Does

RAAHI implements all seven example directions from the track brief, with real, working infrastructure behind each one — not mockups:

| Direction | Implementation |
|---|---|
| **Payment degradation → root cause → recovery action** | Real root-cause classification (rule-based + ML + LLM blend), real Razorpay Payment Link creation |
| **Checkout drop-off recovery** | Dedicated `checkout_abandoned` root cause with fast-response, low-friction policy |
| **Failed-subscription recovery** | Real Razorpay Plan + Subscription objects created via API |
| **B2B receivables chaser** | Real Invoice API, staged reminders scaled to days overdue |
| **Mandate retry sequencer** | Attempt-limit and cooldown enforcement on subscription recovery attempts |
| **Hinglish voice recovery** | Real LLM-generated Hinglish scripts, converted to real playable Hindi audio (gTTS), stored and served from Supabase Storage |
| **Promise-to-pay tracker** | Real NLP intent extraction (Groq LLM) on free-text customer replies — correctly extracts commitment dates from natural language, including Hinglish, and correctly rejects vague/negative replies |

## Architecture

See [`docs/Architecture Diagrams.md`](./docs/Architecture%20Diagrams.md) for the full set of diagrams — system architecture, sequence flow, use case, ER/database schema, guardrail decision flow, and deployment architecture.

At a high level:

```
Synthetic Data / Real Checkout
        │
        ▼
┌───────────────────────────────────────────────────┐
│  Detection → Diagnosis → Decision → Guardrail →    │
│  Execution                                          │
└───────────────────────────────────────────────────┘
        │                          │
        ▼                          ▼
  PostgreSQL (Supabase)      Razorpay APIs
        │                    (Payment Links, Invoices,
        ▼                     Subscriptions, Orders)
  React Dashboard                   │
                                     ▼
                            Webhook Receiver
                        (signature-verified, 17 events)
                                     │
                                     ▼
                        Updates real transaction status
```

## The Five Agents

1. **Detection Agent** — scans for records in `at_risk` or `recovering` status that are currently eligible (respecting `next_eligible_at`, which is set by guardrails, promises, and DND deferrals). Writes the first audit trail entry.

2. **Diagnosis Agent** — classifies root cause via a deterministic lookup table, then computes a confidence score by blending three signals: rule-based confidence, a calibrated Logistic Regression ML model, and an LLM-generated narrative confidence — combined via a **learned meta-blend model** (not hand-picked weights). Also detects systemic events (e.g., if >35% of a batch shares one root cause, flags it as a likely bank/issuer-side outage rather than isolated customer problems).

3. **Decision Agent** — maps root cause to an intervention (retry, payment link, reminder tier), applies cost-aware channel selection (never spends more on contact than the transaction is worth), applies customer-segment adjustments, and schedules the retry using an **ML-learned optimal timing model** rather than a fixed delay.

4. **Guardrail Agent** — the deterministic safety gate. **Zero LLM involvement** — pure rule checks, in strict priority order:
   - Active promise-to-pay suppression
   - Attempt-limit enforcement
   - Escalation ceiling (hard stop at 3 automated attempts, forces human review)
   - Relationship guard (high-value customers downgraded to a gentler channel on repeat contact)
   - Cooldown period
   - Real-time payment-method downtime (via Razorpay's own webhook signal, not inferred)
   - DND window (9 PM–9 AM IST)

   Every check writes a machine-readable violation code (`ATTEMPT_LIMIT_EXCEEDED`, `PROMISE_ACTIVE`, `RELATIONSHIP_GUARD`, etc.) to the audit trail.

5. **Execution Agent** — creates the real Razorpay instrument (Payment Link, Invoice, or Subscription+Plan), generates real Hinglish voice messages where the channel is `voice`, and lets Razorpay's native notification system handle real SMS/email delivery. Recovery confirmation comes entirely from the **webhook receiver**, not from polling or assumption.

## What's Genuinely Real vs. What's Modeled

This project makes a deliberate, honest distinction, tracked via an `outcome_source` field on every transaction:

- **`real_verified`** — outcome confirmed by an actual Razorpay webhook (a real payment happened)
- **`modeled`** — outcome not yet known; record is genuinely awaiting real customer action
- **`training_simulation`** — outcome synthetically labeled *only* to provide training data for ML models, using a documented, multi-factor probability model (never counted in headline recovery metrics)

We validated the entire real-payment path end-to-end: a real payment link was paid with a real Razorpay test card, the real webhook fired, signature verification passed, and the transaction correctly updated to `recovered`. We also validated genuine failure capture: a real checkout attempt was deliberately failed, and Razorpay's real `payment.failed` webhook delivered the actual decline reason (`international_transaction_not_allowed`), which RAAHI mapped correctly into its internal root-cause taxonomy.

## Machine Learning Components

Three real, independently evaluated models:

| Model | Purpose | Result |
|---|---|---|
| **Confidence Model** (Logistic Regression, calibrated via `CalibratedClassifierCV`) | Predicts recovery probability from root cause, amount, attempts, segment | 5-fold CV ROC-AUC: ~0.63–0.65 (honestly modest — synthetic data, not years of production traffic) |
| **Meta-Blend Model** | Learns optimal weighting between rule-based, ML, and LLM confidence signals, replacing hand-picked weights | 0.655 CV-ROC-AUC vs. 0.626 for the fixed-weight blend it replaced — a real, validated improvement |
| **Retry-Timing Model** | Learns the best hour-of-day to retry, per root cause | Correctly rediscovers documented ground-truth timing patterns from noisy synthetic attempt data (up to +173% predicted improvement vs. fixed-time baseline) |

We also directly compared Logistic Regression against LightGBM on the same data (same preprocessing, same cross-validation) — Logistic Regression won (0.626 vs. 0.569 CV-AUC), consistent with the dataset's size, and was kept for production for that reason plus its coefficient-level interpretability.

**Models retrain automatically** every weekend at 11 PM IST (a realistic low-traffic maintenance window), as real webhook-confirmed outcomes accumulate. The retry-timing model is deliberately excluded from this schedule, since it trains on static synthetic ground truth rather than accumulating real data.

**LLM efficiency**: diagnostic reasoning is cached (Redis/Upstash) per `(record_type, failure_reason_code)` pair — since these combinations are finite, this reduced real Groq API calls by ~97–99% across large batches with zero loss in reasoning quality.

## Compliance & Guardrails

RAAHI's Guardrail Agent is intentionally kept free of any LLM — every check is a deterministic function, fully testable in isolation (see [Testing](#testing)). Every verdict is tagged with a machine-readable violation code and written to the audit trail, so any action can be traced back to the exact rule that approved, deferred, or blocked it.

## RAAHI vs. Naive Baseline

To make the intelligence layer's value measurable rather than asserted, we built a parallel **naive baseline**: the same starting synthetic batch, processed with no diagnosis, no segmentation, no guardrails — a fixed retry sent to everyone regardless of context. Results:

| Metric | RAAHI (Intelligent) | Naive Baseline |
|---|---|---|
| Exceptions caught | 34 | 0 |
| Opted-out customers protected | 31 | 0 |
| Exhausted-retry loops stopped | 3 | 0 |
| Channels used (diversity) | 4 | 0 (single fixed channel) |

Naive's zero exception count isn't better performance — it has no mechanism to detect customers who opted out or retries that should stop, meaning it would keep contacting people it shouldn't. RAAHI's exceptions represent real, measurable protection.

## Tech Stack

See [`docs/Tech stack .md`](./docs/Tech%20stack%20.md) for the full breakdown with justifications for every choice.

## Setup & Reproduction

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # fill in your real Razorpay, Groq, Supabase, Redis keys
python -m app.db.init_db
python -m data_generator.reset_and_regenerate
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Docker (local reproducibility)

```bash
docker compose up --build
```

### Reproducing our metrics

```bash
python -m app.ml.train_confidence_model      # confidence model + Brier score + CV-AUC
python -m app.ml.compare_models              # Logistic Regression vs. LightGBM comparison
python -m app.ml.train_meta_blend            # learned blend weights
python -m app.ml.train_retry_timing_model    # retry-timing improvement table
```

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

16 automated tests covering the Guardrail Agent's happy path, boundary conditions (zero amount, missing customer, exact-boundary promise dates), and priority ordering between overlapping rules (e.g., confirming the Escalation Ceiling correctly takes priority over the Relationship Guard once both conditions are met).

## Dashboard Features

- Real-time summary metrics, recovery-by-root-cause chart, honest outcome-source breakdown
- Full audit trail per transaction (every stage, every reasoning string, every violation code)
- Exception list with real protection reasons
- RAAHI vs. Naive Baseline comparison, live
- LLM cache efficiency metrics
- ML model performance (CV-AUC, Brier score, sample sizes) — real, reproducible
- Retry-timing model recommendations vs. baseline
- Guardrail activity panel (approved/deferred/blocked breakdown with real reasons)
- Multi-merchant filtering (D2C, SaaS, B2B — proves the agent generalizes, not hardcoded)
- Live NLP promise-to-pay chat demo — type a real customer reply, get a real extracted commitment
- Real Hinglish voice message playback
- Real Checkout form — enter real customer details, generate a real Razorpay order and checkout page, deliberately fail it, and watch RAAHI capture the genuine decline reason via webhook

## Known Limitations & What's Next

We'd rather state these plainly than have them discovered:

- **Subscription mandate authorization** requires a genuine one-time customer UI interaction that can't be simulated server-side; RAAHI creates real Plan/Subscription objects up to that point and falls back to targeted payment links for the parts that need a live customer.
- **WhatsApp and voice-calling channels** are fully designed and cost-modeled in the Decision layer; WhatsApp delivery and live voice calls require a separate telephony/messaging provider account beyond Razorpay's APIs, which we deliberately scoped out to avoid a hollow, unverifiable integration — SMS and email (both genuinely delivered via Razorpay's native notifications) and generated voice audio cover the same intent.
- **The learned meta-blend and confidence models** are trained on synthetic data with documented, multi-factor structure — not years of real production traffic. We report cross-validated metrics honestly (including modest ones) rather than cherry-picking a favorable split.
- **Real-time observability infrastructure** (Prometheus/Grafana) would be a standard addition once RAAHI runs against continuous live merchant traffic — not meaningful for a batch-oriented demo with no sustained request volume to monitor, so we prioritized application-level metrics (which are real and shown throughout the dashboard) instead.
- **Order-level checkout-abandonment linkage** (tying a specific abandoned cart to a specific downstream recovery record) depends on integration with a merchant's actual storefront, which is outside RAAHI's boundary as a downstream recovery layer.

## Project Structure

```
raahi-revenue-recovery-agent/
├── backend/
│   ├── app/
│   │   ├── agents/          # detection, diagnosis, decision, guardrail, execution
│   │   ├── ml/               # model training scripts, model artifacts
│   │   ├── policies/         # retry policy, cost config, guardrail rules
│   │   ├── routers/          # FastAPI routes (records, dashboard, webhooks, checkout)
│   │   ├── services/         # razorpay client, llm service, voice service, cache
│   │   ├── orchestrator/     # pipeline runner, retrain scheduler
│   │   └── models/           # SQLAlchemy models
│   ├── data_generator/       # synthetic data generation
│   ├── tests/                # pytest suite
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── components/       # dashboard panels, chat demo, real checkout form
│       └── pages/
├── docs/
│   ├── Architecture Diagrams.md
│   ├── README.md
│   └── TECH_STACK.md
└── docker-compose.yml
```

---

<div align="center">

Built by Darshan

</div>
