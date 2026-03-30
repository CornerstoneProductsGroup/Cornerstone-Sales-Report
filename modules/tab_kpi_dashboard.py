from __future__ import annotations

import pandas as pd
import streamlit as st

from .shared_core import money


def _fmt_value(value: float, mode: str) -> str:
    if mode == "money":
        return money(value)
    if mode == "int":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _delta_stacked_html(value: float, reference: float, mode: str) -> str:
    """Return two-line HTML: diff value on first line, pct change on second."""
    delta = float(value) - float(reference)
    if delta > 0:
        arrow = "▲"
        color = "#2e7d32"
    elif delta < 0:
        arrow = "▼"
        color = "#c62828"
    else:
        arrow = "•"
        color = "#808080"

    pct = (abs(delta) / abs(float(reference)) * 100.0) if float(reference) != 0 else 0.0
    delta_val = _fmt_value(abs(delta), mode)

    return (
        f"<div style='color:{color};font-weight:800;font-size:13px;line-height:1.3;'>{arrow} {delta_val}</div>"
        f"<div style='color:{color};font-weight:700;font-size:13px;line-height:1.3;'>{pct:,.1f}%</div>"
    )


def _render_entity_kpi_card(
    *,
    title: str,
    sales: float,
    units: float,
    sales_ref: float,
    units_ref: float,
    baseline_name: str,
    align: str = "left",
):
    sales_delta_html = _delta_stacked_html(sales, sales_ref, "money")
    units_delta_html = _delta_stacked_html(units, units_ref, "int")

    card_html = (
        f"<div class='kpi-card kpi-compact-card'>"
        f"<div class='kpi-title'>{title}</div>"
        f"<div style='display:inline-flex;gap:32px;align-items:flex-start;margin-top:6px;'>"
        f"<div><div class='kpi-mini-label'>Sales</div>"
        f"<div class='kpi-mini-value'>{money(sales)}</div>"
        f"<div style='margin-top:4px;'>{sales_delta_html}</div></div>"
        f"<div><div class='kpi-mini-label'>Units</div>"
        f"<div class='kpi-mini-value'>{units:,.0f}</div>"
        f"<div style='margin-top:4px;'>{units_delta_html}</div></div>"
        f"</div></div>"
    )
    if align == "right":
        card_html = f"<div style='display:flex;justify-content:flex-end;'>{card_html}</div>"
    st.markdown(card_html, unsafe_allow_html=True)


