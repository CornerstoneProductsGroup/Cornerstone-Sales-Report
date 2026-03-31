from __future__ import annotations

from datetime import date
import html as _html
import inspect
import re as _re
from pathlib import Path

import pandas as pd
import streamlit as st

from .app_core import read_weekly_workbook
from .shared_core import (
    APP_TITLE,
    load_vendor_map,
    load_store,
    save_store,
    enrich_sales,
    available_month_labels,
    available_quarter_labels,
    available_year_labels,
    filter_by_period_labels,
    period_from_df,
    compact_selection_label,
    pick_period,
    filter_by_period,
    period_prev_same_length,
    period_yoy,
    ab_labels,
    format_period_range,
    calc_kpis,
    drivers,
    money,
    render_data_management_center,
)
from .ui_styles import apply_global_styles
from . import (
    tab_kpi_dashboard,
    tab_standard_intelligence,
    tab_month_year_compare,
    tab_multi_compare,
    tab_lookup_center,
)


def render_global_view_mode_toggle():
    default_mode = st.session_state.get("global_content_view", "Model View")

    try:
        selected = st.sidebar.segmented_control(
            "Content View",
            options=["Model View", "Visual Analytics"],
            default=default_mode,
            key="global_content_view",
        )
    except Exception:
        selected = st.sidebar.radio(
            "Content View",
            options=["Model View", "Visual Analytics"],
            index=0 if default_mode == "Model View" else 1,
            key="global_content_view",
        )

    return selected or st.session_state.get("global_content_view", "Model View")


def get_global_view_mode():
    return st.session_state.get("global_content_view", "Model View")


def render_current_analysis_view(ctx: dict):
    analysis_view = ctx.get("analysis_view")

    if analysis_view == "Sales Dashboard":
        if hasattr(tab_kpi_dashboard, "render"):
            tab_kpi_dashboard.render(ctx)
            return
        st.warning("Sales Dashboard tab render function was not found.")
    elif analysis_view == "Standard Intelligence":
        if hasattr(tab_standard_intelligence, "render"):
            tab_standard_intelligence.render(ctx)
            return
        st.warning("Standard Intelligence tab render function was not found.")
    elif analysis_view == "Month / Year Compare":
        if hasattr(tab_month_year_compare, "render"):
            tab_month_year_compare.render(ctx)
            return

        # Fallback for older builds that expose only the underlying renderer.
        if hasattr(tab_month_year_compare, "render_standard_view"):
            tab_month_year_compare.render_standard_view(
                dfA=ctx["dfA"],
                dfB=ctx["dfB"],
                kA=ctx["kA"],
                kB=ctx["kB"],
                a_lbl=ctx["a_lbl"],
                b_lbl=ctx["b_lbl"],
                compare_mode=ctx["compare_mode"],
                min_sales=ctx["min_sales"],
            )
            return

        st.warning("Month / Year Compare tab render function was not found.")
    elif analysis_view == "Multi Month / Year Compare":
        if hasattr(tab_multi_compare, "render"):
            tab_multi_compare.render(ctx)
            return
        st.warning("Multi Month / Year Compare tab render function was not found.")
    elif analysis_view == "Lookup Center":
        if hasattr(tab_lookup_center, "render"):
            tab_lookup_center.render(ctx)
            return
        st.warning("Lookup Center tab render function was not found.")


def render_visual_analysis_view(ctx: dict):
    analysis_view = ctx.get("analysis_view")

    if analysis_view == "Sales Dashboard":
        if hasattr(tab_kpi_dashboard, "render"):
            tab_kpi_dashboard.render(ctx)
            return
        st.warning("Sales Dashboard visual dashboard function was not found.")
        return

    if analysis_view == "Standard Intelligence":
        if hasattr(tab_standard_intelligence, "render_visual_only"):
            tab_standard_intelligence.render_visual_only(ctx)
            return
        st.warning("Standard Intelligence visual dashboard function was not found.")
        return

    if analysis_view == "Month / Year Compare":
        if hasattr(tab_month_year_compare, "render_visual_only"):
            tab_month_year_compare.render_visual_only(ctx)
            return

        if hasattr(tab_month_year_compare, "render_visual_executive_dashboard"):
            fn = tab_month_year_compare.render_visual_executive_dashboard
            kwargs = {
                "dfA": ctx["dfA"],
                "dfB": ctx["dfB"],
                "kA": ctx["kA"],
                "kB": ctx["kB"],
                "a_lbl": ctx["a_lbl"],
                "b_lbl": ctx["b_lbl"],
                "min_sales": ctx["min_sales"],
            }

            # Support mixed deployments where the tab function signature differs.
            try:
                sig = inspect.signature(fn)
                accepted = {
                    k: v
                    for k, v in kwargs.items()
                    if k in sig.parameters
                }
                fn(**accepted)
            except Exception:
                # Last-resort fallback for older positional signatures.
                fn(
                    ctx["dfA"],
                    ctx["dfB"],
                    ctx["kA"],
                    ctx["kB"],
                    ctx["a_lbl"],
                    ctx["b_lbl"],
                    ctx["min_sales"],
                )
            return

        st.warning("Month / Year visual dashboard function was not found.")
        return

    if analysis_view == "Multi Month / Year Compare":
        if hasattr(tab_multi_compare, "render_visual_only"):
            tab_multi_compare.render_visual_only(ctx)
            return
        st.warning("Multi Month / Year visual dashboard function was not found.")
        return

    if analysis_view == "Lookup Center":
        st.info("Visual Analytics is not built yet for Lookup Center.")


