import streamlit as st
import pandas as pd
import ezdxf
import io
import math
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="TopoConverter Pro", page_icon="🏗️", layout="wide")

# Conexión a Supabase (Secrets)
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Error: Revisa los Secrets en Streamlit Cloud.")

def calcular_distancia(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# --- 2. PROCESAMIENTO ---
def generar_archivo_topo(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Configuración de capas
    config_capas = {'LP': 1, 'PTA': 4, 'STN': 3, 'AUX': 2, 'DEFAULT': 7}
    puntos_cuadro = []
    
    for _, row in df.iterrows():
        try:
            # Extraer datos de las columnas por índice
            p_id = str(row[0]).strip()
            y = float(row[1])
            x = float(row[2])
            z = float(row[3])
            
            # LIMPIEZA: desc_limpia es la que usamos para la lógica
            desc_bruta = str(row[4]).upper()
            desc_limpia = desc_bruta.strip() 

            # Capas dinámicas (reemplazamos espacios por guiones para AutoCAD)
            nombre_capa = f"TOPO_{desc_limpia.replace(' ', '_')}"
            if nombre_capa not in doc.layers:
                # Buscamos color por palabra clave (ej. si contiene LP)
                color = config_capas['DEFAULT']
                for clave, c_val in config_capas.items():
                    if clave in desc_limpia:
                        color = c_val
                        break
                doc.layers.new(nombre_capa, dxfattribs={'color': color})

            # Dibujo en DXF
            msp.add_point((x, y, z), dxfattribs={'layer': nombre_capa})
            msp.add_text(p_id, dxfattribs={'height': 0.25, 'layer': nombre_capa}).set_pos((x + 0.1, y + 0.1, z))

            # IMPORTANTE: Guardamos si detectamos LP
            if "LP" in desc_limpia:
                puntos_cuadro.append({'p': p_id, 'x': x, 'y': y})
        except:
            continue
            
    return doc, puntos_cuadro

# --- 3. INTERFAZ ---
st.title("🏗️ TopoConverter Pro: Edición Final")
st.markdown("---")

archivo = st.file_uploader("Sube tu archivo .txt o .csv", type=['txt', 'csv'])

if archivo:
    try:
        # Lectura ultra-flexible
        df = pd.read_csv(archivo, sep=None, engine='python', header=None, skipinitialspace=True)
        
        if not df.empty:
            st.write("✅ **Datos cargados correctamente.**")
            st.dataframe(df.head(5))

            if st.button("🚀 PROCESAR Y GENERAR"):
                # PASO 1: Generar datos
                doc, lista_lp = generar_archivo_topo(df)
                
                # PASO 2: Contar y mostrar éxito
                total_lp = len(lista_lp)
                
                if total_lp > 0:
                    st.success(f"💎 ¡Éxito! Se detectaron **{total_lp}** puntos de lindero (LP).")
                    
                    # Mostrar Tabla de Cuadro de Construcción
                    if total_lp > 1:
                        tabla = []
                        for i in range(total_lp - 1):
                            p1, p2 = lista_lp[i], lista_lp[i+1]
                            d = calcular_distancia(p1['x'], p1['y'], p2['x'], p2['y'])
                            tabla.append({
                                "De": p1['p'], 
                                "A": p2['p'], 
                                "Distancia": f"{d:.3f}m", 
                                "Este (X)": f"{p1['x']:.3f}", 
                                "Norte (Y)": f"{p1['y']:.3f}"
                            })
                        st.table(tabla)
                else:
                    st.warning("⚠️ No se encontraron puntos LP en el archivo.")

                # PASO 3: Registro y Descarga
                try:
                    supabase.table("registros_uso").insert({"puntos_procesados": len(df), "nombre_archivo": archivo.name}).execute()
                except: pass

                buffer = io.StringIO()
                doc.write(buffer)
                
                st.download_button(
                    label="⬇️ Descargar archivo DXF",
                    data=buffer.getvalue(),
                    file_name=f"TOPO_{archivo.name.split('.')[0]}.dxf",
                    mime="application/dxf"
                )
                
                # GLOBOS AL FINAL
                st.balloons()
                
        else:
            st.error("El archivo está vacío.")
            
    except Exception as e:
        st.error(f"Error crítico: {e}")
