from __future__ import annotations

import altair as alt
import html

import pandas as pd
import streamlit as st

from .shared_core import (
    first_sale_ever,
    money,
    new_placement,
    period_from_df,
)


def _retailer_logo_url(retailer_name: str) -> str:
    """Return a best-effort logo URL for common retailers; empty string when unknown."""
    key = str(retailer_name or "").strip().lower()
    domain_map = {
        "home depot": "homedepot.com",
        "the home depot": "homedepot.com",
        "depot": "homedepot.com",
        "lowe's": "lowes.com",
        "lowes": "lowes.com",
        "tractor supply": "tractorsupply.com",
        "ace": "acehardware.com",
        "walmart": "walmart.com",
        "amazon": "amazon.com",
        "orgill": "orgill.com",
        "zoro": "zoro.com",
    }
    domain = domain_map.get(key)
    if not domain:
        return ""
    return f"https://logo.clearbit.com/{domain}"


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


def _delta_stack_parts(value: float, reference: float, mode: str) -> tuple[str, str, str]:
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
    return (color, f"{arrow} {delta_val}", f"{arrow} {pct:,.1f}%")


def _render_compact_top_right_kpis(
    *,
    current_label: str,
    compare_label: str | None,
    current_sales: float,
    compare_sales: float,
    current_units: float,
    compare_units: float,
    show_compare: bool,
):
    current_asp = _calc_asp(current_sales, current_units)
    compare_asp = _calc_asp(compare_sales, compare_units)

    metric_specs = [
        ("Total Sales", current_sales, compare_sales, "money"),
        ("Total Units", current_units, compare_units, "int"),
        ("ASP", current_asp, compare_asp, "money"),
    ]

    cards_html = ""
    for title, current_value, compare_value, mode in metric_specs:
        color, delta_line, pct_line = _delta_stack_parts(current_value, compare_value, mode)
        compare_note = (
            f"vs {html.escape(str(compare_label or 'Compare'))}"
            if show_compare
            else "No compare selected"
        )
        delta_html = (
            ""
            if not show_compare
            else (
                "<div class='sales-dashboard-kpi-delta-stack'>"
                f"<div class='sales-dashboard-kpi-delta-line' style='color:{color};'>{delta_line}</div>"
                f"<div class='sales-dashboard-kpi-pct-line' style='color:{color};'>{pct_line}</div>"
                "</div>"
            )
        )
        cards_html += (
            "<div class='kpi-card sales-dashboard-kpi-card'>"
            f"<div class='kpi-title'>{html.escape(title)}</div>"
            f"<div class='kpi-value'>{html.escape(_fmt_value(current_value, mode))}</div>"
            f"<div class='sales-dashboard-kpi-compare'>{compare_note}</div>"
            f"{delta_html}"
            "</div>"
        )

    context_html = (
        "<div class='sales-dashboard-context'>"
        "<div class='sales-dashboard-top-row'>"
        f"<div class='sales-dashboard-kpi-strip'>{cards_html}</div>"
        "</div>"
        "<div class='sales-dashboard-context-copy'>"
        f"<div><strong>Current:</strong> {html.escape(current_label)}</div>"
        + (
            f"<div><strong>Compare:</strong> {html.escape(compare_label or 'None')}</div>"
            if show_compare
            else "<div><strong>Compare:</strong> None</div>"
        )
        + "</div>"
        "</div>"
    )
    st.markdown(context_html, unsafe_allow_html=True)


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
    card_title_prefix: str | None = None,
    current_line_label: str | None = None,
    compare_line_label: str | None = None,
):
    current_asp = _calc_asp(current_sales, current_units)
    compare_asp = _calc_asp(compare_sales, compare_units)

    sales_title = "Total Sales"
    units_title = "Units"
    asp_title = "ASP"
    if card_title_prefix:
        sales_title = f"{card_title_prefix} Sales"
        units_title = f"{card_title_prefix} Units"
        asp_title = f"{card_title_prefix} ASP"

    row_current = current_line_label or current_label
    row_compare = compare_line_label or compare_label

    sales_html = _metric_compare_bar_html(
        metric_label=sales_title,
        current_label=row_current,
        compare_label=row_compare,
        current_value=current_sales,
        compare_value=compare_sales,
        mode="money",
    )
    units_html = _metric_compare_bar_html(
        metric_label=units_title,
        current_label=row_current,
        compare_label=row_compare,
        current_value=current_units,
        compare_value=compare_units,
        mode="int",
    )
    asp_html = _metric_compare_bar_html(
        metric_label=asp_title,
        current_label=row_current,
        compare_label=row_compare,
        current_value=current_asp,
        compare_value=compare_asp,
        mode="money",
    )

    st.markdown(sales_html, unsafe_allow_html=True)
    st.markdown(units_html, unsafe_allow_html=True)
    st.markdown(asp_html, unsafe_allow_html=True)