def render_model_header_and_summary(
    *,
    analysis_view: str,
    scope: str,
    content_view: str,
    compare_mode: str,
    pA,
    pB,
    a_lbl,
    b_lbl,
    kA: dict,
    kB: dict,
    dfA: pd.DataFrame,
    dfB: pd.DataFrame,
    driver_level: str,
):
    if analysis_view == "Multi Month / Year Compare":
        st.markdown(
            f"""
            <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin: 4px 0 10px 0;">
                <span style="padding:6px 10px; border-radius:999px; border:1px solid rgba(128,128,128,0.22); background: var(--secondary-background-color); color: var(--text-color); font-weight:700; font-size:12px;">Scope: {scope}</span>
                <span style="padding:6px 10px; border-radius:999px; border:1px solid rgba(128,128,128,0.22); background: var(--secondary-background-color); color: var(--text-color); font-weight:700; font-size:12px;">Mode: Multi-select period analysis</span>
                <span style="padding:6px 10px; border-radius:999px; border:1px solid rgba(128,128,128,0.22); background: var(--secondary-background-color); color: var(--text-color); font-weight:700; font-size:12px;">Content View: {content_view}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        cur_range = format_period_range(pA)
        cmp_range = format_period_range(pB) if pB is not None else ""
        cmp_name = b_lbl or ""
        cmp_chip = (
            f'<span style="padding:6px 10px; border-radius:999px; border:1px solid rgba(128,128,128,0.22); background: var(--secondary-background-color); color: var(--text-color); font-weight:700; font-size:12px;">Compare: {cmp_name} • {cmp_range}</span>'
            if compare_mode != "None" and pB is not None
            else '<span style="padding:6px 10px; border-radius:999px; border:1px solid rgba(128,128,128,0.22); background: var(--secondary-background-color); color: var(--text-color); font-weight:700; font-size:12px; opacity:0.75;">Compare: None</span>'
        )

        st.markdown(
            f"""
            <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin: 4px 0 10px 0;">
                <span style="padding:6px 10px; border-radius:999px; border:1px solid rgba(128,128,128,0.22); background: var(--secondary-background-color); color: var(--text-color); font-weight:700; font-size:12px;">Scope: {scope}</span>
                <span style="padding:6px 10px; border-radius:999px; border:1px solid rgba(128,128,128,0.22); background: var(--secondary-background-color); color: var(--text-color); font-weight:700; font-size:12px;">Current: {a_lbl} • {cur_range}</span>
                {cmp_chip}
                <span style="padding:6px 10px; border-radius:999px; border:1px solid rgba(128,128,128,0.22); background: var(--secondary-background-color); color: var(--text-color); font-weight:700; font-size:12px;">Content View: {content_view}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    headline_bits = []
    if analysis_view == "Multi Month / Year Compare":
        headline_bits.append("Use the controls inside this tab to analyze multiple months or years together.")
        headline_bits.append("The matrix table highlights the highest selected period in green and the lowest in red for each row.")
        headline_bits.append("Use Rows By to switch between retailer and vendor views.")
    else:
        sales_delta = kA["Sales"] - kB.get("Sales", 0.0)
        units_delta = kA["Units"] - kB.get("Units", 0.0)
        asp_delta = kA["ASP"] - kB.get("ASP", 0.0)
        drv = drivers(dfA, dfB, driver_level)
        top_pos = drv[drv["Sales_Δ"] > 0].head(1) if drv is not None and not drv.empty and "Sales_Δ" in drv.columns else pd.DataFrame()
        top_neg = drv[drv["Sales_Δ"] < 0].tail(1) if drv is not None and not drv.empty and "Sales_Δ" in drv.columns else pd.DataFrame()

        if compare_mode != "None":
            headline_bits.append(
                f"Sales {'up' if sales_delta >= 0 else 'down'} **{money(abs(sales_delta))}** vs comparison."
            )
            headline_bits.append(
                f"Units: **{kA['Units']:,.0f}** ({'up' if units_delta >= 0 else 'down'} **{abs(units_delta):,.0f}** vs comparison)."
            )
            headline_bits.append(
                f"ASP: **{money(kA['ASP'])}** ({'up' if asp_delta >= 0 else 'down'} **{money(abs(asp_delta))}** vs comparison)."
            )
            if not top_pos.empty:
                headline_bits.append(
                    f"Top driver: **{top_pos.iloc[0][driver_level]}** ({money(float(top_pos.iloc[0]['Sales_Δ']))})."
                )
            if not top_neg.empty:
                headline_bits.append(
                    f"Top drag: **{top_neg.iloc[0][driver_level]}** ({money(float(top_neg.iloc[0]['Sales_Δ']))})."
                )
        else:
            headline_bits.append("Choose a comparison mode to see drivers and deltas.")

    def _md_bold_to_html(s: str) -> str:
        parts = []
        last = 0
        for mm in _re.finditer(r"\*\*(.+?)\*\*", s):
            parts.append(_html.escape(s[last:mm.start()]))
            parts.append(f"<strong>{_html.escape(mm.group(1))}</strong>")
            last = mm.end()
        parts.append(_html.escape(s[last:]))
        return "".join(parts)

    _lis = "".join([f"<li>{_md_bold_to_html(x)}</li>" for x in headline_bits])
    st.markdown(
        f"<div class='intel-card'><div class='intel-header'>INTELLIGENCE SUMMARY</div><div class='intel-body'><ul>{_lis}</ul></div></div>",
        unsafe_allow_html=True,
    )


def run_app():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    apply_global_styles()

    logo_path = Path(__file__).resolve().parents[1] / "data" / "cornerstone_logo.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=320)

    st.title(APP_TITLE)

    vm = load_vendor_map()
    store = load_store()

    with st.sidebar:
        st.header("Data")
        uploads = st.file_uploader(
            "Upload weekly sales workbook (.xlsx)",
            type=["xlsx"],
            accept_multiple_files=True,
        )
        year = st.number_input(
            "Year hint (for filename parsing)",
            min_value=2010,
            max_value=2100,
            value=date.today().year,
            step=1,
        )

        if st.button("Ingest upload(s)", disabled=(not uploads)):
            if uploads:
                all_raw = []
                uploaded_names = []

                for up in uploads:
                    raw = read_weekly_workbook(up, int(year))
                    all_raw.append(raw)
                    uploaded_names.append(getattr(up, "name", "upload.xlsx"))

                raw_merged = pd.concat(all_raw, ignore_index=True) if all_raw else pd.DataFrame()
                if raw_merged.empty:
                    st.info("No rows were ingested from the selected upload(s).")
                else:
                    _ = enrich_sales(raw_merged, vm)
                    merged = pd.concat([store, raw_merged], ignore_index=True)
                    save_store(merged)
                    st.success(
                        f"Ingested {len(raw_merged):,} rows from {len(uploaded_names)} file(s): "
                        + ", ".join(uploaded_names)
                    )
                    store = load_store()

        st.divider()
        st.header("Filters")

        scope = st.selectbox("Scope", ["All", "Retailer", "Vendor", "SKU"], index=0)

        df_all = enrich_sales(store, vm)
        scope_pick = None

        if scope == "Retailer":
            scope_pick = st.multiselect(
                "Retailer(s)",
                options=sorted(df_all["Retailer"].dropna().unique()) if "Retailer" in df_all.columns else [],
                default=[],
            )
        elif scope == "Vendor":
            scope_pick = st.multiselect(
                "Vendor(s)",
                options=sorted(df_all["Vendor"].dropna().unique()) if "Vendor" in df_all.columns else [],
                default=[],
            )
        elif scope == "SKU":
            scope_pick = st.multiselect(
                "SKU(s)",
                options=sorted(df_all["SKU"].dropna().unique()) if "SKU" in df_all.columns else [],
                default=[],
            )

        analysis_view = st.radio(
            "Analysis View",
            [
                "Standard Intelligence",
                "Month / Year Compare",
                "Multi Month / Year Compare",
                "Lookup Center",
                "Data Management Center",
            ],
            index=0,
        )

        content_view = render_global_view_mode_toggle()

        multi_granularity = "Month"
        current_labels_sel = []
        compare_labels_sel = []

        if analysis_view == "Data Management Center":
            timeframe = "YTD"
            compare_mode = "None"

        elif analysis_view in ["Standard Intelligence"]:
            timeframe = st.selectbox(
                "Timeframe",
                [
                    "Week (latest)",
                    "Last 4 weeks",
                    "Last 8 weeks",
                    "Last 13 weeks",
                    "Last 26 weeks",
                    "Last 52 weeks",
                    "Quarter",
                    "YTD",
                ],
                index=2,
            )
            quarter_choice = None
            quarter_year_choice = None
            if timeframe == "Quarter":
                quarter_labels = ["Q1", "Q2", "Q3", "Q4"]
                year_options = list(reversed(available_year_labels(df_all)))

                q_col, y_col = st.columns(2)
                with q_col:
                    quarter_choice = st.selectbox(
                        "Quarter",
                        quarter_labels,
                        index=0,
                        key="left_sidebar_quarter_choice",
                    )
                with y_col:
                    quarter_year_choice = st.selectbox(
                        "Year",
                        year_options,
                        index=0,
                        key="left_sidebar_quarter_year_choice",
                    ) if year_options else None

                compare_mode = st.selectbox(
                    "Compare",
                    ["None", "Same quarter last year"],
                    index=1,
                    key="left_sidebar_quarter_compare_mode",
                )
            else:
                compare_mode = st.selectbox(
                    "Compare",
                    ["None", "Prior period (same length)", "YoY (same dates)"],
                    index=1,
                )

        elif analysis_view == "Month / Year Compare":
            multi_granularity = st.selectbox(
                "Compare By",
                ["Month", "Quarter", "Year"],
                index=0,
                key="my_compare_by",
            )
            if multi_granularity == "Month":
                period_options = available_month_labels(df_all)
                timeframe = "Custom Months"
            elif multi_granularity == "Quarter":
                period_options = available_quarter_labels(df_all)
                timeframe = "Custom Quarters"
            else:
                period_options = available_year_labels(df_all)
                timeframe = "Custom Years"

            current_labels_sel = st.multiselect(
                f"Current {multi_granularity}(s)",
                options=period_options,
                default=[period_options[-1]] if period_options else [],
            )
            compare_labels_sel = st.multiselect(
                f"Compare {multi_granularity}(s)",
                options=period_options,
                default=[period_options[-2]] if len(period_options) > 1 else [],
            )

            compare_mode = "Custom selection" if compare_labels_sel else "None"

        elif analysis_view == "Lookup Center":
            timeframe = "Last 8 weeks"
            compare_mode = "None"

        else:
            timeframe = "Multi Selection"
            compare_mode = "None"
            multi_granularity = "Year"
            current_labels_sel = []
            compare_labels_sel = []

        min_sales = st.number_input("Min Sales ($) for lists", min_value=0.0, value=0.0, step=100.0)
        min_units = st.number_input("Min Units for lists", min_value=0.0, value=0.0, step=10.0)
        driver_level = st.selectbox("Driver Level", ["SKU", "Vendor", "Retailer"], index=0)
        show_full_history_lifecycle = st.toggle("Lifecycle uses full history", value=True)

    df_scope = df_all.copy()
    if scope == "Retailer" and scope_pick:
        df_scope = df_scope[df_scope["Retailer"].isin(scope_pick)]
    elif scope == "Vendor" and scope_pick:
        df_scope = df_scope[df_scope["Vendor"].isin(scope_pick)]
    elif scope == "SKU" and scope_pick:
        df_scope = df_scope[df_scope["SKU"].isin(scope_pick)]

    if analysis_view == "Data Management Center":
        render_data_management_center(vm, store)
        return

    if analysis_view == "Month / Year Compare":
        dfA = filter_by_period_labels(df_scope, current_labels_sel, multi_granularity)
        dfB = (
            filter_by_period_labels(df_scope, compare_labels_sel, multi_granularity)
            if compare_labels_sel
            else df_scope.iloc[0:0].copy()
        )
        pA = period_from_df(dfA)
        pB = period_from_df(dfB) if not dfB.empty else None

        if pA is None:
            st.info("Choose one or more months/years to begin.")
            return

        a_lbl = compact_selection_label(current_labels_sel, multi_granularity)
        b_lbl = compact_selection_label(compare_labels_sel, multi_granularity) if pB is not None else None

    elif analysis_view == "Multi Month / Year Compare":
        dfA = df_scope.copy()
        dfB = df_scope.iloc[0:0].copy()
        pA = None
        pB = None
        a_lbl = None
        b_lbl = None

    else:
        if timeframe == "Quarter":
            if not quarter_choice or not quarter_year_choice:
                st.info("Select a quarter and year to begin.")
                return

            quarter_num = int(str(quarter_choice).replace("Q", ""))
            current_quarter_label = f"Q{quarter_num} {quarter_year_choice}"
            prior_quarter_label = f"Q{quarter_num} {int(quarter_year_choice) - 1}"

            dfA = filter_by_period_labels(df_scope, [current_quarter_label], "Quarter")
            pA = period_from_df(dfA)
            if pA is None:
                st.info("No data available for the selected quarter.")
                return

            if compare_mode == "Same quarter last year":
                dfB = filter_by_period_labels(df_scope, [prior_quarter_label], "Quarter")
                pB = period_from_df(dfB) if not dfB.empty else None
                b_lbl = prior_quarter_label
            else:
                pB = None
                dfB = dfA.iloc[0:0].copy()
                b_lbl = None

            a_lbl = current_quarter_label
        else:
            pA = pick_period(df_scope, timeframe)
            if pA is None:
                st.info("Upload or ingest data to begin.")
                return

            dfA = filter_by_period(df_scope, pA)

            if compare_mode == "None":
                pB = None
                dfB = dfA.iloc[0:0].copy()
            elif compare_mode.startswith("Prior"):
                pB = period_prev_same_length(pA)
                dfB = filter_by_period(df_scope, pB)
            else:
                pB = period_yoy(pA)
                dfB = filter_by_period(df_scope, pB)

            a_lbl, b_lbl = ab_labels(timeframe, compare_mode, pA, pB)

    st.sidebar.markdown("### Period Definition")
    if analysis_view == "Multi Month / Year Compare":
        st.sidebar.markdown(
            "<span style='opacity:0.75'>Multi-select analysis mode</span>",
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            f"**Current:** {a_lbl}<br><span style='opacity:0.8'>{format_period_range(pA)}</span>",
            unsafe_allow_html=True,
        )
        if compare_mode != "None" and pB is not None:
            st.sidebar.markdown(
                f"**Compare:** {b_lbl}<br><span style='opacity:0.8'>{format_period_range(pB)}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                "<span style='opacity:0.75'>Compare: None</span>",
                unsafe_allow_html=True,
            )
    st.sidebar.divider()

    kA = calc_kpis(dfA)
    kB = calc_kpis(dfB) if pB is not None else {k: 0.0 for k in kA.keys()}

    df_hist_for_new = df_all.copy()
    if scope == "Retailer" and scope_pick:
        df_hist_for_new = df_hist_for_new[df_hist_for_new["Retailer"].isin(scope_pick)]
    elif scope == "Vendor" and scope_pick:
        df_hist_for_new = df_hist_for_new[df_hist_for_new["Vendor"].isin(scope_pick)]
    elif scope == "SKU" and scope_pick:
        df_hist_for_new = df_hist_for_new[df_hist_for_new["SKU"].isin(scope_pick)]

    ctx = dict(
        dfA=dfA,
        dfB=dfB,
        kA=kA,
        kB=kB,
        a_lbl=a_lbl,
        b_lbl=b_lbl,
        compare_mode=compare_mode,
        min_sales=min_sales,
        min_units=min_units,
        driver_level=driver_level,
        df_scope=df_scope,
        pA=pA,
        pB=pB,
        df_hist_for_new=df_hist_for_new,
        show_full_history_lifecycle=show_full_history_lifecycle,
        analysis_view=analysis_view,
        content_view=content_view,
        scope=scope,
        scope_pick=scope_pick,
    )

    if get_global_view_mode() == "Visual Analytics":
        render_visual_analysis_view(ctx)
        return

    if analysis_view not in ["Sales Dashboard", "Standard Intelligence"]:
        render_model_header_and_summary(
            analysis_view=analysis_view,
            scope=scope,
            content_view=content_view,
            compare_mode=compare_mode,
            pA=pA,
            pB=pB,
            a_lbl=a_lbl,
            b_lbl=b_lbl,
            kA=kA,
            kB=kB,
            dfA=dfA,
            dfB=dfB,
            driver_level=driver_level,
        )

    render_current_analysis_view(ctx)
