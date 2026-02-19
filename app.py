import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA FORZADA ---
st.set_page_config(page_title="Performance Outsourcing", layout="wide", initial_sidebar_state="collapsed")

VALDI_NAVY = "#0d1b3e"
VALDI_PINK = "#d63384"

# CSS Inyectado para asegurar formato en cualquier navegador
st.markdown(f"""
    <style>
    /* Forzar fondo claro y fuentes */
    .stApp {{ background-color: #f8f9fc !important; color: {VALDI_NAVY} !important; }}
    
    /* Estilo del Header */
    header[data-testid="stHeader"] {{ background: {VALDI_NAVY} !important; border-bottom: 4px solid {VALDI_PINK}; }}
    
    /* Títulos y Subtítulos */
    h1, h2, h3, p {{ color: {VALDI_NAVY} !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
    
    /* Tarjetas de Métricas consistentes */
    .metric-container {{
        display: flex; justify-content: space-around; gap: 10px; margin-bottom: 25px;
    }}
    .metric-card {{
        background: white; padding: 20px; border-radius: 12px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;
        flex: 1; border: 1px solid #e0e0e0;
    }}
    .metric-title {{ color: #7f8c8d; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }}
    .metric-value {{ color: {VALDI_NAVY}; font-size: 1.8rem; font-weight: 900; }}

    /* Fix para tablas en enlaces compartidos */
    [data-testid="stDataFrame"] {{ background: white; border-radius: 10px; padding: 5px; }}
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    df = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    
    # Limpieza estricta de SKU (Fix 0 de más)
    df['sku totales'] = df['sku totales'].astype(str).str.replace('.', '', regex=False).str.replace(',', '', regex=False)
    df['sku totales'] = pd.to_numeric(df['sku totales'], errors='coerce').fillna(0).astype(int)
    
    # Limpieza de Pago
    df['pago variable'] = df['pago variable'].astype(str).str.replace(r'[\$\.\s]', '', regex=True)
    df['pago variable'] = pd.to_numeric(df['pago variable'], errors='coerce').fillna(0)
    
    df['fecha día'] = pd.to_datetime(df['fecha día'], dayfirst=True, errors='coerce')
    return df

try:
    df_raw = load_data()

    # Header Profesional
    st.markdown(f"""
        <div style='background:{VALDI_NAVY}; padding:20px; border-radius:10px; border-bottom:5px solid {VALDI_PINK}; margin-bottom:30px;'>
            <h1 style='color:white !important; margin:0;'>Performance Outsourcing</h1>
            <p style='color:{VALDI_PINK} !important; font-weight:bold; margin:0;'>VALDISHOPPER</p>
        </div>
    """, unsafe_allow_html=True)

    # Filtros Horizontales
    f1, f2, f3 = st.columns(3)
    with f1:
        salas = ["Todas las Salas"] + sorted([str(s) for s in df_raw['local'].unique()])
        sala_sel = st.selectbox("SALA", options=salas)
    with f2:
        f_inicio = st.date_input("DESDE", df_raw['fecha día'].min().date())
    with f3:
        f_fin = st.date_input("HASTA", df_raw['fecha día'].max().date())

    df = df_raw.copy()
    if sala_sel != "Todas las Salas":
        df = df[df['local'].astype(str) == sala_sel]
    df = df[(df['fecha día'].dt.date >= f_inicio) & (df['fecha día'].dt.date <= f_fin)]
    
    df['cumple_meta'] = df['sku totales'] >= 200

    # KPIs con HTML directo para evitar deformación
    eficacia = (df['cumple_meta'].sum() / len(df) * 100) if len(df) > 0 else 0
    pago_acumulado = df['pago variable'].sum()

    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card"><div class="metric-title">Turnos</div><div class="metric-value">{len(df)}</div></div>
            <div class="metric-card"><div class="metric-title">Metas OK</div><div class="metric-value" style="color:#2ecc71;">{df['cumple_meta'].sum()}</div></div>
            <div class="metric-card"><div class="metric-title">Eficacia</div><div class="metric-value" style="color:{VALDI_PINK};">{eficacia:.1f}%</div></div>
            <div class="metric-card"><div class="metric-title">Incentivo Total</div><div class="metric-value">${pago_acumulado:,.0f}</div></div>
        </div>
    """, unsafe_allow_html=True)

    # Gráfico con fondo blanco forzado
    st.markdown("### Tendencia de Productividad")
    df_chart = df.groupby(df['fecha día'].dt.date).agg({'sku totales': 'sum', 'cumple_meta': 'mean'}).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_chart['fecha día'], y=df_chart['sku totales'], name="SKU", marker_color='rgba(13,27,62,0.1)'))
    fig.add_trace(go.Scatter(x=df_chart['fecha día'], y=df_chart['cumple_meta']*100, name="%", line=dict(color=VALDI_PINK, width=3), yaxis="y2"))
    
    fig.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        yaxis=dict(title="SKU Totales", gridcolor='#f0f0f0'),
        yaxis2=dict(title="% Cumplimiento", overlaying="y", side="right", range=[0, 100], showgrid=False),
        margin=dict(l=0, r=0, t=10, b=0), height=350, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabla Detalle limpia
    st.markdown("### Detalle de Gestión")
    df_tabla = df[['local', 'rut', 'fecha día', 'sku totales', 'pago variable']].copy()
    df_tabla['fecha día'] = df_tabla['fecha día'].dt.strftime('%d-%m-%Y')
    df_tabla.columns = ['SALA', 'RUT', 'FECHA', 'SKU', 'PAGO VARIABLE']
    
    st.dataframe(df_tabla.sort_values('FECHA', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error en visualización: {e}")