def _render_section_summary_box(
    *,
    summary_title: str,
    current_label: str,
    compare_label: str,
    current_sales: float,
    compare_sales: float,
    current_units: float,
    compare_units: float,
):
    current_asp = _calc_asp(current_sales, current_units)
    compare_asp = _calc_asp(compare_sales, compare_units)

    sales_diff = float(current_sales) - float(compare_sales)
    units_diff = float(current_units) - float(compare_units)
    asp_diff = float(current_asp) - float(compare_asp)

    sales_pct = (sales_diff / float(compare_sales) * 100.0) if float(compare_sales) != 0 else 0.0
    units_pct = (units_diff / float(compare_units) * 100.0) if float(compare_units) != 0 else 0.0
    asp_pct = (asp_diff / float(compare_asp) * 100.0) if float(compare_asp) != 0 else 0.0

    candidates = [
        ("Sales", sales_pct, sales_diff, "money"),
        ("Units", units_pct, units_diff, "int"),
        ("ASP", asp_pct, asp_diff, "money"),
    ]
    biggest_metric, biggest_pct, biggest_diff, biggest_mode = max(candidates, key=lambda x: abs(x[1]))
    if biggest_diff > 0:
        biggest_dir = "up"
    elif biggest_diff < 0:
        biggest_dir = "down"
    else:
        biggest_dir = "flat"

    biggest_change_line = (
        f"Biggest change: {biggest_metric} {biggest_dir} "
        f"{abs(biggest_pct):.1f}%"
    )

    def _metric_row(label: str, cur_val: float, pct: float, mode: str) -> str:
        arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "•")
        color = "#2e7d32" if pct > 0 else ("#c62828" if pct < 0 else "#808080")
        return (
            f"<div class='kpi-side-summary-metric-row'>"
            f"<span class='kpi-side-summary-metric-label'>{label}</span>"
            f"<span class='kpi-side-summary-metric-val'>{_fmt_value(cur_val, mode)}</span>"
            f"<span class='kpi-side-summary-metric-delta' style='color:{color};'>{arrow} {abs(pct):.1f}%</span>"
            f"</div>"
        )

    rows_html = (
        _metric_row("Sales", current_sales, sales_pct, "money")
        + _metric_row("Units", current_units, units_pct, "int")
        + _metric_row("ASP", current_asp, asp_pct, "money")
    )

    summary_html = (
        "<div class='kpi-side-summary'>"
        f"<div class='kpi-side-summary-title'>{summary_title}</div>"
        f"<div class='kpi-side-summary-line'><strong>{current_label}</strong> vs <strong>{compare_label}</strong></div>"
        f"<div class='kpi-side-summary-metrics'>{rows_html}</div>"
        f"<div class='kpi-side-summary-highlight'>{biggest_change_line}</div>"
        "</div>"
    )
    st.markdown(summary_html, unsafe_allow_html=True)


def _render_row_titles(
    *,
    section_title: str,
    subtitle: str | None = None,
):
    left_area, middle_area, _ = st.columns([1.0, 2.2, 0.85], gap="medium")
    with left_area:
        st.markdown(f"<h3 style='text-align:center;margin:18px 0 8px 0;'>{section_title}</h3>", unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<div class='kpi-dim-subtitle'>{subtitle}</div>", unsafe_allow_html=True)
    with middle_area:
        st.markdown(f"<h3 style='text-align:center;margin:18px 0 8px 0;'>{section_title}</h3>", unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<div class='kpi-dim-subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def _render_split_cards_with_bars(
    *,
    current_label: str,
    compare_label: str,
    current_sales: float,
    compare_sales: float,
    current_units: float,
    compare_units: float,
    left_offset_class: str | None = None,
    bar_card_title_prefix: str | None = None,
    bar_current_label: str | None = None,
    bar_compare_label: str | None = None,
    summary_title: str | None = None,
    render_header: bool = False,
    header_current_label: str | None = None,
    header_compare_label: str | None = None,
    split_card_kwargs: dict,
):
    left_area, middle_area, right_area = st.columns([1.0, 2.2, 0.85], gap="medium")
    with left_area:
        if left_offset_class:
            st.markdown(f"<div class='{left_offset_class}'></div>", unsafe_allow_html=True)
        _render_top_metric_compare_bars(
            current_label=current_label,
            compare_label=compare_label,
            current_sales=current_sales,
            compare_sales=compare_sales,
            current_units=current_units,
            compare_units=compare_units,
            card_title_prefix=bar_card_title_prefix,
            current_line_label=bar_current_label,
            compare_line_label=bar_compare_label,
        )
    with middle_area:
        if render_header:
            _render_split_header(header_current_label or current_label, "Difference", header_compare_label or compare_label)
        _render_split_cards(**split_card_kwargs)
    with right_area:
        _render_section_summary_box(
            summary_title=summary_title or split_card_kwargs.get("left_title", "Summary"),
            current_label=bar_current_label or current_label,
            compare_label=bar_compare_label or compare_label,
            current_sales=current_sales,
            compare_sales=compare_sales,
            current_units=current_units,
            compare_units=compare_units,
        )


def _render_right_aligned_section_title(title: str, subtitle: str | None = None):
    _render_row_titles(section_title=title, subtitle=subtitle)



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

        row_name = left_name if left_name != "-" else right_name
        _render_right_aligned_section_title(section_title, f"#{idx + 1} {row_name}")

        _render_split_cards_with_bars(
            current_label=left_name,
            compare_label=right_name,
            current_sales=left_sales,
            compare_sales=right_sales,
            current_units=left_units,
            compare_units=right_units,
            left_offset_class="kpi-left-row-offset",
            bar_card_title_prefix=f"{dim} #{idx + 1}: {row_name}",
            bar_current_label="Current",
            bar_compare_label="Compare",
            summary_title=f"{section_title} #{idx + 1}",
            split_card_kwargs={
                "left_title": f"{dim} #{idx + 1}",
                "right_title": f"{dim} #{idx + 1}",
                "left_sales": left_sales,
                "left_units": left_units,
                "right_sales": right_sales,
                "right_units": right_units,
                "left_ref_sales": left_ref_sales,
                "left_ref_units": left_ref_units,
                "right_ref_sales": right_ref_sales,
                "right_ref_units": right_ref_units,
                "left_baseline": f"{right_label} match",
                "right_baseline": f"{left_label} match",
                "left_best_week_label": left_best_lbl,
                "left_best_week_sales": left_best_sales,
                "left_best_week_units": left_best_units,
                "right_best_week_label": right_best_lbl,
                "right_best_week_sales": right_best_sales,
                "right_best_week_units": right_best_units,
                "left_entity_name": left_name,
                "right_entity_name": right_name,
            },
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

    _render_right_aligned_section_title(section_title, f"{section_title} Total")

    _render_split_cards_with_bars(
        current_label=left_label,
        compare_label=right_label,
        current_sales=left_total_sales,
        compare_sales=right_total_sales,
        current_units=left_total_units,
        compare_units=right_total_units,
        left_offset_class="kpi-left-row-offset",
        bar_card_title_prefix=f"{section_title} Total",
        bar_current_label="Current",
        bar_compare_label="Compare",
        summary_title=f"{section_title} Total",
        split_card_kwargs={
            "left_title": f"{section_title} Total",
            "right_title": f"{section_title} Total",
            "left_sales": left_total_sales,
            "left_units": left_total_units,
            "right_sales": right_total_sales,
            "right_units": right_total_units,
            "left_ref_sales": right_total_sales,
            "left_ref_units": right_total_units,
            "right_ref_sales": left_total_sales,
            "right_ref_units": left_total_units,
            "left_baseline": f"{right_label} top {top_n}",
            "right_baseline": f"{left_label} top {top_n}",
            "left_best_week_label": left_best_lbl,
            "left_best_week_sales": left_best_sales,
            "left_best_week_units": left_best_units,
            "right_best_week_label": right_best_lbl,
            "right_best_week_sales": right_best_sales,
            "right_best_week_units": right_best_units,
            "left_entity_name": left_label,
            "right_entity_name": right_label,
            "outlined_group": True,
        },
    )


def _safe_pct_change(value: float, reference: float) -> float:
    value = float(value or 0.0)
    reference = float(reference or 0.0)
    if reference == 0:
        return 0.0 if value == 0 else 100.0
    return ((value - reference) / abs(reference)) * 100.0


def _delta_color(value: float) -> str:
    if value > 0:
        return "#1f8f4e"
    if value < 0:
        return "#d64541"
    return "#6b7280"


def _fmt_signed_pct(value: float, decimals: int = 1) -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:,.{decimals}f}%"


def _fmt_signed_int(value: float) -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:,.0f}"


