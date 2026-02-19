import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Valdishopper PickerPro", layout="wide")

# Colores corporativos Valdishopper
NAVY_VALDI = "#0d1b3e"
PINK_VALDI = "#d63384"

# --- FUNCIONES DE SOPORTE ---

def limpiar_rut(rut):
    """Limpia puntos, guiones y espacios del RUT."""
    return str(rut).lower().replace(".", "").replace("-", "").strip()

@st.cache_data(ttl=600)
def cargar_datos():
    """Carga datos desde Google Sheets usando la cuenta de servicio streamlit-bot."""
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    
    # Abrir planilla principal
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    # 1. Cargar Productividad
    df_prod = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df_prod.columns = df_prod.columns.str.strip().str.lower() # Normalizar a minúsculas
    df_prod['rut_fijo'] = df_prod['rut'].apply(limpiar_rut)
    
    # 2. Cargar BUK (Base de correos)
    df_buk = pd.DataFrame(sh.worksheet("BUK").get_all_records())
    df_buk.columns = df_buk.columns.str.strip().str.lower()
    # Usar el nombre de columna detectado en la hoja BUK
    col_rut_buk = 'colaborador - número de documento'
    df_buk['rut_fijo'] = df_buk[col_rut_buk].apply(limpiar_rut)
    
    return df_prod, df_buk

def enviar_mail_profesional(destinatario, nombre, html_tabla):
    """Envía el correo usando SMTP con la cuenta asignaciones@valdishopper.com."""
    user = st.secrets["email"]["user"]
    password = st.secrets["email"]["password"] # Tu código: inml wbuv zvos rdur
    
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
          <p style="font-size: 12px; color: #777;">Este es un envío automático. Por favor no respondas a este mensaje.</p>
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
    except Exception as e:
        st.error(f"Error enviando a {destinatario}: {e}")
        return False

# --- LÓGICA DEL DASHBOARD ---

try:
    df_prod, df_buk = cargar_datos()
    
    # Sidebar: Filtros
    st.sidebar.markdown(f"<h2 style='color:{NAVY_VALDI};'>Filtros PickerPro</h2>", unsafe_allow_html=True)
    salas = sorted(df_prod['local'].unique())
    sala_sel = st.sidebar.multiselect("Seleccionar Sala(s)", options=salas, default=salas)
    
    # Filtrar datos por sala
    df_filt = df_prod[df_prod['local'].isin(sala_sel)].copy()

    # Nombres de columnas clave (normalizados a minúsculas)
    c_sku = 'sku totales'
    c_pago = 'pago variable'

    # Limpieza numérica: quitar puntos de miles y convertir a número
    df_filt[c_sku] = pd.to_numeric(df_filt[c_sku].astype(str).str.replace('.', ''), errors='coerce').fillna(0)
    df_filt[c_pago] = pd.to_numeric(df_filt[c_pago].astype(str).str.replace(r'[\$\.]', '', regex=True), errors='coerce').fillna(0)

    # Encabezado Principal
    st.markdown(f"<h1 style='color:{NAVY_VALDI};'>🚀 Performance PickerPro</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{PINK_VALDI}; font-weight:bold;'>Dashboard Operativo | Valdishopper</p>", unsafe_allow_html=True)

    # --- KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    turnos = len(df_filt)
    metas = len(df_filt[df_filt[c_sku] >= 200]) # Meta estándar 200 SKU
    eficacia = (metas / turnos * 100) if turnos > 0 else 0
    pago = df_filt[c_pago].sum()

    k1.metric("Turnos Totales", f"{turnos}")
    k2.metric("Metas Cumplidas", f"{metas}")
    k3.metric("% Eficacia", f"{eficacia:.1f}%")
    k4.metric("Incentivo Total", f"${pago:,.0f}")

    # --- GRÁFICO ---
    st.markdown("### Tendencia de Productividad por Fecha")
    fig = px.bar(df_filt, x='fecha', y=c_sku, color_discrete_sequence=[NAVY_VALDI], 
                 labels={'fecha': 'Fecha de Turno', c_sku: 'Total SKU'})
    st.plotly_chart(fig, use_container_width=True)

    # --- ENVÍO DE REPORTES ---
    st.markdown("---")
    st.subheader("📬 Comunicación con Prestadores")
    
    if st.button("📧 Enviar Reportes Personalizados (SMTP)", type="primary"):
        # Unir producción con BUK para obtener correos
        df_envio = pd.merge(df_filt, df_buk[['rut_fijo', 'colaborador - nombre', 'colaborador - email']], 
                            on='rut_fijo', how='left')
        
        # Agrupar por RUT para enviar un solo correo con todos sus turnos
        agrupados = df_envio.groupby('rut_fijo')
        enviados = 0
        
        progreso = st.progress(0)
        total = len(agrupados)
        
        for i, (rut, grupo) in enumerate(agrupados):
            email = grupo['colaborador - email'].iloc[0]
            nombre = grupo['colaborador - nombre'].iloc[0]
            
            if pd.notna(email) and email != "":
                # Crear tabla HTML para el cuerpo del correo
                tabla_html = grupo[['fecha', 'local', c_sku, c_pago]].to_html(index=False, classes='table')
                exito = enviar_mail_profesional(email, nombre, tabla_html)
                if exito: enviados += 1
            
            progreso.progress((i + 1) / total)
            
        st.success(f"Proceso finalizado: {enviados} correos enviados desde asignaciones@valdishopper.com.")

    # Mostrar tabla de datos al final
    st.markdown("### Detalle de Registros")
    st.dataframe(df_filt, use_container_width=True)

except Exception as e:
    st.error(f"Error crítico en el dashboard: {e}")
