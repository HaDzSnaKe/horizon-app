"""
Horizon - portfolio engine.

Everything financial lives here; app.py only handles the screens.

    load_data()            monthly prices + returns (CSV files from the data notebook)
    build_profiles()       5 model portfolios (mean-variance, one per risk level)
    backtest()             historical growth of a portfolio, rebalanced monthly
    profile_at()           glide path: risk level allowed for the years left
    simulate_goal()        Monte Carlo projection of the goal
    rebalancing_example()  how weights drift over 12 months and the trades to fix it
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

# --------------------------------------------------------------------------
# Universe metadata (codes match the columns of the data files)
# --------------------------------------------------------------------------
ASSETS = {
    "WORLD": "iShares Core MSCI World",
    "EM":    "iShares Core MSCI EM IMI",
    "REIT":  "iShares Dev. Markets Property Yield",
    "CORP":  "iShares Core € Corp Bond",
    "GOVT":  "iShares Core € Govt Bond",
    "ILB":   "iShares € Inflation Linked Govt Bond",
    "SHORT": "iShares € Govt Bond 1-3yr",
    "GOLD":  "iShares Physical Gold",
}
ASSET_CLASS = {
    "WORLD": "Equity", "EM": "Equity", "REIT": "Equity",
    "CORP": "Bonds", "GOVT": "Bonds", "ILB": "Bonds", "SHORT": "Bonds",
    "GOLD": "Gold",
}
EQUITY = [a for a, c in ASSET_CLASS.items() if c == "Equity"]

# Maximum weight per ETF - keeps every portfolio diversified
CAPS = {"WORLD": 0.70, "EM": 0.20, "REIT": 0.10, "CORP": 0.40,
        "GOVT": 0.40, "ILB": 0.20, "SHORT": 0.60, "GOLD": 0.10}

# Risk levels: name, equity band, risk aversion (higher = more cautious)
PROFILES = {
    1: {"name": "Defensive",    "equity": (0.10, 0.25), "lambda": 12.0},
    2: {"name": "Conservative", "equity": (0.25, 0.45), "lambda": 8.0},
    3: {"name": "Balanced",     "equity": (0.45, 0.65), "lambda": 5.0},
    4: {"name": "Growth",       "equity": (0.65, 0.80), "lambda": 3.0},
    5: {"name": "Dynamic",      "equity": (0.80, 0.95), "lambda": 2.0},
}

# Glide path: years left before the goal -> highest risk level allowed
GLIDE_PATH = [(3, 1), (5, 2), (7, 3), (10, 4)]   # <3y: 1, <5y: 2, <7y: 3, <10y: 4

REBALANCING_BAND = 0.05                          # +/- 5 percentage points

# Expected returns: history alone (2014-2026) is too optimistic for equities
# and gold, so we blend it with long-term assumptions ("shrinkage").
# These are the team's annual assumptions - adjust and justify in the memo.
LONG_TERM_RETURNS = {"WORLD": 0.070, "EM": 0.075, "REIT": 0.065, "CORP": 0.030,
                     "GOVT": 0.025, "ILB": 0.025, "SHORT": 0.020, "GOLD": 0.035}
SHRINKAGE = 0.5                                  # weight on the long-term assumptions

BIG_LOSS = 0.10                                  # "large loss" used to show the glide path's protection
FINAL_YEARS = 3                                  # ... measured over the last 3 years before the goal


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def find_data_dir(app_dir: Path) -> Path | None:
    for d in (app_dir / "data", app_dir):
        if (d / "horizon_returns_monthly.csv").exists() and (d / "horizon_prices_monthly.csv").exists():
            return d
    return None


def load_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    read = lambda f: pd.read_csv(data_dir / f, index_col="date", parse_dates=True)
    prices, returns = read("horizon_prices_monthly.csv"), read("horizon_returns_monthly.csv")
    missing = [a for a in ASSETS if a not in returns.columns]
    if missing:
        raise ValueError(f"Missing ETFs in the data files: {', '.join(missing)}")
    cols = list(ASSETS)
    return prices[cols], returns[cols]


def historical_returns(returns: pd.DataFrame) -> pd.Series:
    """Annualised arithmetic mean of the historical monthly returns."""
    return returns.mean() * 12


def asset_stats(returns: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Expected returns (history blended with long-term assumptions) and covariance."""
    lt = pd.Series(LONG_TERM_RETURNS)[returns.columns]
    mu = (1 - SHRINKAGE) * historical_returns(returns) + SHRINKAGE * lt
    return mu, returns.cov() * 12


