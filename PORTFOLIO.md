# Portfolio pack — Quant Lab

Use this folder when applying to **quant research**, **quant developer**, **systematic trading**, or **fintech platform** roles.

This project is a **portfolio system**, not a claim of trading edge.

---

## 30-second pitch

**Quant Lab** is a personal quantitative research and paper-trading engine.  
It separates **data → features → strategy → portfolio construction → risk → broker**, owns its backtester, enforces no look-ahead bias in tests, and simulates execution with a paper broker — so a future live broker can plug in without rewriting the core.

Stack: Python 3.11+, Pandas, NumPy, SciPy, Pydantic, SQLite, Streamlit, pytest.

---

## Links (fill after publish)

| Asset | URL |
| --- | --- |
| GitHub | https://github.com/caalopezgo/quantlab |
| Live demo | _run `docs/PUBLISH_CHECKLIST.md` step 2_ |
| Architecture | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Case note | [`docs/CASE_NOTE.md`](docs/CASE_NOTE.md) |
| Website copy | [`docs/WEBSITE_SECTION.md`](docs/WEBSITE_SECTION.md) |
| Screenshots | [`docs/images/`](docs/images/) |
| Publish steps | [`docs/PUBLISH_CHECKLIST.md`](docs/PUBLISH_CHECKLIST.md)

---

## What to say in interviews

**Lead with engineering judgment, not returns.**

Good:
> I built an owned research pipeline where strategies cannot talk to brokers, the risk engine can override proposals, and look-ahead is prevented architecturally and covered by synthetic tests.

Avoid:
> My momentum strategy beat the market / is profitable / is AI-powered.

If asked about the sample backtest: show the comparison to buy-and-hold VTI, the development/validation split, cash drag from risk limits, and that historical paths are not forecasts.

---

## Checklist before sharing externally

- [x] Hire-me blurb at top of README
- [x] Architecture doc + diagram
- [x] One-page case note
- [x] Website section copy
- [x] Screenshots of Home + Research
- [x] GitHub Actions (`pytest`)
- [x] Streamlit Cloud config (`requirements.txt`, `.streamlit/`)
- [x] Local git commit on `main`
- [x] Public GitHub repository: https://github.com/caalopezgo/quantlab
- [ ] Deploy Streamlit Community Cloud from that repo
- [ ] Paste live demo URL into this file and the website

---

## Role-specific emphasis

| Role | Emphasize |
| --- | --- |
| Quant / systematic | Look-ahead tests, OOS split, costs, risk overlay, no optimizer |
| Quant developer / platform | Interfaces, DI, PaperBroker → future live broker, SQLite repos |
| Data scientist → finance | Measurable features, explainable decisions, no LLM→order path |
| Fintech product eng | Service layer, UI without financial logic, paper safety |

---

## Disclaimer (always include)

Research and paper trading only. Not investment advice. A backtest is not evidence of future profitability. V0.1 cannot place real-money orders.