def _fmt_signed_money(value: float) -> str:
    if value > 0:
        return f"+{money(abs(value))}"
    if value < 0:
        return f"-{money(abs(value))}"
    return money(0.0)


def _money_compact(value: float) -> str:
    value = float(value or 0.0)
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return money(value)


def _arrow_delta_text(value: float, suffix: str) -> str:
    if value > 0:
        return f"▲ {suffix}"
    if value < 0:
        return f"▼ {suffix}"
    return f"• {suffix}"


def _format_week_date(value) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "unknown week"
    return ts.strftime("%Y-%m-%d")


def _series_by_week(df: pd.DataFrame, metric: str = "Sales") -> pd.DataFrame:
    if df.empty or metric not in df.columns or "WeekEnd" not in df.columns:
        return pd.DataFrame(columns=["WeekIndex", "Week Label", "Value"])

    weekly = (
        df.groupby("WeekEnd", as_index=False)
        .agg(Value=(metric, "sum"))
        .sort_values("WeekEnd")
        .reset_index(drop=True)
    )
    weekly["WeekIndex"] = range(1, len(weekly) + 1)
    weekly["Week Label"] = weekly["WeekIndex"].map(lambda idx: f"Week {idx}")
    return weekly[["WeekIndex", "Week Label", "Value"]]


def _prepare_weekly_trend(df_current: pd.DataFrame, df_compare: pd.DataFrame, current_label: str, compare_label: str | None) -> pd.DataFrame:
    current_weekly = _series_by_week(df_current, "Sales")
    compare_weekly = _series_by_week(df_compare, "Sales")
    max_len = max(len(current_weekly), len(compare_weekly))
    if max_len == 0:
        return pd.DataFrame(columns=["Week Label", "Series", "Sales"])

    current_lookup = dict(zip(current_weekly["WeekIndex"], current_weekly["Value"]))
    compare_lookup = dict(zip(compare_weekly["WeekIndex"], compare_weekly["Value"]))

    rows: list[dict[str, object]] = []
    for idx in range(1, max_len + 1):
        week_label = f"Week {idx}"
        rows.append({"Week Label": week_label, "Series": current_label, "Sales": float(current_lookup.get(idx, 0.0))})
        if compare_label:
            rows.append({"Week Label": week_label, "Series": compare_label, "Sales": float(compare_lookup.get(idx, 0.0))})
    return pd.DataFrame(rows)


def _prepare_top_skus(df_current: pd.DataFrame, df_compare: pd.DataFrame) -> pd.DataFrame:
    if df_current.empty or "SKU" not in df_current.columns:
        return pd.DataFrame(columns=["SKU", "Sales", "Delta", "Color", "SalesLabel", "DeltaLabel"])

    current = df_current.groupby("SKU", as_index=False).agg(Sales=("Sales", "sum"))
    compare = (
        df_compare.groupby("SKU", as_index=False).agg(CompareSales=("Sales", "sum"))
        if not df_compare.empty and "SKU" in df_compare.columns
        else pd.DataFrame(columns=["SKU", "CompareSales"])
    )
    merged = current.merge(compare, on="SKU", how="left").fillna({"CompareSales": 0.0})
    merged["Delta"] = merged["Sales"] - merged["CompareSales"]
    merged = merged.sort_values("Sales", ascending=False).head(6).copy()
    merged["Color"] = merged["Delta"].apply(lambda value: "#2da663" if value >= 0 else "#f04e3e")
    merged["SalesLabel"] = merged["Sales"].apply(money)
    merged["DeltaLabel"] = merged["Delta"].apply(_fmt_signed_money)
    return merged