# --------------------------------------------------------------------------
# Model portfolios - mean-variance with an equity band per profile
#   maximise  mu'w - lambda/2 * w'Sigma w
#   s.t.      sum(w) = 1, 0 <= w_i <= cap_i, equity share within the band
# --------------------------------------------------------------------------
def optimise(mu: pd.Series, cov: pd.DataFrame, profile: int) -> pd.Series:
    p = PROFILES[profile]
    assets = list(mu.index)
    m, S = mu.values, cov.values
    eq = np.array([a in EQUITY for a in assets], dtype=float)
    lo, hi = p["equity"]

    objective = lambda w: -(m @ w - 0.5 * p["lambda"] * w @ S @ w)
    constraints = [
        {"type": "eq",   "fun": lambda w: w.sum() - 1},
        {"type": "ineq", "fun": lambda w: eq @ w - lo},
        {"type": "ineq", "fun": lambda w: hi - eq @ w},
    ]
    bounds = [(0.0, CAPS[a]) for a in assets]
    # feasible starting point: middle of the equity band, rest in bonds
    x0 = np.where(eq == 1, (lo + hi) / 2 / eq.sum(), (1 - (lo + hi) / 2) / (len(assets) - eq.sum()))
    res = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"maxiter": 500, "ftol": 1e-12})
    w = np.clip(res.x, 0, None)
    w[w < 0.005] = 0                      # drop dust positions below 0.5%
    w = w / w.sum()
    return pd.Series(w, index=assets)


def build_profiles(returns: pd.DataFrame) -> dict:
    """Weights and expected statistics for the five model portfolios."""
    mu, cov = asset_stats(returns)
    out = {}
    for k in PROFILES:
        w = optimise(mu, cov, k)
        exp_ret = float(mu @ w)
        vol = float(np.sqrt(w @ cov @ w))
        out[k] = {
            "weights": w,
            "exp_return": exp_ret,            # arithmetic, annual
            "volatility": vol,                # annual
            "monthly_mean": exp_ret / 12,
            "monthly_vol": vol / np.sqrt(12),
            "equity_share": float(w[EQUITY].sum()),
        }
    return out


