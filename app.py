import streamlit as st
import pandas as pd
import ezdxf
import io
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="TopoConverter Pro", page_icon="🏗️")

# Acceder a las llaves (deben estar en la configuración de Streamlit Cloud)
# NO pongas las URL/Keys reales aquí, pon los NOMBRES de las variables
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. LÓGICA DE NEGOCIO Y CONVERSIÓN ---

def registrar_uso(puntos, nombre):
    try:
        data = {
            "puntos_procesados": puntos,
            "nombre_archivo": nombre,
            "formato_archivo": nombre.split('.')[-1]
        }
        supabase.table("registros_uso").insert(data).execute()
    except Exception as e:
        st.error(f"Error al registrar en base de datos: {e}")

def generar_dxf(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Se crean capas para que el topógrafo pueda prender/apagar en AutoCAD
    doc.layers.new('PUNTOS_TOPOGRAFICOS', dxfattribs={'color': 2}) # Amarillo
    doc.layers.new('TEXTO_PUNTOS', dxfattribs={'color': 7})       # Blanco/Negro
    
    for _, row in df.iterrows():
        try:
            # Asegúrate de que las columnas en el Excel se llamen exactamente Punto, X, Y, Z
            x, y, z = float(row['X']), float(row['Y']), float(row['Z'])
            punto_nombre = str(row['Punto'])
            desc = str(row.get('Descripcion', ''))

            # Dibujar Punto
            msp.add_point((x, y, z), dxfattribs={'layer': 'PUNTOS_TOPOGRAFICOS'})
            
            # Dibujar Texto
            msp.add_text(f"{punto_nombre} {desc}", 
                         dxfattribs={'height': 0.2, 'layer': 'TEXTO_PUNTOS'}
                        ).set_pos((x + 0.1, y + 0.1, z))
        except Exception:
            continue
            
    out = io.StringIO()
    doc.write(out)
    return out.getvalue()

# --- 3. INTERFAZ DE USUARIO ---
st.title("🏗️ Convertidor: Excel a AutoCAD (DXF)")
st.write("Herramienta profesional para topografía.")

archivo = st.file_uploader("Sube tu planilla (Excel o CSV)", type=['xlsx', 'csv'])

if archivo:
    # Leer datos
    if archivo.name.endswith('xlsx'):
        df = pd.read_excel(archivo)
    else:
        df = pd.read_csv(archivo)
    
    st.write("Vista previa de los datos detectados:")
    st.dataframe(df.head())

    if st.button("🚀 Generar y Registrar"):
        if 'X' in df.columns and 'Y' in df.columns:
            # Generar el archivo
            dxf_string = generar_dxf(df)
            
            # Registrar en Supabase
            registrar_uso(len(df), archivo.name)
            
            st.success(f"¡Listo! {len(df)} puntos procesados.")
            
            # Botón de descarga
            st.download_button(
                label="⬇️ Descargar archivo DXF",
                data=dxf_string,
                file_name=f"LEV_{archivo.name.split('.')[0]}.dxf",
                mime="application/dxf"
            )
        else:
            st.error("Error: El archivo debe tener columnas llamadas 'X' y 'Y'.")
