import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA (Tema Forzado) ---
st.set_page_config(
    page_title="Performance Outsourcing", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

VALDI_NAVY = "#0d1b3e"
VALDI_PINK = "#d63384"

# --- BLOQUEO DE FORMATO Y OCULTACIÓN DE UI ---
st.markdown(f"""
    <style>
    /* 1. Forzar fondo claro y deshabilitar temas del navegador */
    .stApp {{
        background-color: #f8f9fc !important;
        color: {VALDI_NAVY} !important;
    }}

    /* 2. Ocultar botones de Share, GitHub y Menús */
    header, footer, #MainMenu, .stDeployButton, [data-testid="stToolbar"] {{
        visibility: hidden !important;
        display: none !important;
    }}

    /* 3. Banner Superior Valdishopper (Colores Originales) */
    .valdi-header {{
        background-color: {VALDI_NAVY} !important;
        padding: 25px 40px;
        border-bottom: 6px solid {VALDI_PINK} !important;
        border-radius: 8px;
        margin-bottom: 25px;
        color: white !important;
    }}
    .valdi-header h1 {{ color: white !important; margin: 0 !important; font-size: 26px !important; }}
    .valdi-header p {{ color: {VALDI_PINK} !important; margin: 0 !important; font-weight: bold !important; }}

    /* 4. Tarjetas de Métricas (Siempre Blancas) */
    .metric-row {{
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin-bottom: 25px;
    }}
    .metric-card {{
        background-color: white !important;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        text-align: center;
        flex: 1;
        border: 1px solid #eee !important;
    }}
    .metric-title {{ color: #7f8c8d !important; font-size: 0.8rem !important; font-weight: bold !important; text-transform: uppercase; }}
    .metric-value {{ color: {VALDI_NAVY} !important; font-size: 1.8rem !important; font-weight: 800 !important; }}

    /* 5. Inputs con fondo blanco y texto Navy */
    label, p, span, .stSelectbox div, .stDateInput div {{
        color: {VALDI_NAVY} !important;
    }}
    </style>
""", unsafe_allow_html=True)

# --- CARGA Y LIMPIEZA DE DATOS ---
@st.cache_data(ttl=600)
def load_data():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    # Cargar datos operativos
    df = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    
    # FIX SKU: Elimina puntos/comas de miles para evitar el error "x10"
    df['sku totales'] = df['sku totales'].astype(str).str.replace(r'[\.\,]', '', regex=True)
    df['sku totales'] = pd.to_numeric(df['sku totales'], errors='coerce').fillna(0).astype(int)
    
    # Limpieza Pago Variable
    df['pago variable'] = df['pago variable'].astype(str).str.replace(r'[\$\.\s]', '', regex=True)
    df['pago variable'] = pd.to_numeric(df['pago variable'], errors='coerce').fillna(0)
    
    # Convertir fecha
    df['fecha día'] = pd.to_datetime(df['fecha día'], dayfirst=True, errors='coerce')
    
    return df

try:
    df_raw = load_data()

    # --- BANNER SUPERIOR ---
    st.markdown(f"""
        <div class="valdi-header">
            <div>
                <h1>Performance Outsourcing</h1>
                <p>VALDISHOPPER</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- FILTROS Y ACCIONES ---
    c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
    with c1:
        salas = ["Todas las Salas"] + sorted([str(s) for s in df_raw['local'].unique()])
        sala_sel = st.selectbox("SALA", options=salas)
    with c2:
        f_ini = st.date_input("DESDE", df_raw['fecha día'].min().date())
    with c3:
        f_fin = st.date_input("HASTA", df_raw['fecha día'].max().date())
    with c4:
        st.write("") # Espaciador
        st.button("📧 ENVIAR A PRESTADORES", type="primary", use_container_width=True)

    # Lógica de filtrado
    df = df_raw.copy()
    if sala_sel != "Todas las Salas":
        df = df[df['local'].astype(str) == sala_sel]
    df = df[(df['fecha día'].dt.date >= f_ini) & (df['fecha día'].dt.date <= f_fin)]
    
    df['cumple_meta'] = df['sku totales'] >= 200

    # --- MÉTRICAS (HTML DIRECTO) ---
    eficacia = (df['cumple_meta'].sum() / len(df) * 100) if len(df) > 0 else 0
    st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card"><div class="metric-title">Turnos</div><div class="metric-value">{len(df)}</div></div>
            <div class="metric-card"><div class="metric-title">Metas OK</div><div class="metric-value" style="color:#2ecc71;">{df['cumple_meta'].sum()}</div></div>
            <div class="metric-card"><div class="metric-title">Eficacia</div><div class="metric-value" style="color:{VALDI_PINK};">{eficacia:.1f}%</div></div>
            <div class="metric-card"><div class="metric-title">Incentivo Total</div><div class="metric-value">${df['pago variable'].sum():,.0f}</div></div>
        </div>
    """, unsafe_allow_html=True)

    # --- GRÁFICO (CON FONDO BLANCO) ---
    st.write("### Tendencia de Productividad")
    df_chart = df.groupby(df['fecha día'].dt.date).agg({'sku totales': 'sum', 'cumple_meta': 'mean'}).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_chart['fecha día'], y=df_chart['sku totales'], name="SKU", marker_color='rgba(13,27,62,0.1)'))
    fig.add_trace(go.Scatter(x=df_chart['fecha día'], y=df_chart['cumple_meta']*100, name="%", line=dict(color=VALDI_PINK, width=3), yaxis="y2"))
    
    fig.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        yaxis=dict(title="SKU Totales", gridcolor='#f0f0f0'),
        yaxis2=dict(title="% Meta", overlaying="y", side="right", range=[0, 100], showgrid=False),
        margin=dict(l=0, r=0, t=10, b=0), height=350, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- TABLA DETALLE ---
    st.write("### Detalle")
    df_tabla = df[['local', 'rut', 'fecha día', 'sku totales', 'pago variable']].copy()
    df_tabla['fecha día'] = df_tabla['fecha día'].dt.strftime('%d-%m-%Y')
    df_tabla.columns = ['SALA', 'RUT', 'FECHA', 'SKU', 'PAGO VARIABLE']
    
    st.dataframe(df_tabla.sort_values('FECHA', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error técnico: {e}")

