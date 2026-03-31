from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from .shared_core import (
    money,
    pct_fmt,
    kpi_card,
    leader_sales_card,
    biggest_increase_card,
    rename_ab_columns,
    render_df,
    build_momentum,
    opportunity_detector,
    drivers,
    first_sale_ever,
    new_placement,
)
from . import tab_kpi_dashboard


def render(ctx: dict):
    dfA = ctx["dfA"]
    dfB = ctx["dfB"]
    kA = ctx["kA"]
    kB = ctx["kB"]
    a_lbl = ctx["a_lbl"]
    b_lbl = ctx["b_lbl"]
    compare_mode = ctx["compare_mode"]
    min_sales = ctx["min_sales"]
    min_units = ctx["min_units"]
    df_scope = ctx["df_scope"]
    pA = ctx["pA"]
    df_hist_for_new = ctx["df_hist_for_new"]
    show_full_history_lifecycle = ctx["show_full_history_lifecycle"]
    driver_level = ctx["driver_level"]

    def pct_change(cur, prev):
        if prev == 0:
            return np.nan if cur == 0 else np.inf
        return (cur - prev) / prev

    def _delta_html(cur: float, prev: float, is_money: bool):
        d = cur - prev
        color = "#2e7d32" if d > 0 else ("#c62828" if d < 0 else "var(--text-color)")
        arrow = "▲ " if d > 0 else ("▼ " if d < 0 else "")
        abs_s = money(d) if is_money else (f"{d:,.0f}" if abs(d) >= 1 else f"{d:,.2f}")
        return (
            f"<span class='delta-abs' style='color:{color}'>{arrow}{abs_s}</span>"
            f"<span class='delta-pct' style='color:{color}'>({pct_fmt(pct_change(cur, prev))})</span>"
        )

    def kdelta(key: str):
        cur = float(kA.get(key, 0.0))
        prev = float(kB.get(key, 0.0))
        return _delta_html(cur, prev, is_money=(key in ("Sales", "ASP")))

    def _top_by_current(level: str):
        a = dfA.groupby(level, as_index=False).agg(Sales=("Sales", "sum"), Units=("Units", "sum"))
        b = dfB.groupby(level, as_index=False).agg(Sales=("Sales", "sum"), Units=("Units", "sum"))
        m = a.merge(b, on=level, how="outer", suffixes=("_A", "_B")).fillna(0.0)
        if m.empty:
            return None
        row = m.sort_values("Sales_A", ascending=False).iloc[0]
        return str(row[level]), float(row["Sales_A"]), float(row["Sales_B"])

    def _top_by_increase(level: str):
        a = dfA.groupby(level, as_index=False).agg(Sales=("Sales", "sum"))
        b = dfB.groupby(level, as_index=False).agg(Sales=("Sales", "sum"))
        m = a.merge(b, on=level, how="outer", suffixes=("_A", "_B")).fillna(0.0)
        if m.empty:
            return None
        m["Δ"] = m["Sales_A"] - m["Sales_B"]
        row = m.sort_values("Δ", ascending=False).iloc[0]
        return str(row[level]), float(row["Sales_A"]), float(row["Sales_B"])

    def _style_delta_cols(
        df_display: pd.DataFrame,
        df_numeric: pd.DataFrame,
        delta_cols: list[str],
        bold_total: bool = False,
    ):
        def style_row(row):
            idx = row.name
            styles = [""] * len(df_display.columns)

            is_total = False
            if bold_total:
                first_val = str(df_display.iloc[idx, 0]) if idx < len(df_display) else ""
                is_total = first_val == "TOTAL"

            for j, col in enumerate(df_display.columns):
                style_bits = []
                if is_total:
                    style_bits.append("font-weight:800; border-top:2px solid rgba(128,128,128,0.4);")
                if col in delta_cols and col in df_numeric.columns:
                    val = pd.to_numeric(df_numeric.loc[idx, col], errors="coerce")
                    if pd.notna(val):
                        if val > 0:
                            style_bits.append("color:#2e7d32; font-weight:700;")
                        elif val < 0:
                            style_bits.append("color:#c62828; font-weight:700;")
                styles[j] = " ".join(style_bits)
            return styles

        return df_display.style.apply(style_row, axis=1)

    def _parse_weeks(label: str):
        if label == "All weeks":
            return None
        return int(str(label).split()[0])

    def _fmt_metric_value(v: float, metric: str) -> str:
        if pd.isna(v):
            return ""
        return money(v) if metric == "Sales" else f"{float(v):,.0f}"

    def _colorize_delta_value(v: float, metric: str) -> str:
        if pd.isna(v):
            return ""
        sign = "+" if v > 0 else ""
        return f"{sign}{_fmt_metric_value(v, metric)}"

    def _short_week_label(dt_val) -> str:
        d = pd.to_datetime(dt_val)
        return f"{d.month}/{d.day}"

    def _build_hierarchy(df_cur: pd.DataFrame, df_cmp: pd.DataFrame, group_col: str) -> pd.DataFrame:
        a = df_cur.groupby(group_col, as_index=False).agg(Sales_A=("Sales", "sum"))
        b = df_cmp.groupby(group_col, as_index=False).agg(Sales_B=("Sales", "sum"))
        out = a.merge(b, on=group_col, how="outer").fillna(0.0)
        out["Sales_Δ"] = out["Sales_A"] - out["Sales_B"]
        total_delta = float(out["Sales_Δ"].sum()) if not out.empty else 0.0
        out["Contribution_%"] = (out["Sales_Δ"] / total_delta) if total_delta != 0 else 0.0
        return out.sort_values("Sales_Δ", ascending=False).reset_index(drop=True)

    def _display_hierarchy(df_in: pd.DataFrame, group_col: str, height: int = 420):
        show = df_in.copy()
        numeric = show.copy()

        show["Sales_A"] = show["Sales_A"].map(money)
        show["Sales_B"] = show["Sales_B"].map(money)
        show["Sales_Δ"] = show["Sales_Δ"].map(money)
        show["Contribution_%"] = show["Contribution_%"].map(pct_fmt)

        show = rename_ab_columns(show, a_lbl, b_lbl)
        numeric = rename_ab_columns(numeric, a_lbl, b_lbl)

        sales_a_col = f"Sales ({a_lbl})"
        sales_b_col = f"Sales ({b_lbl})" if b_lbl else "Sales (Comparison)"
        cols = [group_col, sales_a_col, sales_b_col, "Sales_Δ", "Contribution_%"]

        styled = _style_delta_cols(show[cols], numeric[cols], ["Sales_Δ"], bold_total=False)
        st.dataframe(
            styled,
            use_container_width=True,
            height=height,
            hide_index=True,
            column_config={
                group_col: st.column_config.TextColumn(width="medium"),
                sales_a_col: st.column_config.TextColumn(width="small"),
                sales_b_col: st.column_config.TextColumn(width="small"),
                "Sales_Δ": st.column_config.TextColumn(width="small"),
                "Contribution_%": st.column_config.TextColumn(width="small"),
            },
        )

    def _compute_lifecycle_custom(df_src: pd.DataFrame, lookback_weeks: int) -> pd.DataFrame:
        d = df_src.copy()
        if d.empty or "WeekEnd" not in d.columns or "SKU" not in d.columns:
            return pd.DataFrame()

        d["WeekEnd"] = pd.to_datetime(d["WeekEnd"], errors="coerce")
        d = d[d["WeekEnd"].notna()].copy()
        if d.empty:
            return pd.DataFrame()

        all_weeks = sorted(d["WeekEnd"].dropna().unique().tolist())
        if not all_weeks:
            return pd.DataFrame()

        sel_weeks = all_weeks[-lookback_weeks:] if len(all_weeks) >= lookback_weeks else all_weeks
        if not sel_weeks:
            return pd.DataFrame()

        end_week = max(sel_weeks)
        look = d[d["WeekEnd"].isin(sel_weeks)].copy()
        hist = d[d["WeekEnd"] <= end_week].copy()

        sku_week = (
            look.groupby(["SKU", "WeekEnd"], as_index=False)
            .agg(Sales=("Sales", "sum"))
        )

        sku_tot = (
            look.groupby("SKU", as_index=False)
            .agg(Sales_lookback=("Sales", "sum"))
        )

        last_week_sales = (
            look[look["WeekEnd"] == end_week]
            .groupby("SKU", as_index=False)
            .agg(Last_Week_Sales=("Sales", "sum"))
        )

        prev_week = sel_weeks[-2] if len(sel_weeks) >= 2 else None
        if prev_week is not None:
            prev_week_sales = (
                look[look["WeekEnd"] == prev_week]
                .groupby("SKU", as_index=False)
                .agg(Prev_Week_Sales=("Sales", "sum"))
            )
        else:
            prev_week_sales = pd.DataFrame(columns=["SKU", "Prev_Week_Sales"])

        first_last = (
            hist.groupby("SKU", as_index=False)
            .agg(
                First_Sale=("WeekEnd", "min"),
                Last_Sale=("WeekEnd", "max"),
            )
        )

        pivot = sku_week.pivot_table(index="SKU", columns="WeekEnd", values="Sales", aggfunc="sum", fill_value=0.0)
        pivot = pivot.reindex(columns=sel_weeks, fill_value=0.0)

        if pivot.empty:
            out = sku_tot.merge(first_last, on="SKU", how="left")
            out = out.merge(last_week_sales, on="SKU", how="left")
            out = out.merge(prev_week_sales, on="SKU", how="left")
            return out

        weeks_with_sales = (pivot > 0).sum(axis=1)
        diffs = pivot.diff(axis=1).iloc[:, 1:] if pivot.shape[1] >= 2 else pd.DataFrame(index=pivot.index)
        weeks_up = (diffs > 0).sum(axis=1) if not diffs.empty else pd.Series(0, index=pivot.index)
        weeks_down = (diffs < 0).sum(axis=1) if not diffs.empty else pd.Series(0, index=pivot.index)
        avg_weekly_sales = pivot.mean(axis=1)

        trend_vals = []
        stage_vals = []

        inactive_cutoff = end_week - pd.Timedelta(weeks=12)

        for sku in pivot.index:
            vals = pivot.loc[sku].astype(float).tolist()
            active_weeks = int((np.array(vals) > 0).sum())
            first_val = vals[0] if vals else 0.0
            last_val = vals[-1] if vals else 0.0

            row_fl = first_last[first_last["SKU"] == sku]
            sku_last_sale = pd.to_datetime(row_fl["Last_Sale"].iloc[0]) if not row_fl.empty else pd.NaT

            growth_pct = np.nan
            if first_val > 0:
                growth_pct = (last_val - first_val) / first_val

            non_zero_vals = [v for v in vals if v > 0]
            mean_non_zero = float(np.mean(non_zero_vals)) if non_zero_vals else 0.0

            if len(vals) >= 2:
                if last_val > vals[-2]:
                    trend = "Up"
                elif last_val < vals[-2]:
                    trend = "Down"
                else:
                    trend = "Flat"
            else:
                trend = "Flat"

            if pd.notna(sku_last_sale) and sku_last_sale <= inactive_cutoff:
                stage = "Inactive 12+ weeks"
            elif active_weeks == 0:
                stage = "Dormant"
            elif active_weeks <= max(2, min(3, lookback_weeks // 4)):
                stage = "Launch"
            elif pd.notna(growth_pct) and growth_pct >= 0.25 and last_val >= mean_non_zero * 0.75:
                stage = "Growth"
            elif active_weeks >= max(3, lookback_weeks // 3) and pd.notna(growth_pct) and growth_pct <= -0.20:
                stage = "Decline"
            else:
                stage = "Mature"

            trend_vals.append(trend)
            stage_vals.append(stage)

        trend_df = pd.DataFrame(
            {
                "SKU": pivot.index,
                "Trend": trend_vals,
                "Weeks With Sales": weeks_with_sales.values,
                "Weeks Up": weeks_up.reindex(pivot.index).fillna(0).astype(int).values,
                "Weeks Down": weeks_down.reindex(pivot.index).fillna(0).astype(int).values,
                "Avg_Weekly_Sales": avg_weekly_sales.values,
                "Stage": stage_vals,
            }
        )

        out = sku_tot.merge(last_week_sales, on="SKU", how="left")
        out = out.merge(prev_week_sales, on="SKU", how="left")
        out = out.merge(first_last, on="SKU", how="left")
        out = out.merge(trend_df, on="SKU", how="left")

        out["Last_Week_Sales"] = out["Last_Week_Sales"].fillna(0.0)
        out["Prev_Week_Sales"] = out["Prev_Week_Sales"].fillna(0.0)
        out["Avg_Weekly_Sales"] = out["Avg_Weekly_Sales"].fillna(0.0)
        out["WoW_Sales_Δ"] = out["Last_Week_Sales"] - out["Prev_Week_Sales"]
        out["Last_Week_vs_Avg"] = out["Last_Week_Sales"] - out["Avg_Weekly_Sales"]

        return out.sort_values(["Sales_lookback", "SKU"], ascending=[False, True]).reset_index(drop=True)

    if hasattr(tab_kpi_dashboard, "render"):
        tab_kpi_dashboard.render(ctx)
        st.divider()

    first_ever = first_sale_ever(df_hist_for_new, pA)
    placements = new_placement(df_hist_for_new, pA)

    st.divider()
    st.subheader("Weekly Detail (Retailer/Vendor x Weeks)")

    with st.expander("Advanced Weekly Detail Settings", expanded=False):
        adv1, adv2, adv3, adv4 = st.columns(4)

        with adv1:
            pivot_dim = st.selectbox(
                "Pivot rows by",
                options=["Retailer", "Vendor"],
                index=0,
                key="std_weekly_pivot_dim",
            )

        with adv2:
            weekly_metric = st.selectbox(
                "Metric",
                options=["Sales", "Units"],
                index=0,
                key="std_weekly_metric",
            )

        with adv3:
            display_timeframe = st.selectbox(
                "Display Time Frame",
                options=["4 weeks", "8 weeks", "13 weeks", "26 weeks", "52 weeks", "All weeks"],
                index=2,
                key="std_weekly_display_timeframe",
            )

        with adv4:
            avg_window_label = st.selectbox(
                "Average Window",
                options=["None", "4 weeks", "8 weeks", "13 weeks", "26 weeks", "52 weeks"],
                index=1,
                key="std_weekly_avg_window",
            )

    d_all = df_scope.copy()
    d_all = d_all[(d_all["Sales"] >= min_sales) | (d_all["Units"] >= min_units)].copy()

    if d_all.empty:
        st.caption("No rows match the current thresholds.")
    else:
        wk_metric = d_all.groupby([pivot_dim, "WeekEnd"], as_index=False).agg(Value=(weekly_metric, "sum"))
        wk_metric["WeekEnd"] = pd.to_datetime(wk_metric["WeekEnd"], errors="coerce")
        wk_metric = wk_metric[wk_metric["WeekEnd"].notna()].copy()

        all_weeks = sorted(pd.to_datetime(wk_metric["WeekEnd"].dropna().unique()).tolist())
        display_n = _parse_weeks(display_timeframe)
        avg_n = None if avg_window_label == "None" else int(str(avg_window_label).split()[0])

        display_weeks = all_weeks[-display_n:] if display_n is not None else all_weeks
        display_weeks_set = set(display_weeks)

        wk_disp = wk_metric[wk_metric["WeekEnd"].isin(display_weeks_set)].copy()

        week_map = {pd.to_datetime(w): _short_week_label(w) for w in display_weeks}
        wk_disp["Week"] = wk_disp["WeekEnd"].map(week_map)

        piv = wk_disp.pivot_table(
            index=pivot_dim,
            columns="Week",
            values="Value",
            aggfunc="sum",
            fill_value=0.0,
        )

        row_order = sorted(wk_disp[pivot_dim].dropna().unique().tolist())
        piv = piv.reindex(row_order)

        display_week_labels = [_short_week_label(w) for w in display_weeks]
        existing_week_cols = [c for c in display_week_labels if c in piv.columns]
        piv = piv.reindex(columns=existing_week_cols, fill_value=0.0)

        numeric = piv.copy()

        if len(existing_week_cols) >= 2:
            last_col = existing_week_cols[-1]
            prev_col = existing_week_cols[-2]
            numeric["Δ vs prior"] = numeric[last_col] - numeric[prev_col]
        else:
            numeric["Δ vs prior"] = 0.0

        if avg_n is None:
            numeric["Avg"] = np.nan
            numeric["Δ vs avg"] = np.nan
        else:
            avg_source_weeks = all_weeks[-avg_n:]
            avg_source = wk_metric.copy()
            avg_source["Week"] = avg_source["WeekEnd"].map(lambda w: _short_week_label(w))
            piv_avg = avg_source.pivot_table(
                index=pivot_dim,
                columns="Week",
                values="Value",
                aggfunc="sum",
                fill_value=0.0,
            )
            piv_avg = piv_avg.reindex(index=numeric.index)
            avg_existing_cols = [_short_week_label(w) for w in avg_source_weeks]
            avg_existing_cols = [c for c in avg_existing_cols if c in piv_avg.columns]

            if avg_existing_cols:
                numeric["Avg"] = piv_avg[avg_existing_cols].mean(axis=1)
                current_col = existing_week_cols[-1] if existing_week_cols else None
                numeric["Δ vs avg"] = numeric[current_col] - numeric["Avg"] if current_col is not None else np.nan
            else:
                numeric["Avg"] = np.nan
                numeric["Δ vs avg"] = np.nan

        total_row = pd.DataFrame([numeric.sum(numeric_only=True)], index=["TOTAL"])
        numeric = pd.concat([numeric, total_row], axis=0)

        display_df = numeric.copy()
        for c in existing_week_cols:
            display_df[c] = display_df[c].map(lambda x: _fmt_metric_value(x, weekly_metric))

        display_df["Δ vs prior"] = display_df["Δ vs prior"].map(
            lambda x: _colorize_delta_value(x, weekly_metric)
        )
        display_df["Avg"] = display_df["Avg"].map(lambda x: _fmt_metric_value(x, weekly_metric))
        display_df["Δ vs avg"] = display_df["Δ vs avg"].map(lambda x: _colorize_delta_value(x, weekly_metric))

        display_df = display_df.reset_index().rename(columns={"index": pivot_dim})
        numeric_reset = numeric.reset_index().rename(columns={"index": pivot_dim})

        weekly_cols = [pivot_dim] + existing_week_cols + ["Δ vs prior", "Avg", "Δ vs avg"]

        styled_weekly = _style_delta_cols(
            display_df[weekly_cols],
            numeric_reset[weekly_cols],
            ["Δ vs prior", "Δ vs avg"],
            bold_total=True,
        )

        col_cfg = {pivot_dim: st.column_config.TextColumn(width="medium")}
        for c in existing_week_cols:
            col_cfg[c] = st.column_config.TextColumn(width="small")
        col_cfg["Δ vs prior"] = st.column_config.TextColumn(width="small")
        col_cfg["Avg"] = st.column_config.TextColumn(width="small")
        col_cfg["Δ vs avg"] = st.column_config.TextColumn(width="small")

        st.dataframe(
            styled_weekly,
            use_container_width=True,
            height=560,
            hide_index=True,
            column_config=col_cfg,
        )

    st.divider()
    st.subheader("Drivers (Contribution to change)")
    if compare_mode == "None":
        st.info("Select a comparison mode to compute drivers.")
    else:
        drv = drivers(dfA, dfB, driver_level)
        drv_show = drv.copy()
        drv_show = drv_show[(drv_show["Sales_A"] >= min_sales) | (drv_show["Sales_B"] >= min_sales)]

        pos = drv_show[drv_show["Sales_Δ"] > 0].sort_values("Sales_Δ", ascending=False).copy()
        neg = drv_show[drv_show["Sales_Δ"] < 0].sort_values("Sales_Δ", ascending=True).copy()

        for d in (pos, neg):
            d["Sales_A"] = d["Sales_A"].map(money)
            d["Sales_B"] = d["Sales_B"].map(money)
            d["Sales_Δ"] = d["Sales_Δ"].map(lambda v: f"{money(v)}")
            d["Contribution_%"] = d["Contribution_%"].map(pct_fmt)

        left, right = st.columns(2)
        pos_disp = rename_ab_columns(pos, a_lbl, b_lbl)
        neg_disp = rename_ab_columns(neg, a_lbl, b_lbl)
        sales_a_col = f"Sales ({a_lbl})"
        sales_b_col = f"Sales ({b_lbl})" if b_lbl else "Sales (Comparison)"

        with left:
            st.markdown("**Positive Contributors**")
            render_df(pos_disp[[driver_level, sales_a_col, sales_b_col, "Sales_Δ", "Contribution_%"]], height=320)
        with right:
            st.markdown("**Negative Contributors**")
            render_df(neg_disp[[driver_level, sales_a_col, sales_b_col, "Sales_Δ", "Contribution_%"]], height=320)

    st.divider()
    st.subheader("New Activity")

    a, b = st.columns(2)
    with a:
        st.markdown("**First Sale Ever (Launches)**")
        if first_ever.empty:
            st.caption("None in this period.")
        else:
            fe = first_ever.copy()
            fe["FirstWeek"] = pd.to_datetime(fe["FirstWeek"], errors="coerce")
            if "FirstRetailer" in fe.columns:
                fe["Retailer"] = fe["FirstRetailer"]
            if "Sales" not in fe.columns:
                if "FirstSales" in fe.columns:
                    fe["Sales"] = fe["FirstSales"]
                else:
                    fe["Sales"] = np.nan
            fe["Date"] = fe["FirstWeek"].dt.date.astype(str)
            fe["Sales"] = fe["Sales"].map(lambda v: "" if pd.isna(v) else money(v))
            cols = [c for c in ["SKU", "Retailer", "Date", "Sales"] if c in fe.columns]
            render_df(fe[cols], height=300)

    with b:
        st.markdown("**New Retailer Placements**")
        if placements.empty:
            st.caption("None in this period.")
        else:
            pl = placements.copy()
            pl["FirstWeek"] = pd.to_datetime(pl["FirstWeek"], errors="coerce")
            if "Sales" not in pl.columns:
                if "FirstSales" in pl.columns:
                    pl["Sales"] = pl["FirstSales"]
                else:
                    pl["Sales"] = np.nan
            pl["Date"] = pl["FirstWeek"].dt.date.astype(str)
            pl["Sales"] = pl["Sales"].map(lambda v: "" if pd.isna(v) else money(v))
            cols = [c for c in ["SKU", "Retailer", "Date", "Sales"] if c in pl.columns]
            render_df(pl[cols], height=300)

    st.divider()
    st.header("Strategic Intelligence")

    st.subheader("1) Contribution Tree (Where did change come from?)")
    if compare_mode == "None":
        st.info("Select a comparison mode to use the contribution tree.")
    else:
        level1_choice = st.selectbox(
            "Level 1 View",
            ["Retailer", "Vendor"],
            index=0,
            key="std_contrib_level1_choice",
        )

        if level1_choice == "Retailer":
            level1_col = "Retailer"
            level2_col = "Vendor"
            level3_col = "SKU"
        else:
            level1_col = "Vendor"
            level2_col = "Retailer"
            level3_col = "SKU"

        lvl1 = _build_hierarchy(dfA, dfB, level1_col)
        st.markdown(f"**Level 1 — {level1_col}s**")
        _display_hierarchy(lvl1, level1_col, height=500)

        lvl1_options = ["(none)"] + lvl1[level1_col].dropna().astype(str).tolist()
        pick1 = st.selectbox(
            f"Select {level1_col} for Level 2",
            lvl1_options,
            index=0,
            key="std_contrib_pick1",
        )

        if pick1 != "(none)":
            dfA_l2 = dfA[dfA[level1_col].astype(str) == str(pick1)].copy()
            dfB_l2 = dfB[dfB[level1_col].astype(str) == str(pick1)].copy()

            lvl2 = _build_hierarchy(dfA_l2, dfB_l2, level2_col)
            st.markdown(f"**Level 2 — {level2_col}s inside {pick1}**")
            _display_hierarchy(lvl2, level2_col, height=500)

            lvl2_options = ["(none)"] + lvl2[level2_col].dropna().astype(str).tolist()
            pick2 = st.selectbox(
                f"Select {level2_col} for Level 3",
                lvl2_options,
                index=0,
                key="std_contrib_pick2",
            )

            if pick2 != "(none)":
                dfA_l3 = dfA_l2[dfA_l2[level2_col].astype(str) == str(pick2)].copy()
                dfB_l3 = dfB_l2[dfB_l2[level2_col].astype(str) == str(pick2)].copy()

                lvl3 = _build_hierarchy(dfA_l3, dfB_l3, level3_col)
                st.markdown(f"**Level 3 — {level3_col}s inside {pick1} → {pick2}**")
                _display_hierarchy(lvl3, level3_col, height=520)

    st.subheader("2) SKU Lifecycle (Launch → Growth → Mature → Decline → Dormant)")

    with st.expander("Advanced SKU Lifecycle Settings", expanded=False):
        lc1, lc2 = st.columns(2)
        with lc1:
            lifecycle_timeframe_label = st.selectbox(
                "Lifecycle Timeframe",
                ["4 weeks", "8 weeks", "13 weeks", "26 weeks", "52 weeks"],
                index=1,
                key="std_lifecycle_timeframe",
            )
        with lc2:
            stage_filter = st.multiselect(
                "Stages",
                ["Launch", "Growth", "Mature", "Decline", "Dormant", "Inactive 12+ weeks"],
                default=["Launch", "Growth", "Mature", "Decline", "Dormant", "Inactive 12+ weeks"],
                key="std_lifecycle_stage_filter",
            )

    lifecycle_weeks = int(lifecycle_timeframe_label.split()[0])

    life_df_src = df_hist_for_new if show_full_history_lifecycle else df_scope
    life = _compute_lifecycle_custom(life_df_src, lifecycle_weeks)

    if life.empty:
        st.caption("Not enough data to compute lifecycle.")
    else:
        if stage_filter:
            life = life[life["Stage"].isin(stage_filter)].copy()

        stage_counts = life["Stage"].value_counts().reset_index()
        stage_counts.columns = ["Stage", "Count"]

        stage_order = [
            "Launch",
            "Growth",
            "Mature",
            "Decline",
            "Dormant",
            "Inactive 12+ weeks",
        ]
        stage_counts["Stage"] = pd.Categorical(stage_counts["Stage"], categories=stage_order, ordered=True)
        stage_counts = stage_counts.sort_values("Stage").reset_index(drop=True)

        st.markdown("**Stage Summary**")
        render_df(stage_counts, height=220)

        st.markdown("**Lifecycle Detail**")
        life_show = life.copy()

        if min_sales > 0 and "Sales_lookback" in life_show.columns:
            life_show = life_show[life_show["Sales_lookback"] >= min_sales].copy()

        rename_map = {
            "Sales_lookback": "Sales (lookback)",
            "Last_Week_Sales": "Last Week Sales",
            "Avg_Weekly_Sales": "Avg Weekly Sales",
            "Last_Week_vs_Avg": "Last Week vs Avg",
            "WoW_Sales_Δ": "WoW Sales Δ",
        }
        life_show = life_show.rename(columns=rename_map)

        cols = [
            c for c in [
                "SKU",
                "Stage",
                "Trend",
                "Sales (lookback)",
                "Last Week Sales",
                "Avg Weekly Sales",
                "Last Week vs Avg",
                "WoW Sales Δ",
                "Weeks Up",
                "Weeks Down",
                "Weeks With Sales",
            ]
            if c in life_show.columns
        ]

        numeric_life = life_show[cols].copy()

        total_row = {"SKU": "TOTAL"}
        for c in cols:
            if c == "SKU":
                continue
            if c in ["Stage", "Trend"]:
                total_row[c] = ""
            elif c in ["Sales (lookback)", "Last Week Sales", "Avg Weekly Sales", "Last Week vs Avg", "WoW Sales Δ"]:
                total_row[c] = pd.to_numeric(numeric_life[c], errors="coerce").fillna(0).sum()
            elif c in ["Weeks Up", "Weeks Down", "Weeks With Sales"]:
                total_row[c] = pd.to_numeric(numeric_life[c], errors="coerce").fillna(0).sum()
            else:
                total_row[c] = ""

        numeric_life = pd.concat([numeric_life, pd.DataFrame([total_row])], ignore_index=True)
        life_show = numeric_life.copy()

        for c in ["Sales (lookback)", "Last Week Sales", "Avg Weekly Sales", "Last Week vs Avg", "WoW Sales Δ"]:
            if c in life_show.columns:
                if c in ["Last Week vs Avg", "WoW Sales Δ"]:
                    life_show[c] = life_show[c].map(
                        lambda v: "" if pd.isna(v) else f"{'+' if float(v) > 0 else ''}{money(float(v))}"
                    )
                else:
                    life_show[c] = life_show[c].map(
                        lambda v: "" if pd.isna(v) else money(float(v))
                    )

        if "Weeks With Sales" in life_show.columns:
            life_show["Weeks With Sales"] = life_show["Weeks With Sales"].map(
                lambda v: "" if pd.isna(v) else f"{int(float(v)):,}"
            )

        if "Weeks Up" in life_show.columns:
            life_show["Weeks Up"] = life_show["Weeks Up"].map(
                lambda v: "" if pd.isna(v) else f"{int(float(v)):,}"
            )

        if "Weeks Down" in life_show.columns:
            life_show["Weeks Down"] = life_show["Weeks Down"].map(
                lambda v: "" if pd.isna(v) else f"{int(float(v)):,}"
            )

        life_cfg = {"SKU": st.column_config.TextColumn(width="medium")}
        for c in cols:
            if c != "SKU":
                life_cfg[c] = st.column_config.TextColumn(width="small")

        styled_life = _style_delta_cols(
            life_show[cols],
            numeric_life[cols],
            ["Last Week vs Avg", "WoW Sales Δ"],
            bold_total=True,
        )

        st.dataframe(
            styled_life,
            use_container_width=True,
            height=620,
            hide_index=True,
            column_config=life_cfg,
        )

    st.divider()
    st.subheader("3) Opportunity Detector (Find expansion + gaps)")
    if compare_mode == "None":
        st.info("Select a comparison mode to power opportunity signals (needs a comparison).")
    else:
        opp = opportunity_detector(df_hist_for_new, dfA, dfB, pA)
        tabs = st.tabs(list(opp.keys()))
        for t, (name, odf) in zip(tabs, opp.items()):
            with t:
                render_df(odf, height=420) if not odf.empty else st.caption(
                    "No signals found with current filters/thresholds."
                )

def render_visual_only(ctx: dict):
    dfA = ctx["dfA"]
    dfB = ctx["dfB"]
    kA = ctx["kA"]
    kB = ctx["kB"]
    a_lbl = ctx["a_lbl"]
    b_lbl = ctx["b_lbl"]
    compare_mode = ctx["compare_mode"]

    st.subheader("Standard Intelligence • Visual Analytics")

    if compare_mode == "None":
        st.info("Select a comparison mode to use Standard Intelligence visual analytics.")
        return

    POSITIVE_BAR = "#2e7d32"
    NEGATIVE_BAR = "#c62828"
    NEUTRAL_BAR = "#808080"

    theme_base = st.get_option("theme.base") or "light"
    is_dark = str(theme_base).lower() == "dark"

    AXIS_TEXT_COLOR = "#F3F4F6" if is_dark else "#111111"
    TITLE_TEXT_COLOR = "#F3F4F6" if is_dark else "#111111"
    LABEL_INSIDE_BAR_COLOR = "#000000"
    OUTLINE_COLOR = "#111111" if is_dark else "#FFFFFF"
    
    # Adaptive label text colors - high contrast readable on both light and dark backgrounds
    LABEL_TEXT_COLOR = "#F3F4F6" if is_dark else "#111111"
    LABEL_POSITIVE_COLOR = "#FFFFFF" if is_dark else "#1B5E20"  # White for dark, dark green for light
    LABEL_NEGATIVE_COLOR = "#FFFFFF" if is_dark else "#B71C1C"   # White for dark, dark red for light
    LABEL_NEUTRAL_COLOR = "#FFFFFF" if is_dark else "#424242"    # White for dark, dark gray for light

    TOTAL_BLOCK_VALUE = 30000.0
    CHANGE_BLOCK_VALUE = 1000.0

    AXIS_LABEL_FONTSIZE = 14
    AXIS_TITLE_FONTSIZE = 15
    CHART_TITLE_FONTSIZE = 18
    Y_LABEL_LIMIT = 260

    def _text_style(font_size: int = 15, color: str = AXIS_TEXT_COLOR):
        return {
            "fontSize": font_size,
            "fontWeight": "bold",
            "color": color,
            "stroke": OUTLINE_COLOR,
            "strokeWidth": 0.6,
        }

    def _format_metric(v: float, metric: str) -> str:
        return money(float(v)) if metric == "Sales" else f"{float(v):,.0f}"

    def _totals_df(metric: str) -> pd.DataFrame:
        cur = float(kA.get(metric, 0.0))
        cmpv = float(kB.get(metric, 0.0))

        if cur > cmpv:
            cur_color, cmp_color = POSITIVE_BAR, NEGATIVE_BAR
        elif cur < cmpv:
            cur_color, cmp_color = NEGATIVE_BAR, POSITIVE_BAR
        else:
            cur_color = cmp_color = NEUTRAL_BAR

        out = pd.DataFrame(
            [
                {"Period": "Current", "Value": cur, "Label": _format_metric(cur, metric), "Color": cur_color},
                {"Period": "Compare", "Value": cmpv, "Label": _format_metric(cmpv, metric), "Color": cmp_color},
            ]
        )
        out["LabelX"] = out["Value"]
        return out

    def _render_total_bars(df: pd.DataFrame, axis_title: str):
        if df.empty:
            st.info("No data available for totals.")
            return

        xmax = float(df["Value"].max()) if not df.empty else 0.0
        xmax = xmax * 1.20 if xmax > 0 else 1.0

        bars = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, size=7)
            .encode(
                y=alt.Y(
                    "Period:N",
                    title="",
                    sort=["Compare", "Current"],
                    axis=alt.Axis(
                        labelFontSize=13,
                        labelColor=AXIS_TEXT_COLOR,
                        labelLimit=220,
                    ),
                ),
                x=alt.X(
                    "Value:Q",
                    title=axis_title,
                    scale=alt.Scale(domain=[0, xmax]),
                    axis=alt.Axis(
                        labelFontSize=AXIS_LABEL_FONTSIZE,
                        titleFontSize=AXIS_TITLE_FONTSIZE,
                        labelColor=AXIS_TEXT_COLOR,
                        titleColor=AXIS_TEXT_COLOR,
                    ),
                ),
                color=alt.Color("Color:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("Period:N", title="Period"),
                    alt.Tooltip("Value:Q", title=axis_title, format=",.2f" if axis_title == "Sales" else ",.0f"),
                ],
            )
            .properties(height=150)
        )

        labels = (
            alt.Chart(df)
            .mark_text(
                align="left",
                dx=8,
                baseline="middle",
                fontSize=16,
                fontWeight="bold",
                color="#000000",
            )
            .encode(
                y=alt.Y("Period:N", sort=["Compare", "Current"]),
                x=alt.X("LabelX:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Label:N",
            )
        )

        st.altair_chart(bars + labels, use_container_width=True)

    def collect_change_contributors_by_dim(
        df_cur: pd.DataFrame,
        df_cmp: pd.DataFrame,
        dim: str,
        *,
        top_n_pos: int | None = None,
        top_n_neg: int | None = None,
        pick_most_negative: bool = False,
    ) -> pd.DataFrame:
        if dim not in df_cur.columns or dim not in df_cmp.columns:
            return pd.DataFrame(columns=["Label", "Delta", "ColorHex", "Side", "Direction"])

        cur = df_cur.groupby(dim, as_index=False).agg(Current=("Sales", "sum"))
        cmp = df_cmp.groupby(dim, as_index=False).agg(Compare=("Sales", "sum"))
        out = cur.merge(cmp, on=dim, how="outer").fillna(0.0)
        out["Label"] = out[dim].astype(str)
        out["Delta"] = out["Current"] - out["Compare"]
        out = out[["Label", "Delta"]].copy()
        out = out[np.isfinite(out["Delta"])].copy()
        out = out[out["Delta"] != 0].copy()

        out["ColorHex"] = np.where(out["Delta"] > 0, POSITIVE_BAR, NEGATIVE_BAR)
        out["Side"] = np.where(out["Delta"] > 0, "right", "left")
        out["Direction"] = np.where(out["Delta"] > 0, "right", "left")

        pos = out[out["Delta"] > 0].sort_values(["Delta", "Label"], ascending=[False, True]).copy()
        neg = out[out["Delta"] < 0].copy()

        if pick_most_negative:
            neg = neg.sort_values(["Delta", "Label"], ascending=[True, True])
            if top_n_neg is not None:
                neg = neg.head(top_n_neg)
            neg = neg.sort_values(["Delta", "Label"], ascending=[False, True])
        else:
            neg = neg.sort_values(["Delta", "Label"], ascending=[False, True])

        if top_n_pos is not None:
            pos = pos.head(top_n_pos)
        if top_n_neg is not None and not pick_most_negative:
            neg = neg.head(top_n_neg)

        return pd.concat([pos, neg], ignore_index=True)

    def single_total_bar_chart(value: float, period_label: str, color_hex: str, xmax: float):
        value = float(max(value, 0.0))
        row_df = pd.DataFrame(
            [
                {
                    "Period": period_label,
                    "X0": 0.0,
                    "X1": value,
                    "Value": value,
                    "Label": money(value),
                    "ColorHex": color_hex,
                }
            ]
        )

        bars = (
            alt.Chart(row_df)
            .mark_bar(stroke="white", strokeWidth=1, size=10)
            .encode(
                y=alt.Y("Period:N", title="", axis=alt.Axis(labelFontSize=13)),
                x=alt.X("X0:Q", title="Sales", scale=alt.Scale(domain=[0, xmax])),
                x2="X1:Q",
                color=alt.Color("ColorHex:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("Period:N", title="Period"),
                    alt.Tooltip("Value:Q", title="Sales", format=",.2f"),
                ],
            )
        )

        labels = (
            alt.Chart(row_df)
            .mark_text(align="left", dx=8, fontSize=14, fontWeight="bold")
            .encode(
                y=alt.Y("Period:N"),
                x=alt.X("X1:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Label:N",
                color=alt.Color("ColorHex:N", scale=None, legend=None),
            )
        )

        return (bars + labels).properties(height=32)

    def change_only_center_chart(changes_df: pd.DataFrame):
        if changes_df.empty or changes_df[changes_df["Delta"] != 0].empty:
            empty_df = pd.DataFrame([{"Msg": "No change contributors available."}])
            return (
                alt.Chart(empty_df)
                .mark_text(fontSize=13, color="#7a7a7a")
                .encode(text="Msg:N")
                .properties(height=60)
            )

        delta_df = changes_df[changes_df["Delta"] != 0].copy()
        delta_df = pd.concat(
            [
                delta_df[delta_df["Delta"] > 0].sort_values(["Delta", "Label"], ascending=[False, True]),
                delta_df[delta_df["Delta"] < 0].sort_values(["Delta", "Label"], ascending=[False, True]),
            ],
            ignore_index=True,
        )

        y_order = delta_df["Label"].astype(str).tolist()

        delta_df["Label"] = delta_df["Label"].astype(str)
        delta_df["X0"] = np.where(delta_df["Delta"] > 0, 0.0, delta_df["Delta"])
        delta_df["X1"] = np.where(delta_df["Delta"] > 0, delta_df["Delta"], 0.0)
        delta_df["DeltaLabel"] = delta_df["Delta"].map(money)

        max_abs = float(delta_df["Delta"].abs().max())
        pad = max(max_abs * 0.08, CHANGE_BLOCK_VALUE * 1.2)
        xmax = max_abs + pad

        bars = (
            alt.Chart(delta_df)
            .mark_bar(stroke="white", strokeWidth=1, size=8)
            .encode(
                y=alt.Y("Label:N", sort=y_order, title="", axis=alt.Axis(labelFontSize=12)),
                x=alt.X("X0:Q", title="Sales Change", scale=alt.Scale(domain=[-xmax, xmax])),
                x2="X1:Q",
                color=alt.Color("ColorHex:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("Label:N", title="Contributor"),
                    alt.Tooltip("Delta:Q", title="Sales Change", format=",.2f"),
                ],
            )
        )

        zero_rule = (
            alt.Chart(pd.DataFrame([{"Zero": 0.0}]))
            .mark_rule(color="#7a7a7a", strokeDash=[4, 4], strokeWidth=1.5)
            .encode(x=alt.X("Zero:Q", scale=alt.Scale(domain=[-xmax, xmax])))
        )

        pos_labels = (
            alt.Chart(delta_df[delta_df["Delta"] > 0])
            .mark_text(align="left", dx=8, fontSize=13, fontWeight="bold", clip=False)
            .encode(
                y=alt.Y("Label:N", sort=y_order),
                x=alt.X("X1:Q", scale=alt.Scale(domain=[-xmax, xmax])),
                text="DeltaLabel:N",
                color=alt.Color("ColorHex:N", scale=None, legend=None),
            )
        )

        neg_labels = (
            alt.Chart(delta_df[delta_df["Delta"] < 0])
            .mark_text(align="right", dx=-8, fontSize=13, fontWeight="bold", clip=False)
            .encode(
                y=alt.Y("Label:N", sort=y_order),
                x=alt.X("X0:Q", scale=alt.Scale(domain=[-xmax, xmax])),
                text="DeltaLabel:N",
                color=alt.Color("ColorHex:N", scale=None, legend=None),
            )
        )

        mid_height = max(90, 28 * len(delta_df))
        return (bars + zero_rule + pos_labels + neg_labels).properties(height=mid_height)

    def render_with_side_margins(chart):
        chart_col, right_gap = st.columns([0.94, 0.06])
        with chart_col:
            st.altair_chart(chart, use_container_width=True)

    def render_change_section(title: str, subtitle: str, chart):
        with st.container(border=True):
            st.markdown(f"#### {title}")
            st.caption(subtitle)
            render_with_side_margins(chart)

    def _sales_contribution_block_chart(current_value: float, compare_value: float, changes_df: pd.DataFrame, title: str = "Sales Contribution Change"):
        def _total_label(v: float) -> str:
            return money(float(v))

        def _change_label(v: float) -> str:
            return money(abs(float(v)))

        current_value = float(max(current_value, 0.0))
        compare_value = float(max(compare_value, 0.0))

        if current_value > compare_value:
            current_color, compare_color = POSITIVE_BAR, NEGATIVE_BAR
        elif current_value < compare_value:
            current_color, compare_color = NEGATIVE_BAR, POSITIVE_BAR
        else:
            current_color = compare_color = NEUTRAL_BAR

        rows = [
            {
                "Period": b_lbl,
                "Kind": "total",
                "Value": compare_value,
                "Direction": "right",
                "ColorHex": compare_color,
                "Side": "right",
                "Text": _total_label(compare_value),
                "BlockValue": TOTAL_BLOCK_VALUE,
            }
        ]

        if changes_df is not None and not changes_df.empty:
            for _, r in changes_df.iterrows():
                rows.append(
                    {
                        "Period": str(r["Label"]),
                        "Kind": "change",
                        "Value": abs(float(r["Delta"])),
                        "Direction": str(r["Direction"]),
                        "ColorHex": str(r["ColorHex"]),
                        "Side": str(r["Side"]),
                        "Text": _change_label(float(r["Delta"])),
                        "BlockValue": CHANGE_BLOCK_VALUE,
                    }
                )

        rows.append(
            {
                "Period": a_lbl,
                "Kind": "total",
                "Value": current_value,
                "Direction": "right",
                "ColorHex": current_color,
                "Side": "right",
                "Text": _total_label(current_value),
                "BlockValue": TOTAL_BLOCK_VALUE,
            }
        )

        row_df = pd.DataFrame(rows)

        total_max = float(max(compare_value, current_value, TOTAL_BLOCK_VALUE))
        change_max = (
            float(row_df.loc[row_df["Kind"] == "change", "Value"].max())
            if (row_df["Kind"] == "change").any()
            else CHANGE_BLOCK_VALUE
        )
        change_max = max(change_max, CHANGE_BLOCK_VALUE)

        center_from_compare = compare_value / 2.0
        min_center_needed = change_max + max(CHANGE_BLOCK_VALUE * 2, change_max * 0.04)
        center_x = max(center_from_compare, min_center_needed)
        center_x = float(np.ceil(center_x / CHANGE_BLOCK_VALUE) * CHANGE_BLOCK_VALUE)

        right_needed_for_changes = center_x + change_max + max(CHANGE_BLOCK_VALUE * 2, change_max * 0.04)
        right_needed_for_totals = total_max + max(TOTAL_BLOCK_VALUE, total_max * 0.02)
        xmax = float(max(right_needed_for_changes, right_needed_for_totals))
        xmax = float(np.ceil(xmax / CHANGE_BLOCK_VALUE) * CHANGE_BLOCK_VALUE)

        block_rows = []
        label_rows = []

        for _, r in row_df.iterrows():
            value = float(max(r["Value"], 0.0))
            block_value = float(r["BlockValue"])

            if r["Kind"] == "total":
                n_blocks = max(1, int(np.ceil(value / block_value))) if value > 0 else 1
                for i in range(n_blocks):
                    x0 = i * block_value if value > 0 else 0.0
                    x1 = min((i + 1) * block_value, value) if value > 0 else 0.0
                    block_rows.append({"Period": r["Period"], "X0": x0, "X1": x1, "ColorHex": r["ColorHex"]})
                label_rows.append({"Period": r["Period"], "X": value, "Text": r["Text"], "ColorHex": r["ColorHex"], "Side": "right"})
            else:
                n_blocks = max(1, int(np.ceil(value / block_value))) if value > 0 else 1
                for i in range(n_blocks):
                    piece_start = i * block_value if value > 0 else 0.0
                    piece_end = min((i + 1) * block_value, value) if value > 0 else 0.0
                    if r["Direction"] == "right":
                        x0 = center_x + piece_start
                        x1 = center_x + piece_end
                    else:
                        x0 = center_x - piece_end
                        x1 = center_x - piece_start
                    block_rows.append({"Period": r["Period"], "X0": x0, "X1": x1, "ColorHex": r["ColorHex"]})
                label_rows.append(
                    {
                        "Period": r["Period"],
                        "X": center_x + value if r["Direction"] == "right" else center_x - value,
                        "Text": r["Text"],
                        "ColorHex": r["ColorHex"],
                        "Side": r["Side"],
                    }
                )

        block_df = pd.DataFrame(block_rows)
        labels_df = pd.DataFrame(label_rows)
        order = row_df["Period"].tolist()
        
        # Map bar colors to label colors for readability on both light and dark backgrounds
        def _get_label_color(color_hex: str) -> str:
            if color_hex == POSITIVE_BAR:
                return LABEL_POSITIVE_COLOR
            elif color_hex == NEGATIVE_BAR:
                return LABEL_NEGATIVE_COLOR
            else:
                return LABEL_NEUTRAL_COLOR
        
        labels_df["LabelColor"] = labels_df["ColorHex"].apply(_get_label_color)

        def _bar_layer(df_sub: pd.DataFrame, color_hex: str):
            if df_sub.empty:
                return None
            return (
                alt.Chart(df_sub)
                .mark_bar(color=color_hex, stroke="white", strokeWidth=1)
                .encode(
                    y=alt.Y(
                        "Period:N",
                        sort=order,
                        title="",
                        axis=alt.Axis(
                            labelFontSize=AXIS_LABEL_FONTSIZE,
                            labelColor=AXIS_TEXT_COLOR,
                            labelLimit=220,
                        ),
                    ),
                    x=alt.X(
                        "X0:Q",
                        title="Sales",
                        scale=alt.Scale(domain=[0, xmax]),
                        axis=alt.Axis(
                            labelFontSize=AXIS_LABEL_FONTSIZE,
                            titleFontSize=AXIS_TITLE_FONTSIZE,
                            labelColor=AXIS_TEXT_COLOR,
                            titleColor=AXIS_TEXT_COLOR,
                        ),
                    ),
                    x2="X1:Q",
                )
            )

        layers = []
        for color_hex in (POSITIVE_BAR, NEGATIVE_BAR, NEUTRAL_BAR):
            lyr = _bar_layer(block_df[block_df["ColorHex"] == color_hex].copy(), color_hex)
            if lyr is not None:
                layers.append(lyr)

        layers.append(
            alt.Chart(pd.DataFrame([{"Center": center_x}]))
            .mark_rule(color="#7a7a7a", strokeDash=[4, 4], strokeWidth=1.5)
            .encode(x=alt.X("Center:Q", scale=alt.Scale(domain=[0, xmax])))
        )

        layers.append(
            alt.Chart(labels_df[labels_df["Side"] == "right"])
            .mark_text(align="left", dx=8, fontSize=14, fontWeight="bold")
            .encode(
                y=alt.Y("Period:N", sort=order),
                x=alt.X("X:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Text:N",
                color=alt.Color("LabelColor:N", scale=None, legend=None),
            )
        )

        layers.append(
            alt.Chart(labels_df[labels_df["Side"] == "left"])
            .mark_text(align="right", dx=-8, fontSize=14, fontWeight="bold")
            .encode(
                y=alt.Y("Period:N", sort=order),
                x=alt.X("X:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Text:N",
                color=alt.Color("LabelColor:N", scale=None, legend=None),
            )
        )

        return alt.layer(*layers).properties(
            height=max(300, len(order) * 42),
            title=alt.TitleParams(title, fontSize=CHART_TITLE_FONTSIZE, color=TITLE_TEXT_COLOR),
        )

    def _vendor_delta_df() -> pd.DataFrame:
        cur = dfA.groupby("Vendor", as_index=False).agg(Current=("Sales", "sum"))
        cmpv = dfB.groupby("Vendor", as_index=False).agg(Compare=("Sales", "sum"))
        out = cur.merge(cmpv, on="Vendor", how="outer").fillna(0.0)
        out["Vendor"] = out["Vendor"].astype(str)
        out["Sales_Δ"] = out["Current"] - out["Compare"]
        out["Label"] = out["Sales_Δ"].map(money)
        return out

    def _sku_delta_df() -> pd.DataFrame:
        cur = dfA.groupby("SKU", as_index=False).agg(Current=("Sales", "sum"))
        cmpv = dfB.groupby("SKU", as_index=False).agg(Compare=("Sales", "sum"))
        out = cur.merge(cmpv, on="SKU", how="outer").fillna(0.0)
        out["SKU"] = out["SKU"].astype(str)
        out["Sales_Δ"] = out["Current"] - out["Compare"]
        out["Label"] = out["Sales_Δ"].map(money)
        return out

    def _render_positive_lollipop(df: pd.DataFrame, y_col: str, title: str):
        if df.empty:
            st.info(f"No data available for {title.lower()}.")
            return

        df = df.copy()
        df["Zero"] = 0.0
        df["RightLabelX"] = 0.0
        xmax = float(df["Sales_Δ"].max()) if not df.empty else 0.0
        xmax = xmax * 1.15 if xmax > 0 else 1.0

        y_enc = alt.Y(
            f"{y_col}:N",
            sort=alt.SortField(field="Sales_Δ", order="descending"),
            title="",
            axis=alt.Axis(labels=False, ticks=False, domain=False),
        )

        rules = (
            alt.Chart(df)
            .mark_rule(strokeWidth=2.5, color=POSITIVE_BAR)
            .encode(
                y=y_enc,
                x=alt.X(
                    "Zero:Q",
                    title="Sales Change",
                    scale=alt.Scale(domain=[0, xmax]),
                    axis=alt.Axis(
                        labelFontSize=AXIS_LABEL_FONTSIZE,
                        titleFontSize=AXIS_TITLE_FONTSIZE,
                        labelColor=AXIS_TEXT_COLOR,
                        titleColor=AXIS_TEXT_COLOR,
                    ),
                ),
                x2="Sales_Δ:Q",
            )
        )

        dots = (
            alt.Chart(df)
            .mark_circle(size=150, color=POSITIVE_BAR)
            .encode(
                y=y_enc,
                x=alt.X("Sales_Δ:Q", scale=alt.Scale(domain=[0, xmax])),
                tooltip=[
                    alt.Tooltip(f"{y_col}:N", title="Name"),
                    alt.Tooltip("Current:Q", title=a_lbl, format=",.2f"),
                    alt.Tooltip("Compare:Q", title=b_lbl, format=",.2f"),
                    alt.Tooltip("Sales_Δ:Q", title="Change", format=",.2f"),
                ],
            )
        )

        labels = (
            alt.Chart(df)
            .mark_text(align="left", dx=8, fontSize=14, fontWeight="bold", color=LABEL_POSITIVE_COLOR)
            .encode(
                y=y_enc,
                x=alt.X("Sales_Δ:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Label:N",
            )
        )

        name_labels = (
            alt.Chart(df)
            .mark_text(align="right", dx=-8, fontSize=14, fontWeight="bold", color=AXIS_TEXT_COLOR)
            .encode(
                y=y_enc,
                x=alt.X("RightLabelX:Q", scale=alt.Scale(domain=[0, xmax])),
                text=f"{y_col}:N",
            )
        )

        st.altair_chart(
            (rules + dots + labels + name_labels).properties(
                height=max(280, len(df) * 40),
                title=alt.TitleParams(title, fontSize=CHART_TITLE_FONTSIZE, color=TITLE_TEXT_COLOR),
            ),
            use_container_width=True,
        )

    def _render_negative_lollipop(df: pd.DataFrame, y_col: str, title: str, show_right_labels: bool = True):
        if df.empty:
            st.info(f"No data available for {title.lower()}.")
            return

        df = df.copy()
        df["Zero"] = 0.0
        df["RightLabelX"] = 0.0
        xmax = float(df["Sales_Δ"].abs().max()) if not df.empty else 0.0
        xmax = xmax * 1.15 if xmax > 0 else 1.0

        y_enc = alt.Y(
            f"{y_col}:N",
            sort=alt.SortField(field="Sales_Δ", order="ascending"),
            title="",
            axis=alt.Axis(labels=False, ticks=False, domain=False),
        )

        rules = (
            alt.Chart(df)
            .mark_rule(strokeWidth=2.5, color=NEGATIVE_BAR)
            .encode(
                y=y_enc,
                x=alt.X(
                    "Zero:Q",
                    title="Sales Change",
                    scale=alt.Scale(domain=[-xmax, 0]),
                    axis=alt.Axis(
                        labelFontSize=AXIS_LABEL_FONTSIZE,
                        titleFontSize=AXIS_TITLE_FONTSIZE,
                        labelColor=AXIS_TEXT_COLOR,
                        titleColor=AXIS_TEXT_COLOR,
                    ),
                ),
                x2="Sales_Δ:Q",
            )
        )

        dots = (
            alt.Chart(df)
            .mark_circle(size=150, color=NEGATIVE_BAR)
            .encode(
                y=y_enc,
                x=alt.X("Sales_Δ:Q", scale=alt.Scale(domain=[-xmax, 0])),
                tooltip=[
                    alt.Tooltip(f"{y_col}:N", title="Name"),
                    alt.Tooltip("Current:Q", title=a_lbl, format=",.2f"),
                    alt.Tooltip("Compare:Q", title=b_lbl, format=",.2f"),
                    alt.Tooltip("Sales_Δ:Q", title="Change", format=",.2f"),
                ],
            )
        )

        value_labels = (
            alt.Chart(df)
            .mark_text(align="right", dx=-8, fontSize=14, fontWeight="bold", color=LABEL_NEGATIVE_COLOR)
            .encode(
                y=y_enc,
                x=alt.X("Sales_Δ:Q", scale=alt.Scale(domain=[-xmax, 0])),
                text="Label:N",
            )
        )

        name_labels = (
            alt.Chart(df)
            .mark_text(align="left", dx=8, fontSize=14, fontWeight="bold", color=AXIS_TEXT_COLOR)
            .encode(
                y=y_enc,
                x=alt.X("RightLabelX:Q", scale=alt.Scale(domain=[-xmax, 0])),
                text=f"{y_col}:N",
            )
        )

        st.altair_chart(
            (rules + dots + value_labels + name_labels).properties(
                height=max(280, len(df) * 40),
                title=alt.TitleParams(title, fontSize=CHART_TITLE_FONTSIZE, color=TITLE_TEXT_COLOR),
            ),
            use_container_width=True,
        )

    st.markdown(
        """
        <style>
        [data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
            border-width: 2px !important;
            border-radius: 8px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    sales_col, units_col = st.columns(2)

    with sales_col:
        with st.container(border=True):
            st.markdown(f"#### Sales Total ({a_lbl} vs {b_lbl})")
            _render_total_bars(_totals_df("Sales"), "Sales")

    with units_col:
        with st.container(border=True):
            st.markdown(f"#### Units Total ({a_lbl} vs {b_lbl})")
            _render_total_bars(_totals_df("Units"), "Units")

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    current_sales = float(kA.get("Sales", 0.0))
    compare_sales = float(kB.get("Sales", 0.0))

    if current_sales > compare_sales:
        current_color = POSITIVE_BAR
        compare_color = NEGATIVE_BAR
    elif current_sales < compare_sales:
        current_color = NEGATIVE_BAR
        compare_color = POSITIVE_BAR
    else:
        current_color = NEUTRAL_BAR
        compare_color = NEUTRAL_BAR

    total_max = max(current_sales, compare_sales)
    total_xmax = total_max * 1.04 if total_max > 0 else 1.0

    retailer_change_rows = collect_change_contributors_by_dim(dfA, dfB, "Retailer")
    compare_chart = single_total_bar_chart(compare_sales, "Compare", compare_color, total_xmax)
    change_chart = change_only_center_chart(retailer_change_rows)
    current_chart = single_total_bar_chart(current_sales, "Current", current_color, total_xmax)
    stacked_compare_view = alt.vconcat(compare_chart, change_chart, current_chart, spacing=0).resolve_scale(x="independent")
    render_change_section(
        "Sales Change Compare",
        "Retailers: positives first (highest to lowest), then negatives (closest to zero down to most negative)",
        stacked_compare_view,
    )

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    vendor_change_rows = collect_change_contributors_by_dim(dfA, dfB, "Vendor")
    vendor_compare_chart = single_total_bar_chart(compare_sales, "Compare", compare_color, total_xmax)
    vendor_change_chart = change_only_center_chart(vendor_change_rows)
    vendor_current_chart = single_total_bar_chart(current_sales, "Current", current_color, total_xmax)
    stacked_vendor_view = alt.vconcat(
        vendor_compare_chart, vendor_change_chart, vendor_current_chart, spacing=0
    ).resolve_scale(x="independent")
    render_change_section(
        "Sales Change Compare by Vendor",
        "Vendors: positives first (highest to lowest), then negatives (closest to zero down to most negative)",
        stacked_vendor_view,
    )

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    sku_change_rows = collect_change_contributors_by_dim(
        dfA, dfB, "SKU", top_n_pos=10, top_n_neg=10, pick_most_negative=True,
    )
    sku_compare_chart = single_total_bar_chart(compare_sales, "Compare", compare_color, total_xmax)
    sku_change_chart = change_only_center_chart(sku_change_rows)
    sku_current_chart = single_total_bar_chart(current_sales, "Current", current_color, total_xmax)
    stacked_sku_view = alt.vconcat(
        sku_compare_chart, sku_change_chart, sku_current_chart, spacing=0
    ).resolve_scale(x="independent")
    render_change_section(
        "Sales Change Compare by SKU",
        "Top 10 positive SKUs first, then top 10 negative SKUs",
        stacked_sku_view,
    )
