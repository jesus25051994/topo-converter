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
    st.error("Error: Revisa los Secrets en Streamlit Cloud.")

def calcular_distancia(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# --- 2. EL CORAZÓN DEL PROCESAMIENTO ---
def procesar_archivo_limpio(file_content):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    config_capas = {'LP': 1, 'PTA': 4, 'STN': 3, 'AUX': 2, 'DEFAULT': 7}
    datos_limpios = []
    puntos_para_cuadro = []

    # Leemos línea por línea para evitar errores de formato
    lines = file_content.decode("utf-8").splitlines()
    
    for line in lines:
        parts = line.split(',')
        if len(parts) >= 4:
            try:
                p = parts[0].strip()
                y = float(parts[1].strip())
                x = float(parts[2].strip())
                z = float(parts[3].strip())
                # Si no hay descripción, ponemos 'S/D'
                desc = parts[4].strip().upper() if len(parts) > 4 else "S/D"
                
                # Crear capa
                layer_name = f"TOPO_{desc}"
                if layer_name not in doc.layers:
                    color = config_capas.get(desc, config_capas['DEFAULT'])
                    doc.layers.new(layer_name, dxfattribs={'color': color})

                # Dibujar
                msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
                msp.add_text(p, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((x + 0.1, y + 0.1, z))

                # Guardar para la tabla visual
                datos_limpios.append([p, y, x, z, desc])

                # Guardar para el cuadro si contiene LP
                if "LP" in desc:
                    puntos_para_cuadro.append({'p': p, 'x': x, 'y': y})
            except:
                continue

    df_preview = pd.DataFrame(datos_limpios, columns=['Punto', 'Norte (Y)', 'Este (X)', 'Elev (Z)', 'Desc'])
    return doc, puntos_para_cuadro, df_preview

# --- 3. INTERFAZ ---
st.title("🏗️ TopoConverter Pro: Versión Ultra-Compatible")

archivo = st.file_uploader("Sube tu archivo puerta del mar.txt", type=['txt', 'csv'])

if archivo:
    # Procesamos el contenido
    content = archivo.read()
    doc, lista_lp, df_resumen = procesar_archivo_limpio(content)
    
    st.write("📋 **Vista previa de datos (Limpios):**")
    st.dataframe(df_resumen.head(10))

    if st.button("🚀 GENERAR TODO"):
        # Registro en Supabase
        try:
            supabase.table("registros_uso").insert({"puntos_procesados": len(df_resumen), "nombre_archivo": archivo.name}).execute()
        except: pass

        # Cuadro de Construcción
        if len(lista_lp) > 1:
            st.success(f"📊 Se encontraron {len(lista_lp)} puntos de lindero (LP).")
            tabla_final = []
            for i in range(len(lista_lp) - 1):
                p1, p2 = lista_lp[i], lista_lp[i+1]
                dist = calcular_distancia(p1['x'], p1['y'], p2['x'], p2['y'])
                tabla_final.append({
                    "Vértice": p1['p'], "A Vértice": p2['p'],
                    "Distancia (m)": f"{dist:.3f}",
                    "X (Este)": f"{p1['x']:.3f}", "Y (Norte)": f"{p1['y']:.3f}"
                })
            st.table(tabla_final)
        else:
            st.warning("⚠️ No se detectaron suficientes puntos 'LP'. Revisa las etiquetas en la vista previa de arriba.")

        # Descarga DXF
        buffer = io.StringIO()
        doc.write(buffer)
        st.download_button("⬇️ Descargar DXF", buffer.getvalue(), "topo_final.dxf", "application/dxf")
        st.balloons()
