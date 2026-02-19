import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Valdishopper PickerPro", layout="wide")

NAVY_VALDI = "#0d1b3e"
PINK_VALDI = "#d63384"

# --- FUNCIONES DE SOPORTE ---
def limpiar_rut(rut):
    return str(rut).lower().replace(".", "").replace("-", "").strip()

@st.cache_data(ttl=600)
def cargar_datos():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    # Cargar y normalizar nombres de columnas a minúsculas
    df_prod = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df_prod.columns = df_prod.columns.str.strip().str.lower()
    df_prod['rut_fijo'] = df_prod['rut'].apply(limpiar_rut)
    
    df_buk = pd.DataFrame(sh.worksheet("BUK").get_all_records())
    df_buk.columns = df_buk.columns.str.strip().str.lower()
    # Nombre exacto según tu hoja BUK: 'colaborador - número de documento'
    df_buk['rut_fijo'] = df_buk['colaborador - número de documento'].apply(limpiar_rut)
    
    return df_prod, df_buk

def enviar_mail_profesional(destinatario, nombre, html_tabla):
    user = st.secrets["email"]["user"]
    password = st.secrets["email"]["password"]
    
    msg = MIMEMultipart()
    msg['From'] = f"Asignaciones Valdishopper <{user}>"
    msg['To'] = destinatario
    msg['Subject'] = f"📊 Reporte de Gestión - {nombre}"
    
    cuerpo_html = f"""
    <html>
      <body style="font-family: sans-serif; color: #333;">
        <div style="background-color: {NAVY_VALDI}; padding: 20px; color: white;">
          <h2 style="margin:0;">Resumen de Gestión Operativa</h2>
          <p style="color: {PINK_VALDI}; margin:0;">VALDISHOPPER</p>
        </div>
        <div style="padding: 20px;">
          <p>Hola <b>{nombre}</b>,</p>
          <p>Este es el detalle de tu producción acumulada en el periodo seleccionado:</p>
          {html_tabla}
          <br>
          <p style="font-size: 12px; color: #777;">Envío automático. Favor no responder.</p>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(cuerpo_html, 'html'))
    
    try:
        with smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except:
        return False

# --- LÓGICA DEL DASHBOARD ---
try:
    df_prod, df_buk = cargar_datos()
    
    # Nombres de columnas según el error detectado
    C_FECHA = 'fecha día' 
    C_SKU = 'sku totales'
    C_PAGO = 'pago variable'
    C_LOCAL = 'local'

    # Filtros en Sidebar
    st.sidebar.markdown(f"<h2 style='color:{NAVY_VALDI};'>Filtros PickerPro</h2>", unsafe_allow_html=True)
    salas = sorted(df_prod[C_LOCAL].unique())
    sala_sel = st.sidebar.multiselect("Seleccionar Sala(s)", options=salas, default=salas)
    
    df_filt = df_prod[df_prod[C_LOCAL].isin(sala_sel)].copy()

    # Limpieza numérica
    df_filt[C_SKU] = pd.to_numeric(df_filt[C_SKU].astype(str).str.replace('.', ''), errors='coerce').fillna(0)
    df_filt[C_PAGO] = pd.to_numeric(df_filt[C_PAGO].astype(str).str.replace(r'[\$\.]', '', regex=True), errors='coerce').fillna(0)

    # UI Principal
    st.markdown(f"<h1 style='color:{NAVY_VALDI};'>🚀 Performance PickerPro</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{PINK_VALDI}; font-weight:bold;'>Dashboard Operativo | Valdishopper</p>", unsafe_allow_html=True)

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    turnos = len(df_filt)
    metas = len(df_filt[df_filt[C_SKU] >= 200])
    eficacia = (metas / turnos * 100) if turnos > 0 else 0
    pago = df_filt[C_PAGO].sum()

    k1.metric("Turnos Totales", f"{turnos}")
    k2.metric("Metas Cumplidas", f"{metas}")
    k3.metric("% Eficacia", f"{eficacia:.1f}%")
    k4.metric("Incentivo Total", f"${pago:,.0f}")

    # Gráfico Corregido con 'fecha día'
    st.markdown("### Tendencia de Productividad por Fecha")
    fig = px.bar(df_filt, x=C_FECHA, y=C_SKU, color_discrete_sequence=[NAVY_VALDI], 
                 labels={C_FECHA: 'Fecha de Turno', C_SKU: 'Total SKU'})
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    if st.button("📧 Enviar Reportes Personalizados (SMTP)", type="primary"):
        # Unir con BUK
        df_envio = pd.merge(df_filt, df_buk[['rut_fijo', 'colaborador - nombre', 'colaborador - email']], 
                            on='rut_fijo', how='left')
        
        agrupados = df_envio.groupby('rut_fijo')
        enviados = 0
        progreso = st.progress(0)
        
        for i, (rut, grupo) in enumerate(agrupados):
            email = grupo['colaborador - email'].iloc[0]
            nombre = grupo['colaborador - nombre'].iloc[0]
            
            if pd.notna(email) and email != "":
                # Seleccionar columnas existentes para la tabla del mail
                tabla_html = grupo[[C_FECHA, C_LOCAL, C_SKU, C_PAGO]].to_html(index=False)
                if enviar_mail_profesional(email, nombre, tabla_html):
                    enviados += 1
            progreso.progress((i + 1) / len(agrupados))
            
        st.success(f"Finalizado: {enviados} correos enviados desde asignaciones@valdishopper.com.")

    st.dataframe(df_filt, use_container_width=True)

except Exception as e:
    st.error(f"Error crítico: {e}")
