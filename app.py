import streamlit as st
import pandas as pd
import ezdxf
import io
import math
from supabase import create_client, Client

st.set_page_config(page_title="TopoConverter Pro", page_icon="🏗️", layout="wide")

# Conexión a Supabase
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Error: Revisa los Secrets en Streamlit.")

def calcular_distancia(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def generar_dxf_pro(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    config_capas = {'LP': 1, 'PTA': 4, 'STN': 3, 'AUX': 2, 'DEFAULT': 7}
    puntos_para_cuadro = []

    for i, row in df.iterrows():
        try:
            p = str(row['Punto']).strip()
            y = float(row['Y'])
            x = float(row['X'])
            z = float(row['Z'])
            
            # LIMPIEZA EXTREMA: Quitamos espacios, saltos de línea y pasamos a Mayúsculas
            desc_raw = str(row['Desc']).upper().strip()
            
            # Crear capa
            layer_name = f"TOPO_{desc_raw}"
            if layer_name not in doc.layers:
                color = config_capas.get(desc_raw, config_capas['DEFAULT'])
                doc.layers.new(layer_name, dxfattribs={'color': color})

            # Dibujar en CAD
            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(p, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x + 0.1, y + 0.1, z))

            # BÚSQUEDA FLEXIBLE: Si 'LP' aparece en cualquier parte de la descripción
            if "LP" in desc_raw:
                puntos_para_cuadro.append({'p': p, 'x': x, 'y': y})

        except:
            continue

    return doc, puntos_para_cuadro

st.title("🏗️ TopoConverter Pro")
st.markdown("---")

archivo = st.file_uploader("Sube tu archivo puerta del mar.txt", type=['txt', 'csv'])

if archivo:
    # IMPORTANTE: Forzamos la lectura de columnas ignorando posibles errores de formato
    try:
        df = pd.read_csv(archivo, names=['Punto', 'Y', 'X', 'Z', 'Desc'], skipinitialspace=True)
    except:
        st.error("Error al leer el archivo. Asegúrate de que sea un TXT separado por comas.")

    st.write("📋 **Vista previa de datos cargados:**")
    st.dataframe(df.head(10))

    if st.button("🚀 PROCESAR Y GENERAR CUADRO"):
        doc, lista_lp = generar_dxf_pro(df)
        
        # Validación de salida
        if len(lista_lp) > 1:
            st.success(f"📊 **Cuadro de Construcción Generado: {len(lista_lp)} vértices LP encontrados.**")
            
            tabla_final = []
            for i in range(len(lista_lp) - 1):
                p1, p2 = lista_lp[i], lista_lp[i+1]
                dist = calcular_distancia(p1['x'], p1['y'], p2['x'], p2['y'])
                
                tabla_final.append({
                    "Vértice": p1['p'],
                    "A Vértice": p2['p'],
                    "Distancia (m)": f"{dist:.3f}",
                    "Este (X)": f"{p1['x']:.3f}",
                    "Norte (Y)": f"{p1['y']:.3f}"
                })
            
            st.table(tabla_final)
            
            buffer = io.StringIO()
            doc.write(buffer)
            st.download_button(
                label="⬇️ Descargar archivo DXF",
                data=buffer.getvalue(),
                file_name="topo_resultado.dxf",
                mime="application/dxf"
            )
            st.balloons()
        else:
            # Esto nos dirá si Python está viendo algo o nada
            st.warning(f"⚠️ El sistema detectó {len(lista_lp)} puntos LP. Por favor, revisa que la columna de descripción en tu archivo diga LP.")
            st.write("Dato detectado en la última columna:", df['Desc'].unique())
