import streamlit as st
import pandas as pd
import ezdxf
import io
import math
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN DE PÁGINA Y CONEXIÓN ---
st.set_page_config(page_title="TopoConverter Pro", page_icon="🏗️", layout="wide")

# Conexión segura a Supabase mediante Secrets
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Error de configuración: Verifica los Secrets en Streamlit Cloud.")

# --- 2. FUNCIONES TÉCNICAS (EL CEREBRO) ---

def calcular_distancia(x1, y1, x2, y2):
    """Calcula la distancia plana entre dos puntos."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def registrar_uso(puntos, nombre):
    """Guarda un log del uso en Supabase."""
    try:
        supabase.table("registros_uso").insert({
            "puntos_procesados": puntos,
            "nombre_archivo": nombre,
            "formato_archivo": "MICRO_SURVEY_PNEZD"
        }).execute()
    except:
        pass # Silencioso para no interrumpir al usuario

def generar_dxf_pro(df):
    """Genera el archivo DXF con capas por código y lista puntos para el cuadro."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Colores para AutoCAD (1:Rojo, 2:Amarillo, 3:Verde, 4:Cian, 7:Blanco)
    config_capas = {
        'LP': 1,    # Límite de Propiedad -> Rojo
        'PTA': 4,   # Puntos de Terreno -> Cian
        'STN': 3,   # Estaciones -> Verde
        'AUX': 2,   # Auxiliares -> Amarillo
        'DEFAULT': 7
    }

    puntos_cuadro = []

    for i, row in df.iterrows():
        try:
            # Extraer datos (P, N, E, Z, D)
            p = str(row['Punto'])
            y = float(row['Y'])  # Norte
            x = float(row['X'])  # Este
            z = float(row['Z'])  # Elevación
            desc = str(row['Desc']).upper().strip() # Limpieza de espacios
            
            # Crear o asignar capa según descripción
            layer_name = f"TOPO_{desc}"
            if layer_name not in doc.layers:
                color = config_capas.get(desc, config_capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            # Dibujar Punto en CAD
            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            
            # Dibujar Texto (Número de punto)
            msp.add_text(
                p, 
                dxfattribs={'height': 0.25, 'layer': layer_name}
            ).set_pos((x + 0.1, y + 0.1, z))

            # Si es un lindero (LP), guardarlo para el Cuadro de Construcción
            if 'LP' in desc:
                puntos_cuadro.append({'p': p, 'x': x, 'y': y})

        except Exception:
            continue

    return doc, puntos_cuadro

# --- 3. INTERFAZ DE USUARIO (FRONTEND) ---

st.title("🏗️ TopoConverter Pro")
st.subheader("Automatización de Planillas MicroSurvey a AutoCAD")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.info("📌 **Instrucciones:**\n1. Sube tu archivo .txt o .csv\n2. El formato debe ser: *Punto, Norte, Este, Elevación, Descripción*.\n3. Los puntos marcados como **LP** generarán automáticamente el Cuadro de Construcción.")
    archivo = st.file_uploader("Subir archivo de levantamiento", type=['txt', 'csv'])

if archivo:
    # Leer datos asumiendo el formato P,N,E,Z,D de MicroSurvey
    df = pd.read_csv(archivo, names=['Punto', 'Y', 'X', 'Z', 'Desc'])
    
    with col2:
        st.write("✅ **Vista previa del archivo cargado:**")
        st.dataframe(df.head(10), use_container_width=True)

    st.markdown("---")
    
    if st.button("🚀 PROCESAR LEVANTAMIENTO Y GENERAR CUADRO"):
        doc, lista_lp = generar_dxf_pro(df)
        
        # 1. Mostrar Cuadro de Construcción si existen puntos LP
        if len(lista_lp) > 1:
            st.success("📊 **Cuadro de Construcción Generado (Linderos LP)**")
            tabla_datos = []
            for i in range(len(lista_lp) - 1):
                p1, p2 = lista_lp[i], lista_lp[i+1]
                dist = calcular_distancia(p1['x'], p1['y'], p2['x'], p2['y'])
                tabla_datos.append({
                    "Vértice": p1['p'],
                    "A Vértice": p2['p'],
                    "Distancia (m)": f"{dist:.3f}",
                    "Este (X)": f"{p1['x']:.3f}",
                    "Norte (Y)": f"{p1['y']:.3f}"
                })
            st.table(tabla_datos)
        else:
            st.warning("⚠️ No se encontraron suficientes puntos con el código **'LP'** para generar el Cuadro de Construcción.")

        # 2. Preparar el archivo DXF para descarga
        buffer = io.StringIO()
        doc.write(buffer)
        dxf_data = buffer.getvalue()
        
        # 3. Registro en Base de Datos
        registrar_uso(len(df), archivo.name)
        
        # 4. Botón de Descarga
        st.download_button(
            label="⬇️ Descargar archivo DXF para AutoCAD",
            data=dxf_data,
            file_name=f"PLAN_TOPO_{archivo.name.split('.')[0]}.dxf",
            mime="application/dxf"
        )
        
        st.balloons()
