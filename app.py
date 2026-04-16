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
    
    # Procesamiento de puntos
    for i, row in df.iterrows():
        try:
            p_id = str(row[0]).strip()
            y = float(row[1])
            x = float(row[2])
            z = float(row[3])
            
            desc_bruta = str(row[4]).upper()
            desc_limpia = "".join(desc_bruta.split()) 

            # Capas
            layer_name = f"TOPO_{desc_limpia}"
            if layer_name not in doc.layers:
                color = config_capas.get(desc_limpia, config_capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            # Dibujo
            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(p_id, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x + 0.1, y + 0.1, z))

            if "LP" in desc_limpia:
                puntos_cuadro.append({'p': p_id, 'x': x, 'y': y})
        except:
            continue
            
    return doc, puntos_cuadro

st.title("🏗️ TopoConverter Pro")

archivo = st.file_uploader("Sube tu archivo", type=['txt', 'csv'])

if archivo:
    try:
        df = pd.read_csv(archivo, sep=None, engine='python', header=None, skipinitialspace=True)
        
        if not df.empty:
            st.write("✅ Archivo cargado correctamente.")
            
            if st.button("🚀 GENERAR DXF + CUADRO"):
                doc, lista_lp = generar_archivo_topo(df)
                
                if len(lista_lp) > 1:
                    st.success(f"📊 ¡Cuadro generado con {len(lista_lp)} puntos LP!")
                    
                    # --- AQUÍ SE GENERA LA TABLA ---
                    tabla_datos = []
                    for i in range(len(lista_lp) - 1):
                        p1 = lista_lp[i]
                        p2 = lista_lp[i+1]
                        dist = calcular_distancia(p1['x'], p1['y'], p2['x'], p2['y'])
                        
                        tabla_datos.append({
                            "De": p1['p'], 
                            "A": p2['p'], 
                            "Distancia": f"{dist:.3f} m", 
                            "Este (X)": f"{p1['x']:.3f}", 
                            "Norte (Y)": f"{p1['y']:.3f}"
                        })
                    
                    # Mostrar la tabla en la app
                    st.table(tabla_datos)
                    # -------------------------------
                
                    # Registro opcional en Supabase
                    try:
                        supabase.table("registros_uso").insert({"puntos_procesados": len(df), "nombre_archivo": archivo.name}).execute()
                    except: pass
                
                # Botón de Descarga (Siempre disponible si se procesó)
                buffer = io.StringIO()
                doc.write(buffer)
                st.download_button(
                    label="⬇️ Descargar DXF",
                    data=buffer.getvalue(),
                    file_name=f"TOPO_{archivo.name.split('.')[0]}.dxf",
                    mime="application/dxf"
                )
                
                st.balloons()
                
    except Exception as e:
        st.error(f"Error crítico: {e}")
