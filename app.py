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

# --- 2. PROCESAMIENTO ROBUSTO ---
def procesar_topo(file_bytes):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    config_capas = {'LP': 1, 'PTA': 4, 'STN': 3, 'AUX': 2, 'DEFAULT': 7}
    
    puntos_para_cuadro = []
    datos_limpios = []

    # Decodificar el archivo de forma segura
    content = file_bytes.decode("utf-8", errors="ignore")
    lines = content.splitlines()

    for line in lines:
        # Limpiar la línea y separar por comas
        parts = [p.strip() for p in line.split(',') if p.strip()]
        
        if len(parts) >= 4:
            try:
                p_id = parts[0]
                norte = float(parts[1])
                este = float(parts[2])
                elev = float(parts[3])
                desc = parts[4].upper() if len(parts) > 4 else "S/D"

                # Capas y Dibujo
                layer_name = f"TOPO_{desc}"
                if layer_name not in doc.layers:
                    color = config_capas.get(desc, config_capas['DEFAULT'])
                    doc.layers.new(layer_name, dxfattribs={'color': color})

                msp.add_point((este, norte, elev), dxfattribs={'layer': layer_name})
                msp.add_text(p_id, dxfattribs={'height': 0.25, 'layer': layer_name}).set_pos((este + 0.1, norte + 0.1, elev))

                datos_limpios.append([p_id, norte, este, elev, desc])

                if "LP" in desc:
                    puntos_para_cuadro.append({'p': p_id, 'x': este, 'y': norte})
            except:
                continue

    df = pd.DataFrame(datos_limpios, columns=['Punto', 'Norte (Y)', 'Este (X)', 'Elev (Z)', 'Desc'])
    return doc, puntos_para_cuadro, df

# --- 3. INTERFAZ ---
st.title("🏗️ TopoConverter Pro: Versión Ultra-Compatible")

archivo = st.file_uploader("Sube tu archivo puerta del mar.txt", type=['txt', 'csv'])

if archivo:
    # IMPORTANTE: No usamos archivo.read() antes del botón para no agotar el buffer
    file_bytes = archivo.getvalue()
    doc, lista_lp, df_resumen = procesar_topo(file_bytes)

    if not df_resumen.empty:
        st.write("📋 **Vista previa de datos (Limpiados):**")
        st.dataframe(df_resumen.head(20))

        if st.button("🚀 GENERAR TODO"):
            # Registro Supabase
            try:
                supabase.table("registros_uso").insert({"puntos_procesados": len(df_resumen), "nombre_archivo": archivo.name}).execute()
            except: pass

            # Cuadro de construcción
            if len(lista_lp) > 1:
                st.subheader(f"📊 Cuadro de Construcción ({len(lista_lp)} puntos LP)")
                tabla = []
                for i in range(len(lista_lp) - 1):
                    p1, p2 = lista_lp[i], lista_lp[i+1]
                    d = calcular_distancia(p1['x'], p1['y'], p2['x'], p2['y'])
                    tabla.append({"De": p1['p'], "A": p2['p'], "Distancia": f"{d:.3f}m", "X": p1['x'], "Y": p1['y']})
                st.table(tabla)
            
            # Descarga DXF
            buffer = io.StringIO()
            doc.write(buffer)
            st.download_button("⬇️ Descargar DXF", buffer.getvalue(), "dibujo.dxf", "application/dxf")
            st.balloons()
    else:
        st.error("No se pudieron procesar datos. Verifica el formato del archivo.")
