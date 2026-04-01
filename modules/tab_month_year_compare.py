from __future__ import annotations

import re

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from .shared_core import (
    money,
    pct_fmt,
    rename_ab_columns,
    render_df,
    count_sales_card,
    kpi_card,
    selection_total_card,
    top_two_card,
    biggest_increase_card,
)
from .app_core import make_simple_data_pdf


def render(ctx: dict):
    st.markdown(
        """
        <style>
        .kpi-card .kpi-title{font-size:13px !important;}
        .kpi-card .kpi-value{font-size:31px !important;}
        .kpi-card .kpi-delta{font-size:15px !important;}
        .kpi-card .kpi-sub{font-size:15px !important;}
        .kpi-card .top-two-item .kpi-big-name{font-size:22px !important;}
        .kpi-card .top-two-item .kpi-value{font-size:30px !important;}
        .kpi-card .top-two-item .kpi-delta{font-size:14px !important;}
        .kpi-card .top-two-item .kpi-sub{font-size:14px !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_standard_view(
        dfA=ctx["dfA"],
        dfB=ctx["dfB"],
        kA=ctx["kA"],
        kB=ctx["kB"],
        a_lbl=ctx["a_lbl"],
        b_lbl=ctx["b_lbl"],
        compare_mode=ctx["compare_mode"],
        min_sales=ctx["min_sales"],
    )


def render_visual_only(ctx: dict):
    st.markdown(
        """
        <style>
        .kpi-card .kpi-title{font-size:13px !important;}
        .kpi-card .kpi-value{font-size:31px !important;}
        .kpi-card .kpi-delta{font-size:15px !important;}
        .kpi-card .kpi-sub{font-size:15px !important;}
        .kpi-card .top-two-item .kpi-big-name{font-size:22px !important;}
        .kpi-card .top-two-item .kpi-value{font-size:30px !important;}
        .kpi-card .top-two-item .kpi-delta{font-size:14px !important;}
        .kpi-card .top-two-item .kpi-sub{font-size:14px !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_visual_executive_dashboard(
        dfA=ctx["dfA"],
        dfB=ctx["dfB"],
        kA=ctx["kA"],
        kB=ctx["kB"],
        a_lbl=ctx["a_lbl"],
        b_lbl=ctx["b_lbl"],
        min_sales=ctx["min_sales"],
    )


def render_visual_executive_dashboard(
    dfA: pd.DataFrame,
    dfB: pd.DataFrame,
    kA: dict,
    kB: dict,
    a_lbl: str,
    b_lbl: str,
    min_sales: float,
):
    PERIOD_DOMAIN = [a_lbl, b_lbl]
    PERIOD_RANGE = ["#1f77b4", "#ff7f0e"]

    Q_DOMAIN = ["Q1", "Q2", "Q3", "Q4"]
    Q_RANGE = ["#dbe7f5", "#a8c4e5", "#6f9fd1", "#2f6fb3"]

    POSITIVE_BAR = "#2e7d32"
    NEGATIVE_BAR = "#c62828"
    NEUTRAL_BAR = "#808080"

    TOTAL_BLOCK_VALUE = 25000.0
    CHANGE_BLOCK_VALUE = 1000.0

    def is_year_label(lbl: str) -> bool:
        return bool(re.fullmatch(r"\d{4}", str(lbl or "").strip()))

    def year_compare_mode() -> bool:
        return is_year_label(a_lbl) and is_year_label(b_lbl)

    def pct_change(cur: float, prev: float):
        if prev == 0:
            return np.nan if cur == 0 else np.inf
        return (cur - prev) / prev

    def delta_html(cur: float, prev: float, is_money: bool):
        d = float(cur) - float(prev)
        pc = pct_change(float(cur), float(prev))
        color = POSITIVE_BAR if d > 0 else (NEGATIVE_BAR if d < 0 else "var(--text-color)")
        arrow = "▲ " if d > 0 else ("▼ " if d < 0 else "")
        abs_s = money(d) if is_money else f"{d:,.0f}"
        return (
            f"<span class='delta-abs' style='color:{color}'>{arrow}{abs_s}</span>"
            f"<span class='delta-pct' style='color:{color}'>({pct_fmt(pc)})</span>"
        )

    def prep_compare_metric(
        df_cur: pd.DataFrame,
        df_cmp: pd.DataFrame,
        level: str,
        metric: str = "Sales",
        top_n: int = 10,
    ) -> pd.DataFrame:
        cur = df_cur.groupby(level, dropna=False, as_index=False).agg(Current=(metric, "sum"))
        cmp = df_cmp.groupby(level, dropna=False, as_index=False).agg(Compare=(metric, "sum"))
        out = cur.merge(cmp, on=level, how="outer").fillna(0.0)
        out[level] = out[level].astype(str)
        out["Delta"] = out["Current"] - out["Compare"]
        out["Total"] = out["Current"] + out["Compare"]
        out = out.sort_values(["Total", level], ascending=[False, True]).head(top_n).copy()
        return out

    def prep_quarter_stacked(df_cur: pd.DataFrame, df_cmp: pd.DataFrame, metric: str) -> pd.DataFrame:
        if "Quarter" not in df_cur.columns or "Quarter" not in df_cmp.columns:
            return pd.DataFrame()

        cur = df_cur.copy()
        cmp = df_cmp.copy()

        cur["Quarter"] = cur["Quarter"].astype(str).str.upper().str.strip()
        cmp["Quarter"] = cmp["Quarter"].astype(str).str.upper().str.strip()

        cur = cur[cur["Quarter"].isin(Q_DOMAIN)]
        cmp = cmp[cmp["Quarter"].isin(Q_DOMAIN)]

        if cur.empty or cmp.empty:
            return pd.DataFrame()

        a = cur.groupby("Quarter", as_index=False)[metric].sum()
        b = cmp.groupby("Quarter", as_index=False)[metric].sum()

        a["Period"] = a_lbl
        b["Period"] = b_lbl
        a.rename(columns={metric: "Value"}, inplace=True)
        b.rename(columns={metric: "Value"}, inplace=True)

        out = pd.concat([a, b], ignore_index=True)
        out["Quarter"] = pd.Categorical(out["Quarter"], categories=Q_DOMAIN, ordered=True)
        out = out.sort_values(["Period", "Quarter"]).copy()

        out["Label"] = out["Value"].map(lambda v: f"{v:,.0f}" if metric == "Units" else money(v))
        out["Start"] = out.groupby("Period")["Value"].cumsum() - out["Value"]
        out["LabelX"] = out["Start"] + (out["Value"] * 0.50)

        total_by_period = out.groupby("Period")["Value"].transform("sum")
        out["ShowLabel"] = np.where(
            (out["Value"] > 0) & (out["Value"] / total_by_period >= 0.08),
            out["Label"],
            "",
        )
        return out

    def stacked_total_chart(
        metric_name: str,
        df_cur: pd.DataFrame,
        df_cmp: pd.DataFrame,
        fallback_cur: float,
        fallback_cmp: float,
    ):
        metric = "Units" if metric_name == "Units" else "Sales"

        color_cur = POSITIVE_BAR if float(fallback_cur) >= float(fallback_cmp) else NEGATIVE_BAR
        color_cmp = POSITIVE_BAR if float(fallback_cmp) > float(fallback_cur) else NEGATIVE_BAR

        stacked = pd.DataFrame()
        if year_compare_mode():
            stacked = prep_quarter_stacked(df_cur, df_cmp, metric)

        if stacked.empty:
            chart_df = pd.DataFrame(
                [
                    {"Period": "Current", "Value": float(fallback_cur), "ColorHex": color_cur},
                    {"Period": "Compare", "Value": float(fallback_cmp), "ColorHex": color_cmp},
                ]
            )

            xmax = float(chart_df["Value"].max()) if not chart_df.empty else 0.0
            xmax = xmax * 1.20 if xmax > 0 else 1.0

            bars = (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, size=7)
                .encode(
                    y=alt.Y("Period:N", title="", sort=["Compare", "Current"], axis=alt.Axis(labelFontSize=13)),
                    x=alt.X("Value:Q", title=metric_name, scale=alt.Scale(domain=[0, xmax])),
                    color=alt.Color("ColorHex:N", scale=None, legend=None),
                    tooltip=[
                        alt.Tooltip("Period:N", title="Period"),
                        alt.Tooltip("Value:Q", title=metric_name, format=",.0f" if metric == "Units" else ",.2f"),
                    ],
                )
                .properties(height=150)
            )

            label_df = chart_df.copy()
            label_df["Label"] = label_df["Value"].map(lambda v: f"{v:,.0f}" if metric == "Units" else money(v))
            label_df["LabelX"] = label_df["Value"]

            labels = (
                alt.Chart(label_df)
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

            return bars + labels

        totals = (
            stacked.groupby("Period", as_index=False)
            .agg(Value=("Value", "sum"))
            .assign(
                ColorHex=lambda d: d["Period"].map({
                    a_lbl: color_cur,
                    b_lbl: color_cmp,
                })
            )
        )
        
        # Replace period labels with "Current" and "Compare"
        totals["DisplayPeriod"] = totals["Period"].map({a_lbl: "Current", b_lbl: "Compare"})
        totals["SortKey"] = totals["DisplayPeriod"].map({"Compare": 0, "Current": 1})
        totals = totals.sort_values("SortKey")

        xmax = float(totals["Value"].max()) if not totals.empty else 0.0
        xmax = xmax * 1.20 if xmax > 0 else 1.0

        bars = (
            alt.Chart(totals)
            .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, size=7)
            .encode(
                y=alt.Y("DisplayPeriod:N", title="", sort=["Compare", "Current"], axis=alt.Axis(labelFontSize=13)),
                x=alt.X("Value:Q", title=metric_name, scale=alt.Scale(domain=[0, xmax])),
                color=alt.Color("ColorHex:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("DisplayPeriod:N", title="Period"),
                    alt.Tooltip("Value:Q", title=metric_name, format=",.0f" if metric == "Units" else ",.2f"),
                ],
            )
            .properties(height=150)
        )

        totals["Label"] = totals["Value"].map(lambda v: f"{v:,.0f}" if metric == "Units" else money(v))
        totals["LabelX"] = totals["Value"]

        labels = (
            alt.Chart(totals)
            .mark_text(
                align="left",
                dx=8,
                baseline="middle",
                fontSize=16,
                fontWeight="bold",
                color="#000000",
            )
            .encode(
                y=alt.Y("DisplayPeriod:N", sort=["Compare", "Current"]),
                x=alt.X("LabelX:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Label:N",
            )
        )

        return bars + labels

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
            # Select the most negative contributors (largest decreases), then
            # display them closest-to-zero down to most-negative so the bottom
            # bar is the largest decrease.
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

    def simple_period_block_chart(
        current_value: float,
        compare_value: float,
        current_label: str,
        compare_label: str,
        changes_df: pd.DataFrame,
    ):
        def full_total_label(v: float) -> str:
            return money(float(v))

        def abs_change_label(v: float) -> str:
            return money(abs(float(v)))

        current_value = float(max(current_value, 0.0))
        compare_value = float(max(compare_value, 0.0))

        if current_value > compare_value:
            current_color = POSITIVE_BAR
            compare_color = NEGATIVE_BAR
        elif current_value < compare_value:
            current_color = NEGATIVE_BAR
            compare_color = POSITIVE_BAR
        else:
            current_color = NEUTRAL_BAR
            compare_color = NEUTRAL_BAR

        rows = [
            {
                "Period": compare_label,
                "Kind": "total",
                "Value": compare_value,
                "Direction": "right",
                "ColorHex": compare_color,
                "Side": "right",
                "Text": full_total_label(compare_value),
                "BlockValue": TOTAL_BLOCK_VALUE,
            }
        ]

        if changes_df is not None and not changes_df.empty:
            for _, r in changes_df.iterrows():
                delta = float(r["Delta"])
                rows.append(
                    {
                        "Period": str(r["Label"]),
                        "Kind": "change",
                        "Value": abs(delta),
                        "Direction": str(r["Direction"]),
                        "ColorHex": str(r["ColorHex"]),
                        "Side": str(r["Side"]),
                        "Text": abs_change_label(delta),
                        "BlockValue": CHANGE_BLOCK_VALUE,
                    }
                )

        rows.append(
            {
                "Period": current_label,
                "Kind": "total",
                "Value": current_value,
                "Direction": "right",
                "ColorHex": current_color,
                "Side": "right",
                "Text": full_total_label(current_value),
                "BlockValue": TOTAL_BLOCK_VALUE,
            }
        )

        row_df = pd.DataFrame(rows)

        total_max = float(max(compare_value, current_value, TOTAL_BLOCK_VALUE))
        if (row_df["Kind"] == "change").any():
            change_max = float(row_df.loc[row_df["Kind"] == "change", "Value"].max())
        else:
            change_max = CHANGE_BLOCK_VALUE

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
        total_label_rows = []

        for _, r in row_df.iterrows():
            value = float(max(r["Value"], 0.0))
            block_value = float(r["BlockValue"])

            if r["Kind"] == "total":
                if value <= 0:
                    block_rows.append(
                        {
                            "Period": r["Period"],
                            "X0": 0.0,
                            "X1": 0.0,
                            "ColorHex": r["ColorHex"],
                        }
                    )
                    total_label_rows.append(
                        {
                            "Period": r["Period"],
                            "X": 0.0,
                            "Text": r["Text"],
                            "ColorHex": r["ColorHex"],
                            "Side": r["Side"],
                        }
                    )
                else:
                    n_blocks = int(np.ceil(value / block_value))
                    for i in range(n_blocks):
                        x0 = i * block_value
                        x1 = min((i + 1) * block_value, value)
                        block_rows.append(
                            {
                                "Period": r["Period"],
                                "X0": x0,
                                "X1": x1,
                                "ColorHex": r["ColorHex"],
                            }
                        )
                    total_label_rows.append(
                        {
                            "Period": r["Period"],
                            "X": value,
                            "Text": r["Text"],
                            "ColorHex": r["ColorHex"],
                            "Side": "right",
                        }
                    )
            else:
                if value <= 0:
                    block_rows.append(
                        {
                            "Period": r["Period"],
                            "X0": center_x,
                            "X1": center_x,
                            "ColorHex": r["ColorHex"],
                        }
                    )
                    total_label_rows.append(
                        {
                            "Period": r["Period"],
                            "X": center_x,
                            "Text": r["Text"],
                            "ColorHex": r["ColorHex"],
                            "Side": r["Side"],
                        }
                    )
                else:
                    n_blocks = int(np.ceil(value / block_value))
                    for i in range(n_blocks):
                        piece_start = i * block_value
                        piece_end = min((i + 1) * block_value, value)

                        if r["Direction"] == "right":
                            x0 = center_x + piece_start
                            x1 = center_x + piece_end
                        else:
                            x0 = center_x - piece_end
                            x1 = center_x - piece_start

                        block_rows.append(
                            {
                                "Period": r["Period"],
                                "X0": x0,
                                "X1": x1,
                                "ColorHex": r["ColorHex"],
                            }
                        )

                    total_label_rows.append(
                        {
                            "Period": r["Period"],
                            "X": center_x + value if r["Direction"] == "right" else center_x - value,
                            "Text": r["Text"],
                            "ColorHex": r["ColorHex"],
                            "Side": r["Side"],
                        }
                    )

        block_df = pd.DataFrame(block_rows)
        totals_df = pd.DataFrame(total_label_rows)
        order = row_df["Period"].tolist()

        chart_height = max(230, 44 * len(order))

        def _layer(df_sub: pd.DataFrame, color_hex: str):
            if df_sub.empty:
                return None
            return (
                alt.Chart(df_sub)
                .mark_bar(color=color_hex, stroke="white", strokeWidth=1)
                .encode(
                    y=alt.Y("Period:N", sort=order, title="", axis=alt.Axis(labelFontSize=13)),
                    x=alt.X("X0:Q", title="Sales", scale=alt.Scale(domain=[0, xmax])),
                    x2="X1:Q",
                    tooltip=[alt.Tooltip("Period:N", title="Period")],
                )
            )

        layers = []

        green_df = block_df[block_df["ColorHex"] == POSITIVE_BAR].copy()
        red_df = block_df[block_df["ColorHex"] == NEGATIVE_BAR].copy()
        gray_df = block_df[block_df["ColorHex"] == NEUTRAL_BAR].copy()

        green_layer = _layer(green_df, POSITIVE_BAR)
        red_layer = _layer(red_df, NEGATIVE_BAR)
        gray_layer = _layer(gray_df, NEUTRAL_BAR)

        for lyr in (green_layer, red_layer, gray_layer):
            if lyr is not None:
                layers.append(lyr)

        center_rule = (
            alt.Chart(pd.DataFrame([{"Center": center_x}]))
            .mark_rule(color="#7a7a7a", strokeDash=[4, 4], strokeWidth=1.5)
            .encode(x=alt.X("Center:Q", scale=alt.Scale(domain=[0, xmax])))
        )
        layers.append(center_rule)

        right_labels = (
            alt.Chart(totals_df[totals_df["Side"] == "right"])
            .mark_text(align="left", dx=10, fontSize=14, fontWeight="bold", clip=False)
            .encode(
                y=alt.Y("Period:N", sort=order),
                x=alt.X("X:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Text:N",
                color=alt.Color("ColorHex:N", scale=None, legend=None),
            )
        )
        layers.append(right_labels)

        left_labels = (
            alt.Chart(totals_df[totals_df["Side"] == "left"])
            .mark_text(align="right", dx=-10, fontSize=14, fontWeight="bold", clip=False)
            .encode(
                y=alt.Y("Period:N", sort=order),
                x=alt.X("X:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Text:N",
                color=alt.Color("ColorHex:N", scale=None, legend=None),
            )
        )
        layers.append(left_labels)

        chart = alt.layer(*layers).properties(height=chart_height)
        return chart

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

    def prep_grouped_share(df: pd.DataFrame, dim_name: str) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=[dim_name, "Series", "Value", "SharePct", "Label", "SortTotal", "Start", "RowColor"]
            )

        long_df = df[[dim_name, "Current", "Compare", "Total"]].melt(
            id_vars=[dim_name, "Total"],
            value_vars=["Current", "Compare"],
            var_name="Series",
            value_name="Value",
        )

        color_base = df[[dim_name, "Current", "Compare", "Total"]].copy()
        color_base["CurrentColor"] = np.where(
            color_base["Current"] > color_base["Compare"],
            "green",
            np.where(color_base["Current"] < color_base["Compare"], "red", "neutral"),
        )
        color_base["CompareColor"] = np.where(
            color_base["Compare"] > color_base["Current"],
            "green",
            np.where(color_base["Compare"] < color_base["Current"], "red", "neutral"),
        )

        long_df = long_df.merge(
            color_base[[dim_name, "CurrentColor", "CompareColor"]],
            on=dim_name,
            how="left",
        )

        long_df["Series"] = long_df["Series"].replace({"Current": a_lbl, "Compare": b_lbl})
        long_df["RowColor"] = np.where(
            long_df["Series"] == a_lbl,
            long_df["CurrentColor"],
            long_df["CompareColor"],
        )

        long_df["SharePct"] = np.where(long_df["Total"] > 0, long_df["Value"] / long_df["Total"], 0.0)
        long_df["Label"] = long_df.apply(
            lambda r: f'{money(r["Value"])} • {r["SharePct"]:.0%}' if r["Value"] > 0 else "",
            axis=1,
        )
        long_df["SortTotal"] = long_df["Total"]
        long_df["Start"] = 0.0
        return long_df

    def grouped_lollipop_chart(long_df: pd.DataFrame, dim_name: str, height: int = 760):
        if long_df.empty:
            return None

        xmax = float(long_df["Value"].max()) if not long_df.empty else 0.0
        xmax = xmax * 1.40 if xmax > 0 else 1.0

        color_enc = alt.Color(
            "RowColor:N",
            scale=alt.Scale(
                domain=["green", "red", "neutral"],
                range=[POSITIVE_BAR, NEGATIVE_BAR, NEUTRAL_BAR],
            ),
            legend=None,
        )

        y_enc = alt.Y(
            f"{dim_name}:N",
            sort=alt.SortField(field="SortTotal", order="descending"),
            title="",
            scale=alt.Scale(paddingInner=0.10, paddingOuter=0.08),
            axis=alt.Axis(labelFontSize=14),
        )

        yoff_enc = alt.YOffset(
            "Series:N",
            sort=[a_lbl, b_lbl],
            scale=alt.Scale(paddingInner=0.00, paddingOuter=0.85),
        )

        rules = (
            alt.Chart(long_df)
            .mark_rule(strokeWidth=2.5)
            .encode(
                y=y_enc,
                yOffset=yoff_enc,
                x=alt.X("Start:Q", scale=alt.Scale(domain=[0, xmax], nice=True), title="Sales"),
                x2="Value:Q",
                color=color_enc,
                tooltip=[
                    alt.Tooltip(f"{dim_name}:N", title=dim_name),
                    alt.Tooltip("Series:N", title="Series"),
                    alt.Tooltip("Value:Q", title="Sales", format=",.2f"),
                    alt.Tooltip("SharePct:Q", title="% of row total", format=".0%"),
                ],
            )
        )

        dots = (
            alt.Chart(long_df)
            .mark_circle(size=150)
            .encode(
                y=y_enc,
                yOffset=yoff_enc,
                x=alt.X("Value:Q", scale=alt.Scale(domain=[0, xmax], nice=True), title="Sales"),
                color=color_enc,
                tooltip=[
                    alt.Tooltip(f"{dim_name}:N", title=dim_name),
                    alt.Tooltip("Series:N", title="Series"),
                    alt.Tooltip("Value:Q", title="Sales", format=",.2f"),
                    alt.Tooltip("SharePct:Q", title="% of row total", format=".0%"),
                ],
            )
        )

        labels = (
            alt.Chart(long_df[long_df["Label"] != ""])
            .mark_text(
                align="left",
                dx=10,
                baseline="middle",
                fontSize=15,
                fontWeight="bold",
            )
            .encode(
                y=y_enc,
                yOffset=yoff_enc,
                x=alt.X("Value:Q", scale=alt.Scale(domain=[0, xmax], nice=True)),
                text="Label:N",
                color=color_enc,
            )
        )

        return (rules + dots + labels).properties(height=height)

    def prep_sku_movers():
        sA = dfA.groupby("SKU", as_index=False).agg(Current=("Sales", "sum"))
        sB = dfB.groupby("SKU", as_index=False).agg(Compare=("Sales", "sum"))
        sku = sA.merge(sB, on="SKU", how="outer").fillna(0.0)
        sku["Delta"] = sku["Current"] - sku["Compare"]
        sku = sku[(sku["Current"] >= min_sales) | (sku["Compare"] >= min_sales)].copy()

        inc = sku.sort_values(["Delta", "SKU"], ascending=[False, True]).head(10).copy()
        dec = sku.sort_values(["Delta", "SKU"], ascending=[True, True]).head(10).copy()
        inc["Start"] = 0.0
        dec["Start"] = 0.0
        return inc, dec

    def render_with_side_margins(chart):
        # Keep a consistent right-side gutter while preserving left alignment.
        chart_col, right_gap = st.columns([0.94, 0.06])
        with chart_col:
            st.altair_chart(chart, use_container_width=True)

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

    def render_change_section(title: str, subtitle: str, chart):
        with st.container(border=True):
            st.markdown(f"#### {title}")
            st.caption(subtitle)
            render_with_side_margins(chart)

    def mover_lollipop_chart(df: pd.DataFrame, metric_title: str, positive: bool, height: int = 430):
        if df.empty:
            return None

        df = df.copy()
        df["DeltaLabel"] = df["Delta"].map(money)

        xmax = float(df["Delta"].max()) if positive else float(df["Delta"].abs().max())
        xmax = xmax * 1.40 if xmax > 0 else 1.0

        if positive:
            order = alt.SortField(field="Delta", order="descending")
            x_scale = alt.Scale(domain=[0, xmax], nice=True)
            color = POSITIVE_BAR
            align = "left"
            dx = 10
        else:
            order = alt.SortField(field="Delta", order="ascending")
            x_scale = alt.Scale(domain=[-xmax, 0], nice=True)
            color = NEGATIVE_BAR
            align = "right"
            dx = -10

        y_enc = alt.Y(
            "SKU:N",
            sort=order,
            title="",
            scale=alt.Scale(paddingInner=0.35, paddingOuter=0.18),
            axis=alt.Axis(labelFontSize=13),
        )

        rules = (
            alt.Chart(df)
            .mark_rule(strokeWidth=2.5, color=color)
            .encode(
                y=y_enc,
                x=alt.X("Start:Q", scale=x_scale, title=metric_title),
                x2="Delta:Q",
            )
        )

        dots = (
            alt.Chart(df)
            .mark_circle(size=150, color=color)
            .encode(
                y=y_enc,
                x=alt.X("Delta:Q", scale=x_scale, title=metric_title),
                tooltip=[
                    alt.Tooltip("SKU:N", title="SKU"),
                    alt.Tooltip("Current:Q", title=a_lbl, format=",.2f"),
                    alt.Tooltip("Compare:Q", title=b_lbl, format=",.2f"),
                    alt.Tooltip("Delta:Q", title="Change", format=",.2f"),
                ],
            )
        )

        labels = (
            alt.Chart(df)
            .mark_text(
                align=align,
                dx=dx,
                color=color,
                fontSize=15,
                fontWeight="bold",
            )
            .encode(
                y=y_enc,
                x=alt.X("Delta:Q", scale=x_scale),
                text="DeltaLabel:N",
            )
        )

        return (rules + dots + labels).properties(height=height)

    sales_col, units_col = st.columns(2)

    with sales_col:
        with st.container(border=True):
            st.markdown(f"#### Sales Total ({a_lbl} vs {b_lbl})")
            sales_chart = stacked_total_chart(
                metric_name="Sales",
                df_cur=dfA,
                df_cmp=dfB,
                fallback_cur=float(kA["Sales"]),
                fallback_cmp=float(kB["Sales"]),
            )
            st.altair_chart(sales_chart, use_container_width=True)

    with units_col:
        with st.container(border=True):
            st.markdown(f"#### Units Total ({a_lbl} vs {b_lbl})")
            units_chart = stacked_total_chart(
                metric_name="Units",
                df_cur=dfA,
                df_cmp=dfB,
                fallback_cur=float(kA["Units"]),
                fallback_cmp=float(kB["Units"]),
            )
            st.altair_chart(units_chart, use_container_width=True)

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    current_sales = float(kA["Sales"])
    compare_sales = float(kB["Sales"])

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
        vendor_compare_chart,
        vendor_change_chart,
        vendor_current_chart,
        spacing=0,
    ).resolve_scale(x="independent")
    render_change_section(
        "Sales Change Compare by Vendor",
        "Vendors: positives first (highest to lowest), then negatives (closest to zero down to most negative)",
        stacked_vendor_view,
    )

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    sku_change_rows = collect_change_contributors_by_dim(
        dfA,
        dfB,
        "SKU",
        top_n_pos=10,
        top_n_neg=10,
        pick_most_negative=True,
    )

    sku_compare_chart = single_total_bar_chart(compare_sales, "Compare", compare_color, total_xmax)
    sku_change_chart = change_only_center_chart(sku_change_rows)
    sku_current_chart = single_total_bar_chart(current_sales, "Current", current_color, total_xmax)

    stacked_sku_view = alt.vconcat(
        sku_compare_chart,
        sku_change_chart,
        sku_current_chart,
        spacing=0,
    ).resolve_scale(x="independent")
    render_change_section(
        "Sales Change Compare by SKU",
        "Top 10 positive SKUs first, then top 10 negative SKUs",
        stacked_sku_view,
    )


def render_standard_view(
    dfA: pd.DataFrame,
    dfB: pd.DataFrame,
    kA: dict,
    kB: dict,
    a_lbl: str,
    b_lbl: str,
    compare_mode: str,
    min_sales: float,
):
    def render_shaded_total_table(df: pd.DataFrame, height: int = 760):
        st.dataframe(df, use_container_width=True, hide_index=True, height=height)

    def pct_change(cur, prev):
        if prev == 0:
            return np.nan if cur == 0 else np.inf
        return (cur - prev) / prev

    def _delta_html(cur: float, prev: float, is_money: bool):
        d = cur - prev
        pc = pct_change(cur, prev)
        color = "#2e7d32" if d > 0 else ("#c62828" if d < 0 else "var(--text-color)")
        arrow = "▲ " if d > 0 else ("▼ " if d < 0 else "")
        abs_s = money(d) if is_money else (f"{d:,.0f}" if abs(d) >= 1 else f"{d:,.2f}")
        return (
            f"<span class='delta-abs' style='color:{color}'>{arrow}{abs_s}</span>"
            f"<span class='delta-pct' style='color:{color}'>({pct_fmt(pc)})</span>"
        )

    def kdelta(key: str) -> str:
        cur = float(kA.get(key, 0.0))
        prev = float(kB.get(key, 0.0))
        return _delta_html(cur, prev, is_money=(key in ("Sales", "ASP")))

    def _top_by_increase(level: str):
        a = dfA.groupby(level, as_index=False).agg(Sales_A=("Sales", "sum"))
        b = dfB.groupby(level, as_index=False).agg(Sales_B=("Sales", "sum"))
        m = a.merge(b, on=level, how="outer").fillna(0.0)
        m["Δ"] = m["Sales_A"] - m["Sales_B"]
        if m.empty:
            return None
        r = m.sort_values("Δ", ascending=False).iloc[0]
        return str(r[level]), float(r["Sales_A"]), float(r["Sales_B"])

    def _top_decrease(level: str):
        a = dfA.groupby(level, as_index=False).agg(Sales_A=("Sales", "sum"))
        b = dfB.groupby(level, as_index=False).agg(Sales_B=("Sales", "sum"))
        m = a.merge(b, on=level, how="outer").fillna(0.0)
        m["Δ"] = m["Sales_A"] - m["Sales_B"]
        if m.empty:
            return None
        r = m.sort_values("Δ", ascending=True).iloc[0]
        return str(r[level]), float(r["Sales_A"]), float(r["Sales_B"])

    def _top_two_with_compare(df_sel: pd.DataFrame, df_other: pd.DataFrame, level: str):
        if df_sel.empty:
            return []
        cur = df_sel.groupby(level, as_index=False).agg(Sales=("Sales", "sum"), Units=("Units", "sum"))
        if not df_other.empty:
            oth = df_other.groupby(level, as_index=False).agg(
                Other_Sales=("Sales", "sum"),
                Other_Units=("Units", "sum"),
            )
        else:
            oth = pd.DataFrame(columns=[level, "Other_Sales", "Other_Units"])
        m = cur.merge(oth, on=level, how="left").fillna(0.0)
        total_sales = float(m["Sales"].sum())
        total_units = float(m["Units"].sum())
        out = []
        for _, r in m.sort_values(["Sales", level], ascending=[False, True]).head(2).iterrows():
            sales = float(r["Sales"])
            units = float(r["Units"])
            out.append(
                {
                    "name": str(r[level]),
                    "sales": sales,
                    "other_sales": float(r["Other_Sales"]),
                    "share": (sales / total_sales) if total_sales else np.nan,
                    "units": units,
                    "other_units": float(r["Other_Units"]),
                    "unit_share": (units / total_units) if total_units else np.nan,
                }
            )
        return out

    cur_sku = dfA.groupby("SKU", as_index=False).agg(Sales=("Sales", "sum"), Units=("Units", "sum"))
    cmp_sku = dfB.groupby("SKU", as_index=False).agg(Sales=("Sales", "sum"), Units=("Units", "sum"))

    cur_only = cur_sku.merge(
        cmp_sku[["SKU", "Sales"]].rename(columns={"Sales": "Compare_Sales"}),
        on="SKU",
        how="left",
    ).fillna(0.0)
    cur_only = cur_only[(cur_only["Sales"] > 0) & (cur_only["Compare_Sales"] <= 0)].copy()

    cmp_only = cmp_sku.merge(
        cur_sku[["SKU", "Sales"]].rename(columns={"Sales": "Current_Sales"}),
        on="SKU",
        how="left",
    ).fillna(0.0)
    cmp_only = cmp_only[(cmp_only["Sales"] > 0) & (cmp_only["Current_Sales"] <= 0)].copy()

    new_count = int(len(cur_only))
    new_sales = float(cur_only["Sales"].sum())
    lost_count = int(len(cmp_only))
    lost_sales = float(cmp_only["Sales"].sum())
    net_count = new_count - lost_count
    net_sales = new_sales - lost_sales
    net_pct = (net_sales / lost_sales) if lost_sales != 0 else (np.nan if net_sales == 0 else np.inf)

    n1, n2, n3 = st.columns(3)
    with n1:
        count_sales_card("New SKUs", new_count, new_sales, color="#2e7d32", signed_sales=True)
    with n2:
        count_sales_card("Lost SKUs", lost_count, -lost_sales, color="#c62828", signed_sales=True)
    with n3:
        count_sales_card(
            "Net New vs Lost",
            net_count,
            net_sales,
            color=("#2e7d32" if net_sales > 0 else ("#c62828" if net_sales < 0 else "var(--text-color)")),
            signed_sales=True,
            pct=net_pct,
        )

    st.write("")
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        selection_total_card(f"{a_lbl} Total", kA, kB)
        st.write("")
        selection_total_card(f"{b_lbl} Total", kB, kA)
    with g2:
        top_two_card(f"Top 2 Retailers ({a_lbl})", _top_two_with_compare(dfA, dfB, "Retailer"))
        st.write("")
        top_two_card(f"Top 2 Retailers ({b_lbl})", _top_two_with_compare(dfB, dfA, "Retailer"))
    with g3:
        top_two_card(f"Top 2 Vendors ({a_lbl})", _top_two_with_compare(dfA, dfB, "Vendor"))
        st.write("")
        top_two_card(f"Top 2 Vendors ({b_lbl})", _top_two_with_compare(dfB, dfA, "Vendor"))
    with g4:
        top_two_card(f"Top 2 SKUs ({a_lbl})", _top_two_with_compare(dfA, dfB, "SKU"))
        st.write("")
        top_two_card(f"Top 2 SKUs ({b_lbl})", _top_two_with_compare(dfB, dfA, "SKU"))

    st.write("")
    i1, i2, i3 = st.columns(3)
    iR = _top_by_increase("Retailer")
    iV = _top_by_increase("Vendor")
    iS = _top_by_increase("SKU")
    with i1:
        if iR:
            biggest_increase_card("Retailer w/ Biggest Increase", iR[0], iR[1], iR[2])
    with i2:
        if iV:
            biggest_increase_card("Vendor w/ Biggest Increase", iV[0], iV[1], iV[2])
    with i3:
        if iS:
            biggest_increase_card("SKU w/ Biggest Increase", iS[0], iS[1], iS[2])

    d1, d2, d3 = st.columns(3)
    decR = _top_decrease("Retailer")
    decV = _top_decrease("Vendor")
    decS = _top_decrease("SKU")
    with d1:
        if decR:
            biggest_increase_card("Retailer w/ Biggest Decrease", decR[0], decR[1], decR[2])
    with d2:
        if decV:
            biggest_increase_card("Vendor w/ Biggest Decrease", decV[0], decV[1], decV[2])
    with d3:
        if decS:
            biggest_increase_card("SKU w/ Biggest Decrease", decS[0], decS[1], decS[2])

    try:
        export_df = dfA[["Retailer", "Vendor", "SKU", "Sales", "Units"]].copy() if not dfA.empty else pd.DataFrame()
        if not export_df.empty:
            export_df = export_df.groupby(["Retailer", "Vendor", "SKU"], as_index=False).agg(
                Sales=("Sales", "sum"),
                Units=("Units", "sum"),
            )
        pdf_bytes = make_simple_data_pdf(
            title=f"Month/Year Compare Report — {a_lbl} vs {b_lbl}",
            subtitle=f"Compare Mode: {compare_mode}",
            data_df=export_df,
        )
        if pdf_bytes:
            st.download_button(
                "⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"month_year_compare_{a_lbl}_{b_lbl}.pdf".replace(" ", "_").lower(),
                mime="application/pdf",
                key="download_myc_pdf",
            )
    except Exception:
        pass

    st.divider()
    st.subheader("Current Only / Compare Only Activity")

    cur_s = dfA.groupby("SKU", as_index=False).agg(Current_Units=("Units", "sum"), Current_Sales=("Sales", "sum"))
    cmp_s = dfB.groupby("SKU", as_index=False).agg(Compare_Units=("Units", "sum"), Compare_Sales=("Sales", "sum"))

    lost = cmp_s.merge(cur_s, on="SKU", how="left").fillna(0.0)
    lost = lost[(lost["Compare_Sales"] > 0) & (lost["Current_Sales"] <= 0)].copy().sort_values(
        "Compare_Sales", ascending=False
    )

    new_act = cur_s.merge(cmp_s, on="SKU", how="left").fillna(0.0)
    new_act = new_act[(new_act["Current_Sales"] > 0) & (new_act["Compare_Sales"] <= 0)].copy().sort_values(
        "Current_Sales", ascending=False
    )

    lcol, rcol = st.columns(2)
    with lcol:
        st.markdown("**In Compare and Not Current**")
        if lost.empty:
            st.caption("None.")
        else:
            show_lost = lost[["SKU", "Compare_Units", "Compare_Sales"]].rename(
                columns={"Compare_Units": "Units", "Compare_Sales": "Sales"}
            ).copy()
            show_lost["Units"] = -show_lost["Units"]
            show_lost["Sales"] = -show_lost["Sales"]
            total_row = pd.DataFrame(
                [{"SKU": "Total", "Units": show_lost["Units"].sum(), "Sales": show_lost["Sales"].sum()}]
            )
            show_lost = pd.concat([show_lost, total_row], ignore_index=True)
            show_lost["Units"] = show_lost["Units"].map(lambda v: f"{v:,.0f}")
            show_lost["Sales"] = show_lost["Sales"].map(money)
            render_df(show_lost, height=360)

    with rcol:
        st.markdown("**In Current and Not Compare**")
        if new_act.empty:
            st.caption("None.")
        else:
            show_new = new_act[["SKU", "Current_Units", "Current_Sales"]].rename(
                columns={"Current_Units": "Units", "Current_Sales": "Sales"}
            ).copy()
            total_row = pd.DataFrame(
                [{"SKU": "Total", "Units": show_new["Units"].sum(), "Sales": show_new["Sales"].sum()}]
            )
            show_new = pd.concat([show_new, total_row], ignore_index=True)
            show_new["Units"] = show_new["Units"].map(lambda v: f"{v:,.0f}")
            show_new["Sales"] = show_new["Sales"].map(money)
            render_df(show_new, height=360)

    st.divider()
    st.subheader("Comparison Detail")

    pivot_dim = st.selectbox("Compare rows by", options=["Retailer", "Vendor"], index=0, key="mod_compare_dim")
    comp_a = dfA.groupby(pivot_dim, as_index=False).agg(Sales_A=("Sales", "sum"))
    comp_b = dfB.groupby(pivot_dim, as_index=False).agg(Sales_B=("Sales", "sum"))
    comp = comp_a.merge(comp_b, on=pivot_dim, how="outer").fillna(0.0)
    comp["Difference"] = comp["Sales_A"] - comp["Sales_B"]
    comp["% Change"] = np.where(comp["Sales_B"] != 0, comp["Difference"] / comp["Sales_B"], np.nan)
    comp = comp.sort_values("Sales_A", ascending=False)

    total = pd.DataFrame(
        [
            {
                pivot_dim: "Total",
                "Sales_A": comp["Sales_A"].sum(),
                "Sales_B": comp["Sales_B"].sum(),
                "Difference": comp["Difference"].sum(),
                "% Change": np.nan if comp["Sales_B"].sum() == 0 else comp["Difference"].sum() / comp["Sales_B"].sum(),
            }
        ]
    )
    comp_show = pd.concat([comp, total], ignore_index=True)
    show = rename_ab_columns(comp_show.copy(), a_lbl, b_lbl)
    sales_a_col = f"Sales ({a_lbl})"
    sales_b_col = f"Sales ({b_lbl})" if b_lbl else "Sales (Comparison)"
    show[sales_a_col] = show[sales_a_col].map(money)
    show[sales_b_col] = show[sales_b_col].map(money)
    show["Difference"] = show["Difference"].map(money)
    show["% Change"] = show["% Change"].map(pct_fmt)
    render_shaded_total_table(show[[pivot_dim, sales_a_col, sales_b_col, "Difference", "% Change"]], height=900)

    st.divider()
    st.subheader("Movers")

    a = dfA.groupby("SKU", as_index=False).agg(Sales_A=("Sales", "sum"))
    b = dfB.groupby("SKU", as_index=False).agg(Sales_B=("Sales", "sum"))
    m = a.merge(b, on="SKU", how="outer").fillna(0.0)
    m["Difference"] = m["Sales_A"] - m["Sales_B"]
    m["% Change"] = np.where(m["Sales_B"] != 0, m["Difference"] / m["Sales_B"], np.nan)
    m = m[(m["Sales_A"] >= min_sales) | (m["Sales_B"] >= min_sales)].copy()

    inc = m[m["Difference"] > 0].sort_values("Difference", ascending=False).head(15).copy()
    dec = m[m["Difference"] < 0].sort_values("Difference", ascending=True).head(15).copy()

    for ddf in (inc, dec):
        ddf.rename(columns={"Sales_A": f"Sales ({a_lbl})", "Sales_B": f"Sales ({b_lbl})"}, inplace=True)
        ddf[f"Sales ({a_lbl})"] = ddf[f"Sales ({a_lbl})"].map(money)
        ddf[f"Sales ({b_lbl})"] = ddf[f"Sales ({b_lbl})"].map(money)
        ddf["Difference"] = ddf["Difference"].map(money)
        ddf["% Change"] = ddf["% Change"].map(pct_fmt)

    x, y = st.columns(2)
    with x:
        st.markdown("**Top Increasing**")
        if not inc.empty:
            render_df(inc[["SKU", f"Sales ({a_lbl})", f"Sales ({b_lbl})", "Difference", "% Change"]], height=360)
        else:
            st.caption("None.")
    with y:
        st.markdown("**Top Declining**")
        if not dec.empty:
            render_df(dec[["SKU", f"Sales ({a_lbl})", f"Sales ({b_lbl})", "Difference", "% Change"]], height=360)
        else:
            st.caption("None.")
