"""Plain-English and technical definitions. No investment advice."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    name: str
    plain: str
    technical: str


GLOSSARY: dict[str, Term] = {
    "etf": Term(
        "ETF",
        "A fund you can buy like a stock that owns a basket of investments.",
        "An exchange-traded fund is a pooled vehicle whose shares trade on an exchange and typically track an index or other published rules.",
    ),
    "ticker": Term(
        "Ticker",
        "The short symbol used to identify a listed instrument (for example VTI).",
        "An exchange symbol uniquely identifying a listed security in market-data and order systems.",
    ),
    "close": Term(
        "Close",
        "The official end-of-day price for a trading session.",
        "The session's official closing print. In this system, signals dated T use the close of T and are not tradable until the next session.",
    ),
    "adjusted_price": Term(
        "Adjusted price",
        "A price series that has been restated so dividends and splits do not create fake jumps.",
        "Split- and dividend-adjusted OHLC (Yahoo auto_adjust). Appropriate for total-return research. This is the series Quant Lab uses for signals and backtests.",
    ),
    "momentum": Term(
        "Momentum",
        "An asset that has recently been rising tends, statistically in some historical settings, to continue outperforming for some period. We measure this rather than assume it.",
        "Trailing total return over a fixed lookback, price(T)/price(T-M)-1. Eligibility in V0.1 requires this value to be strictly positive.",
    ),
    "trend": Term(
        "Trend filter",
        "A simple rule that asks whether price is above a long moving average.",
        "close(T) > SMA_N(T). Default N = 200 trading sessions. The SMA at T uses prices through T only.",
    ),
    "sma": Term(
        "Moving average",
        "The average price over the last N days. It smooths noise.",
        "Simple moving average with min_periods=N. A value at T is the mean of the last N closes including T.",
    ),
    "volatility": Term(
        "Volatility",
        "How strongly the price moves around.",
        "Annualized standard deviation of daily simple returns, using 252 sessions per year unless configured otherwise.",
    ),
    "drawdown": Term(
        "Drawdown",
        "The percentage decline from the portfolio's previous high.",
        "equity(T)/cummax(equity)-1. Maximum drawdown is the minimum of that series.",
    ),
    "sharpe": Term(
        "Sharpe ratio",
        "Return relative to the amount of volatility taken.",
        "Mean excess daily return divided by the standard deviation of daily returns, then multiplied by sqrt(252). V0.1 uses a configurable risk-free rate (default 0).",
    ),
    "sortino": Term(
        "Sortino ratio",
        "Like Sharpe, but it only penalizes downside moves.",
        "Mean excess return divided by the standard deviation of negative daily returns, annualized by sqrt(252).",
    ),
    "cagr": Term(
        "CAGR",
        "The constant annual growth rate that would take starting capital to ending capital.",
        "(end/start)^(1/years)-1 with years = n_obs / 252.",
    ),
    "calmar": Term(
        "Calmar ratio",
        "Growth rate compared with the worst peak-to-trough decline.",
        "CAGR / |maximum drawdown|. Undefined if drawdown is zero or CAGR is undefined.",
    ),
    "backtest": Term(
        "Backtest",
        "A simulation of how rules would have behaved using historical data.",
        "Walk-forward application of a dated rule set to historical prices, with explicit execution lag and costs. A backtest is not evidence of future profitability.",
    ),
    "look_ahead": Term(
        "Look-ahead bias",
        "Accidentally using information you would not have had at the time. It makes a strategy look better than it was.",
        "Using X_{T+k}, k>0, in a decision dated T, or earning T's return from a signal that requires the close of T. Quant Lab forbids this architecturally.",
    ),
    "overfitting": Term(
        "Overfitting",
        "Fitting rules so tightly to one historical stretch that they fail on the next stretch.",
        "In-sample performance that does not persist out of sample. V0.1 reports development and validation windows separately and does not search for 'best' parameters.",
    ),
    "development": Term(
        "Development period",
        "The earlier historical window used to inspect a hypothesis.",
        "Default 2010–2019. Parameters must not be changed after seeing validation results if you want an honest split.",
    ),
    "validation": Term(
        "Validation period",
        "A later window used to see whether the same unchanged rules still behave similarly.",
        "Default 2020–present. Good development and bad validation is a warning of overfitting, not a license to retune.",
    ),
    "paper_trading": Term(
        "Paper trading",
        "Simulated orders and fills. No real money moves.",
        "Orders are sent only to PaperBroker and persisted locally. V0.1 cannot place live brokerage orders.",
    ),
    "cash_buffer": Term(
        "Cash buffer",
        "A forced uninvested fraction so the book is never fully deployed.",
        "Default 10%. Combined with max gross exposure 90%. The risk engine, not the strategy, enforces this.",
    ),
    "gross_exposure": Term(
        "Gross exposure",
        "How much of the portfolio is invested, ignoring the sign of positions.",
        "Sum of absolute position weights. V0.1 is long-only, so this equals the invested fraction.",
    ),
    "rebalance": Term(
        "Rebalance",
        "Trading to move the portfolio toward a new target mix.",
        "For Momentum + Trend, a new target is computed on the last session of each month and filled at the next open.",
    ),
    "transaction_cost": Term(
        "Transaction cost",
        "An estimate of what it costs to trade, not just the price you see.",
        "V0.1 charges a configurable number of basis points on notional, default 5 bps each side. No spread, impact, or partial-fill model yet.",
    ),
    "basis_point": Term(
        "Basis point",
        "One hundredth of a percent. 5 bps = 0.05%.",
        "1 bp = 1e-4. A 5 bp cost on $1,000 notional is $0.50.",
    ),
    "vti": Term(
        "VTI",
        "A fund that owns a very broad slice of the US stock market. Our default benchmark.",
        "Vanguard Total Stock Market ETF. Buy-and-hold VTI is the simple alternative every research strategy is compared against.",
    ),
    "safe_asset": Term(
        "Safe asset",
        "The fallback holding when nothing in the universe qualifies. Here, short-term Treasuries (SHY) or cash.",
        "Configured default SHY. Used when the eligible momentum/trend set is empty or history is insufficient.",
    ),
}


def get_term(key: str) -> Term | None:
    return GLOSSARY.get(key.lower())
