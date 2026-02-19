import streamlit as st
import pandas as pd
import gspread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Función de limpieza de RUT (Crucial para Valdishopper)
def limpiar_rut(rut):
    return str(rut).lower().replace(".", "").replace("-", "").strip()

# 2. Conexión segura a Google Sheets
def cargar_datos():
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
    
    # Abre tu planilla principal
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    
    # Carga de pestañas específicas
    df_prod = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df_buk = pd.DataFrame(sh.worksheet("BUK").get_all_records())
    
    return df_prod, df_buk

# 3. Interfaz del Dashboard
st.set_page_config(page_title="Valdishopper PickerPro", layout="wide")
st.title("📊 Performance PickerPro")

try:
    df_prod, df_buk = cargar_datos()
    
    # Aplicar normalización de RUT
    df_prod['rut_fijo'] = df_prod['RUT'].apply(limpiar_rut)
    df_buk['rut_fijo'] = df_buk['Colaborador - Número de Documento'].apply(limpiar_rut)
    
    # Mostrar métricas en tarjetas
    st.write("Datos cargados correctamente.")
    
except Exception as e:
    st.error(f"Error de conexión: {e}")