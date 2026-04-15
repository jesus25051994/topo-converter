import streamlit as st
import pandas as pd
import ezdxf
import io
import math
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="TopoConverter Pro", page_icon="🏗️", layout="wide")

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Error: Configura SUPABASE_URL y SUPABASE_KEY en los Secrets de Streamlit.")

def calcular_distancia(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# --- 2. PROCESAMIENTO ---
def generar_dxf_pro(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Colores: 1=Rojo, 4=Cian, 3=Verde, 2=Amarillo, 7=Blanco
    config_capas = {'LP': 1, 'PTA': 4, 'STN': 3, 'AUX': 2, 'DEFAULT': 7}
    puntos_para_cuadro = []

    for i, row in df.iterrows():
        try:
            # Limpieza profunda de datos
            p = str(row['Punto']).strip()
            y = float(row['Y'])
            x = float(row['X'])
            z = float(row['Z'])
            desc_limpia = str(row['Desc']).upper().strip()
            
            # Crear capas dinámicas
            layer_name = f"TOPO_{desc_limpia}"
            if layer_name not in doc.layers:
                color = config_capas.get(desc_limpia, config_capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            # Dibujar en AutoCAD
            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(p, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x + 0.1, y + 0.1, z))

            # COLECTAR TODOS LOS LP (No importa si están salteados)
            if "LP" in desc_limpia:
                puntos_para_cuadro.append({'p': p, 'x': x, 'y': y})

        except:
            continue

    return doc, puntos_para_cuadro

# --- 3. INTERFAZ ---
st.title("🏗️ TopoConverter Pro")
st.markdown("---")

archivo = st.file_uploader("Sube tu archivo puerta del mar.txt", type=['txt', 'csv'])

if archivo:
    # Carga de datos robusta
    df = pd.read_csv(archivo, names=['Punto', 'Y', 'X', 'Z', 'Desc'], dtype=str)
    st.write("📋 **Vista previa de datos:**")
    st.dataframe(df.head(5))

    if st.button("🚀 PROCESAR LEVANTAMIENTO"):
        doc, lista_lp = generar_dxf_pro(df)
        
        # EL CUADRO AHORA USA LA LISTA FILTRADA DE LP
        if len(lista_lp) > 1:
            st.success(f"📊 **Cuadro de Construcción Generado ({len(lista_lp)} vértices encontrados)**")
            
            tabla_final = []
            for i in range(len(lista_lp) - 1):
                p1 = lista_lp[i]
                p2 = lista_lp[i+1]
                dist = calcular_distancia(float(p1['x']), float(p1['y']), float(p2['x']), float(p2['y']))
                
                tabla_final.append({
                    "Vértice": p1['p'],
                    "A Vértice": p2['p'],
                    "Distancia (m)": f"{dist:.3f}",
                    "Este (X)": f"{float(p1['x']):.3f}",
                    "Norte (Y)": f"{float(p1['y']):.3f}"
                })
            
            st.table(tabla_final)
            
            # Descarga
            buffer = io.StringIO()
            doc.write(buffer)
            st.download_button(
                label="⬇️ Descargar archivo DXF para AutoCAD",
                data=buffer.getvalue(),
                file_name="topo_resultado.dxf",
                mime="application/dxf"
            )
            st.balloons()
        else:
            st.warning(f"⚠️ Solo se encontró {len(lista_lp)} punto(s) LP. Se necesitan al menos 2 para medir distancias.")