def _prepare_retailer_share(df_current: pd.DataFrame, df_compare: pd.DataFrame) -> pd.DataFrame:
    cols = ["Retailer", "Sales", "CompareSales", "Delta", "Color", "SalesLabel", "DeltaLabel", "DeltaX", "SalesX"]
    if df_current.empty or "Retailer" not in df_current.columns:
        return pd.DataFrame(columns=cols)

    current = (
        df_current.groupby("Retailer", as_index=False)
        .agg(Sales=("Sales", "sum"))
        .sort_values("Sales", ascending=False)
        .reset_index(drop=True)
    )
    compare = (
        df_compare.groupby("Retailer", as_index=False).agg(CompareSales=("Sales", "sum"))
        if not df_compare.empty and "Retailer" in df_compare.columns
        else pd.DataFrame(columns=["Retailer", "CompareSales"])
    )
    merged = current.merge(compare, on="Retailer", how="outer").fillna(0.0)
    merged = merged.sort_values("Sales", ascending=False).reset_index(drop=True)

    if len(merged) > 4:
        top = merged.head(4).copy()
        top.loc[len(top)] = {
            "Retailer": "Other",
            "Sales": float(merged.iloc[4:]["Sales"].sum()),
            "CompareSales": float(merged.iloc[4:]["CompareSales"].sum()),
        }
        merged = top

    merged["Delta"] = merged["Sales"] - merged["CompareSales"]
    merged["Color"] = merged["Delta"].apply(_delta_color)
    merged["SalesLabel"] = merged["Sales"].apply(money)
    merged["DeltaLabel"] = merged["Delta"].apply(_fmt_signed_money)
    max_sales = float(merged["Sales"].max()) if not merged.empty else 1.0
    merged["SalesX"] = merged["Sales"] + (max_sales * 0.015)
    merged["DeltaX"] = merged["Sales"] + (max_sales * 0.125)
    return merged[cols]


def _prepare_retailer_share_change(df_current: pd.DataFrame, df_compare: pd.DataFrame) -> pd.DataFrame:
    cols = ["Retailer", "CurrentShare", "CompareShare", "Delta", "DeltaText", "DeltaColor", "ShareLabel"]
    if df_current.empty or "Retailer" not in df_current.columns:
        return pd.DataFrame(columns=cols)

    cur = (
        df_current.groupby("Retailer", as_index=False)
        .agg(Sales=("Sales", "sum"))
        .sort_values("Sales", ascending=False)
    )
    cmp = (
        df_compare.groupby("Retailer", as_index=False)
        .agg(CompareSales=("Sales", "sum"))
        if (not df_compare.empty and "Retailer" in df_compare.columns)
        else pd.DataFrame(columns=["Retailer", "CompareSales"])
    )

    merged = cur.merge(cmp, on="Retailer", how="outer").fillna(0.0)
    cur_total = float(merged["Sales"].sum()) or 1.0
    cmp_total = float(merged["CompareSales"].sum()) or 1.0
    merged["CurrentShare"] = (merged["Sales"] / cur_total) * 100.0
    merged["CompareShare"] = (merged["CompareSales"] / cmp_total) * 100.0
    merged["Delta"] = merged["CurrentShare"] - merged["CompareShare"]
    merged = merged.sort_values("CurrentShare", ascending=False).head(8).copy()
    merged["DeltaColor"] = merged["Delta"].apply(_delta_color)

    def _delta_text(value: float) -> str:
        if value > 0:
            return f"▲ +{value:.1f}%"
        if value < 0:
            return f"▼ {value:.1f}%"
        return f"• {value:.1f}%"

    merged["DeltaText"] = merged["Delta"].apply(_delta_text)
    merged["ShareLabel"] = merged["CurrentShare"].map(lambda value: f"{value:.1f}%")
    return merged[cols]


def _prepare_top_movers(df_current: pd.DataFrame, df_compare: pd.DataFrame) -> list[dict[str, object]]:
    if df_current.empty or "SKU" not in df_current.columns:
        return []

    current = df_current.groupby("SKU", as_index=False).agg(Sales=("Sales", "sum"))
    compare = (
        df_compare.groupby("SKU", as_index=False).agg(CompareSales=("Sales", "sum"))
        if not df_compare.empty and "SKU" in df_compare.columns
        else pd.DataFrame(columns=["SKU", "CompareSales"])
    )
    combined = current.merge(compare, on="SKU", how="outer").fillna(0.0)
    combined["Delta"] = combined["Sales"] - combined["CompareSales"]
    combined["Pct"] = combined.apply(lambda row: _safe_pct_change(row["Sales"], row["CompareSales"]), axis=1)

    if "Retailer" in df_current.columns:
        retailer_lookup = (
            df_current.groupby(["SKU", "Retailer"], as_index=False)
            .agg(Sales=("Sales", "sum"))
            .sort_values(["SKU", "Sales"], ascending=[True, False])
            .drop_duplicates(subset=["SKU"])
        )
        combined = combined.merge(retailer_lookup[["SKU", "Retailer"]], on="SKU", how="left")
    else:
        combined["Retailer"] = ""

    movers = pd.concat(
        [
            combined.sort_values("Delta", ascending=False).head(4),
            combined.sort_values("Delta", ascending=True).head(4),
        ],
        ignore_index=True,
    )

    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for _, row in movers.iterrows():
        sku = str(row["SKU"])
        if sku in seen:
            continue
        seen.add(sku)
        delta = float(row["Delta"])
        rows.append(
            {
                "SKU": sku,
                "Retailer": str(row.get("Retailer", "") or ""),
                "DeltaText": (f"+{money(abs(delta))}" if delta >= 0 else f"-{money(abs(delta))}"),
                "PctText": _fmt_signed_pct(float(row["Pct"]), 0),
                "Color": _delta_color(delta),
            }
        )
        if len(rows) == 7:
            break
    return rows


