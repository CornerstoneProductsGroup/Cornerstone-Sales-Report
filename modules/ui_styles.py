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

    .sales-exec-accent{height:14px;background:#1f3f72;border-radius:0;margin:0 0 8px 0;}
    .sales-exec-row-label{font-size:12px;font-weight:700;color:#4b5563;margin:0 0 4px 0;}
    .sales-exec-kpi-ribbon{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:0;border:1px solid rgba(148,163,184,0.35);background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.08);margin-bottom:8px;}
    .sales-exec-kpi-tile{padding:14px 16px;border-right:1px solid rgba(203,213,225,0.8);min-width:0;}
    .sales-exec-kpi-tile:last-child{border-right:none;}
    .sales-exec-kpi-title{font-size:13px;font-weight:700;letter-spacing:0.01em;color:#5b6472;text-transform:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
    .sales-exec-kpi-metric-row{display:flex;align-items:center;gap:6px;margin-top:6px;flex-wrap:wrap;}
    .sales-exec-kpi-value{font-size:21px;font-weight:800;line-height:1.1;color:#1f2937;}
    .sales-exec-kpi-delta{font-size:14px;font-weight:800;line-height:1.1;}
    .sales-exec-kpi-meta-line{font-size:12px;line-height:1.25;color:#4b5563;margin-top:4px;}
    .sales-exec-context{font-size:12px;color:#6b7280;margin:0 0 10px 0;}

    .sales-movers-table{display:flex;flex-direction:column;gap:0;height:540px;}
    .sales-movers-row{display:grid;grid-template-columns:minmax(0,1.1fr) auto auto minmax(0,1fr);gap:10px;align-items:center;padding:6px 6px;border-top:1px solid rgba(226,232,240,0.9);flex:1;}
    .sales-movers-row:first-child{border-top:none;}
    .sales-movers-sku{font-size:13px;font-weight:800;color:#111827;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
    .sales-movers-delta,.sales-movers-pct{font-size:13px;font-weight:800;white-space:nowrap;}
    .sales-movers-retailer{font-size:13px;color:#374151;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}

    .sales-new-products-list{display:flex;flex-direction:column;gap:0;}
    .sales-new-products-item{padding:12px 4px 12px 18px;border-top:1px solid rgba(226,232,240,0.9);font-size:14px;font-weight:600;color:#243244;position:relative;line-height:1.35;}
    .sales-new-products-item:first-child{border-top:none;}
    .sales-new-products-item::before{content:'•';position:absolute;left:4px;top:12px;color:#667085;font-size:18px;line-height:1;}

    @media (max-width: 1100px) {
        .sales-dashboard-top-row{justify-content:flex-start;}
        .sales-dashboard-kpi-strip{justify-content:flex-start;}
        .sales-exec-kpi-ribbon{grid-template-columns:repeat(4,minmax(140px,1fr));}
    }

    @media (max-width: 768px) {
        .sales-dashboard-kpi-strip{display:grid;grid-template-columns:repeat(2, minmax(140px, 1fr));width:100%;}
        .sales-dashboard-kpi-card{max-width:none;min-width:0;}
        .sales-exec-kpi-ribbon{grid-template-columns:repeat(2,minmax(150px,1fr));}
        .sales-movers-row{grid-template-columns:minmax(0,1fr) auto;gap:8px;}
        .sales-movers-retailer{grid-column:1 / -1;text-align:left;}
    }

    @media (max-width: 540px) {
        .sales-dashboard-kpi-strip{grid-template-columns:1fr;}
        .sales-exec-kpi-ribbon{grid-template-columns:1fr;}
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
