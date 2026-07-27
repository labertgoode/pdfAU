import os
import io
import zipfile
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

st.set_page_config(page_title="Generador de Reconocimientos", layout="centered")

st.title("Sistema de Generacion de Reconocimientos")
st.write("Procesamiento volatil en memoria. Cumplimiento de no persistencia (SGSI).")

def obtener_iniciales(nombre):
    if pd.isna(nombre):
        return "SIN_NOMBRE"
    palabras = str(nombre).split()
    return "".join([palabra[0].upper() for palabra in palabras if palabra])

uploaded_excel = st.file_uploader("Cargar archivo Excel (.xlsx)", type=["xlsx"])
uploaded_pdf = st.file_uploader("Cargar Plantilla PDF Base (.pdf)", type=["pdf"])

plantilla_tiene_titulo = st.checkbox("La plantilla ya incluye el titulo del webinar")

# ==========================================
# NUEVA SECCIÓN DE CALIBRACIÓN INTERACTIVA
# ==========================================
with st.expander("Ajustes de Calibración Visual (Modificar si cambió el diseño del PDF)"):
    st.info("Usa estos controles para mover el texto si la nueva plantilla tiene las líneas en otra posición. Valores menores = más abajo.")
    col1, col2 = st.columns(2)
    with col1:
        # Modifiqué el valor por defecto a 250 asumiendo que bajó un poco, pero puedes ajustarlo.
        POSICION_Y_NOMBRE = st.slider("Altura del Nombre (Y)", min_value=0, max_value=600, value=250, step=5)
        MAX_ANCHO_LINEA = st.slider("Ancho máx. Nombre", min_value=200, max_value=700, value=480, step=10)
        tamanio_fuente_nombre_base = st.slider("Tamaño Letra Nombre", min_value=10, max_value=50, value=24)
    with col2:
        POSICION_Y_TITULO = st.slider("Altura del Título (Y)", min_value=0, max_value=600, value=180, step=5)
        DESFASE_X = st.slider("Desfase Horizontal (X)", min_value=-150, max_value=150, value=0, step=5, help="Negativo = Izquierda, Positivo = Derecha")
        tamanio_fuente_titulo_base = st.slider("Tamaño Letra Título", min_value=10, max_value=50, value=16)
# ==========================================

if uploaded_excel and uploaded_pdf:
    if st.button("Procesar"):
        try:
            # Extraer el nombre del archivo y formatearlo con comillas
            file_name = uploaded_excel.name.replace(".xlsx", "")
            nombre_platica = f'"{file_name}"'

            df = pd.read_excel(uploaded_excel, sheet_name="Aprobados", usecols="B")
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)
                control_duplicados = {}

                # Aplicamos el ajuste horizontal
                CENTRO_X = (PAGE_WIDTH / 2) + DESFASE_X

                for index, row in df.iterrows():
                    nombre_participante = row.iloc[0]
                    if pd.isna(nombre_participante):
                        continue

                    nombre_str = str(nombre_participante).strip()
                    iniciales = obtener_iniciales(nombre_str)
                    
                    if iniciales in control_duplicados:
                        control_duplicados[iniciales] += 1
                        nombre_archivo_pdf = f"Reconocimiento_{iniciales}_{control_duplicados[iniciales]}.pdf"
                    else:
                        control_duplicados[iniciales] = 0
                        nombre_archivo_pdf = f"Reconocimiento_{iniciales}.pdf"

                    temp_pdf_buffer = io.BytesIO()
                    c = canvas.Canvas(temp_pdf_buffer, pagesize=landscape(letter))
                    
                    # 1. DIBUJAR EL NOMBRE (Auto-ajustable a la linea negra)
                    tamanio_fuente_nombre = tamanio_fuente_nombre_base
                    while c.stringWidth(nombre_str, "Helvetica-Bold", tamanio_fuente_nombre) > MAX_ANCHO_LINEA and tamanio_fuente_nombre > 10:
                        tamanio_fuente_nombre -= 1 
                    
                    c.setFont("Helvetica-Bold", tamanio_fuente_nombre)
                    c.setFillColor(HexColor("#000000")) # Nombre en Negro
                    c.drawCentredString(CENTRO_X, POSICION_Y_NOMBRE, nombre_str)
                    
                    # 2. DIBUJAR EL TITULO (Si la casilla no esta marcada)
                    if not plantilla_tiene_titulo:
                        tamanio_fuente_titulo = tamanio_fuente_titulo_base
                        # Evitar que el titulo se salga de los margenes
                        while c.stringWidth(nombre_platica, "Helvetica-Bold", tamanio_fuente_titulo) > 500 and tamanio_fuente_titulo > 10:
                            tamanio_fuente_titulo -= 1

                        c.setFont("Helvetica-Bold", tamanio_fuente_titulo)
                        c.setFillColor(HexColor("#000000")) # Titulo en Negro oscuro
                        c.drawCentredString(CENTRO_X, POSICION_Y_TITULO, nombre_platica)
                        
                    c.save()
                    
                    # FUSION EN MEMORIA RAM
                    temp_pdf_buffer.seek(0)
                    text_reader = PdfReader(temp_pdf_buffer)
                    
                    uploaded_pdf.seek(0)
                    template_reader = PdfReader(uploaded_pdf)
                    
                    writer = PdfWriter()
                    page = template_reader.pages[0]
                    page.merge_page(text_reader.pages[0])
                    writer.add_page(page)
                    
                    output_pdf_buffer = io.BytesIO()
                    writer.write(output_pdf_buffer)
                    output_pdf_buffer.seek(0)
                    
                    zip_file.writestr(nombre_archivo_pdf, output_pdf_buffer.getvalue())

            zip_buffer.seek(0)
            
            st.success(f"Proceso finalizado. Registros procesados: {len(control_duplicados)}")
            
            st.download_button(
                label="Descargar paquete de reconocimientos (.ZIP)",
                data=zip_buffer,
                file_name=f"Reconocimientos_{file_name}.zip",
                mime="application/zip"
            )
            
            print(f"INFO: [AUDIT] Ejecucion exitosa. Dataset: {file_name}. Items: {len(control_duplicados)}.")

        except Exception as e:
            st.error("Error en el procesamiento de archivos. Verifique el formato.")
            print(f"ERROR: [AUDIT] Fallo en ejecucion: {str(e)}")
