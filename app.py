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
st.write("Procesamiento volatil en memoria. Cumplimiento de no persistencia.")


def obtener_iniciales(nombre):
    if pd.isna(nombre):
        return "SIN_NOMBRE"
    palabras = str(nombre).split()
    return "".join([palabra[0].upper() for palabra in palabras if palabra])


uploaded_excel = st.file_uploader("Cargar archivo Excel (.xlsx)", type=["xlsx"])
uploaded_pdf = st.file_uploader("Cargar Plantilla PDF Base (.pdf)", type=["pdf"])

# Casilla de verificacion para el titulo en la plantilla
plantilla_tiene_titulo = st.checkbox("La plantilla ya incluye el titulo del webinar")

if uploaded_excel and uploaded_pdf:
    if st.button("Procesar"):
        try:
            file_name = uploaded_excel.name.replace(".xlsx", "")
            nombre_platica = f"Webinar {file_name}"

            df = pd.read_excel(uploaded_excel, sheet_name="Aprobados", usecols="B")
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)
                control_duplicados = {}

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

                    # Ajuste dinamico del tamaño de fuente segun la longitud del nombre
                    longitud_nombre = len(nombre_str)
                    if longitud_nombre > 35:
                        tamanio_fuente = 16
                    elif longitud_nombre > 25:
                        tamanio_fuente = 20
                    else:
                        tamanio_fuente = 24

                    c.setFont("Helvetica-Bold", tamanio_fuente)
                    c.drawCentredString(PAGE_WIDTH / 2, 300, nombre_str)

                    # Logica condicional para la impresion del titulo
                    if not plantilla_tiene_titulo:
                        c.setFont("Helvetica", 14)
                        c.setFillColor(HexColor("#008080"))
                        c.drawCentredString(PAGE_WIDTH / 2, 230, nombre_platica)

                    c.save()

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

            st.success(f"Proceso finalizado. Registros: {len(control_duplicados)}")

            st.download_button(
                label="Descargar paquete (.ZIP)",
                data=zip_buffer,
                file_name=f"Reconocimientos_{file_name}.zip",
                mime="application/zip"
            )

            print(f"INFO: [AUDIT] Ejecucion exitosa. Dataset: {file_name}. Items: {len(control_duplicados)}.")

        except Exception as e:
            st.error("Error en el procesamiento de archivos.")
            print(f"ERROR: [AUDIT] Fallo en ejecucion: {str(e)}")