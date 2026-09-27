from __future__ import annotations

import json

import altair as alt
import pandas as pd
import streamlit as st

from .shared_core import money

MONTHLY_GOAL = 240_000.0
WEEKLY_TARGET = 60_000.0
WEEKS_SHOWN = 12
BAR_COLOR = "#24409c"


def _weekly_totals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "WeekEnd" not in df.columns or "Sales" not in df.columns:
        return pd.DataFrame(columns=["WeekEnd", "Sales"])
    out = df[["WeekEnd", "Sales"]].copy()
    out["WeekEnd"] = pd.to_datetime(out["WeekEnd"], errors="coerce")
    out["Sales"] = pd.to_numeric(out["Sales"], errors="coerce").fillna(0.0)
    out = out.dropna(subset=["WeekEnd"])
    return out.groupby("WeekEnd", as_index=False)["Sales"].sum().sort_values("WeekEnd")


def _peak_chart(weeks: pd.DataFrame) -> alt.Chart:
    labels = weeks["WeekEnd"].dt.strftime("%m/%d").tolist()
    half = 0.32
    rows = []
    for i, sales in enumerate(weeks["Sales"].tolist()):
        rows += [
            {"x": i - half, "y": 0.0, "week": i},
            {"x": float(i), "y": sales, "week": i},
            {"x": i + half, "y": 0.0, "week": i},
        ]
    tri = pd.DataFrame(rows)
    sales_vals = weeks["Sales"].tolist()
    peaks = pd.DataFrame({"x": range(len(labels)), "y": sales_vals, "Week": labels})
    # Labels sit ~2-9% of the y-range above each peak; lift ones that would straddle the target line above it.
    y_top = max(max(sales_vals, default=0.0), WEEKLY_TARGET) * 1.1
    collides = (peaks["y"] < WEEKLY_TARGET) & (peaks["y"] > WEEKLY_TARGET - 0.1 * y_top)
    peaks["label_y"] = peaks["y"].where(~collides, WEEKLY_TARGET + 0.02 * y_top)

    x_axis = alt.Axis(
        values=list(range(len(labels))),
        labelExpr=f"{json.dumps(labels)}[datum.value]",
        labelAngle=-45,
        grid=False,
        title=None,
    )
    x_scale = alt.Scale(domain=[-0.6, len(labels) - 0.4], nice=False)
    y_enc = alt.Y("y:Q", title=None, axis=alt.Axis(format="$,.0f", gridDash=[4, 4]))

    area = alt.Chart(tri).mark_area(color=BAR_COLOR, interpolate="linear").encode(
        x=alt.X("x:Q", scale=x_scale, axis=x_axis),
        y=y_enc,
        detail="week:N",
    )
    text = alt.Chart(peaks).mark_text(dy=-10, color="#444", fontWeight="bold").encode(
        x=alt.X("x:Q", scale=x_scale),
        y=alt.Y("label_y:Q", title=None),
        text=alt.Text("y:Q", format="$,.0f"),
        tooltip=[alt.Tooltip("Week:N"), alt.Tooltip("y:Q", title="Sales", format="$,.0f")],
    )
    target = pd.DataFrame({"y": [WEEKLY_TARGET]})
    rule = alt.Chart(target).mark_rule(color="#d62728", strokeDash=[6, 4], size=2).encode(y="y:Q")
    rule_text = alt.Chart(target).mark_text(
        align="left", dx=4, dy=-8, color="#d62728", fontWeight="bold"
    ).encode(y="y:Q", x=alt.value(0), text=alt.value(f"Target {money(WEEKLY_TARGET)}"))
    return (area + rule + rule_text + text).properties(height=360)


def _month_to_date(weeks: pd.DataFrame) -> float:
    latest_week = weeks["WeekEnd"].iloc[-1]
    # A week counts toward the month its WeekEnd falls in, so the goal resets on the first week of a new month.
    month_mask = weeks["WeekEnd"].dt.to_period("M") == latest_week.to_period("M")
    return float(weeks.loc[month_mask, "Sales"].sum())


def _progress_text(mtd: float) -> str:
    # Progress text is markdown; escape $ so a pair isn't rendered as LaTeX.
    return f"{money(mtd)} / {money(MONTHLY_GOAL)}".replace("$", "\\$")


def render_goal_strip(df_scope: pd.DataFrame):
    weeks = _weekly_totals(df_scope)
    if weeks.empty:
        return
    latest_sales = float(weeks["Sales"].iloc[-1])
    latest_week = weeks["WeekEnd"].iloc[-1]
    mtd = _month_to_date(weeks)
    week_pct = latest_sales / WEEKLY_TARGET
    month_pct = mtd / MONTHLY_GOAL

    box_height = 175
    prev_period = latest_week.to_period("M") - 1
    prev_total = float(weeks.loc[weeks["WeekEnd"].dt.to_period("M") == prev_period, "Sales"].sum())
    prev_pct = prev_total / MONTHLY_GOAL

    c1, c2, c3, c4 = st.columns(4)
    with c1, st.container(border=True, height=box_height):
        st.metric(f"Last Week Total (ending {latest_week:%m/%d/%Y})", money(latest_sales))
    with c2, st.container(border=True, height=box_height):
        st.metric(
            f"Weekly Goal ({money(WEEKLY_TARGET)})",
            f"{week_pct * 100:,.1f}%",
            delta=f"{'+' if latest_sales >= WEEKLY_TARGET else '-'}{money(abs(latest_sales - WEEKLY_TARGET))} vs goal",
        )
    with c3, st.container(border=True, height=box_height):
        st.metric(f"{latest_week:%B} Goal ({money(MONTHLY_GOAL)})", f"{month_pct * 100:,.1f}%")
        st.progress(min(month_pct, 1.0), text=_progress_text(mtd))
    with c4, st.container(border=True, height=box_height):
        st.metric(f"{prev_period:%B} Total (Last Full Month)", money(prev_total))
        st.progress(
            min(prev_pct, 1.0),
            text=f"{prev_pct * 100:,.1f}% of {money(MONTHLY_GOAL)} goal".replace("$", "\\$"),
        )


def render_target_chart(df_scope: pd.DataFrame):
    weeks = _weekly_totals(df_scope)
    if weeks.empty:
        return
    recent = weeks.tail(WEEKS_SHOWN).reset_index(drop=True)
    st.markdown(f"#### Weekly Sales vs {money(WEEKLY_TARGET)} Target (last {len(recent)} weeks)")
    st.altair_chart(_peak_chart(recent), use_container_width=True)


def render(ctx: dict):
    st.subheader("Weekly Goals")
    weeks = _weekly_totals(ctx.get("df_scope", pd.DataFrame()))
    if weeks.empty:
        st.info("Upload or ingest data to begin.")
        return

    latest = weeks.iloc[-1]
    latest_week = latest["WeekEnd"]
    mtd = _month_to_date(weeks)
    pct = mtd / MONTHLY_GOAL if MONTHLY_GOAL else 0.0

    left, _ = st.columns([1, 2])
    with left:
        st.metric(f"Latest Week Total (week ending {latest_week:%m/%d/%Y})", money(latest["Sales"]))
        st.metric(
            f"{latest_week:%B} Goal Progress",
            f"{pct * 100:,.1f}%",
            help=f"{money(mtd)} of {money(MONTHLY_GOAL)} monthly goal",
        )
        st.progress(min(pct, 1.0), text=_progress_text(mtd))

    render_target_chart(ctx.get("df_scope", pd.DataFrame()))
