from __future__ import annotations

import pandas as pd
import streamlit as st


def build_zero_sales_detail(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Retailer",
        "Vendor",
        "SKU",
        "Units",
        "Price",
        "Sales",
        "StartDate",
        "EndDate",
        "SourceFile",
        "Reason",
    ]
    if df.empty or "Sales" not in df.columns:
        return pd.DataFrame(columns=columns)

    detail = df.copy()
    detail["Sales"] = pd.to_numeric(detail["Sales"], errors="coerce")
    detail["Units"] = pd.to_numeric(detail.get("Units"), errors="coerce").fillna(0.0)
    detail["Price"] = pd.to_numeric(detail.get("Price"), errors="coerce")
    detail = detail[detail["Sales"].fillna(0.0).eq(0.0)].copy()
    detail["Reason"] = "Zero units"
    detail.loc[detail["Price"].isna(), "Reason"] = "Missing price"
    detail.loc[detail["Price"].eq(0.0), "Reason"] = "Price is $0"

    for column in columns:
        if column not in detail.columns:
            detail[column] = pd.NA
    return detail[columns].sort_values(
        ["Reason", "Units", "Retailer", "SKU"],
        ascending=[True, False, True, True],
    )


def build_zero_sales_summary(detail: pd.DataFrame) -> pd.DataFrame:
    columns = ["Retailer", "Vendor", "SKU", "Reason", "Records", "Units", "First Week", "Last Week"]
    if detail.empty:
        return pd.DataFrame(columns=columns)

    summary = (
        detail.groupby(["Retailer", "Vendor", "SKU", "Reason"], dropna=False, as_index=False)
        .agg(
            Records=("SKU", "size"),
            Units=("Units", "sum"),
            **{
                "First Week": ("EndDate", "min"),
                "Last Week": ("EndDate", "max"),
            },
        )
        .sort_values(["Units", "Records", "Retailer", "SKU"], ascending=[False, False, True, True])
    )
    return summary[columns]


def render(ctx: dict):
    st.subheader("Zero-Dollar SKUs")
    detail = build_zero_sales_detail(ctx.get("df_scope", pd.DataFrame()))

    if detail.empty:
        st.success("No $0 sales records were found in the selected scope.")
        return

    actionable = detail[detail["Reason"].isin(["Missing price", "Price is $0"])]
    summary = build_zero_sales_summary(detail)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Unique SKUs", f"{detail['SKU'].nunique():,}")
    metric_cols[1].metric("$0 Records", f"{len(detail):,}")
    metric_cols[2].metric("Affected Units", f"{detail['Units'].sum():,.0f}")
    metric_cols[3].metric("Pricing Issues", f"{len(actionable):,}")

    reason_options = ["All"] + sorted(detail["Reason"].dropna().unique().tolist())
    selected_reason = st.segmented_control(
        "Reason",
        options=reason_options,
        default="All",
    )
    filtered_detail = detail if selected_reason in (None, "All") else detail[detail["Reason"] == selected_reason]
    filtered_summary = build_zero_sales_summary(filtered_detail)

    summary_tab, records_tab = st.tabs(["SKU Summary", "Source Records"])
    with summary_tab:
        st.dataframe(
            filtered_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Records": st.column_config.NumberColumn(format="%d"),
                "Units": st.column_config.NumberColumn(format="%.0f"),
                "First Week": st.column_config.DateColumn(format="MM/DD/YYYY"),
                "Last Week": st.column_config.DateColumn(format="MM/DD/YYYY"),
            },
        )
    with records_tab:
        st.dataframe(
            filtered_detail,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Units": st.column_config.NumberColumn(format="%.0f"),
                "Price": st.column_config.NumberColumn(format="$%.2f"),
                "Sales": st.column_config.NumberColumn(format="$%.2f"),
                "StartDate": st.column_config.DateColumn(format="MM/DD/YYYY"),
                "EndDate": st.column_config.DateColumn(format="MM/DD/YYYY"),
            },
        )

    st.download_button(
        "Download $0 Records",
        data=filtered_detail.to_csv(index=False).encode("utf-8"),
        file_name="zero_dollar_skus.csv",
        mime="text/csv",
        use_container_width=True,
    )