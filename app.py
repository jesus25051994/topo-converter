import streamlit as st
import pandas as pd
import ezdxf
import io
import math
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="TopoConverter Pro", page_icon="🏗️")
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. FUNCIONES TÉCNICAS ---

def calcular_rumbo(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    distancia = math.sqrt(dx**2 + dy**2)
    return distancia

def registrar_uso(puntos, nombre):
    try:
        supabase.table("registros_uso").insert({
            "puntos_procesados": puntos,
            "nombre_archivo": nombre,
            "formato_archivo": "CSV_MICRO"
        }).execute()
    except: pass

def generar_dxf_pro(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Definición de capas por descripción
    capas = {
        'LP': 1,   # Rojo para Perímetro
        'PTA': 4,  # Cian para puntos de terreno
        'STN': 3,  # Verde para estaciones
        'DEFAULT': 7 # Blanco
    }

    puntos_cuadro = []

    for i, row in df.iterrows():
        try:
            p, y, x, z = row['Punto'], float(row['Y']), float(row['X']), float(row['Z'])
            desc = str(row['Desc']).upper()
            
            # Determinar capa según descripción
            layer_name = f"TOPO_{desc}"
            if layer_name not in doc.layers:
                color = capas.get(desc, capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            # Dibujar Punto y Texto
            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(f"{int(p)}", dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x+0.1, y+0.1, z))

            # Guardar datos para el cuadro si es LP (Límite de Propiedad)
            if 'LP' in desc:
                puntos_cuadro.append({'p': int(p), 'x': x, 'y': y})

        except: continue

    return doc, puntos_cuadro

# --- 3. INTERFAZ ---
st.title("🏗️ TopoConverter Pro: MicroSurvey Edition")
st.info("Formato detectado: Punto, Norte, Este, Elevación, Descripción")

archivo = st.file_uploader("Sube el TXT/CSV de MicroSurvey", type=['txt', 'csv'])

if archivo:
    # Leer el archivo con el formato P,N,E,Z,D que nos pasó
    df = pd.read_csv(archivo, names=['Punto', 'Y', 'X', 'Z', 'Desc'])
    st.dataframe(df.head())

    if st.button("🚀 Generar DXF + Cuadro de Construcción"):
        doc, puntos_cuadro = generar_dxf_pro(df)
        
        # Lógica del Cuadro de Construcción
        if len(puntos_cuadro) > 1:
            st.subheader("📊 Cuadro de Construcción (Vista Previa)")
            tabla_datos = []
            for i in range(len(puntos_cuadro) - 1):
                p1 = puntos_cuadro[i]
                p2 = puntos_cuadro[i+1]
                dist = calcular_rumbo(p1['x'], p1['y'], p2['x'], p2['y'])
                tabla_datos.append({
                    "De": p1['p'], "A": p2['p'], 
                    "Distancia (m)": round(dist, 3),
                    "Coord X": round(p1['x'], 3), "Coord Y": round(p1['y'], 3)
                })
            st.table(tabla_datos)
        
        # Preparar descarga
        out = io.StringIO()
        doc.write(out)
        
        registrar_uso(len(df), archivo.name)
        
        st.download_button(
            label="⬇️ Descargar DXF con Capas Inteligentes",
            data=out.getvalue(),
            file_name="levantamiento_organizado.dxf",
            mime="application/dxf"
        )
