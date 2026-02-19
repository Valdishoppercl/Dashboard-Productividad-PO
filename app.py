import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import base64

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Performance Outsourcing", layout="wide")

VALDI_NAVY = "#0d1b3e"
VALDI_PINK = "#d63384"

# Estilos CSS para replicar tu Dashboard original
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fc; }}
    [data-testid="stHeader"] {{ background: {VALDI_NAVY}; color: white; border-bottom: 4px solid {VALDI_PINK}; }}
    h1 {{ color: {VALDI_NAVY}; font-size: 1.5rem !important; margin-bottom: 0px !important; }}
    .metric-card {{ background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); text-align: center; }}
    .metric-title {{ color: #95a5a6; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; }}
    .metric-value {{ color: {VALDI_NAVY}; font-size: 1.6rem; font-weight: 800; }}
    </style>
""", unsafe_allow_html=True)

# --- CARGA Y LIMPIEZA DE DATOS ---
def limpiar_rut(rut):
    import re
    return re.sub(r'[^0-9k]', '', str(rut).lower())

@st.cache_data(ttl=600)
def load_data():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    # Cargar datos de Producción
    df = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    
    # CORRECCIÓN SKU: Forzamos a string, quitamos puntos de miles y convertimos a entero
    # Esto evita que '75' se convierta en '750' por errores de interpretación decimal
    df['sku totales'] = df['sku totales'].astype(str).str.replace('.', '', regex=False)
    df['sku totales'] = pd.to_numeric(df['sku totales'], errors='coerce').fillna(0).astype(int)
    
    # Limpieza de Pago Variable
    df['pago variable'] = df['pago variable'].astype(str).str.replace(r'[\$\.\s]', '', regex=True)
    df['pago variable'] = pd.to_numeric(df['pago variable'], errors='coerce').fillna(0)
    
    # Conversión de Fecha
    df['fecha día'] = pd.to_datetime(df['fecha día'], dayfirst=True, errors='coerce')
    
    return df

# --- INTERFAZ PRINCIPAL ---
try:
    df_raw = load_data()

    # Header con botones
    col_t1, col_t2 = st.columns([7, 3])
    with col_t1:
        st.markdown(f"<h1>Performance Outsourcing</h1><span style='color:{VALDI_PINK}; font-weight:700;'>VALDISHOPPER</span>", unsafe_allow_html=True)
    with col_t2:
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            if st.button("📥 CSV"):
                csv = df_raw.to_csv(index=False).encode('utf-8-sig')
                st.download_button("Confirmar Descarga", csv, "Export_Valdishopper.csv", "text/csv")
        with c_b2:
            if st.button("📧 ENVIAR A PRESTADORES", type="primary"):
                st.info("Iniciando envío masivo...")

    # Filtros (Fila horizontal como el original)
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
    
    # Lógica de Meta
    df['cumple_meta'] = df['sku totales'] >= 200

    # --- KPIs (Cards Estilo Original) ---
    st.write("")
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f"<div class='metric-card'><div class='metric-title'>Turnos</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='metric-card'><div class='metric-title'>Metas OK</div><div class='metric-value' style='color:#27ae60;'>{df['cumple_meta'].sum()}</div></div>", unsafe_allow_html=True)
    with k3: 
        eficacia = (df['cumple_meta'].sum() / len(df) * 100) if len(df) > 0 else 0
        st.markdown(f"<div class='metric-card'><div class='metric-title'>Eficacia</div><div class='metric-value' style='color:{VALDI_PINK};'>{eficacia:.0f}%</div></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='metric-card'><div class='metric-title'>Incentivo Total</div><div class='metric-value'>${df['pago variable'].sum():,.0f}</div></div>", unsafe_allow_html=True)

    # --- GRÁFICOS (Réplica de tu diseño) ---
    st.write("### Demanda vs Cumplimiento")
    df_chart = df.groupby(df['fecha día'].dt.date).agg({'sku totales': 'sum', 'cumple_meta': 'mean'}).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_chart['fecha día'], y=df_chart['sku totales'], name="SKU", marker_color='rgba(13,27,62,0.1)'))
    fig.add_trace(go.Scatter(x=df_chart['fecha día'], y=df_chart['cumple_meta']*100, name="%", line=dict(color=VALDI_PINK, width=2), yaxis="y2"))
    
    fig.update_layout(
        yaxis=dict(title="SKU"),
        yaxis2=dict(title="%", overlaying="y", side="right", range=[0, 100]),
        margin=dict(l=0, r=0, t=30, b=0), height=350, showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- TABLA DETALLE (Columnas exactas solicitadas) ---
    st.write("### Detalle")
    df_tabla = df[['local', 'rut', 'fecha día', 'sku totales', 'pago variable']].copy()
    df_tabla['fecha día'] = df_tabla['fecha día'].dt.strftime('%d-%m-%Y')
    df_tabla.columns = ['SALA', 'RUT', 'FECHA', 'SKU', 'PAGO VARIABLE']
    
    st.dataframe(df_tabla.sort_values('FECHA', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error en el procesamiento: {e}")
