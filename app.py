"""
Horizon - goal-based robo-advisor (FIN127 prototype).

Run:  streamlit run app.py
Data: horizon_prices_monthly.csv and horizon_returns_monthly.csv in ./data
      (produced by the horizon_etf_data notebook)
"""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import engine as E
import ui as U

st.set_page_config(page_title="Horizon", page_icon="🌅", layout="wide")

APP_DIR = Path(__file__).parent
COLORS = U.ASSET_COLORS
ACCENT, MUTED = U.INK, "#A9B4C2"
PLOT_CONFIG = {"displayModeBar": False}
REALISTIC_MONTHLY = 3_000   # above this, a target is treated as out of reach for a retail saver
PAGES = ["1 · Your goal", "2 · Risk profile", "3 · Your portfolio", "4 · Goal tracking"]


# --------------------------------------------------------------------------
# State: values survive switching pages (Streamlit drops widget state
# for widgets that are not on screen, so we keep our own copy).
# --------------------------------------------------------------------------
DEFAULTS = {
    "page": PAGES[0],
    "goal_name": "Buy a home",
    "target": 50_000,
    "years": 10,
    "initial": 10_000,
    "monthly": 250,
    "profile_override": None,
}


def init_state():
    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)


def bind(key):
    """Widget kwargs that read from and write back to st.session_state[key]."""
    wkey = f"_w_{key}"
    st.session_state[wkey] = st.session_state[key]

    def _sync():
        st.session_state[key] = st.session_state[wkey]
    return {"key": wkey, "on_change": _sync}


def go_to(page):
    st.session_state.page = page


def eur(x):
    return f"€{x:,.0f}".replace(",", " ")


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def prob(x):
    """Probabilities are never shown as certain: > 99% / < 1%."""
    if x >= 0.995:
        return "> 99%"
    if x < 0.005:
        return "< 1%"
    return f"{x * 100:.0f}%"


# --------------------------------------------------------------------------
# Data (cached)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_data():
    data_dir = E.find_data_dir(APP_DIR)
    if data_dir is None:
        return None
    prices, returns = E.load_data(data_dir)
    return prices, returns, E.build_profiles(returns)


# --------------------------------------------------------------------------
# Questionnaire (MiFID II suitability: knowledge & experience,
# financial situation incl. capacity for loss, objectives & risk tolerance)
# --------------------------------------------------------------------------
QUESTIONS = [
    ("q_experience", "Which investments have you held before?", [
        ("None - I have never invested", 1), ("Only a savings account", 1),
        ("Bank funds or pension savings", 2),
        ("ETFs or individual shares, occasionally", 3), ("I invest regularly in ETFs or shares", 4),
        ("I invest actively in many types of assets", 5)]),
    ("q_knowledge", "If interest rates rise, what usually happens to bond prices?", [
        ("They rise", None), ("They stay the same", None), ("They fall", None), ("I don't know", None)]),
    ("q_drop", "Your portfolio loses 20% in a few months. What do you do?", [
        ("Sell everything", 1), ("Sell part of it", 2), ("Wait and do nothing", 4),
        ("Invest more while prices are low", 5)]),
    ("q_max_loss", "What is the largest yearly loss you could accept?", [
        ("5%", 1), ("10%", 2), ("15%", 3), ("25%", 4), ("More than 25%", 5)]),
    ("q_capacity", "If this investment lost a quarter of its value, how would your daily life be affected?", [
        ("Seriously - I would need this money", 1), ("Noticeably", 2), ("A little", 4), ("Not at all", 5)]),
    ("q_income", "How stable is your income?", [
        ("Unstable or no income", 1), ("Somewhat stable", 3), ("Very stable", 5)]),
    ("q_flexibility", "What if you are short of your target on the goal date?", [
        ("The amount and date are fixed - I must reach them", 1),
        ("I could wait a little longer", 3), ("The goal is flexible", 5)]),
]


KNOWLEDGE_KEY, KNOWLEDGE_CORRECT = "q_knowledge", "They fall"
KNOWLEDGE_CAP = 3   # a client who does not understand bond risk is capped at Balanced