def _prepare_growth_series(df_current: pd.DataFrame, df_compare: pd.DataFrame, compare_label: str | None) -> pd.DataFrame:
    current = _series_by_week(df_current, "Sales")
    if current.empty:
        return pd.DataFrame(columns=["Week Label", "Current Growth", "Compare Growth"])

    current["Current Growth"] = current["Value"].pct_change().fillna(0.0) * 100.0

    if compare_label:
        compare = _series_by_week(df_compare, "Sales")
        compare["Compare Growth"] = compare["Value"].pct_change().fillna(0.0) * 100.0
        out = current[["WeekIndex", "Week Label", "Current Growth"]].merge(
            compare[["WeekIndex", "Compare Growth"]],
            on="WeekIndex",
            how="left",
        )
        out["Compare Growth"] = out["Compare Growth"].fillna(0.0)
        return out[["Week Label", "Current Growth", "Compare Growth"]]

    current["Compare Growth"] = current["Current Growth"].rolling(3, min_periods=1).mean()
    return current[["Week Label", "Current Growth", "Compare Growth"]]


def _build_new_product_lines(df_scope: pd.DataFrame, df_current: pd.DataFrame, movers: list[dict[str, object]]) -> list[str]:
    period = period_from_df(df_current)
    if period is None or df_scope.empty:
        return ["No new or emerging product signals for the selected timeframe."]

    lines: list[str] = []
    first_ever = first_sale_ever(df_scope, period)
    if not first_ever.empty:
        row = first_ever.iloc[0]
        retailer = str(row.get("FirstRetailer", row.get("Retailer", "a new retailer")))
        start_week = _format_week_date(row.get("FirstWeek"))
        lines.append(f"New SKU {row['SKU']} launched at {retailer} in week starting {start_week}.")

    placements = new_placement(df_scope, period)
    if not placements.empty:
        row = placements.iloc[0]
        start_week = _format_week_date(row.get("FirstWeek"))
        lines.append(f"New retailer placement: {row['SKU']} started selling at {row['Retailer']} in week starting {start_week}.")

    if movers:
        best = next((item for item in movers if item["Color"] == "#1f8f4e"), movers[0])
        lines.append(f"Fastest growing SKU: {best['SKU']} {best['PctText']}.")

    if not lines:
        lines.append("No new or emerging product signals for the selected timeframe.")
    return lines[:3]


