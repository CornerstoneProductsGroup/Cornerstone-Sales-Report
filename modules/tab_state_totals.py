from __future__ import annotations

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

    with st.expander("Filters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            week_options = sorted(df["WeekEnd"].dropna().dt.date.astype(str).unique().tolist())
            selected_weeks = st.multiselect("Week End", options=week_options, default=week_options[-1:] if week_options else [])
        with c2:
            state_options = sorted(df["State"].dropna().astype(str).unique().tolist())
            selected_states = st.multiselect("State", options=state_options, default=[])
        with c3:
            retailer_options = sorted(df["Retailer"].dropna().astype(str).unique().tolist())
            selected_retailers = st.multiselect("Retailer", options=retailer_options, default=[])
        with c4:
            vendor_options = sorted(df["Vendor"].dropna().astype(str).unique().tolist())
            selected_vendors = st.multiselect("Vendor", options=vendor_options, default=[])

    filtered = df.copy()
    if selected_weeks:
        filtered = filtered[filtered["WeekEnd"].dt.date.astype(str).isin(selected_weeks)]
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

    st.markdown("### Units by State")
    st.bar_chart(state_summary.set_index("State")["Units"])
    render_df(_format_table(state_summary), height=320)

    st.markdown("### SKU / Vendor / Retailer by State")
    render_df(_format_table(detail), height=420)

    st.markdown("### SKU Summary")
    render_df(_format_table(sku_summary), height=360)