def questionnaire_score():
    """
    Risk level from the six scored questions (average, rounded). The knowledge
    question is not scored: it is a check. Knowing how bonds work should not
    push a cautious client into more risk, but a client who does not know is
    capped at Balanced, as MiFID II requires products the client understands.
    Returns (level, capped_by_knowledge) or (None, False) if unanswered.
    """
    pts = []
    for key, _, options in QUESTIONS:
        ans = st.session_state.get(key)
        if ans is None:
            return None, False
        if key != KNOWLEDGE_KEY:
            pts.append(dict(options)[ans])
    level = int(np.clip(np.floor(np.mean(pts) + 0.5), 1, 5))
    if st.session_state[KNOWLEDGE_KEY] != KNOWLEDGE_CORRECT and level > KNOWLEDGE_CAP:
        return KNOWLEDGE_CAP, True
    return level, False


def current_profile():
    """(score from answers, starting profile after the horizon cap, profile in use)."""
    score, _ = questionnaire_score()
    if score is None:
        return None, None, None
    start = E.profile_at(st.session_state.years, score)
    used = st.session_state.profile_override or start
    return score, start, used


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def style(fig, h=360):
    return U.plotly_style(fig, h)


def donut(weights):
    w = weights[weights > 0].sort_values(ascending=False)
    fig = go.Figure(go.Pie(labels=[E.ASSETS[a] for a in w.index], values=w.values, hole=0.62,
                           marker=dict(colors=[COLORS[a] for a in w.index], line=dict(color=U.PAPER, width=2)),
                           sort=False,
                           texttemplate="%{percent:.0%}", hovertemplate="%{label}: %{percent:.1%}<extra></extra>"))
    style(fig, 340)
    fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.0, y=0.5, yanchor="middle"))
    return fig


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def page_goal():
    st.header("What are you investing for?")
    st.caption("Horizon builds and manages your portfolio around a goal, not just a risk label.")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Goal", **bind("goal_name"))
        st.number_input("Target amount (€)", min_value=1_000, max_value=5_000_000, step=1_000, **bind("target"))
        st.slider("Years until the goal", 1, 40, **bind("years"))
    with c2:
        st.number_input("Starting capital (€)", min_value=0, max_value=5_000_000, step=500, **bind("initial"))
        st.number_input("Monthly contribution (€)", min_value=0, max_value=50_000, step=25, **bind("monthly"))
    s = st.session_state
    invested = s.initial + s.monthly * 12 * s.years
    st.info(f"**{s.goal_name}**: {eur(s.target)} by {date.today().year + s.years}. "
            f"You will invest {eur(invested)} in total; the rest has to come from returns.")
    st.button("Continue to risk profile", type="primary", on_click=go_to, args=(PAGES[1],))


def page_profile():
    st.header("Your risk profile")
    st.caption("Seven questions, as required for suitability under MiFID II. The bond question checks "
               "your knowledge: it can limit your risk level but never raises it.")
    for key, question, options in QUESTIONS:
        labels = [o[0] for o in options]
        st.session_state.setdefault(key, None)
        idx = labels.index(st.session_state[key]) if st.session_state[key] in labels else None
        wkey = f"_w_{key}"
        st.radio(question, labels, index=idx, key=wkey,
                 on_change=lambda k=key, w=wkey: st.session_state.__setitem__(k, st.session_state[w]))
    score, start, _ = current_profile()
    if score is None:
        st.warning("Answer every question to see your profile.")
        return
    st.session_state.profile_override = None
    if questionnaire_score()[1]:
        msg = (f"Your answers suggest a higher level, but the bond question was not answered correctly, "
               f"so Horizon caps you at **{score} · {E.PROFILES[score]['name']}**: you should understand "
               "the risks of what you hold.")
    else:
        msg = f"Your answers point to **{score} · {E.PROFILES[score]['name']}**."
    if start < score:
        msg += (f" With {st.session_state.years} years to go, Horizon starts you at "
                f"**{start} · {E.PROFILES[start]['name']}** and keeps lowering risk as the goal approaches.")
    st.success(msg)
    st.button("Continue to your portfolio", type="primary", on_click=go_to, args=(PAGES[2],))