def _build_exec_kpi_tiles(ctx: dict, sales_per_week: float, compare_sales_per_week: float, new_sku_count: int) -> dict[str, list[dict[str, object]]]:
    kA = ctx["kA"]
    kB = ctx["kB"]
    dfA = ctx.get("dfA", pd.DataFrame())
    dfB = ctx.get("dfB", pd.DataFrame())
    show_compare = ctx["compare_mode"] != "None"

    def _build_tile(title: str, value: float, reference: float, mode: str) -> dict[str, object]:
        if mode == "money":
            value_fmt = money(value)
            diff_fmt = _fmt_signed_money(value - reference)
        else:
            value_fmt = f"{value:,.0f}"
            diff_fmt = _fmt_signed_int(value - reference)

        pct = _safe_pct_change(value, reference) if show_compare else 0.0
        delta_text = (
            _arrow_delta_text(value - reference, f"{diff_fmt} ({_fmt_signed_pct(pct)})")
            if show_compare
            else ""
        )
        return {
            "title": title,
            "value": value_fmt,
            "delta": delta_text,
            "color": _delta_color(value - reference),
        }

    def _last_two_months(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "WeekEnd" not in df.columns:
            return df
        d = df.copy()
        d["WeekEnd"] = pd.to_datetime(d["WeekEnd"], errors="coerce")
        anchor = d["WeekEnd"].max()
        if pd.isna(anchor):
            return df
        cutoff = anchor - pd.Timedelta(days=60)
        return d[d["WeekEnd"] >= cutoff].copy()

    def _sku_metrics(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "SKU" not in df.columns or "Sales" not in df.columns:
            return pd.DataFrame(columns=["SKU", "Sales"])
        out = (
            df.assign(SKU=df["SKU"].astype(str))
            .groupby("SKU", as_index=False)
            .agg(Sales=("Sales", "sum"))
        )
        return out

    def _sku_churn(primary_df: pd.DataFrame, reference_df: pd.DataFrame) -> tuple[int, float, int, float]:
        primary = _sku_metrics(primary_df)
        reference = _sku_metrics(reference_df)
        if primary.empty and reference.empty:
            return (0, 0.0, 0, 0.0)

        reference_skus = set(reference["SKU"].tolist()) if not reference.empty else set()
        primary_skus = set(primary["SKU"].tolist()) if not primary.empty else set()

        new_rows = primary[~primary["SKU"].isin(reference_skus)] if not primary.empty else primary
        lost_rows = reference[~reference["SKU"].isin(primary_skus)] if not reference.empty else reference

        return (
            int(len(new_rows)),
            float(new_rows["Sales"].sum()) if not new_rows.empty else 0.0,
            int(len(lost_rows)),
            float(lost_rows["Sales"].sum()) if not lost_rows.empty else 0.0,
        )

    def _build_sku_churn_tile(
        primary_df: pd.DataFrame,
        reference_df: pd.DataFrame,
        primary_name: str,
        reference_name: str,
    ) -> dict[str, object]:
        primary_2m = _last_two_months(primary_df)
        reference_2m = _last_two_months(reference_df)
        primary_only_count, primary_only_sales, reference_only_count, reference_only_sales = _sku_churn(primary_2m, reference_2m)
        if not show_compare:
            return {
                "title": "SKU Movement (2M)",
                "value": "No compare selected",
                "delta": "",
                "color": "#6b7280",
                "meta_lines": [],
            }

        if primary_name == "Current":
            return {
                "title": "SKU Movement (2M)",
                "value": f"New SKUs (Current not Compare): {primary_only_count:,}",
                "delta": f"Total Sales (New): {money(primary_only_sales)}",
                "color": _delta_color(primary_only_sales - reference_only_sales),
                "meta_lines": [
                    f"Lost SKUs (Compare not Current): {reference_only_count:,}",
                    f"Total Sales (Lost): {money(reference_only_sales)}",
                ],
            }

        if primary_name == "Compare":
            return {
                "title": "SKU Movement (2M)",
                "value": f"New SKUs (Compare not Current): {primary_only_count:,}",
                "delta": f"Total Sales (New): {money(primary_only_sales)}",
                "color": _delta_color(primary_only_sales - reference_only_sales),
                "meta_lines": [
                    f"Lost SKUs (Compare not Current): {primary_only_count:,}",
                    f"Total Sales (Lost): {money(primary_only_sales)}",
                ],
            }

        return {
            "title": "SKU Movement (2M)",
            "value": f"In {primary_name} Not {reference_name}: {primary_only_count:,}",
            "delta": f"Sales ({primary_name}-only): {money(primary_only_sales)}",
            "color": _delta_color(primary_only_sales - reference_only_sales),
            "meta_lines": [
                f"In {reference_name} Not {primary_name}: {reference_only_count:,}",
                f"Sales ({reference_name}-only): {money(reference_only_sales)}",
            ],
        }

    current_sales = float(kA.get("Sales", 0.0))
    current_units = float(kA.get("Units", 0.0))
    current_asp = float(kA.get("ASP", 0.0))

    compare_sales = float(kB.get("Sales", 0.0))
    compare_units = float(kB.get("Units", 0.0))
    compare_asp = float(kB.get("ASP", 0.0))

    current_tiles = [
        _build_tile("Total Sales", current_sales, compare_sales, "money"),
        _build_tile("Total Units", current_units, compare_units, "int"),
        _build_tile("ASP", current_asp, compare_asp, "money"),
        _build_sku_churn_tile(dfA, dfB, "Current", "Compare"),
    ]

    compare_tiles = [
        _build_tile("Total Sales", compare_sales, current_sales, "money"),
        _build_tile("Total Units", compare_units, current_units, "int"),
        _build_tile("ASP", compare_asp, current_asp, "money"),
        _build_sku_churn_tile(dfB, dfA, "Compare", "Current"),
    ] if show_compare else []

    return {"current": current_tiles, "compare": compare_tiles}


def _render_exec_kpi_ribbon(
    current_tiles: list[dict[str, object]],
    current_row_label: str,
    current_label: str,
    compare_label: str | None,
    compare_tiles: list[dict[str, object]] | None = None,
    compare_row_label: str | None = None,
):
    def _tiles_html(tiles: list[dict[str, object]]) -> str:
        html_out = ""
        for tile in tiles:
            delta_html = ""
            if tile.get("delta"):
                delta_html = f"<span class='sales-exec-kpi-delta' style='color:{tile['color']};'>{html.escape(tile['delta'])}</span>"
            meta_html = ""
            for line in tile.get("meta_lines", []):
                meta_html += f"<div class='sales-exec-kpi-meta-line'>{html.escape(str(line))}</div>"
            html_out += (
                "<div class='sales-exec-kpi-tile'>"
                f"<div class='sales-exec-kpi-title'>{html.escape(tile['title'])}</div>"
                "<div class='sales-exec-kpi-metric-row'>"
                f"<div class='sales-exec-kpi-value'>{html.escape(tile['value'])}</div>"
                f"{delta_html}"
                "</div>"
                f"{meta_html}"
                "</div>"
            )
        return html_out

    sections_html = (
        "<div class='sales-exec-row-label'>"
        f"{html.escape(current_row_label)}"
        "</div>"
        f"<div class='sales-exec-kpi-ribbon'>{_tiles_html(current_tiles)}</div>"
    )

    if compare_tiles and compare_row_label:
        sections_html += (
            "<div class='sales-exec-row-label'>"
            f"{html.escape(compare_row_label)}"
            "</div>"
            f"<div class='sales-exec-kpi-ribbon'>{_tiles_html(compare_tiles)}</div>"
        )

    context = f"Current: {current_label}"
    if compare_label:
        context += f"  |  Compare: {compare_label}"

    st.markdown(
        "<div class='sales-exec-accent'></div>"
        f"{sections_html}"
        f"<div class='sales-exec-context'>{html.escape(context)}</div>",
        unsafe_allow_html=True,
    )


def _render_movers_panel(movers: list[dict[str, object]]):
    if not movers:
        st.info("No movers available for the selected timeframe.")
        return

    rows_html = ""
    for mover in movers:
        rows_html += (
            "<div class='sales-movers-row'>"
            f"<div class='sales-movers-sku'>{html.escape(str(mover['SKU']))}</div>"
            f"<div class='sales-movers-delta' style='color:{mover['Color']};'>{html.escape(str(mover['DeltaText']))}</div>"
            f"<div class='sales-movers-pct' style='color:{mover['Color']};'>{html.escape(str(mover['PctText']))}</div>"
            f"<div class='sales-movers-retailer'>{html.escape(str(mover['Retailer']))}</div>"
            "</div>"
        )

    st.markdown(f"<div class='sales-movers-table'>{rows_html}</div>", unsafe_allow_html=True)


def _render_new_products_panel(lines: list[str]):
    items_html = "".join(
        f"<div class='sales-new-products-item'>{html.escape(line)}</div>" for line in lines
    )
    st.markdown(f"<div class='sales-new-products-list'>{items_html}</div>", unsafe_allow_html=True)


def _weekly_sales_trend_chart(df: pd.DataFrame, current_label: str, compare_label: str | None):
    if df.empty:
        return None

    domain = [current_label] + ([compare_label] if compare_label else [])
    color_range = ["#2b78d0", "#7f93b0"] if compare_label else ["#2b78d0"]
    return (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(size=70, filled=True))
        .encode(
            x=alt.X("Week Label:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Sales:Q", title=None, axis=alt.Axis(format="$,.0s", gridColor="#e5e7eb")),
            color=alt.Color("Series:N", scale=alt.Scale(domain=domain, range=color_range), legend=alt.Legend(title=None, orient="bottom")),
            tooltip=[alt.Tooltip("Series:N"), alt.Tooltip("Week Label:N", title="Week"), alt.Tooltip("Sales:Q", format=",.0f")],
        )
        .properties(height=230)
    )


def _top_sku_chart(df: pd.DataFrame):
    if df.empty:
        return None

    ymax = float(df["Sales"].max()) * 1.30 if not df.empty else 1.0
    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("SKU:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-28)),
            y=alt.Y("Sales:Q", title=None, axis=alt.Axis(labels=False, ticks=False, domain=False), scale=alt.Scale(domain=[0, ymax])),
            color=alt.Color("Color:N", scale=None, legend=None),
            tooltip=[alt.Tooltip("SKU:N"), alt.Tooltip("Sales:Q", format=",.0f")],
        )
    )
    labels = (
        alt.Chart(df)
        .mark_text(align="center", baseline="bottom", dy=-8, color="#1f2937", fontSize=13, fontWeight="bold")
        .encode(
            x=alt.X("SKU:N", sort="-y", title=None),
            y=alt.Y("Sales:Q", scale=alt.Scale(domain=[0, ymax])),
            text="SalesLabel:N",
        )
    )
    delta_labels = (
        alt.Chart(df)
        .mark_text(align="center", baseline="bottom", dy=-24, fontSize=12, fontWeight="bold")
        .encode(
            x=alt.X("SKU:N", sort="-y", title=None),
            y=alt.Y("Sales:Q", scale=alt.Scale(domain=[0, ymax])),
            text="DeltaLabel:N",
            color=alt.Color("Color:N", scale=None, legend=None),
        )
    )
    return (bars + labels + delta_labels).properties(height=280)


