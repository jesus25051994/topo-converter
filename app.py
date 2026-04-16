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
    st.error("Error en Secrets.")

def calcular_distancia(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def generar_archivo_topo(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    config_capas = {'LP': 1, 'PTA': 4, 'STN': 3, 'AUX': 2, 'DEFAULT': 7}
    
    puntos_cuadro = []
    
    # --- SECCIÓN DE DEBUG EN PANTALLA ---
    st.write("🔍 **Análisis de etiquetas (Primeros 10 puntos):**")
    
    for i, row in df.iterrows():
        try:
            p_id = str(row[0]).strip()
            y = float(row[1])
            x = float(row[2])
            z = float(row[3])
            
            # Limpieza total
            desc_bruta = str(row[4]).upper()
            desc_limpia = "".join(desc_bruta.split()) 

            # Imprimir en la web los primeros 10 para no saturar
            if i < 10:
                es_lp = "✅ SÍ" if "LP" in desc_limpia else "❌ NO"
                st.write(f"Punto {p_id}: Contenido='{desc_limpia}' | ¿Detectado como LP?: {es_lp}")

            layer_name = f"TOPO_{desc_limpia}"
            if layer_name not in doc.layers:
                color = config_capas.get(desc_limpia, config_capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(p_id, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x + 0.1, y + 0.1, z))

            if "LP" in desc_limpia:
                puntos_cuadro.append({'p': p_id, 'x': x, 'y': y})
        except:
            continue
            
    return doc, puntos_cuadro

st.title("🏗️ TopoConverter Pro: Modo Debug")

archivo = st.file_uploader("Sube tu archivo", type=['txt', 'csv'])

if archivo:
    try:
        df = pd.read_csv(archivo, sep=None, engine='python', header=None, skipinitialspace=True)
        
        if not df.empty:
            if st.button("🚀 PROCESAR Y DEBUGUEAR"):
                doc, lista_lp = generar_archivo_topo(df)
                
                if len(lista_lp) > 1:
                    st.success(f"📊 ¡Cuadro generado con {len(lista_lp)} puntos!")
                    # ... (aquí iría la tabla que ya tienes)
                
                st.balloons()
                
                # Descarga
                buffer = io.StringIO()
                doc.write(buffer)
                st.download_button("⬇️ Descargar DXF", buffer.getvalue(), "topo.dxf")
                
    except Exception as e:
        st.error(f"Error crítico al leer el archivo: {e}")
