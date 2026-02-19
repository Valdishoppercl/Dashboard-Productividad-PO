import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Performance Outsourcing", layout="wide", initial_sidebar_state="collapsed")

VALDI_NAVY = "#0d1b3e"
VALDI_PINK = "#d63384"

# --- CSS DE ALTA PRIORIDAD PARA BLINDAR EL DISEÑO ---
st.markdown(f"""
    <style>
    /* Forzar fondo claro en toda la app */
    .stApp {{ background-color: #f8f9fc !important; }}
    
    /* Ocultar elementos innecesarios de Streamlit */
    #MainMenu, footer, header {{ visibility: hidden !important; }}

    /* Banner Superior Valdishopper */
    .valdi-banner {{
        background-color: {VALDI_NAVY} !important;
        padding: 30px 40px;
        border-bottom: 6px solid {VALDI_PINK} !important;
        border-radius: 10px;
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: white !important;
    }}
    .valdi-banner h1 {{ color: white !important; margin: 0 !important; font-size: 28px !important; }}
    .valdi-banner p {{ color: {VALDI_PINK} !important; margin: 0 !important; font-weight: bold !important; }}

    /* Tarjetas de Métricas Blancas */
    .metric-container {{
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 30px;
    }}
    .metric-card {{
        background-color: white !important;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
        text-align: center;
        flex: 1;
        border: 1px solid #eee !important;
    }}
    .metric-title {{ color: #7f8c8d !important; font-size: 0.9rem !important; font-weight: bold !important; text-transform: uppercase; margin-bottom: 10px; }}
    .metric-value {{ color: {VALDI_NAVY} !important; font-size: 2.2rem !important; font-weight: 900 !important; }}

    /* Fix para Filtros y Labels (Forzar color negro/navy sobre fondo claro) */
    label, .stSelectbox, .stDateInput {{ color: {VALDI_NAVY} !important; font-weight: 600 !important; }}
    div[data-baseweb="select"] {{ background-color: white !important; border-radius: 8px !important; }}
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    df = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    
    # Limpieza de datos (Evitar el 0 de más en SKU)
    df['sku totales'] = df['sku totales'].astype(str).str.replace(r'[\.\,]', '', regex=True)
    df['sku totales'] = pd.to_numeric(df['sku totales'], errors='coerce').fillna(0).astype(int)
    
    df['pago variable'] = df['pago variable'].astype(str).str.replace(r'[\$\.\s]', '', regex=True)
    df['pago variable'] = pd.to_numeric(df['pago variable'], errors='coerce').fillna(0)
    
    df['fecha día'] = pd.to_datetime(df['fecha día'], dayfirst=True, errors='coerce')
    return df

try:
    df_raw = load_data()

    # --- HEADER SUPERIOR ---
    st.markdown(f"""
        <div class="valdi-banner">
            <div>
                <h1>Performance Outsourcing</h1>
                <p>VALDISHOPPER</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- FILTROS Y BOTÓN DE ENVÍO ---
    c_f1, c_f2, c_f3, c_btn = st.columns([3, 2, 2, 3])
    with c_f1:
        salas = ["Todas las Salas"] + sorted([str(s) for s in df_raw['local'].unique()])
        sala_sel = st.selectbox("SALA", options=salas)
    with c_f2:
        f_inicio = st.date_input("DESDE", df_raw['fecha día'].min().date())
    with c_f3:
        f_fin = st.date_input("HASTA", df_raw['fecha día'].max().date())
    with c_btn:
        st.write("") # Espaciador
        if st.button("📧 ENVIAR A PRESTADORES", use_container_width=True):
            st.info("Iniciando proceso de envío masivo...")

    # Lógica de filtrado
    df = df_raw.copy()
    if sala_sel != "Todas las Salas":
        df = df[df['local'].astype(str) == sala_sel]
    df = df[(df['fecha día'].dt.date >= f_inicio) & (df['fecha día'].dt.date <= f_fin)]
    
    df['cumple_meta'] = df['sku totales'] >= 200

    # --- MÉTRICAS (HTML DIRECTO PARA EVITAR DEFORMACIÓN) ---
    eficacia = (df['cumple_meta'].sum() / len(df) * 100) if len(df) > 0 else 0
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card"><div class="metric-title">Turnos</div><div class="metric-value">{len(df)}</div></div>
            <div class="metric-card"><div class="metric-title">Metas OK</div><div class="metric-value" style="color:#2ecc71;">{df['cumple_meta'].sum()}</div></div>
            <div class="metric-card"><div class="metric-title">Eficacia</div><div class="metric-value" style="color:{VALDI_PINK};">{eficacia:.1f}%</div></div>
            <div class="metric-card"><div class="metric-title">Incentivo Total</div><div class="metric-value">${df['pago variable'].sum():,.0f}</div></div>
        </div>
    """, unsafe_allow_html=True)

    # --- GRÁFICO ---
    st.markdown("<h3 style='color:#0d1b3e;'>Tendencia de Productividad</h3>", unsafe_allow_html=True)
    df_chart = df.groupby(df['fecha día'].dt.date).agg({'sku totales': 'sum', 'cumple_meta': 'mean'}).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_chart['fecha día'], y=df_chart['sku totales'], name="SKU", marker_color='rgba(13,27,62,0.1)'))
    fig.add_trace(go.Scatter(x=df_chart['fecha día'], y=df_chart['cumple_meta']*100, name="%", line=dict(color=VALDI_PINK, width=3), yaxis="y2"))
    
    fig.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        yaxis=dict(title="SKU Totales", gridcolor='#eee'),
        yaxis2=dict(title="% Meta", overlaying="y", side="right", range=[0, 100], showgrid=False),
        margin=dict(l=0, r=0, t=10, b=0), height=350, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- TABLA DETALLE ---
    st.markdown("<h3 style='color:#0d1b3e;'>Detalle de Gestión</h3>", unsafe_allow_html=True)
    df_tabla = df[['local', 'rut', 'fecha día', 'sku totales', 'pago variable']].copy()
    df_tabla['fecha día'] = df_tabla['fecha día'].dt.strftime('%d-%m-%Y')
    df_tabla.columns = ['SALA', 'RUT', 'FECHA', 'SKU', 'PAGO VARIABLE']
    
    st.dataframe(df_tabla.sort_values('FECHA', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