# --------------------------------------------------------------------------
# Backtest
# --------------------------------------------------------------------------
def backtest(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Growth of 100 with monthly rebalancing to the target weights."""
    r = returns[weights.index] @ weights
    growth = 100 * (1 + r).cumprod()
    start = growth.index[0] - pd.offsets.MonthEnd(1)
    return pd.concat([pd.Series([100.0], index=[start]), growth])


def performance(growth: pd.Series) -> dict:
    r = growth.pct_change().dropna()
    years = len(r) / 12
    return {
        "Annualised return": (growth.iloc[-1] / growth.iloc[0]) ** (1 / years) - 1,
        "Volatility": r.std() * np.sqrt(12),
        "Max drawdown": (growth / growth.cummax() - 1).min(),
        "Worst 12 months": (growth / growth.shift(12) - 1).min(),
    }


BENCHMARK = pd.Series({"WORLD": 0.60, "GOVT": 0.40})   # classic 60/40


# --------------------------------------------------------------------------
# Glide path
# --------------------------------------------------------------------------
def profile_at(years_left: float, base_profile: int) -> int:
    """Risk level used when `years_left` remain before the goal."""
    for limit, cap in GLIDE_PATH:
        if years_left < limit:
            return min(base_profile, cap)
    return base_profile


def glide_path_table(base_profile: int, years: int, profiles: dict) -> pd.DataFrame:
    """Weights at the start of each year until the goal."""
    rows = {}
    for y in range(years):
        rows[y] = profiles[profile_at(years - y, base_profile)]["weights"]
    df = pd.DataFrame(rows).T
    df.index.name = "Year"
    return df


# --------------------------------------------------------------------------
# Monte Carlo
# --------------------------------------------------------------------------
T_DF = 5   # Student-t degrees of freedom: fatter tails than the normal, so crashes are more frequent


def simulate_goal(initial: float, monthly: float, years: int, base_profile: int,
                  profiles: dict, n_paths: int = 5000, glide: bool = True,
                  seed: int = 7, return_growth: bool = False):
    """
    Simulated wealth, shape (months + 1, n_paths). Monthly log-returns have
    the mean and volatility of the portfolio in force that month (the glide
    path changes it as the goal gets closer) and fat-tailed Student-t shocks.
    Contributions are added at the end of each month. A fixed seed keeps the
    results stable when the user moves a slider.
    With return_growth=True, also returns the monthly market growth factors
    (months, n_paths), used to measure losses independently of contributions.
    """
    months = int(round(years * 12))
    rng = np.random.default_rng(seed)
    shocks = rng.standard_t(T_DF, size=(months, n_paths)) / np.sqrt(T_DF / (T_DF - 2))  # unit variance
    wealth = np.empty((months + 1, n_paths))
    growth = np.empty((months, n_paths))
    wealth[0] = initial
    for t in range(months):
        k = profile_at((months - t) / 12, base_profile) if glide else base_profile
        m, s = profiles[k]["monthly_mean"], profiles[k]["monthly_vol"]
        sigma = np.sqrt(np.log(1 + s ** 2 / (1 + m) ** 2))   # lognormal with mean m, sd s
        mu_log = np.log(1 + m) - sigma ** 2 / 2
        growth[t] = np.exp(mu_log + sigma * shocks[t])
        wealth[t + 1] = wealth[t] * growth[t] + monthly
    return (wealth, growth) if return_growth else wealth


def big_loss_probability(growth: np.ndarray, loss: float = BIG_LOSS, years: int = FINAL_YEARS) -> float:
    """Share of paths whose portfolio loses more than `loss` over the final `years` before the goal."""
    window = growth[-min(years * 12, growth.shape[0]):]
    return float((window.prod(axis=0) < 1 - loss).mean())


def goal_summary(wealth: np.ndarray, target: float, initial: float, monthly: float) -> dict:
    final = wealth[-1]
    months = wealth.shape[0] - 1
    return {
        "probability": float((final >= target).mean()),
        "median": float(np.median(final)),
        "p10": float(np.percentile(final, 10)),
        "p90": float(np.percentile(final, 90)),
        "invested": initial + monthly * months,
    }


def required_monthly(initial: float, years: int, target: float, base_profile: int,
                     profiles: dict, prob: float = 0.75) -> float | None:
    """Smallest monthly contribution reaching `target` with probability `prob`."""
    def p(c):
        w = simulate_goal(initial, c, years, base_profile, profiles, n_paths=2000)
        return (w[-1] >= target).mean()
    lo, hi = 0.0, max(target / max(years * 12, 1), 100.0)
    if p(lo) >= prob:
        return 0.0
    for _ in range(20):                      # make sure hi is enough
        if p(hi) >= prob:
            break
        hi *= 2
    else:
        return None
    for _ in range(25):                      # bisection to about 1 euro
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if p(mid) >= prob else (mid, hi)
        if hi - lo < 1:
            break
    return float(np.ceil(hi))


# --------------------------------------------------------------------------
# Rebalancing illustration
# --------------------------------------------------------------------------
def drift_over(returns: pd.DataFrame, weights: pd.Series, start: pd.Timestamp,
               months: int = 12) -> pd.DataFrame:
    """Weights after `months` without rebalancing, starting on target at `start`."""
    window = returns.loc[returns.index > start].iloc[:months]
    value = weights * (1 + window[weights.index]).prod()
    drifted = value / value.sum()
    df = pd.DataFrame({"Target": weights, "After 12 months": drifted})
    df["Drift (pp)"] = (df["After 12 months"] - df["Target"]) * 100
    df["Trade to rebalance (% of portfolio)"] = (df["Target"] - df["After 12 months"]) * 100
    return df[df["Target"] > 0]


def largest_drift_start(returns: pd.DataFrame, weights: pd.Series, months: int = 12) -> pd.Timestamp:
    """Start month whose 12-month window produced the largest drift (for the demo)."""
    starts = returns.index[:-months]
    if len(starts) == 0:
        return returns.index[0]
    drifts = [drift_over(returns, weights, s, months)["Drift (pp)"].abs().max() for s in starts]
    return starts[int(np.argmax(drifts))]
