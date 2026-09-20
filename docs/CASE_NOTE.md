# Case note — Momentum + Trend vs Buy & Hold VTI

**One page.** For interviews and portfolio pages.  
**Not a recommendation to invest.** Historical simulation only.

---

## Hypothesis

Assets that are (1) above a long moving average and (2) showing positive intermediate-horizon total return have historically tended, in some markets and periods, to continue outperforming for a time.  
If nothing qualifies, hold a short-duration Treasury ETF (SHY) or cash.

This is a **classic** academic/practitioner idea (cross-sectional / time-series momentum + trend filter), not a proprietary claim of edge.

## Method

| Piece | Choice |
| --- | --- |
| Universe | VTI, QQQ, IWM, EFA, EEM, TLT, GLD · safe = SHY · benchmark = VTI |
| Trend | Close > 200-session SMA |
| Momentum | Trailing total return over 126 sessions; must be > 0 |
| Selection | Top 2 by momentum · equal weight |
| Rebalance | Month-end signal → fill next session **open** |
| Costs | 5 bps of notional, each side |
| Risk | Max ~90% invested · 10% cash buffer · 50% max per risk asset · no leverage/shorts |
| Prices | Yahoo split/dividend-adjusted daily bars |
| Capital (study) | $10,000 starting |

Buy & Hold VTI is run as a **fully invested** simple alternative (not passed through the same cash buffer), so part of any return gap can be **cash drag**, not only signal quality.

## Validation design

| Window | Dates | Purpose |
| --- | --- | --- |
| Development | 2010–2019 | Inspect the hypothesis |
| Validation | 2020 → latest | Same **frozen** parameters |

No grid search. No “best Sharpe” hunt in V0.1.

## Illustrative results (Yahoo cache, as of sample run)

Rounded; regenerate with `python scripts/sample_backtest.py`. Numbers will move if Yahoo revises history.

| Path (full sample ~2010→2026) | End ($10k start) | CAGR | Vol | Sharpe | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Momentum + Trend (+ risk) | ~$35k | ~7.9% | ~12.9% | ~0.65 | ~−28% |
| VTI Buy & Hold | ~$87k | ~13.9% | ~17.4% | ~0.83 | ~−35% |

**Reading:** In this window the rule was **less wealthy** than buy-and-hold VTI, with **lower volatility and shallower max drawdown**, under a cash buffer the benchmark did not share. That is evidence for **discussion**, not for superiority.

Development vs validation can diverge; divergence is a warning about regime dependence / overfitting risk, not a license to retune after seeing the answer.

## Limitations

- Yahoo is delayed and vendor-adjusted; not a production feed  
- Next-open fill model; flat bps costs; no impact / partial fills  
- Small ETF universe; equal weight only  
- Risk overlay changes the investable set vs pure strategy weights  
- One hypothesis; no factor orthogonalization, vol targeting, or walk-forward yet  

## Engineering takeaway (the interview point)

The useful artifact is the **system**:

- Owned backtester with an explicit time contract  
- Look-ahead prevented in code and proven with synthetic tests  
- Risk as a separate layer that can override  
- Broker abstraction with paper persistence  
- UI that cannot smuggle trading logic  

A future live broker implements the same `Broker` interface; strategies stay untouched.

---

*Paper research environment. Not investment advice. Past simulation ≠ future results.*