def page_portfolio(prices, returns, profiles):
    score, start, used = current_profile()
    if score is None:
        st.warning("Complete the risk profile first.")
        st.button("Go to risk profile", on_click=go_to, args=(PAGES[1],))
        return
    names = {k: f"{k} · {v['name']}" for k, v in E.PROFILES.items()}
    st.header(f"Your portfolio: {names[used]}")
    choice = st.select_slider("Compare risk levels", options=list(names), value=used,
                              format_func=lambda k: names[k] + (" (recommended)" if k == start else ""))
    st.session_state.profile_override = None if choice == start else choice
    P = profiles[choice]

    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(donut(P["weights"]), width="stretch", config=PLOT_CONFIG)
    with c2:
        st.metric("Expected return (per year)", pct(P["exp_return"]),
                  help="Forward-looking estimate: history blended with long-term assumptions, "
                       "so it is lower than the backtest below.")
        st.metric("Expected volatility", pct(P["volatility"]))
        st.metric("Equity share", pct(P["equity_share"], 0))
    table = pd.DataFrame({"ETF": [E.ASSETS[a] for a in P["weights"].index],
                          "Asset class": [E.ASSET_CLASS[a] for a in P["weights"].index],
                          "Weight": P["weights"].values})
    table = table[table.Weight > 0].sort_values("Weight", ascending=False)
    st.dataframe(table.style.format({"Weight": "{:.1%}"}), hide_index=True, width="stretch")

    st.subheader("How it would have performed")
    g = E.backtest(returns, P["weights"])
    b = E.backtest(returns, E.BENCHMARK)
    fig = go.Figure()
    fig.add_scatter(x=b.index, y=b.values, name="Benchmark 60/40 (World / € Govt)", line=dict(color=MUTED, width=2))
    fig.add_scatter(x=g.index, y=g.values, name=f"Horizon {names[choice]}", line=dict(color=ACCENT, width=3))
    fig.update_yaxes(title="Value of €100")
    st.plotly_chart(style(fig), width="stretch", config=PLOT_CONFIG)
    perf = pd.DataFrame({f"Horizon {names[choice]}": E.performance(g), "Benchmark 60/40": E.performance(b)})
    st.dataframe(perf.style.format("{:.1%}"), width="stretch")
    st.caption(f"Backtest {g.index[0]:%b %Y} – {g.index[-1]:%b %Y}, monthly rebalancing, "
               "total returns in EUR. Past performance does not guarantee future results.")

    with st.expander("How the five portfolios are built"):
        mu, cov = E.asset_stats(returns)
        hist = E.historical_returns(returns)
        fig = go.Figure()
        vols = np.sqrt(np.diag(cov))
        fig.add_scatter(x=vols, y=mu.values, mode="markers+text", text=list(mu.index),
                        textposition="top center", marker=dict(size=10, color=[COLORS[a] for a in mu.index]),
                        name="Individual ETFs")
        fig.add_scatter(x=[profiles[k]["volatility"] for k in profiles],
                        y=[profiles[k]["exp_return"] for k in profiles],
                        mode="lines+markers+text", text=[str(k) for k in profiles], textposition="middle left",
                        line=dict(color=ACCENT), marker=dict(size=12), name="Horizon profiles 1–5")
        fig.update_xaxes(title="Volatility (annual)", tickformat=".0%")
        fig.update_yaxes(title="Expected return (annual)", tickformat=".0%")
        st.plotly_chart(style(fig, 380), width="stretch", config=PLOT_CONFIG)
        st.markdown(
            "Each profile maximises expected return minus a risk penalty (mean-variance), with a "
            "**risk-aversion level** and an **equity band** per profile, no short selling, and a cap "
            "per ETF to stay diversified (gold and real estate ≤ 10%, emerging markets ≤ 20%).\n\n"
            f"**Expected returns** blend the 2014–2026 history ({1 - E.SHRINKAGE:.0%}) with long-term "
            f"assumptions ({E.SHRINKAGE:.0%}), because one decade of strong equity and gold markets "
            "would otherwise make risk look almost free.")
        er = pd.DataFrame({"ETF": [E.ASSETS[a] for a in mu.index], "Historical": hist.values,
                           "Long-term assumption": [E.LONG_TERM_RETURNS[a] for a in mu.index],
                           "Used by Horizon": mu.values})
        st.dataframe(er.style.format({c: "{:.1%}" for c in er.columns[1:]}), hide_index=True)
        bands = pd.DataFrame({"Profile": [names[k] for k in E.PROFILES],
                              "Equity band": [f"{lo:.0%}–{hi:.0%}" for lo, hi in (v["equity"] for v in E.PROFILES.values())],
                              "Risk aversion λ": [v["lambda"] for v in E.PROFILES.values()]})
        st.dataframe(bands, hide_index=True)
    st.button("Continue to goal tracking", type="primary", on_click=go_to, args=(PAGES[3],))


