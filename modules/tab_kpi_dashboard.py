from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from .shared_core import money


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
        "<div class='sales-dashboard-context-copy'>"
        f"<div><strong>Current:</strong> {html.escape(current_label)}</div>"
        + (
            f"<div><strong>Compare:</strong> {html.escape(compare_label or 'None')}</div>"
            if show_compare
            else "<div><strong>Compare:</strong> None</div>"
        )
        + "</div>"
        "<div class='sales-dashboard-top-row'>"
        f"<div class='sales-dashboard-kpi-strip'>{cards_html}</div>"
        "</div>"
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


def render(ctx: dict):
    kA = ctx["kA"]
    kB = ctx["kB"]
    a_lbl = ctx["a_lbl"]
    b_lbl = ctx["b_lbl"]
    compare_mode = ctx["compare_mode"]

    st.markdown("### Sales Dashboard")

    _render_compact_top_right_kpis(
        current_label=a_lbl or "Current timeframe",
        compare_label=b_lbl,
        current_sales=float(kA.get("Sales", 0.0)),
        compare_sales=float(kB.get("Sales", 0.0)),
        current_units=float(kA.get("Units", 0.0)),
        compare_units=float(kB.get("Units", 0.0)),
        show_compare=(compare_mode != "None" and bool(b_lbl)),
    )
