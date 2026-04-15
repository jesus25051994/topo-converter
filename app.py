import streamlit as st
import pandas as pd
import ezdxf
import io
import math
from supabase import create_client, Client

st.set_page_config(page_title="TopoConverter Pro", page_icon="🏗️", layout="wide")

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Error de configuración en Secrets.")

def calcular_distancia(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def generar_dxf_pro(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    config_capas = {'LP': 1, 'PTA': 4, 'STN': 3, 'AUX': 2, 'DEFAULT': 7}
    puntos_cuadro = []

    for i, row in df.iterrows():
        try:
            p = str(row['Punto'])
            y = float(row['Y'])
            x = float(row['X'])
            z = float(row['Z'])
            # Usamos strip() para limpiar espacios y convertimos a string puro
            desc_original = str(row['Desc'])
            desc_limpia = desc_original.upper().strip()
            
            layer_name = f"TOPO_{desc_limpia}"
            if layer_name not in doc.layers:
                color = config_capas.get(desc_limpia, config_capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(p, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x + 0.1, y + 0.1, z))

            # Lógica ultra-flexible para detectar LP
            if "LP" in desc_limpia:
                puntos_cuadro.append({'p': p, 'x': x, 'y': y})

        except:
            continue

    return doc, puntos_cuadro

st.title("🏗️ TopoConverter Pro")
st.info("Formato esperado: Punto, Norte (Y), Este (X), Elevación (Z), Descripción")

archivo = st.file_uploader("Sube tu archivo .txt o .csv", type=['txt', 'csv'])

if archivo:
    # Leemos el archivo asegurándonos de que trate todo como texto primero para no perder datos
    df = pd.read_csv(archivo, names=['Punto', 'Y', 'X', 'Z', 'Desc'], dtype={'Punto': str, 'Desc': str})
    st.dataframe(df.head(10))

    if st.button("🚀 PROCESAR LEVANTAMIENTO Y GENERAR CUADRO"):
        doc, lista_lp = generar_dxf_pro(df)
        
        # DEBUG: Esto te dirá cuántos LP encontró realmente
        # st.write(f"DEBUG: Encontrados {len(lista_lp)} puntos LP")

        if len(lista_lp) > 1:
            st.success("📊 **Cuadro de Construcción Generado**")
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
            
            buffer = io.StringIO()
            doc.write(buffer)
            st.download_button(
                label="⬇️ Descargar archivo DXF",
                data=buffer.getvalue(),
                file_name="levantamiento_pro.dxf",
                mime="application/dxf"
            )
            st.balloons()
        else:
            st.warning(f"⚠️ El sistema no detectó suficientes puntos con la etiqueta 'LP'. Revisa que en tu archivo la descripción sea exactamente LP (encontrados: {len(lista_lp)})")
