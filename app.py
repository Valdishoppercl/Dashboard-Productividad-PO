import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Performance Outsourcing", layout="wide")

VALDI_NAVY = "#0d1b3e"
VALDI_PINK = "#d63384"

# CSS para mantener el formato al compartir el enlace
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fc; }}
    [data-testid="stHeader"] {{ background: {VALDI_NAVY}; color: white; border-bottom: 4px solid {VALDI_PINK}; }}
    .main-title {{ color: {VALDI_NAVY}; font-size: 1.8rem; font-weight: 800; margin-bottom: 0px; }}
    .brand-text {{ color: {VALDI_PINK}; font-weight: 700; font-size: 0.9rem; text-transform: uppercase; }}
    .metric-card {{ 
        background: white; padding: 20px; border-radius: 12px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;
        border: 1px solid #eee;
    }}
    .metric-title {{ color: #7f8c8d; font-size: 0.85rem; font-weight: bold; margin-bottom: 5px; }}
    .metric-value {{ color: {VALDI_NAVY}; font-size: 1.8rem; font-weight: 900; }}
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    df = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    
    # --- CORRECCIÓN SKU (ELIMINA EL 0 DE MÁS) ---
    # Limpiamos puntos y comas, luego convertimos a entero
    df['sku totales'] = df['sku totales'].astype(str).str.replace('.', '', regex=False).str.replace(',', '', regex=False)
    df['sku totales'] = pd.to_numeric(df['sku totales'], errors='coerce').fillna(0).astype(int)
    
    df['pago variable'] = df['pago variable'].astype(str).str.replace(r'[\$\.\s]', '', regex=True)
    df['pago variable'] = pd.to_numeric(df['pago variable'], errors='coerce').fillna(0)
    df['fecha día'] = pd.to_datetime(df['fecha día'], dayfirst=True, errors='coerce')
    
    return df

try:
    df_raw = load_data()

    # Encabezado Fijo
    col_header, col_btn = st.columns([7, 3])
    with col_header:
        st.markdown(f"<p class='main-title'>Performance Outsourcing</p><p class='brand-text'>VALDISHOPPER</p>", unsafe_allow_html=True)
    with col_btn:
        st.button("📧 ENVIAR A PRESTADORES", type="primary", use_container_width=True)

    # Filtros
    st.markdown("---")
    f1, f2, f3 = st.columns(3)
    with f1:
        salas = ["Todas las Salas"] + sorted([str(s) for s in df_raw['local'].unique()])
        sala_sel = st.selectbox("SALA", options=salas)
    with f2:
        f_inicio = st.date_input("DESDE", df_raw['fecha día'].min())
    with f3:
        f_fin = st.date_input("HASTA", df_raw['fecha día'].max())

    df = df_raw.copy()
    if sala_sel != "Todas las Salas":
        df = df[df['local'].astype(str) == sala_sel]
    df = df[(df['fecha día'].dt.date >= f_inicio) & (df['fecha día'].dt.date <= f_fin)]
    
    df['cumple_meta'] = df['sku totales'] >= 200

    # KPIs con tarjetas personalizadas (Para que no pierdan formato)
    st.write("")
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f"<div class='metric-card'><div class='metric-title'>Turnos</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='metric-card'><div class='metric-title'>Metas OK</div><div class='metric-value' style='color:#2ecc71;'>{df['cumple_meta'].sum()}</div></div>", unsafe_allow_html=True)
    with k3: 
        eficacia = (df['cumple_meta'].sum() / len(df) * 100) if len(df) > 0 else 0
        st.markdown(f"<div class='metric-card'><div class='metric-title'>Eficacia</div><div class='metric-value' style='color:{VALDI_PINK};'>{eficacia:.0f}%</div></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='metric-card'><div class='metric-title'>Incentivo Total</div><div class='metric-value'>${df['pago variable'].sum():,.0f}</div></div>", unsafe_allow_html=True)

    # Gráfico Demanda vs Cumplimiento
    st.write("### Tendencia de Productividad")
    df_chart = df.groupby(df['fecha día'].dt.date).agg({'sku totales': 'sum', 'cumple_meta': 'mean'}).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_chart['fecha día'], y=df_chart['sku totales'], name="SKU", marker_color='rgba(13,27,62,0.1)'))
    fig.add_trace(go.Scatter(x=df_chart['fecha día'], y=df_chart['cumple_meta']*100, name="%", line=dict(color=VALDI_PINK, width=3), yaxis="y2"))
    
    fig.update_layout(
        yaxis=dict(title="SKU Totales"),
        yaxis2=dict(title="% Cumplimiento", overlaying="y", side="right", range=[0, 100]),
        margin=dict(l=0, r=0, t=20, b=0), height=350, showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabla de Detalle Limpia
    st.write("### Detalle de Gestión")
    df_tabla = df[['local', 'rut', 'fecha día', 'sku totales', 'pago variable']].copy()
    df_tabla['fecha día'] = df_tabla['fecha día'].dt.strftime('%d-%m-%Y')
    df_tabla.columns = ['SALA', 'RUT', 'FECHA', 'SKU', 'PAGO VARIABLE']
    
    st.dataframe(df_tabla.sort_values('FECHA', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error de carga: {e}")