def _retailer_share_chart(df: pd.DataFrame):
    if df.empty:
        return None

    x_max = max(float(df["Sales"].max()) * 1.32 if not df.empty else 1.0, 1.0)
    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=6, color="#2b78d0")
        .encode(
            y=alt.Y("Retailer:N", sort="-x", title=None),
            x=alt.X("Sales:Q", title=None, axis=alt.Axis(labels=False, ticks=False, domain=False), scale=alt.Scale(domain=[0, x_max])),
            tooltip=[
                alt.Tooltip("Retailer:N"),
                alt.Tooltip("Sales:Q", format=",.0f"),
                alt.Tooltip("Delta:Q", title="Difference", format=",.0f"),
            ],
        )
    )
    sales_labels = (
        alt.Chart(df)
        .mark_text(align="left", baseline="middle", dx=8, color="#1f2937", fontSize=13, fontWeight="bold")
        .encode(
            y=alt.Y("Retailer:N", sort="-x", title=None),
            x=alt.X("SalesX:Q", scale=alt.Scale(domain=[0, x_max])),
            text="SalesLabel:N",
        )
    )
    delta_labels = (
        alt.Chart(df)
        .mark_text(align="left", baseline="middle", dx=8, fontSize=12, fontWeight="bold")
        .encode(
            y=alt.Y("Retailer:N", sort="-x", title=None),
            x=alt.X("DeltaX:Q", scale=alt.Scale(domain=[0, x_max])),
            text="DeltaLabel:N",
            color=alt.Color("Color:N", scale=None, legend=None),
        )
    )

    return (bars + delta_labels + sales_labels).properties(height=300)


def _retailer_share_change_chart(df: pd.DataFrame):
    if df.empty:
        return None

    x_max = max(float(df["CurrentShare"].max()) + 22.0, 35.0)
    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=6, color="#4a90e2")
        .encode(
            y=alt.Y("Retailer:N", sort="-x", title=None),
            x=alt.X("CurrentShare:Q", title=None, scale=alt.Scale(domain=[0, x_max]), axis=alt.Axis(format=",.0f")),
            tooltip=[
                alt.Tooltip("Retailer:N"),
                alt.Tooltip("CurrentShare:Q", title="Current Share", format=",.1f"),
                alt.Tooltip("CompareShare:Q", title="Compare Share", format=",.1f"),
                alt.Tooltip("Delta:Q", title="Change", format=",.1f"),
            ],
        )
    )
    share_text = (
        alt.Chart(df)
        .mark_text(align="left", baseline="middle", dx=6, color="#1f2937", fontWeight="bold", fontSize=15)
        .encode(
            y=alt.Y("Retailer:N", sort="-x", title=None),
            x=alt.X("CurrentShare:Q", scale=alt.Scale(domain=[0, x_max])),
            text="ShareLabel:N",
        )
    )
    delta_text = (
        alt.Chart(df)
        .mark_text(align="left", baseline="middle", dx=74, fontWeight="bold", fontSize=14)
        .encode(
            y=alt.Y("Retailer:N", sort="-x", title=None),
            x=alt.X("CurrentShare:Q", scale=alt.Scale(domain=[0, x_max])),
            text="DeltaText:N",
            color=alt.Color("DeltaColor:N", scale=None, legend=None),
        )
    )
    return (bars + share_text + delta_text).properties(height=220)


