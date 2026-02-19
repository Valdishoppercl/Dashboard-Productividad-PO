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

# --- FUNCIONES DE LIMPIEZA Y CARGA ---
def limpiar_rut(rut):
    return str(rut).lower().replace(".", "").replace("-", "").strip()

@st.cache_data(ttl=600) # Cache para no saturar la API de Google
def cargar_datos():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    # Cargar y limpiar Productividad
    df_prod = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df_prod['rut_fijo'] = df_prod['RUT'].apply(limpiar_rut)
    
    # Cargar y limpiar BUK
    df_buk = pd.DataFrame(sh.worksheet("BUK").get_all_records())
    df_buk['rut_fijo'] = df_buk['Colaborador - Número de Documento'].apply(limpiar_rut)
    
    return df_prod, df_buk

# --- INTERFAZ DE USUARIO ---
try:
    df_prod, df_buk = cargar_datos()

    # Sidebar: Filtros
    st.sidebar.header("Filtros de Gestión")
    salas_disponibles = sorted(df_prod['Local'].unique())
    sala_select = st.sidebar.multiselect("Seleccionar Sala(s)", options=salas_disponibles, default=salas_disponibles[0])
    
    # Filtrar datos
    df_filtrado = df_prod[df_prod['Local'].isin(sala_select)] if sala_select else df_prod

    # Encabezado
    st.markdown(f"<h1 style='color:{NAVY_VALDI};'>🚀 Performance PickerPro</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{PINK_VALDI}; font-weight:bold;'>VALDISHOPPER - Panel de Control</p>", unsafe_allow_html=True)

    # --- MÉTRICAS (KPIs) ---
    col1, col2, col3, col4 = st.columns(4)
    total_turnos = len(df_filtrado)
    # Suponiendo que la meta es SKU >= 200 según tus capturas anteriores
    metas_ok = len(df_filtrado[df_filtrado['SKU Totales'] >= 200])
    eficacia = (metas_ok / total_turnos * 100) if total_turnos > 0 else 0
    pago_total = df_filtrado['Pago Variable'].sum() if 'Pago Variable' in df_filtrado.columns else 0

    col1.metric("Turnos Totales", f"{total_turnos}")
    col2.metric("Metas Cumplidas", f"{metas_ok}", delta_color="normal")
    col3.metric("% Eficacia", f"{eficacia:.1f}%")
    col4.metric("Incentivo Total", f"${pago_total:,.0f}")

    # --- GRÁFICOS ---
    st.markdown("### Tendencia de Productividad")
    fig = px.bar(df_filtrado, x='Fecha', y='SKU Totales', 
                 color_discrete_sequence=[NAVY_VALDI],
                 title="Volumen de SKU por Fecha")
    st.plotly_chart(fig, use_container_width=True)

    # --- DETALLE Y ACCIONES ---
    st.markdown("### Detalle de Gestión")
    st.dataframe(df_filtrado[['Local', 'RUT', 'Fecha', 'SKU Totales']].sort_values(by='Fecha', ascending=False), use_container_width=True)

    if st.button("📧 Enviar Reportes Seleccionados", type="primary"):
        st.info("Iniciando motor de envío masivo desde asignaciones@valdishopper.com...")
        # Aquí insertaremos la lógica de envío SMTP en el siguiente paso

except Exception as e:
    st.error(f"Error al procesar el dashboard: {e}")