def _rollup_by_dim(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    if dim not in df.columns or df.empty:
        return pd.DataFrame(columns=[dim, "Sales", "Units"])

    out = (
        df.groupby(dim, as_index=False)
        .agg(Sales=("Sales", "sum"), Units=("Units", "sum"))
        .sort_values("Sales", ascending=False)
        .reset_index(drop=True)
    )
    return out


def _build_lookup(df_roll: pd.DataFrame, dim: str) -> dict[str, tuple[float, float]]:
    if df_roll.empty:
        return {}
    out: dict[str, tuple[float, float]] = {}
    for _, r in df_roll.iterrows():
        out[str(r[dim])] = (float(r["Sales"]), float(r["Units"]))
    return out


def _calc_asp(sales: float, units: float) -> float:
    return (float(sales) / float(units)) if float(units) != 0 else 0.0


def _best_week_stats(df: pd.DataFrame, dim: str | None = None, key: str | None = None) -> tuple[str, float, float, float]:
    if df.empty or "Sales" not in df.columns:
        return ("-", 0.0, 0.0, 0.0)

    d = df.copy()
    if dim and key is not None and dim in d.columns:
        d = d[d[dim].astype(str) == str(key)]
    if d.empty:
        return ("-", 0.0, 0.0, 0.0)

    if "WeekEnd" not in d.columns:
        sales = float(d["Sales"].sum())
        units = float(d["Units"].sum()) if "Units" in d.columns else 0.0
        return ("-", sales, units, _calc_asp(sales, units))

    wk = (
        d.groupby("WeekEnd", as_index=False)
        .agg(Sales=("Sales", "sum"), Units=("Units", "sum"))
        .sort_values("Sales", ascending=False)
    )
    if wk.empty:
        return ("-", 0.0, 0.0, 0.0)

    top = wk.iloc[0]
    best_end = pd.to_datetime(top["WeekEnd"], errors="coerce")
    best_label = best_end.strftime("%Y-%m-%d") if pd.notna(best_end) else "-"

    if "WeekLabel" in d.columns and pd.notna(best_end):
        labels = d.loc[pd.to_datetime(d["WeekEnd"], errors="coerce") == best_end, "WeekLabel"].dropna()
        if not labels.empty:
            best_label = str(labels.iloc[0])

    best_sales = float(top["Sales"])
    best_units = float(top["Units"])
    return (best_label, best_sales, best_units, _calc_asp(best_sales, best_units))


def _metric_compare_bar_html(
    *,
    metric_label: str,
    current_label: str,
    compare_label: str,
    current_value: float,
    compare_value: float,
    mode: str,
) -> str:
    max_val = max(abs(float(current_value)), abs(float(compare_value)), 1.0)
    current_pct = (abs(float(current_value)) / max_val) * 100.0
    compare_pct = (abs(float(compare_value)) / max_val) * 100.0
    if float(current_value) > float(compare_value):
        current_fill_class = "kpi-bar-fill-high"
        compare_fill_class = "kpi-bar-fill-low"
    elif float(current_value) < float(compare_value):
        current_fill_class = "kpi-bar-fill-low"
        compare_fill_class = "kpi-bar-fill-high"
    else:
        current_fill_class = "kpi-bar-fill-neutral"
        compare_fill_class = "kpi-bar-fill-neutral"

    return (
        "<div class='kpi-bar-card'>"
        f"<div class='kpi-bar-title'>{metric_label}</div>"
        "<div class='kpi-bar-row'>"
        f"<div class='kpi-bar-row-label'>{current_label}</div>"
        f"<div class='kpi-bar-row-value'>{_fmt_value(current_value, mode)}</div>"
        "</div>"
        "<div class='kpi-bar-track'>"
        f"<div class='kpi-bar-fill {current_fill_class}' style='width:{current_pct:,.1f}%;'></div>"
        "</div>"
        "<div class='kpi-bar-row' style='margin-top:6px;'>"
        f"<div class='kpi-bar-row-label'>{compare_label}</div>"
        f"<div class='kpi-bar-row-value'>{_fmt_value(compare_value, mode)}</div>"
        "</div>"
        "<div class='kpi-bar-track'>"
        f"<div class='kpi-bar-fill {compare_fill_class}' style='width:{compare_pct:,.1f}%;'></div>"
        "</div>"
        "</div>"
    )


def _render_top_metric_compare_bars(
    *,
    current_label: str,
    compare_label: str,
    current_sales: float,
    compare_sales: float,
    current_units: float,
    compare_units: float,
):
    current_asp = _calc_asp(current_sales, current_units)
    compare_asp = _calc_asp(compare_sales, compare_units)

    sales_html = _metric_compare_bar_html(
        metric_label="Total Sales",
        current_label=current_label,
        compare_label=compare_label,
        current_value=current_sales,
        compare_value=compare_sales,
        mode="money",
    )
    units_html = _metric_compare_bar_html(
        metric_label="Units",
        current_label=current_label,
        compare_label=compare_label,
        current_value=current_units,
        compare_value=compare_units,
        mode="int",
    )
    asp_html = _metric_compare_bar_html(
        metric_label="ASP",
        current_label=current_label,
        compare_label=compare_label,
        current_value=current_asp,
        compare_value=compare_asp,
        mode="money",
    )

    st.markdown(sales_html, unsafe_allow_html=True)
    st.markdown(units_html, unsafe_allow_html=True)
    st.markdown(asp_html, unsafe_allow_html=True)



# New header with three centered titles above each card
def _render_split_header(current_label: str, diff_label: str, compare_label: str):
    st.markdown(
        f"""
        <div class='kpi-split-title-row' style='margin-bottom:10px;'>
            <div class='kpi-split-col'><h3 style='margin:0;font-size:18px;text-align:center;'>{current_label}</h3></div>
            <div class='kpi-split-col'><h3 style='margin:0;font-size:18px;text-align:center;'>{diff_label}</h3></div>
            <div class='kpi-split-col'><h3 style='margin:0;font-size:18px;text-align:center;'>{compare_label}</h3></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_split_cards(
    *,
    left_title: str,
    right_title: str,
    left_sales: float,
    left_units: float,
    right_sales: float,
    right_units: float,
    left_ref_sales: float,
    left_ref_units: float,
    right_ref_sales: float,
    right_ref_units: float,
    left_baseline: str,
    right_baseline: str,
    left_best_week_label: str,
    left_best_week_sales: float,
    left_best_week_units: float,
    right_best_week_label: str,
    right_best_week_sales: float,
    right_best_week_units: float,
    left_entity_name: str | None = None,
    right_entity_name: str | None = None,
    outlined_group: bool = False,
):
    def title_html(title: str, entity_name: str | None) -> str:
        if entity_name:
            return (
                f"<div class='kpi-split-card-title-small'>{title}</div>"
                f"<div class='kpi-split-card-title-name'>{entity_name}</div>"
            )
        return f"<div class='kpi-group-title kpi-split-card-title'>{title}</div>"

    def diff_html(val_now, val_prev, mode):
        delta = float(val_now) - float(val_prev)
        if delta > 0:
            arrow = "▲"
            color = "#2e7d32"
        elif delta < 0:
            arrow = "▼"
            color = "#c62828"
        else:
            arrow = "•"
            color = "#808080"
        pct = (abs(delta) / abs(float(val_prev)) * 100.0) if float(val_prev) != 0 else 0.0
        if mode == "money":
            val_fmt = money(abs(delta))
        else:
            val_fmt = f"{abs(delta):,.0f}"
        return (
            f"<div style='color:{color};font-weight:800;font-size:28px;line-height:1.18;text-align:center;'>{arrow} {val_fmt}</div>"
            f"<div style='color:{color};font-weight:700;font-size:16px;line-height:1.2;text-align:center;margin-top:2px;'>{pct:,.1f}%</div>"
        )

    group_start = "<div class='kpi-summary-wrap'><div class='kpi-summary-outline'>" if outlined_group else ""
    group_end = "</div></div>" if outlined_group else ""

    st.markdown(
        f"""
        {group_start}
        <div class='kpi-split-title-row'>
            <div class='kpi-split-col'>
                {title_html(left_title, left_entity_name)}
            </div>
            <div class='kpi-split-col'>
                <div class='kpi-group-title kpi-split-card-title'>Difference</div>
            </div>
            <div class='kpi-split-col'>
                {title_html(right_title, right_entity_name)}
            </div>
        </div>
        <div class='kpi-split-row'>
            <div class='kpi-split-col'>
                <div class='kpi-card kpi-compact-card' style='text-align:center;'>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>Sales</div>
                        <div class='kpi-mini-value'>{money(left_sales)}</div>
                    </div>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>Units</div>
                        <div class='kpi-mini-value'>{left_units:,.0f}</div>
                    </div>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>ASP</div>
                        <div class='kpi-mini-value'>{money(_calc_asp(left_sales, left_units))}</div>
                    </div>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>Biggest Week</div>
                        <div style='font-size:15px;font-weight:700;line-height:1.35;'>{left_best_week_label}</div>
                        <div style='font-size:15px;font-weight:700;line-height:1.35;'>{money(left_best_week_sales)} | {left_best_week_units:,.0f} units</div>
                    </div>
                </div>
            </div>
            <div class='kpi-split-col'>
                <div class='kpi-card kpi-compact-card' style='text-align:center;'>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>Sales Diff</div>
                        {diff_html(left_sales, right_sales, 'money')}
                    </div>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>Units Diff</div>
                        {diff_html(left_units, right_units, 'int')}
                    </div>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>ASP Diff</div>
                        {diff_html(_calc_asp(left_sales, left_units), _calc_asp(right_sales, right_units), 'money')}
                    </div>
                </div>
            </div>
            <div class='kpi-split-col'>
                <div class='kpi-card kpi-compact-card' style='text-align:center;'>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>Sales</div>
                        <div class='kpi-mini-value'>{money(right_sales)}</div>
                    </div>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>Units</div>
                        <div class='kpi-mini-value'>{right_units:,.0f}</div>
                    </div>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>ASP</div>
                        <div class='kpi-mini-value'>{money(_calc_asp(right_sales, right_units))}</div>
                    </div>
                    <div class='kpi-metric-block'>
                        <div class='kpi-mini-label'>Biggest Week</div>
                        <div style='font-size:15px;font-weight:700;line-height:1.35;'>{right_best_week_label}</div>
                        <div style='font-size:15px;font-weight:700;line-height:1.35;'>{money(right_best_week_sales)} | {right_best_week_units:,.0f} units</div>
                    </div>
                </div>
            </div>
        </div>
        {group_end}
        """,
        unsafe_allow_html=True,
    )


def _render_grouped_dim_card(
    *,
    section_label: str,
    dim: str,
    top_roll: pd.DataFrame,
    ref_roll: pd.DataFrame,
    top_n: int,
    align: str = "left",
):
    ref_lookup = _build_lookup(ref_roll, dim)
    top_rows = top_roll.head(top_n)

    rows_html = ""
    for idx, (_, row) in enumerate(top_rows.iterrows(), start=1):
        name = str(row[dim])
        sales = float(row["Sales"])
        units = float(row["Units"])
        ref_sales, ref_units = ref_lookup.get(name, (0.0, 0.0))

        sales_delta = _delta_stacked_html(sales, ref_sales, "money")
        units_delta = _delta_stacked_html(units, ref_units, "int")
        divider = "<div style='border-top:1px solid rgba(128,128,128,0.25);margin:10px 0 8px 0;'></div>" if idx > 1 else ""

        rows_html += (
            f"{divider}"
            f"<div style='margin-bottom:2px;'>"
            f"  <span style='opacity:0.60;font-size:13px;font-weight:700;'>#{idx}</span>"
            f"  <strong style='font-size:16px;margin-left:5px;'>{name}</strong>"
            f"</div>"
            f"<div style='display:inline-flex;gap:32px;align-items:flex-start;'>"
            f"  <div>"
            f"    <div class='kpi-mini-label'>Sales</div>"
            f"    <div class='kpi-mini-value'>{money(sales)}</div>"
            f"    <div style='margin-top:3px;'>{sales_delta}</div>"
            f"  </div>"
            f"  <div>"
            f"    <div class='kpi-mini-label'>Units</div>"
            f"    <div class='kpi-mini-value'>{units:,.0f}</div>"
            f"    <div style='margin-top:3px;'>{units_delta}</div>"
            f"  </div>"
            f"</div>"
        )


    card_html = (
        f"<div class='kpi-card kpi-group-card'>"
        f"<div class='kpi-group-title'>{section_label}</div>"
        f"{rows_html}"
        f"</div>"
    )
    if align == "right":
        card_html = f"<div style='display:flex;justify-content:flex-end;'>{card_html}</div>"
    st.markdown(card_html, unsafe_allow_html=True)

def _render_retailer_vendor_row(
    *,
    retailers_a: pd.DataFrame,
    retailers_b: pd.DataFrame,
    vendors_a: pd.DataFrame,
    vendors_b: pd.DataFrame,
    dfA: pd.DataFrame,
    dfB: pd.DataFrame,
    a_lbl: str,
    b_lbl: str,
):
    _render_dimension_section(
        section_title="Top 3 Retailers",
        dim="Retailer",
        top_n=3,
        left_roll=retailers_a,
        right_roll=retailers_b,
        left_df=dfA,
        right_df=dfB,
        left_label=a_lbl,
        right_label=b_lbl,
    )

    _render_dimension_section(
        section_title="Top 3 Vendors",
        dim="Vendor",
        top_n=3,
        left_roll=vendors_a,
        right_roll=vendors_b,
        left_df=dfA,
        right_df=dfB,
        left_label=a_lbl,
        right_label=b_lbl,
    )


def _render_dimension_section(
    *,
    section_title: str,
    dim: str,
    top_n: int,
    left_roll: pd.DataFrame,
    right_roll: pd.DataFrame,
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_label: str,
    right_label: str,
):
    st.markdown(f"<h3 style='text-align:center;margin:18px 0 10px 0;'>{section_title}</h3>", unsafe_allow_html=True)

    left_top = left_roll.head(top_n).copy()
    right_top = right_roll.head(top_n).copy()

    left_lookup = _build_lookup(right_roll, dim)
    right_lookup = _build_lookup(left_roll, dim)

    max_rows = max(len(left_top), len(right_top), top_n)
    for idx in range(max_rows):
        if idx < len(left_top):
            left_row = left_top.iloc[idx]
            left_name = str(left_row[dim])
            left_sales = float(left_row["Sales"])
            left_units = float(left_row["Units"])
        else:
            left_name = "-"
            left_sales = 0.0
            left_units = 0.0

        if idx < len(right_top):
            right_row = right_top.iloc[idx]
            right_name = str(right_row[dim])
            right_sales = float(right_row["Sales"])
            right_units = float(right_row["Units"])
        else:
            right_name = "-"
            right_sales = 0.0
            right_units = 0.0

        left_ref_sales, left_ref_units = left_lookup.get(left_name, (0.0, 0.0))
        right_ref_sales, right_ref_units = right_lookup.get(right_name, (0.0, 0.0))
        left_best_lbl, left_best_sales, left_best_units, _ = _best_week_stats(left_df, dim, left_name)
        right_best_lbl, right_best_sales, right_best_units, _ = _best_week_stats(right_df, dim, right_name)

        _render_split_cards(
            left_title=f"{dim} #{idx + 1}",
            right_title=f"{dim} #{idx + 1}",
            left_sales=left_sales,
            left_units=left_units,
            right_sales=right_sales,
            right_units=right_units,
            left_ref_sales=left_ref_sales,
            left_ref_units=left_ref_units,
            right_ref_sales=right_ref_sales,
            right_ref_units=right_ref_units,
            left_baseline=f"{right_label} match",
            right_baseline=f"{left_label} match",
            left_best_week_label=left_best_lbl,
            left_best_week_sales=left_best_sales,
            left_best_week_units=left_best_units,
            right_best_week_label=right_best_lbl,
            right_best_week_sales=right_best_sales,
            right_best_week_units=right_best_units,
            left_entity_name=left_name,
            right_entity_name=right_name,
        )

    left_names = left_top[dim].astype(str).tolist() if (not left_top.empty and dim in left_top.columns) else []
    right_names = right_top[dim].astype(str).tolist() if (not right_top.empty and dim in right_top.columns) else []

    left_total_sales = float(left_top["Sales"].sum()) if "Sales" in left_top.columns else 0.0
    left_total_units = float(left_top["Units"].sum()) if "Units" in left_top.columns else 0.0
    right_total_sales = float(right_top["Sales"].sum()) if "Sales" in right_top.columns else 0.0
    right_total_units = float(right_top["Units"].sum()) if "Units" in right_top.columns else 0.0

    left_scope = left_df[left_df[dim].astype(str).isin(left_names)].copy() if (dim in left_df.columns and left_names) else left_df.iloc[0:0].copy()
    right_scope = right_df[right_df[dim].astype(str).isin(right_names)].copy() if (dim in right_df.columns and right_names) else right_df.iloc[0:0].copy()

    left_best_lbl, left_best_sales, left_best_units, _ = _best_week_stats(left_scope)
    right_best_lbl, right_best_sales, right_best_units, _ = _best_week_stats(right_scope)

    _render_split_cards(
        left_title=f"{section_title} Total",
        right_title=f"{section_title} Total",
        left_sales=left_total_sales,
        left_units=left_total_units,
        right_sales=right_total_sales,
        right_units=right_total_units,
        left_ref_sales=right_total_sales,
        left_ref_units=right_total_units,
        right_ref_sales=left_total_sales,
        right_ref_units=left_total_units,
        left_baseline=f"{right_label} top {top_n}",
        right_baseline=f"{left_label} top {top_n}",
        left_best_week_label=left_best_lbl,
        left_best_week_sales=left_best_sales,
        left_best_week_units=left_best_units,
        right_best_week_label=right_best_lbl,
        right_best_week_sales=right_best_sales,
        right_best_week_units=right_best_units,
        left_entity_name=left_label,
        right_entity_name=right_label,
        outlined_group=True,
    )


def render(ctx: dict):
    dfA = ctx["dfA"]
    dfB = ctx["dfB"]
    a_lbl = ctx.get("a_lbl") or "Current"
    b_lbl = ctx.get("b_lbl") or "Compare"

    if dfA.empty:
        st.info("No data available for the selected filters.")
        return

    st.markdown(
        """
        <style>
        .kpi-compact-card{padding:16px 20px !important; border-radius:10px !important; margin-bottom:10px; display:block !important; width:100% !important; min-width:0 !important;}
        .kpi-compact-card .kpi-title{font-size:15px !important; white-space:nowrap;}
        .kpi-mini-label{font-size:13px; font-weight:700; opacity:0.70; text-transform:uppercase; white-space:nowrap;}
        .kpi-mini-value{font-size:28px; font-weight:800; line-height:1.18; white-space:nowrap;}
        .kpi-group-card{padding:12px 16px !important; border-radius:10px !important; margin-bottom:6px; display:inline-block !important; width:auto !important; min-width:0 !important;}
        .kpi-group-title{font-size:13px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; opacity:0.75; margin-bottom:12px; white-space:nowrap;}
        .kpi-split-row{display:flex;justify-content:center;gap:64px;margin:0 0 8px 0;}
        .kpi-split-title-row{display:flex;justify-content:center;gap:64px;margin:4px 0 6px 0;}
        .kpi-split-col{flex:1;max-width:290px;margin:0 8px;}
        .kpi-split-card-title{text-align:center;margin-bottom:8px;display:block;}
        .kpi-split-card-title-small{text-align:center;font-size:12px;font-weight:800;letter-spacing:0.04em;opacity:0.72;text-transform:uppercase;margin-bottom:2px;}
        .kpi-split-card-title-name{text-align:center;font-size:20px;font-weight:900;line-height:1.2;margin-bottom:8px;}
        .kpi-summary-wrap{text-align:center;}
        .kpi-summary-outline{display:inline-block;border:4px solid rgba(80,80,80,0.45); border-radius:12px; padding:10px 6px 8px 6px; margin:14px 0 12px 0;}
        .kpi-summary-outline .kpi-split-col{flex:0 0 290px; max-width:290px;}
        .kpi-metric-block{margin-bottom:14px;}
        .kpi-metric-block:last-child{margin-bottom:0;}
        .kpi-center-line{width:100%;background:rgba(20,20,20,0.82);border-radius:0;}
        .kpi-bar-card{border:2px solid rgba(128,128,128,0.35);border-radius:10px;padding:8px 10px 7px 10px;background:var(--secondary-background-color);margin-bottom:6px;}
        .kpi-bar-title{font-size:11px;font-weight:800;letter-spacing:0.04em;text-transform:uppercase;opacity:0.78;margin-bottom:5px;}
        .kpi-bar-row{display:flex;justify-content:space-between;align-items:center;gap:10px;}
        .kpi-bar-row-label{font-size:10px;font-weight:800;text-transform:uppercase;opacity:0.70;white-space:nowrap;}
        .kpi-bar-row-value{font-size:12px;font-weight:800;white-space:nowrap;}
        .kpi-bar-track{width:100%;height:9px;border-radius:999px;background:rgba(120,120,120,0.20);overflow:hidden;margin-top:3px;}
        .kpi-bar-fill{height:100%;border-radius:999px;}
        .kpi-bar-fill-high{background:linear-gradient(90deg,#2e7d32 0%,#4caf50 100%);}
        .kpi-bar-fill-low{background:linear-gradient(90deg,#c62828 0%,#ef5350 100%);}
        .kpi-bar-fill-neutral{background:linear-gradient(90deg,#60656d 0%,#8a9099 100%);}
        .kpi-right-offset{height:28px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    total_sales_a = float(dfA["Sales"].sum()) if "Sales" in dfA.columns else 0.0
    total_units_a = float(dfA["Units"].sum()) if "Units" in dfA.columns else 0.0
    total_sales_b = float(dfB["Sales"].sum()) if "Sales" in dfB.columns else 0.0
    total_units_b = float(dfB["Units"].sum()) if "Units" in dfB.columns else 0.0
    best_a_lbl, best_a_sales, best_a_units, _ = _best_week_stats(dfA)
    best_b_lbl, best_b_sales, best_b_units, _ = _best_week_stats(dfB)

    left_area, right_area = st.columns([1.25, 1.75], gap="large")
    with left_area:
        _render_top_metric_compare_bars(
            current_label=a_lbl,
            compare_label=b_lbl,
            current_sales=total_sales_a,
            compare_sales=total_sales_b,
            current_units=total_units_a,
            compare_units=total_units_b,
        )
    with right_area:
        st.markdown("<div class='kpi-right-offset'></div>", unsafe_allow_html=True)
        _render_split_header(a_lbl, "Difference", b_lbl)
        _render_split_cards(
            left_title="Period Total",
            right_title="Period Total",
            left_sales=total_sales_a,
            left_units=total_units_a,
            right_sales=total_sales_b,
            right_units=total_units_b,
            left_ref_sales=total_sales_b,
            left_ref_units=total_units_b,
            right_ref_sales=total_sales_a,
            right_ref_units=total_units_a,
            left_baseline=b_lbl,
            right_baseline=a_lbl,
            left_best_week_label=best_a_lbl,
            left_best_week_sales=best_a_sales,
            left_best_week_units=best_a_units,
            right_best_week_label=best_b_lbl,
            right_best_week_sales=best_b_sales,
            right_best_week_units=best_b_units,
        )

    retailers_a = _rollup_by_dim(dfA, "Retailer")
    retailers_b = _rollup_by_dim(dfB, "Retailer")
    vendors_a = _rollup_by_dim(dfA, "Vendor")
    vendors_b = _rollup_by_dim(dfB, "Vendor")

    _render_retailer_vendor_row(
        retailers_a=retailers_a,
        retailers_b=retailers_b,
        vendors_a=vendors_a,
        vendors_b=vendors_b,
        dfA=dfA,
        dfB=dfB,
        a_lbl=a_lbl,
        b_lbl=b_lbl,
    )
