import streamlit as st

def apply_global_styles():
    st.markdown("""
    <style>
    /* KPI Card Styling - Simple with color-coded changes */
    .kpi-card{border:2px solid rgba(128,128,128,0.35);border-radius:16px;padding:16px 18px;background: var(--secondary-background-color);box-shadow:0 2px 8px rgba(0,0,0,0.08);}
    .kpi-title{font-size:12px;font-weight:600;letter-spacing:0.02em;color: #000000;opacity: 0.70;text-transform:uppercase;}
    .kpi-value{font-size:28px;font-weight:800;line-height:1.15;color: #000000;}
    .kpi-delta{font-size:13px;margin-top:6px;color: var(--text-color);opacity: 0.80;}
    .kpi-delta .delta-abs{ font-weight:800; }
    .kpi-delta .delta-pct{ font-weight:700; opacity:0.88; margin-left:6px; }
    .kpi-delta .delta-note{ opacity:0.75; margin-left:6px; }
    .kpi-big-main{font-size:30px;font-weight:800;line-height:1.05;margin-top:4px;color: #000000;}
    .kpi-big-name{font-size:22px;font-weight:700;line-height:1.15;margin-top:6px;color: #000000;}
    .kpi-big-total{font-size:13px;opacity:0.78;margin-top:6px;color: #000000;}
    .kpi-big-pct{font-size:13px;font-weight:700;margin-top:4px;}
    .intel-card{border:1px solid rgba(128,128,128,0.22);border-radius:16px;padding:14px 16px;background: var(--secondary-background-color);margin-bottom:14px;}
    .intel-header{font-size:12px;font-weight:800;letter-spacing:0.06em;color: var(--text-color);opacity:0.70;}
    .intel-body{margin-top:8px;color: var(--text-color);font-size:15px;line-height:1.45;}
    .intel-body ul{margin: 0;padding-left: 18px;}
    .intel-body li{margin: 6px 0;}
    
    /* Enhanced Table Styling with Alternating Rows */
    .report-table{width:100% !important;table-layout:auto;border-collapse: collapse;font-size:14px !important;line-height:1.3;}
    .report-table th, .report-table td{padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.18);text-align:left;white-space:nowrap;}
    .report-table th{font-size:13px !important;font-weight:700;color:var(--text-color);opacity:0.82;background: rgba(79, 172, 254, 0.08);border-bottom:2px solid rgba(79, 172, 254, 0.3);}
    .report-table td{color:var(--text-color);}
    .report-table tbody tr:nth-child(even){background-color:rgba(128,128,128,0.04);}
    .report-table tbody tr:hover{background-color:rgba(79, 172, 254, 0.08);transition:background-color 0.2s ease;}
    
    /* Streamlit Dataframe Enhancement */
    div[data-testid="stDataFrame"] * {font-size:14px !important;}
    div[data-testid="stDataFrame"] {border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);}

    /* Sales dashboard top-left KPI strip */
    .sales-dashboard-context{display:flex;flex-direction:column;align-items:flex-start;gap:8px;margin:0 0 10px 0;}
    .sales-dashboard-top-row{display:flex;justify-content:flex-start;align-items:flex-start;width:100%;margin:0;}
    .sales-dashboard-kpi-strip{display:flex;justify-content:flex-start;gap:10px;flex-wrap:wrap;max-width:100%;}
    .sales-dashboard-kpi-card{min-width:150px;max-width:170px;padding:12px 14px;border-radius:14px;}
    .sales-dashboard-kpi-card .kpi-title{font-size:11px;letter-spacing:0.05em;}
    .sales-dashboard-kpi-card .kpi-value{font-size:24px;line-height:1.05;margin-top:4px;}
    .sales-dashboard-kpi-compare{font-size:11px;color:var(--text-color);opacity:0.66;margin-top:6px;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
    .sales-dashboard-kpi-delta-stack{margin-top:8px;display:flex;flex-direction:column;gap:2px;}
    .sales-dashboard-kpi-delta-line{font-size:13px;font-weight:800;line-height:1.15;}
    .sales-dashboard-kpi-pct-line{font-size:12px;font-weight:700;line-height:1.1;}
    .sales-dashboard-context-copy{font-size:13px;color:var(--text-color);opacity:0.82;line-height:1.35;}

    @media (max-width: 1100px) {
        .sales-dashboard-top-row{justify-content:flex-start;}
        .sales-dashboard-kpi-strip{justify-content:flex-start;}
    }

    @media (max-width: 768px) {
        .sales-dashboard-kpi-strip{display:grid;grid-template-columns:repeat(2, minmax(140px, 1fr));width:100%;}
        .sales-dashboard-kpi-card{max-width:none;min-width:0;}
    }

    @media (max-width: 540px) {
        .sales-dashboard-kpi-strip{grid-template-columns:1fr;}
    }
    
    /* Dataframe Header Styling */
    div[data-testid="stDataFrame"] [data-testid="stTableHeaderCell"] {
        background: linear-gradient(135deg, rgba(79, 172, 254, 0.12) 0%, rgba(79, 172, 254, 0.06) 100%) !important;
        font-weight:700 !important;
        border-bottom:2px solid rgba(79, 172, 254, 0.3) !important;
    }
    
    /* Dataframe Row Alternating Colors */
    div[data-testid="stDataFrame"] [data-testid="stTableBodyRow"] {
        transition:background-color 0.2s ease !important;
    }
    
    div[data-testid="stDataFrame"] [data-testid="stTableBodyRow"]:nth-child(even) {
        background-color:rgba(128,128,128,0.04) !important;
    }
    
    div[data-testid="stDataFrame"] [data-testid="stTableBodyRow"]:hover {
        background-color:rgba(79, 172, 254, 0.08) !important;
    }
    </style>
    """, unsafe_allow_html=True)
