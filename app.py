import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA (Estilo Valdishopper) ---
st.set_page_config(page_title="Performance Outsourcing", layout="wide")

VALDI_NAVY = "#0d1b3e"
VALDI_PINK = "#d63384"

# Estilo para ocultar menús de Streamlit y mejorar la tabla
st.markdown(f"""
    <style>
    .main {{ background-color: #f8f9fc; }}
    [data-testid="stHeader"] {{ background: {VALDI_NAVY}; color: white; border-bottom: 4px solid {VALDI_PINK}; }}
    h1 {{ color: {VALDI_NAVY}; font-size: 1.5rem !important; margin-bottom: 0px !important; }}
    .metric-card {{ background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); text-align: center; }}
    </style>
""", unsafe_allow_html=True)

# --- CARGA Y LIMPIEZA ---
def limpiar_rut(rut):
    import re
    return re.sub(r'[^0-9k]', '', str(rut).lower())

@st.cache_data(ttl=600)
def load_data():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    # Cargar datos operativos
    df = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    
    # Limpieza de SKU: Quitar puntos de miles antes de convertir a número para evitar el "x10"
    df['sku totales'] = pd.to_numeric(df['sku totales'].astype(str).str.replace('.', '', regex=False), errors='coerce').fillna(0)
    
    # Limpieza de Pago: Quitar $, puntos y espacios
    df['pago variable'] = pd.to_numeric(df['pago variable'].astype(str).str.replace(r'[\$\.\s]', '', regex=True), errors='coerce').fillna(0)
    
    # Convertir fecha
    df['fecha día'] = pd.to_datetime(df['fecha día'], dayfirst=True, errors='coerce')
    
    return df

# --- INTERFAZ ---
try:
    df_raw = load_data()

    # Encabezado (Réplica de tu Script)
    col_t1, col_t2 = st.columns([8, 2])
    with col_t1:
        st.markdown(f"<h1>Performance Outsourcing</h1><span style='color:{VALDI_PINK}; font-weight:700;'>VALDISHOPPER</span>", unsafe_allow_html=True)
    with col_t2:
        if st.button("📧 ENVIAR A PRESTADORES", type="primary"):
            st.info("Procesando envíos...")

    # Filtros (Misma fila que en tu script)
    st.markdown("---")
    f1, f2, f3 = st.columns(3)
    with f1:
        salas = ["Todas las Salas"] + sorted([str(s) for s in df_raw['local'].unique()])
        sala_sel = st.selectbox("SALA", options=salas)
    with f2:
        f_inicio = st.date_input("DESDE", df_raw['fecha día'].min())
    with f3:
        f_fin = st.date_input("HASTA", df_raw['fecha día'].max())

    # Aplicar Filtros
    df = df_raw.copy()
    if sala_sel != "Todas las Salas":
        df = df[df['local'].astype(str) == sala_sel]
    df = df[(df['fecha día'].dt.date >= f_inicio) & (df['fecha día'].dt.date <= f_fin)]
    
    df['cumple_meta'] = df['sku totales'] >= 200

    # KPIs (Cards blancas como en tu script)
    st.write("")
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f"<div class='metric-card'><small>Turnos</small><br><b>{len(df)}</b></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='metric-card'><small>Metas OK</small><br><b style='color:green;'>{df['cumple_meta'].sum()}</b></div>", unsafe_allow_html=True)
    with k3: 
        eficacia = (df['cumple_meta'].sum() / len(df) * 100) if len(df) > 0 else 0
        st.markdown(f"<div class='metric-card'><small>Eficacia</small><br><b style='color:{VALDI_PINK};'>{eficacia:.0f}%</b></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='metric-card'><small>Incentivo Total</small><br><b>${df['pago variable'].sum():,.0f}</b></div>", unsafe_allow_html=True)

    # Gráfico Demanda vs Cumplimiento (Doble eje como en tu script)
    st.write("### Demanda vs Cumplimiento")
    df_chart = df.groupby(df['fecha día'].dt.date).agg({'sku totales': 'sum', 'cumple_meta': 'mean'}).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_chart['fecha día'], y=df_chart['sku totales'], name="SKU", marker_color='rgba(13,27,62,0.1)'))
    fig.add_trace(go.Scatter(x=df_chart['fecha día'], y=df_chart['cumple_meta']*100, name="%", line=dict(color=VALDI_PINK, width=2), yaxis="y2"))
    
    fig.update_layout(
        yaxis=dict(title="SKU"),
        yaxis2=dict(title="%", overlaying="y", side="right", range=[0, 100]),
        margin=dict(l=0, r=0, t=20, b=0), height=300, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabla Detalle (Columnas exactas de tu script)
    st.write("### Detalle")
    # Seleccionamos y renombramos solo lo que nos interesa
    df_tabla = df[['local', 'rut', 'fecha día', 'sku totales', 'pago variable']].copy()
    df_tabla['fecha día'] = df_tabla['fecha día'].dt.strftime('%d-%m-%Y')
    df_tabla.columns = ['SALA', 'RUT', 'FECHA', 'SKU', 'PAGO VARIABLE']
    
    st.dataframe(df_tabla.sort_values('FECHA', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