def _weekly_growth_chart(df: pd.DataFrame):
    if df.empty:
        return None

    bars = (
        alt.Chart(df)
        .mark_bar(color="#4a90e2", opacity=0.9, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("Week Label:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Current Growth:Q", title=None, axis=alt.Axis(format=",.0f")),
            tooltip=[alt.Tooltip("Week Label:N"), alt.Tooltip("Current Growth:Q", title="Current Growth", format=",.1f")],
        )
    )
    line = (
        alt.Chart(df)
        .mark_line(color="#375a8c", point=True, strokeDash=[6, 4])
        .encode(
            x=alt.X("Week Label:N", title=None),
            y=alt.Y("Compare Growth:Q", title=None),
            tooltip=[alt.Tooltip("Week Label:N"), alt.Tooltip("Compare Growth:Q", title="Trend", format=",.1f")],
        )
    )
    rule = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#cbd5e1").encode(y="y:Q")
    return (rule + bars + line).properties(height=180)


def render(ctx: dict):
    kA = ctx["kA"]
    kB = ctx["kB"]
    a_lbl = ctx["a_lbl"]
    b_lbl = ctx["b_lbl"]
    compare_mode = ctx["compare_mode"]
    dfA = ctx["dfA"]
    dfB = ctx["dfB"]
    df_scope = ctx.get("df_scope", pd.DataFrame())

    current_label = a_lbl or "Current timeframe"
    compare_label = b_lbl if compare_mode != "None" and b_lbl else None

    current_weeks = max(int(dfA["WeekEnd"].nunique()) if (not dfA.empty and "WeekEnd" in dfA.columns) else 0, 1)
    compare_weeks = max(int(dfB["WeekEnd"].nunique()) if (not dfB.empty and "WeekEnd" in dfB.columns) else 0, 1)
    current_sales_per_week = float(kA.get("Sales", 0.0)) / current_weeks
    compare_sales_per_week = float(kB.get("Sales", 0.0)) / compare_weeks if compare_label else 0.0

    anchor = pd.to_datetime(dfA.get("WeekEnd"), errors="coerce").max() if (not dfA.empty and "WeekEnd" in dfA.columns) else pd.NaT
    if pd.notna(anchor) and not df_scope.empty and "WeekEnd" in df_scope.columns:
        hist_up_to_anchor = df_scope[pd.to_datetime(df_scope["WeekEnd"], errors="coerce") <= anchor].copy()
    else:
        hist_up_to_anchor = pd.DataFrame()

    overall_weekly = (
        hist_up_to_anchor.groupby("WeekEnd", as_index=False).agg(Sales=("Sales", "sum")).sort_values("WeekEnd").tail(8)
        if not hist_up_to_anchor.empty
        else pd.DataFrame(columns=["WeekEnd", "Sales"])
    )
    period = period_from_df(dfA)
    new_sku_count = len(first_sale_ever(df_scope, period)) if period is not None and not df_scope.empty else 0

    st.markdown("### Sales Dashboard")

    tiles = _build_exec_kpi_tiles(
        ctx,
        sales_per_week=current_sales_per_week,
        compare_sales_per_week=compare_sales_per_week,
        new_sku_count=new_sku_count,
    )
    _render_exec_kpi_ribbon(
        current_tiles=tiles["current"],
        current_row_label=f"Current Totals: {current_label}",
        current_label=current_label,
        compare_label=compare_label,
        compare_tiles=tiles["compare"] if compare_label else None,
        compare_row_label=(f"Compare Totals: {compare_label}" if compare_label else None),
    )

    weekly_trend = _prepare_weekly_trend(dfA, dfB, current_label, compare_label)
    trend_col, _ = st.columns([2.6, 0.75], gap="small")
    with trend_col:
        with st.container(border=True):
            st.markdown("#### Weekly Sales Trend")
            trend_chart = _weekly_sales_trend_chart(weekly_trend, current_label, compare_label)
            if trend_chart is None:
                st.info("No weekly trend data available for the selected timeframe.")
            else:
                st.altair_chart(trend_chart, use_container_width=True)

    top_skus = _prepare_top_skus(dfA, dfB)
    retailer_share = _prepare_retailer_share(dfA, dfB)
    movers = _prepare_top_movers(dfA, dfB)

    left_col, middle_col = st.columns([1.15, 1.45], gap="small")

    with left_col:
        with st.container(border=True):
            st.markdown("#### Top Selling SKUs")
            sku_chart = _top_sku_chart(top_skus)
            if sku_chart is None:
                st.info("No SKU sales available for the selected timeframe.")
            else:
                st.altair_chart(sku_chart, use_container_width=True)

    with middle_col:
        with st.container(border=True):
            st.markdown("#### Sales by Retailer")
            share_chart = _retailer_share_chart(retailer_share)
            if share_chart is None:
                st.info("No retailer mix available for the selected timeframe.")
            else:
                st.altair_chart(share_chart, use_container_width=True)

    share_change_df = _prepare_retailer_share_change(dfA, dfB)
    bottom_left, bottom_right = st.columns([1.75, 0.95], gap="small")

    with bottom_left:
        with st.container(border=True):
            st.markdown("#### Retailer Share Change")
            share_change_chart = _retailer_share_change_chart(share_change_df)
            if share_change_chart is None:
                st.info("No retailer share change data available for the selected timeframe.")
            else:
                st.altair_chart(share_change_chart, use_container_width=True)

    with bottom_right:
        with st.container(border=True):
            st.markdown("#### Top Movers")
            _render_movers_panel(movers)
