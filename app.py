import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="Productividad | Valdishopper", layout="wide")

VALDI_NAVY = "#0d1b3e"
VALDI_PINK = "#d63384"
VALDI_BG = "#f8f9fc"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {VALDI_BG}; }}
    .main-header {{
        background-color: {VALDI_NAVY};
        padding: 15px 40px;
        border-bottom: 4px solid {VALDI_PINK};
        color: white;
        margin-bottom: 20px;
    }}
    </style>
    <div class="main-header">
        <h1 style='margin:0; font-size: 1.5rem;'>Performance Outsourcing</h1>
        <span style='color:{VALDI_PINK}; font-weight:700; font-size:0.8rem;'>VALDISHOPPER</span>
    </div>
""", unsafe_allow_html=True)

# --- FUNCIONES CORE ---

def normalizar_rut(rut):
    if not rut: return ""
    import re
    return re.sub(r'[^0-9k]', '', str(rut).lower())

@st.cache_data(ttl=600)
def load_all_data():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    df_prod = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df_prod.columns = df_prod.columns.str.strip().str.lower()
    
    df_buk = pd.DataFrame(sh.worksheet("BUK").get_all_records())
    df_buk.columns = df_buk.columns.str.strip().str.lower()
    
    return df_prod, df_buk

# --- PROCESAMIENTO ---

try:
    df_prod, df_buk = load_all_data()
    
    # Nombres de columnas detectados en tus errores previos
    C_FECHA = 'fecha día'
    C_SKU = 'sku totales'
    C_PAGO = 'pago variable'
    C_LOCAL = 'local'
    C_RUT_PROD = 'rut'
    C_RUT_BUK = 'colaborador - número de documento'

    # 1. CONVERSIÓN CRÍTICA DE FECHA (Soluciona el error .dt)
    df_prod[C_FECHA] = pd.to_datetime(df_prod[C_FECHA], dayfirst=True, errors='coerce')
    
    # Sidebar: Filtros
    with st.sidebar:
        st.header("Filtros")
        locales = ["Todos"] + sorted(df_prod[C_LOCAL].unique().tolist())
        f_local = st.selectbox("SALA", locales)
        # Ajustamos el rango de fechas basado en los datos reales
        min_date = df_prod[C_FECHA].min().date() if not df_prod[C_FECHA].isnull().all() else datetime.now().date()
        max_date = df_prod[C_FECHA].max().date() if not df_prod[C_FECHA].isnull().all() else datetime.now().date()
        
        f_inicio = st.date_input("DESDE", min_date)
        f_fin = st.date_input("HASTA", max_date)

    # Aplicar Filtros
    df_filt = df_prod.copy()
    if f_local != "Todos":
        df_filt = df_filt[df_filt[C_LOCAL] == f_local]
    
    # Filtro de fecha usando .dt.date para comparar correctamente
    df_filt = df_filt[(df_filt[C_FECHA].dt.date >= f_inicio) & (df_filt[C_FECHA].dt.date <= f_fin)]

    # Limpieza numérica
    df_filt[C_SKU] = pd.to_numeric(df_filt[C_SKU].astype(str).str.replace('.', ''), errors='coerce').fillna(0)
    df_filt[C_PAGO] = pd.to_numeric(df_filt[C_PAGO].astype(str).str.replace(r'[\$\.]', '', regex=True), errors='coerce').fillna(0)
    df_filt['cumple_meta'] = df_filt[C_SKU] >= 200

    # --- MÉTRICAS ---
    m1, m2, m3, m4 = st.columns(4)
    total_turnos = len(df_filt)
    metas_ok = df_filt['cumple_meta'].sum()
    eficacia = (metas_ok / total_turnos * 100) if total_turnos > 0 else 0
    total_pago = df_filt[C_PAGO].sum()

    m1.metric("Turnos", total_turnos)
    m2.metric("Metas OK", metas_ok)
    m3.metric("Eficacia", f"{eficacia:.1f}%")
    m4.metric("Incentivo Total", f"${total_pago:,.0f}")

    # --- GRÁFICOS ---
    st.write("### Tendencia de Productividad")
    df_daily = df_filt.groupby(df_filt[C_FECHA].dt.date).agg({C_SKU: 'sum', 'cumple_meta': 'mean'}).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_daily[C_FECHA], y=df_daily[C_SKU], name="SKU Totales", marker_color=VALDI_NAVY))
    fig.add_trace(go.Scatter(x=df_daily[C_FECHA], y=df_daily['cumple_meta']*100, name="% Meta", line=dict(color=VALDI_PINK, width=3), yaxis="y2"))
    
    fig.update_layout(
        yaxis=dict(title="Volumen SKU"),
        yaxis2=dict(title="% Cumplimiento", overlaying="y", side="right", range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_filt, use_container_width=True)

except Exception as e:
    st.error(f"Error en el dashboard: {e}")
