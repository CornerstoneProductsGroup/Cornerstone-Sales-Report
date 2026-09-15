from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from .shared_core import render_df


def _fmt_units(value) -> str:
    return f"{float(value):,.0f}"


def _fmt_pct(value) -> str:
    return f"{float(value) * 100:,.1f}%"


def _with_share(df: pd.DataFrame, units_col: str = "Units") -> pd.DataFrame:
    out = df.copy()
    total = float(pd.to_numeric(out[units_col], errors="coerce").fillna(0.0).sum())
    out["% of Total"] = (pd.to_numeric(out[units_col], errors="coerce").fillna(0.0) / total) if total else 0.0
    return out


def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Units" in out.columns:
        out["Units"] = out["Units"].map(_fmt_units)
    if "% of Total" in out.columns:
        out["% of Total"] = out["% of Total"].map(_fmt_pct)
    return out


def render(ctx: dict):
    df = ctx.get("df_state", pd.DataFrame()).copy()
    st.subheader("State Totals")

    if df.empty:
        st.info("No state totals have been uploaded yet. Use Data Management Center > State Totals Upload to add the State Totals tab from the new workbook.")
        return

    df["Units"] = pd.to_numeric(df["Units"], errors="coerce").fillna(0.0)
    df["WeekEnd"] = pd.to_datetime(df.get("WeekEnd"), errors="coerce")
    df = df[df["Units"].ne(0)].copy()

    week_range_options = {
        "Last Week": 1,
        "Last 4 Weeks": 4,
        "Last 8 Weeks": 8,
        "Last 12 Weeks": 12,
        "Last 24 Weeks": 24,
        "Last 36 Weeks": 36,
        "Last 52 Weeks": 52,
    }
    quarter_options = ["Q1", "Q2", "Q3", "Q4"]
    month_periods = sorted(df["WeekEnd"].dropna().dt.to_period("M").unique())
    month_options = [p.strftime("%B %Y") for p in month_periods]
    year_options = sorted(df["WeekEnd"].dropna().dt.year.dropna().astype(int).unique().tolist())

    with st.expander("Filters", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            search_by = st.selectbox("Search By", options=["Week", "Month", "Quarter", "Year"], index=0)
        with c2:
            if search_by == "Week":
                selected_timeframe = st.selectbox("Timeframe", options=list(week_range_options.keys()), index=0)
            elif search_by == "Quarter":
                selected_timeframe = st.multiselect("Timeframe", options=quarter_options, default=[])
            elif search_by == "Month":
                selected_timeframe = st.multiselect("Timeframe", options=month_options, default=[])
            else:
                selected_timeframe = st.multiselect("Timeframe", options=year_options, default=[])
        with c3:
            state_options = sorted(df["State"].dropna().astype(str).unique().tolist())
            selected_states = st.multiselect("State", options=state_options, default=[])
        with c4:
            retailer_options = sorted(df["Retailer"].dropna().astype(str).unique().tolist())
            selected_retailers = st.multiselect("Retailer", options=retailer_options, default=[])
        with c5:
            vendor_options = sorted(df["Vendor"].dropna().astype(str).unique().tolist())
            selected_vendors = st.multiselect("Vendor", options=vendor_options, default=[])

    filtered = df.copy()
    if search_by == "Week":
        unique_weeks = sorted(df["WeekEnd"].dropna().unique())
        n = week_range_options[selected_timeframe]
        weeks_to_keep = unique_weeks[-n:] if unique_weeks else []
        filtered = filtered[filtered["WeekEnd"].isin(weeks_to_keep)]
    elif search_by == "Quarter":
        if selected_timeframe:
            quarter_labels = filtered["WeekEnd"].dt.quarter.map(lambda q: f"Q{int(q)}" if pd.notna(q) else None)
            filtered = filtered[quarter_labels.isin(selected_timeframe)]
    elif search_by == "Month":
        if selected_timeframe:
            month_labels = filtered["WeekEnd"].dt.to_period("M").apply(
                lambda p: p.strftime("%B %Y") if pd.notna(p) else None
            )
            filtered = filtered[month_labels.isin(selected_timeframe)]
    else:
        if selected_timeframe:
            filtered = filtered[filtered["WeekEnd"].dt.year.isin(selected_timeframe)]

    if selected_states:
        filtered = filtered[filtered["State"].isin(selected_states)]
    if selected_retailers:
        filtered = filtered[filtered["Retailer"].isin(selected_retailers)]
    if selected_vendors:
        filtered = filtered[filtered["Vendor"].isin(selected_vendors)]

    if filtered.empty:
        st.info("No rows match the selected filters.")
        return

    total_units = float(filtered["Units"].sum())
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Units", f"{total_units:,.0f}")
    k2.metric("States", f"{filtered['State'].nunique():,}")
    k3.metric("SKUs", f"{filtered['SKU'].nunique():,}")
    k4.metric("Retailers", f"{filtered['Retailer'].nunique():,}")

    state_summary = (
        filtered.groupby("State", as_index=False)
        .agg(
            Units=("Units", "sum"),
            SKUs=("SKU", "nunique"),
            Vendors=("Vendor", "nunique"),
            Retailers=("Retailer", "nunique"),
        )
        .sort_values("Units", ascending=False)
    )
    state_summary = _with_share(state_summary)

    detail = (
        filtered.groupby(["State", "Retailer", "Vendor", "SKU"], as_index=False)
        .agg(Units=("Units", "sum"))
        .sort_values(["State", "Units"], ascending=[True, False])
    )
    detail = _with_share(detail)

    sku_summary = (
        filtered.groupby(["SKU", "Vendor"], as_index=False)
        .agg(Units=("Units", "sum"), States=("State", "nunique"), Retailers=("Retailer", "nunique"))
        .sort_values("Units", ascending=False)
    )
    sku_summary = _with_share(sku_summary)

    def _state_bar_chart(data: pd.DataFrame, label_font_size: int = 11):
        order = data["State"].tolist()
        base = alt.Chart(data).encode(
            x=alt.X("State:N", sort=order, title="State"),
            y=alt.Y("Units:Q", title="Units"),
        )
        bars = base.mark_bar(color="#1f77b4")
        units_labels = base.mark_text(dy=-26, fontWeight="bold", fontSize=label_font_size).encode(
            text=alt.Text("Units:Q", format=",.0f")
        )
        pct_labels = base.mark_text(dy=-11, fontSize=label_font_size - 1).encode(
            text=alt.Text("% of Total:Q", format=".1%")
        )
        st.altair_chart(bars + units_labels + pct_labels, use_container_width=True)

    st.markdown("### Units by State (Top 10)")
    _state_bar_chart(state_summary.head(10), label_font_size=16)

    if len(state_summary) > 10:
        st.markdown("### Units by State (Remaining)")
        _state_bar_chart(state_summary.iloc[10:])
    render_df(_format_table(state_summary), height=320)

    st.markdown("### SKU / Vendor / Retailer by State")
    render_df(_format_table(detail), height=420)

    st.markdown("### SKU Summary")
    render_df(_format_table(sku_summary), height=360)
