# app_termo.py
import streamlit as st
import pandas as pd
import numpy as np
from CoolProp.CoolProp import PropsSI
from scipy.interpolate import RegularGridInterpolator, griddata
import io

st.set_page_config(page_title="TermoTables - propiedades", layout="wide")

st.title("TermoTables - propiedades e interpolación (Streamlit + Python)")
st.write("Modo: usa CoolProp (recomendado) o carga una tabla CSV para interpolación 2D.")

mode = st.radio("Selecciona modo", ["CoolProp (propiedades)", "Tabla/CSV (interpolación 2D)"])

if mode == "CoolProp (propiedades)":
    st.subheader("Obtener propiedades con CoolProp")
    fluid = st.text_input("Nombre del fluido (ej: Water, R134a, Air)", "Water")
    outputs = st.multiselect("Propiedades a obtener (CoolProp keys)", 
                             ["T","P","D","H","S","V","CP","CV"],
                             default=["T","P","D","H"])
    # Mapa simple de nombres de salida a claves de CoolProp
    map_keys = {"T":"T", "P":"P", "D":"D", "H":"H", "S":"S", "V":"Dmolar", "CP":"Cpmass", "CV":"Cvmass"}
    input1 = st.selectbox("Variable 1 (input)", ["T (K)","P (Pa)","H (J/kg)","D (kg/m3)"])
    val1 = st.number_input("Valor 1", value=300.0, format="%.6f")
    input2 = st.selectbox("Variable 2 (input)", ["P (Pa)","T (K)","H (J/kg)","D (kg/m3)"])
    val2 = st.number_input("Valor 2", value=101325.0, format="%.6f")
    if st.button("Calcular propiedades"):
        # Convert friendly name to CoolProp input keys
        input_map = {"T (K)": "T", "P (Pa)":"P", "H (J/kg)":"Hmass", "D (kg/m3)":"Dmass"}
        key1 = input_map[input1]
        key2 = input_map[input2]
        try:
            results = {}
            for out in outputs:
                out_key = map_keys.get(out, out)
                # PropsSI expects (output, input1, val1, input2, val2, fluid)
                val = PropsSI(out_key, key1, float(val1), key2, float(val2), fluid)
                results[out] = val
            st.write("**Resultados (SI):**")
            st.table(pd.DataFrame.from_dict(results, orient="index", columns=["Valor"]))
        except Exception as e:
            st.error(f"Error al obtener propiedades: {e}\nNota: asegúrate del nombre del fluido y rangos válidos.")

else:
    st.subheader("Interpolación 2D desde tabla CSV")
    uploaded = st.file_uploader("Sube CSV (columnas: x, y, prop) o una rejilla (x,y,prop1,prop2...)", type=["csv","txt"])
    if uploaded is not None:
        df = pd.read_csv(uploaded)
        st.write("Preview de la tabla:")
        st.dataframe(df.head())
        st.info("Opciones para interpolar: si tienes una malla regular con columnas (x,y,prop) o tres columnas (x,y,prop).")
        # Ask which columns are x and y
        cols = df.columns.tolist()
        x_col = st.selectbox("Eje X (por ejemplo temperatura)", cols, index=0)
        y_col = st.selectbox("Eje Y (por ejemplo presión)", cols, index=1)
        prop_cols = [c for c in cols if c not in (x_col, y_col)]
        prop_col = st.selectbox("Propiedad a interpolar", prop_cols)
        method = st.selectbox("Método de interpolación", ["linear","nearest","cubic"])
        xq = st.number_input("Valor X a interpolar", value=float(df[x_col].median()))
        yq = st.number_input("Valor Y a interpolar", value=float(df[y_col].median()))
        if st.button("Interpolar"):
            # Detect if grid is regular -> use RegularGridInterpolator
            # Try to pivot into grid
            try:
                xv = np.sort(df[x_col].unique())
                yv = np.sort(df[y_col].unique())
                grid_shape = (len(xv), len(yv))
                # Try to reshape if regular grid
                pivot = df.pivot_table(index=x_col, columns=y_col, values=prop_col)
                if pivot.shape == grid_shape:
                    grid = pivot.values
                    interp = RegularGridInterpolator((xv, yv), grid, method=method, bounds_error=False, fill_value=None)
                    val = interp([[xq, yq]])[0]
                    st.success(f"Interpolación (RegularGrid) -> {val}")
                else:
                    # fallback using griddata
                    pts = df[[x_col, y_col]].values
                    vals = df[prop_col].values
                    val = griddata(pts, vals, (xq, yq), method=method)
                    st.success(f"Interpolación (griddata) -> {val}")
            except Exception as e:
                st.error(f"No se pudo interpolar: {e}")

        st.write("Ejemplo: puedes generar una malla para graficar la propiedad.")
        if st.button("Graficar malla (preview)"):
            import matplotlib.pyplot as plt
            xv = np.sort(df[x_col].unique())
            yv = np.sort(df[y_col].unique())
            try:
                pivot = df.pivot_table(index=x_col, columns=y_col, values=prop_col)
                fig, ax = plt.subplots()
                c = ax.pcolormesh(yv, xv, pivot.values, shading='auto')
                fig.colorbar(c, ax=ax)
                ax.set_xlabel(y_col); ax.set_ylabel(x_col)
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Error al graficar: {e}")
