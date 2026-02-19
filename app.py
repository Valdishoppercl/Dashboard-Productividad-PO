import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIGURACIÓN ESTÉTICA (Basada en tu Index.html) ---
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

# --- FUNCIONES CORE (Traducción de tu .gs) ---

def normalizar_rut(rut):
    if not rut: return ""
    import re
    return re.sub(r'[^0-9k]', '', str(rut).lower())

@st.cache_data(ttl=600)
def load_all_data():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    # Cargar Hoja Principal
    raw_prod = sh.worksheet("Resumen Diario Outsourcing").get_all_values()
    df_prod = pd.DataFrame(raw_prod[1:], columns=raw_prod[0])
    
    # Cargar Hoja BUK
    raw_buk = sh.worksheet("BUK").get_all_values()
    df_buk = pd.DataFrame(raw_buk[1:], columns=raw_buk[0])
    
    return df_prod, df_buk

def enviar_reporte_smtp(destinatario, nombre, html_tabla, total_sku, total_pago):
    user = st.secrets["email"]["user"]
    password = st.secrets["email"]["password"]
    
    msg = MIMEMultipart()
    msg['From'] = f"Asignaciones Valdishopper <{user}>"
    msg['To'] = destinatario
    msg['Subject'] = f"📊 Detalle Gestión - {nombre}"
    
    # El mismo diseño de tu .gs
    html = f"""
    <div style="font-family:sans-serif; color:#333; max-width:600px; border:1px solid #eee; border-radius:10px; overflow:hidden;">
        <div style="background:{VALDI_NAVY}; color:white; padding:20px; border-bottom:4px solid {VALDI_PINK};">
            <h2 style="margin:0; font-size:18px;">Detalle de Gestión Operativa</h2>
            <p style="color:{VALDI_PINK}; margin:0; font-weight:bold; font-size:12px; letter-spacing:1px;">VALDISHOPPER</p>
        </div>
        <div style="padding:20px;">
            <p>Hola <b>{nombre}</b>,</p>
            {html_tabla}
            <div style="background:#f1f3f8; padding:15px; border-radius:8px; margin-top:15px;">
                <b>Total SKU:</b> {total_sku}<br>
                <b>Total Incentivo Variable:</b> ${total_pago:,.0f}
            </div>
        </div>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)

# --- PROCESAMIENTO ---

try:
    df_prod, df_buk = load_all_data()
    
    # Filtros laterales
    with st.sidebar:
        st.header("Filtros")
        locales = ["Todos"] + sorted(df_prod.iloc[:, 3].unique().tolist())
        f_local = st.selectbox("SALA", locales)
        f_inicio = st.date_input("DESDE", datetime.now())
        f_fin = st.date_input("HASTA", datetime.now())

    # Limpieza de datos (Índices idénticos a tu .gs)
    df_filt = df_prod.copy()
    # Convertir fecha
    df_filt.iloc[:, 0] = pd.to_datetime(df_filt.iloc[:, 0], dayfirst=True, errors='coerce')
    
    # Aplicar Filtros
    if f_local != "Todos":
        df_filt = df_filt[df_filt.iloc[:, 3] == f_local]
    df_filt = df_filt[(df_filt.iloc[:, 0].dt.date >= f_inicio) & (df_filt.iloc[:, 0].dt.date <= f_fin)]

    # Mapeo de columnas (sku: col 9, pago: col 11)
    df_filt['sku_val'] = pd.to_numeric(df_filt.iloc[:, 9].str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
    df_filt['pago_val'] = pd.to_numeric(df_filt.iloc[:, 11].str.replace(r'[^0-9,]', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0)
    df_filt['cumple_meta'] = df_filt['sku_val'] >= 200

    # --- MÉTRICAS (Igual a tus cards de Index.html) ---
    m1, m2, m3, m4 = st.columns(4)
    total_turnos = len(df_filt)
    metas_ok = df_filt['cumple_meta'].sum()
    eficacia = (metas_ok / total_turnos * 100) if total_turnos > 0 else 0
    total_pago = df_filt['pago_val'].sum()

    m1.metric("Turnos", total_turnos)
    m2.metric("Metas OK", metas_ok)
    m3.metric("Eficacia", f"{eficacia:.1f}%")
    m4.metric("Incentivo Total", f"${total_pago:,.0f}")

    # --- GRÁFICOS ---
    c1, c2 = st.columns([7, 5])
    
    with c1:
        st.write("Demanda vs Cumplimiento")
        df_daily = df_filt.groupby(df_filt.iloc[:, 0].dt.date).agg({'sku_val': 'sum', 'cumple_meta': 'mean'}).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_daily.iloc[:,0], y=df_daily['sku_val'], name="SKU", marker_color='rgba(13,27,62,0.2)'))
        fig.add_trace(go.Scatter(x=df_daily.iloc[:,0], y=df_daily['cumple_meta']*100, name="%", line=dict(color=VALDI_PINK, width=3)))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.write("Top 5 Salas")
        df_rank = df_filt.groupby(df_filt.iloc[:, 3])['cumple_meta'].mean().sort_values(ascending=False).head(5) * 100
        fig_rank = px.bar(df_rank, orientation='h', color_discrete_sequence=[VALDI_NAVY])
        fig_rank.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), showlegend=False, xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_rank, use_container_width=True)

    # --- ACCIONES ---
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([2, 8])
    
    if col_btn1.button("📧 ENVIAR A PRESTADORES", type="primary"):
        # Lógica de cruce con BUK idéntica a enviarReportesPersonalizados()
        df_buk['rut_limpio'] = df_buk.iloc[:, 0].apply(normalizar_rut)
        df_filt['rut_limpio'] = df_filt.iloc[:, 4].apply(normalizar_rut)
        
        df_merge = pd.merge(df_filt, df_buk, on='rut_limpio', how='inner')
        
        enviados = 0
        for rut, grupo in df_merge.groupby('rut_limpio'):
            email = grupo.iloc[0, -1] # Asumiendo columna D es email
            nombre = f"{grupo.iloc[0, -3]} {grupo.iloc[0, -2]}"
            
            # Crear tabla HTML para el mail
            tabla_html = grupo[['sku_val', 'pago_val']].to_html(classes='table', index=False)
            
            try:
                enviar_reporte_smtp(email, nombre, tabla_html, grupo['sku_val'].sum(), grupo['pago_val'].sum())
                enviados += 1
            except: pass
            
        st.success(f"Se enviaron {enviados} reportes personalizados.")

    # --- TABLA ---
    st.dataframe(df_filt.iloc[:, [3, 4, 0, 9, 11]], use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
