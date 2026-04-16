import streamlit as st
import pandas as pd
import ezdxf
import io
import math
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="TopoConverter Pro", page_icon="🏗️")

# Es recomendable usar try-except aquí por si los secrets no están configurados
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Error de conexión con Supabase. Revisa tus Secrets.")

# --- 2. FUNCIONES TÉCNICAS ---

def calcular_rumbo(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    distancia = math.sqrt(dx**2 + dy**2)
    return distancia

def registrar_uso(puntos, nombre):
    try:
        supabase.table("registros_uso").insert({
            "puntos_processed": puntos,
            "nombre_archivo": nombre,
            "formato_archivo": "CSV_MICRO"
        }).execute()
    except: 
        pass

def generar_dxf_pro(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Definición de colores base
    colores_capas = {
        'LP': 1,   # Rojo
        'PTA': 4,  # Cian
        'STN': 3,  # Verde
        'DEFAULT': 7 
    }

    puntos_cuadro = []

    for i, row in df.iterrows():
        try:
            # Asignación correcta de columnas según tu pd.read_csv
            p_id = str(row['Punto']).strip()
            y = float(row['Y'])
            x = float(row['X'])
            z = float(row['Z'])
            desc_bruta = str(row['Desc']).upper().strip()
            
            # Limpiar nombre para la capa
            desc_limpia = "".join(desc_bruta.split())
            layer_name = f"TOPO_{desc_limpia}"
            
            # Crear capa si no existe
            if layer_name not in doc.layers:
                # Buscamos si la descripción bruta contiene alguna clave (ej: 'LP')
                color = colores_capas['DEFAULT']
                for clave, cod_color in colores_capas.items():
                    if clave in desc_bruta:
                        color = cod_color
                        break
                doc.layers.new(layer_name, dxfattribs={'color': color})

            # Dibujar Punto y Texto (Usando p_id que es la variable correcta)
            msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
            msp.add_text(p_id, 
                         dxfattribs={'height': 0.25, 'layer': layer_name}
                        ).set_pos((x + 0.1, y + 0.1, z))

            # Guardar datos para el cuadro si es LP (Límite de Propiedad)
            if 'LP' in desc_bruta:
                puntos_cuadro.append({'p': p_id, 'x': x, 'y': y})

        except Exception as e:
            continue

    return doc, puntos_cuadro

# --- 3. INTERFAZ ---
st.title("🏗️ TopoConverter Pro: MicroSurvey Edition")
st.info("Formato esperado: Punto, Norte (Y), Este (X), Elevación (Z), Descripción")

archivo = st.file_uploader("Sube el TXT/CSV de MicroSurvey", type=['txt', 'csv'])

if archivo:
    # Leemos el archivo. Nota: Se asume que no tiene encabezado por el uso de 'names'
    df = pd.read_csv(archivo, names=['Punto', 'Y', 'X', 'Z', 'Desc'])
    st.subheader("Vista previa de datos")
    st.dataframe(df.head())

    if st.button("🚀 Generar DXF + Cuadro de Construcción"):
        doc, puntos_cuadro = generar_dxf_pro(df)
        
        # Lógica del Cuadro de Construcción
        if len(puntos_cuadro) > 1:
            st.subheader("📊 Cuadro de Construcción")
            tabla_datos = []
            for i in range(len(puntos_cuadro) - 1):
                p1 = puntos_cuadro[i]
                p2 = puntos_cuadro[i+1]
                dist = calcular_rumbo(p1['x'], p1['y'], p2['x'], p2['y'])
                tabla_datos.append({
                    "De": p1['p'], 
                    "A": p2['p'], 
                    "Distancia (m)": round(dist, 3),
                    "Este (X)": round(p1['x'], 3), 
                    "Norte (Y)": round(p1['y'], 3)
                })
            st.table(tabla_datos)
        
        # Preparar descarga del DXF
        out = io.StringIO()
        doc.write(out)
        dxf_string = out.getvalue()
        
        registrar_uso(len(df), archivo.name)
        
        st.download_button(
            label="⬇️ Descargar DXF",
            data=dxf_string,
            file_name="levantamiento_topo.dxf",
            mime="application/dxf"
        )
