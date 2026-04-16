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
    
    # Procesamiento de puntos y capas
    for i, row in df.iterrows():
        try:
            p_id = str(row[0]).strip()
            y = float(row[1])
            x = float(row[2])
            z = float(row[3])
            
            desc_bruta = str(row[4]).upper()
            desc_limpia = "".join(desc_bruta.split()) 

            layer_name = f"TOPO_{desc_limpia}"
            if layer_name not in doc.layers:
                color = config_capas.get(desc_limpia, config_capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(p_id, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x + 0.1, y + 0.1, z))

            # Si el punto es LP, lo guardamos para el cuadro
            if "LP" in desc_limpia:
                puntos_cuadro.append({'p': p_id, 'x': x, 'y': y})
        except:
            continue
            
    return doc, puntos_cuadro

st.title("🏗️ TopoConverter Pro")

archivo = st.file_uploader("Sube tu archivo", type=['txt', 'csv'])

if archivo:
    try:
        # Lectura automática con detección de separador
        df = pd.read_csv(archivo, sep=None, engine='python', header=None, skipinitialspace=True)
        
        if not df.empty:
            st.write("✅ Archivo cargado correctamente.")
            
            if st.button("🚀 GENERAR DXF + CUADRO"):
                # PASO 1: Generar el archivo DXF y recolectar puntos LP
                doc, lista_lp = generar_archivo_topo(df)
                
                # PASO 2: Generar y mostrar el Cuadro de Construcción
                if len(lista_lp) > 1:
                    st.success(f"📊 ¡Cuadro generado con {len(lista_lp)} puntos LP!")
                    
                    tabla_datos = []
                    # Recorremos los puntos para calcular distancias entre ellos
                    for i in range(len(lista_lp) - 1):
                        p1 = lista_lp[i]
                        p2 = lista_lp[i+1]
                        dist = calcular_distancia(p1['x'], p1['y'], p2['x'], p2['y'])
                        
                        tabla_datos.append({
                            "De (Punto)": p1['p'], 
                            "A (Punto)": p2['p'], 
                            "Distancia (m)": f"{dist:.3f}", 
                            "Este (X)": f"{p1['x']:.3f}", 
                            "Norte (Y)": f"{p1['y']:.3f}"
                        })
                    
                    # Pintamos la tabla visual en la web
                    st.table(tabla_datos)
                else:
                    st.warning(f"⚠️ Se detectaron {len(lista_lp)} puntos LP. Se necesitan al menos 2 para generar la tabla.")
                
                # PASO 3: Configurar el botón de descarga del DXF
                buffer = io.StringIO()
                doc.write(buffer)
                
                st.download_button(
                    label="⬇️ Descargar archivo DXF",
                    data=buffer.getvalue(),
                    file_name=f"TOPO_{archivo.name.split('.')[0]}.dxf",
                    mime="application/dxf"
                )
                
                # Festejo final
                st.balloons()
                
    except Exception as e:
        st.error(f"Error crítico: {e}")
