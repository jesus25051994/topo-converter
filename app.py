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
    st.error("Error: Revisa los Secrets en Streamlit.")

def calcular_distancia(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# --- 2. PROCESAMIENTO ---
def generar_archivo_topo(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    config_capas = {'LP': 1, 'PTA': 4, 'STN': 3, 'AUX': 2, 'DEFAULT': 7}
    
    puntos_cuadro = []
    
    for _, row in df.iterrows():
        try:
            p_id = str(row[0]).strip()
            y = float(row[1])
            x = float(row[2])
            z = float(row[3])
            
            # Limpieza total de etiquetas
            desc_bruta = str(row[4]).upper()
            desc_limpia = "".join(desc_bruta.split()) 

            # Dibujo en CAD
            layer_name = f"TOPO_{desc_limpia}"
            if layer_name not in doc.layers:
                color = config_capas.get(desc_limpia, config_capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(p_id, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x + 0.1, y + 0.1, z))

            # Colección de Linderos
            if "LP" in desc_limpia:
                puntos_cuadro.append({'p': p_id, 'x': x, 'y': y})
        except:
            continue
            
    return doc, puntos_cuadro

# --- 3. INTERFAZ ---
st.title("🏗️ TopoConverter Pro")
st.markdown("---")

archivo = st.file_uploader("Sube tu archivo .txt o .csv", type=['txt', 'csv'])

if archivo:
    try:
        df = pd.read_csv(archivo, sep=None, engine='python', header=None, skipinitialspace=True)
        
        if not df.empty:
            st.write("✅ **Pre-visualización de datos lista.**")
            
            if st.button("🚀 PROCESAR Y GENERAR"):
                doc, lista_lp = generar_archivo_topo(df)
                
                # MOSTRAR SOLO EL TOTAL
                total_lp = len(lista_lp)
                if total_lp > 0:
                    st.success(f"💎 Se detectaron un total de **{total_lp}** puntos de lindero (LP).")
                else:
                    st.warning("⚠️ No se encontraron puntos LP.")

                # Mostrar Tabla si hay suficientes puntos
                if total_lp > 1:
                    tabla = []
                    for i in range(total_lp - 1):
                        p1, p2 = lista_lp[i], lista_lp[i+1]
                        d = calcular_distancia(p1['x'], p1['y'], p2['x'], p2['y'])
                        tabla.append({
                            "De": p1['p'], "A": p2['p'], 
                            "Distancia": f"{d:.3f}m", 
                            "Este (X)": f"{p1['x']:.3f}", "Norte (Y)": f"{p1['y']:.3f}"
                        })
                    st.table(tabla)

                # Registro y Descarga
                try:
                    supabase.table("registros_uso").insert({"puntos_procesados": len(df), "nombre_archivo": archivo.name}).execute()
                except: pass

                buffer = io.StringIO()
                doc.write(buffer)
                st.download_button("⬇️ Descargar DXF Final", buffer.getvalue(), "levantamiento.dxf")
                
                st.balloons() # ¡Que no falten los globos!
                
    except Exception as e:
        st.error(f"Error: {e}")