def page_tracking(prices, returns, profiles):
    score, start, used = current_profile()
    if score is None:
        st.warning("Complete the risk profile first.")
        st.button("Go to risk profile", on_click=go_to, args=(PAGES[1],))
        return
    s = st.session_state
    base = s.profile_override or score     # glide path starts from the investor's own level
    st.header(f"{s.goal_name}: are you on track?")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.slider("Monthly contribution (€)", 0, max(3_000, int(s.monthly)), step=25, **bind("monthly"))
    with c2:
        st.slider("Years until the goal", 1, 40, **bind("years"))
    with c3:
        st.number_input("Target amount (€)", min_value=1_000, step=1_000, **bind("target"))

    wealth, growth = E.simulate_goal(s.initial, s.monthly, s.years, base, profiles, return_growth=True)
    res = E.goal_summary(wealth, s.target, s.initial, s.monthly)
    w_flat, g_flat = E.simulate_goal(s.initial, s.monthly, s.years, base, profiles, glide=False,
                                     return_growth=True)
    flat = E.goal_summary(w_flat, s.target, s.initial, s.monthly)

    U.sunrise(res["probability"], prob(res["probability"]),
              f"chance of reaching {eur(s.target)} by {date.today().year + s.years}")
    m2, m3, m4 = st.columns(3)
    m2.metric("Median outcome", eur(res["median"]))
    m3.metric("Bad case (1 in 10)", eur(res["p10"]))
    m4.metric("Total invested", eur(res["invested"]))
    need = E.required_monthly(s.initial, s.years, s.target, base, profiles)
    goal_line = (f"With **{eur(s.monthly)} per month** for **{s.years} years**, you have a "
                 f"**{prob(res['probability'])} chance** of reaching **{eur(s.target)}**. ")
    gap = res["median"] - s.target
    goal_line += (f"In a typical scenario you end **{eur(abs(gap))} {'above' if gap >= 0 else 'below'}** "
                  "your target. ")
    if need is None or need > REALISTIC_MONTHLY:
        st.error(goal_line + "This target looks out of reach"
                 + (f": you would need about **{eur(need)} per month**" if need is not None else "")
                 + ". Lower the target or give yourself more time.")
    elif res["probability"] >= 0.75:
        if need == 0:
            st.success(goal_line + "Your starting capital alone gives you at least a 75% chance: "
                                   "monthly contributions are optional.")
        else:
            st.success(goal_line + (f"You are on track. {eur(need)} per month would be enough for a 75% chance."
                                    if need < s.monthly else "You are on track."))
    else:
        st.warning(goal_line + f"For a 75% chance, invest about **{eur(need)} per month** "
                               "or give yourself more time.")

    # fan chart
    months = wealth.shape[0] - 1
    x = pd.date_range(pd.Timestamp.today().normalize(), periods=months + 1, freq="MS")
    q = np.percentile(wealth, [10, 25, 50, 75, 90], axis=1)
    invested = s.initial + s.monthly * np.arange(months + 1)
    fig = go.Figure()
    fig.add_scatter(x=x, y=q[4], line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=x, y=q[0], fill="tonexty", fillcolor="rgba(19,41,75,0.08)", line=dict(width=0),
                    name="80% of outcomes")
    fig.add_scatter(x=x, y=q[3], line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=x, y=q[1], fill="tonexty", fillcolor="rgba(19,41,75,0.18)", line=dict(width=0),
                    name="50% of outcomes")
    fig.add_scatter(x=x, y=q[2], line=dict(color=ACCENT, width=3), name="Median")
    fig.add_scatter(x=x, y=invested, line=dict(color=MUTED, dash="dot"), name="Money invested")
    fig.add_hline(y=s.target, line=dict(color=U.SUN, width=3),
                  annotation_text=f"Target {eur(s.target)}", annotation_position="top left")
    fig.update_yaxes(title="Portfolio value (€)", tickformat=",.0f")
    st.plotly_chart(style(fig, 420), width="stretch", config=PLOT_CONFIG)
    st.caption("5,000 simulated market paths using each portfolio's expected return and volatility, with "
               "fat-tailed shocks so that crashes are more frequent than in a normal distribution. "
               "Amounts are nominal (not adjusted for inflation).")

    # glide path
    st.subheader("Glide path: risk falls as the goal gets closer")
    gp = E.glide_path_table(base, s.years, profiles)
    years_idx = date.today().year + gp.index
    fig = go.Figure()
    for a in E.ASSETS:
        if gp[a].max() > 0:
            fig.add_bar(x=years_idx, y=gp[a], name=E.ASSETS[a], marker_color=COLORS[a])
    fig.update_layout(barmode="stack", bargap=0.15)
    fig.update_yaxes(tickformat=".0%", title="Allocation")
    st.plotly_chart(style(fig, 380), width="stretch", config=PLOT_CONFIG)
    loss_g, loss_f = E.big_loss_probability(growth), E.big_loss_probability(g_flat)
    window = min(s.years, E.FINAL_YEARS)
    period = f"the last {window} years" if window > 1 else "the last year"
    cmp = pd.DataFrame({
        "With glide path": [prob(res["probability"]), eur(res["median"]), eur(res["p10"]), pct(loss_g)],
        "Without glide path": [prob(flat["probability"]), eur(flat["median"]), eur(flat["p10"]), pct(loss_f)],
    }, index=["Probability of reaching the goal", "Median outcome", "Bad case (1 in 10)",
              f"Chance of losing > {E.BIG_LOSS:.0%} in {period}"])
    st.dataframe(cmp, width="stretch")
    if loss_f - loss_g > 0.001:
        st.caption(f"The glide path gives up some upside, but it cuts the chance of a loss of more than "
                   f"{E.BIG_LOSS:.0%} in {period} before the goal, when there is no time left to "
                   f"recover, from {pct(loss_f)} to {pct(loss_g)}.")
    else:
        st.caption("Your portfolio is already at a cautious level for this horizon, "
                   "so the glide path changes little.")

    # rebalancing
    st.subheader("Automatic rebalancing")
    w_now = profiles[E.profile_at(s.years, base)]["weights"]
    default_start = E.largest_drift_start(returns, w_now)
    starts = list(returns.index[:-12])
    start_m = st.select_slider("Example period (12 months starting)", options=starts, value=default_start,
                               format_func=lambda d: f"{d:%b %Y}")
    d = E.drift_over(returns, w_now, start_m)
    d.index = [E.ASSETS[a] for a in d.index]
    triggered = d["Drift (pp)"].abs().max() > E.REBALANCING_BAND * 100
    st.dataframe(d.style.format({"Target": "{:.1%}", "After 12 months": "{:.1%}",
                                 "Drift (pp)": "{:+.1f}", "Trade to rebalance (% of portfolio)": "{:+.1f}"})
                 .map(lambda v: f"color:{U.BAD};font-weight:600" if abs(v) > E.REBALANCING_BAND * 100 else "",
                      subset=["Drift (pp)"]),
                 width="stretch")
    if triggered:
        st.info("At least one ETF drifted more than ±5 points from its target, so Horizon sells what has "
                "grown too large and buys what has fallen behind, bringing the portfolio back to target.")
    else:
        st.info("All ETFs stayed within ±5 points of target: no trade needed this time.")


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
def main():
    init_state()
    U.inject_css()
    with st.sidebar:
        U.brand()
        st.radio("Steps", PAGES, key="page", label_visibility="collapsed")
        st.divider()
        st.caption("FIN127 prototype. Advice is simulated and no real money is invested.")

    data = get_data()
    if data is None:
        st.error("Data files not found. Run the **horizon_etf_data** notebook and copy "
                 "`horizon_prices_monthly.csv` and `horizon_returns_monthly.csv` into the `data` folder.")
        st.stop()
    prices, returns, profiles = data

    page = st.session_state.page
    if page == PAGES[0]:
        page_goal()
    elif page == PAGES[1]:
        page_profile()
    elif page == PAGES[2]:
        page_portfolio(prices, returns, profiles)
    else:
        page_tracking(prices, returns, profiles)


main()
