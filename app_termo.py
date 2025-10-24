# ============================================================
# app_termo.py
# Streamlit app para obtener propiedades termodinámicas
# con CoolProp o por interpolación de tablas
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
from CoolProp.CoolProp import PropsSI
from scipy.interpolate import RegularGridInterpolator, griddata
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURACIÓN BÁSICA
# ============================================================
st.set_page_config(page_title="TermoTables - Propiedades Termodinámicas", layout="wide")

st.title("📘 TermoTables - Propiedades Termodinámicas (CoolProp + Interpolación)")
st.write("""
Esta herramienta permite obtener propiedades termodinámicas de agua, refrigerantes y gases.
Puedes usar **CoolProp** para obtener propiedades directamente o **subir una tabla CSV** para interpolar valores.

### 🧮 Guía rápida de propiedades:
| Símbolo | Nombre | Unidad (SI) | Descripción breve |
|----------|---------|-------------|-------------------|
| **T** | Temperatura | K | Grado de agitación térmica |
| **P** | Presión | Pa | Fuerza ejercida por unidad de área |
| **D** | Densidad | kg/m³ | Masa por unidad de volumen |
| **H** | Entalpía | J/kg | Energía total (interna + PV) |
| **S** | Entropía | J/kg·K | Energía no disponible para trabajo |
| **V** | Volumen específico | m³/kg | Volumen ocupado por 1 kg |
| **CP** | Calor específico a P constante | J/kg·K | Energía para subir 1 K a P constante |
| **CV** | Calor específico a V constante | J/kg·K | Energía para subir 1 K a V constante |
""")

mode = st.radio("Selecciona modo de operación", ["CoolProp (propiedades)", "Tabla CSV (interpolación 2D)"])

# ============================================================
# MODO COOLPROP
# ============================================================
if mode == "CoolProp (propiedades)":
    st.subheader("📗 Obtener propiedades con CoolProp")

    fluid = st.text_input("Nombre del fluido (ejemplo: Water, R134a, Air)", "Water")

    outputs = st.multiselect(
        "Propiedades a obtener (CoolProp keys)",
        ["T", "P", "D", "H", "S", "V", "CP", "CV"],
        default=["T", "P", "D", "H"]
    )

    input1 = st.selectbox("Variable 1 (entrada)", ["T (C°)", "P (KPa)", "H (J/kg)", "D (kg/m³)"])
    input2 = st.selectbox("Variable 2 (entrada)", ["P (KPa)", "T (C°)", "H (J/kg)", "D (kg/m³)"])

    # Conversión de unidades amigables
    if "T" in input1:
        val1 = st.number_input("Temperatura (°C)", value=25.0)
    else:
        val1 = st.number_input("Valor 1", value=300.0)

    if "P" in input2:
        val2 = st.number_input("Presión (kPa)", value=101.325)
    else:
        val2 = st.number_input("Valor 2", value=101325.0)

    # Funciones de conversión
    T_in_K = lambda C: C + 273.15
    P_in_Pa = lambda kPa: kPa * 1000

    # Aplicar conversión antes del cálculo
    if "T" in input1:
        val1 = T_in_K(val1)
    if "P" in input1:
        val1 = P_in_Pa(val1)
    if "T" in input2:
        val2 = T_in_K(val2)
    if "P" in input2:
        val2 = P_in_Pa(val2)

    if st.button("Calcular propiedades"):
        input_map = {"T (K)": "T", "P (Pa)": "P", "H (J/kg)": "Hmass", "D (kg/m³)": "Dmass"}
        map_keys = {
            "T": "T", "P": "P", "D": "Dmass", "H": "Hmass", "S": "Smass",
            "V": "Vmass", "CP": "Cpmass", "CV": "Cvmass"
        }

        units_map = {
            "T": "K", "P": "Pa", "D": "kg/m³", "H": "J/kg", "S": "J/kg·K",
            "V": "m³/kg", "CP": "J/kg·K", "CV": "J/kg·K"
        }

        desc_map = {
            "T": "Temperatura",
            "P": "Presión",
            "D": "Densidad",
            "H": "Entalpía específica",
            "S": "Entropía específica",
            "V": "Volumen específico",
            "CP": "Calor específico a P constante",
            "CV": "Calor específico a V constante"
        }

        try:
            key1 = input_map[input1]
            key2 = input_map[input2]
            results = {}
            for out in outputs:
                out_key = map_keys.get(out, out)
                val = PropsSI(out_key, key1, float(val1), key2, float(val2), fluid)
                results[out] = val

            df = pd.DataFrame({
                "Propiedad": [desc_map[o] for o in results.keys()],
                "Símbolo": results.keys(),
                "Valor": results.values(),
                "Unidad": [units_map[o] for o in results.keys()]
            })
            st.success("✅ Cálculo exitoso")
            st.dataframe(df, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error al obtener propiedades: {e}\nRevisa nombre del fluido y valores válidos.")

# ============================================================
# MODO TABLA (CSV)
# ============================================================
else:
    st.subheader("📘 Interpolación 2D desde tabla CSV")
    uploaded = st.file_uploader("Sube CSV con columnas (x, y, propiedad)", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.write("Vista previa de datos:")
        st.dataframe(df.head())

        cols = df.columns.tolist()
        x_col = st.selectbox("Eje X (por ejemplo Temperatura)", cols, index=0)
        y_col = st.selectbox("Eje Y (por ejemplo Presión)", cols, index=1)
        prop_col = st.selectbox("Propiedad a interpolar", [c for c in cols if c not in (x_col, y_col)])
        method = st.selectbox("Método de interpolación", ["linear", "nearest", "cubic"])

        xq = st.number_input("Valor X a interpolar", value=float(df[x_col].median()))
        yq = st.number_input("Valor Y a interpolar", value=float(df[y_col].median()))

        if st.button("Interpolar"):
            try:
                xv = np.sort(df[x_col].unique())
                yv = np.sort(df[y_col].unique())
                pivot = df.pivot_table(index=x_col, columns=y_col, values=prop_col)
                if pivot.shape == (len(xv), len(yv)):
                    grid = pivot.values
                    interp = RegularGridInterpolator((xv, yv), grid, method=method, bounds_error=False, fill_value=None)
                    val = interp([[xq, yq]])[0]
                else:
                    pts = df[[x_col, y_col]].values
                    vals = df[prop_col].values
                    val = griddata(pts, vals, (xq, yq), method=method)
                st.success(f"Valor interpolado ≈ **{val:.5f}**")
            except Exception as e:
                st.error(f"No se pudo interpolar: {e}")

        if st.button("Graficar malla"):
            try:
                xv = np.sort(df[x_col].unique())
                yv = np.sort(df[y_col].unique())
                pivot = df.pivot_table(index=x_col, columns=y_col, values=prop_col)
                fig, ax = plt.subplots()
                c = ax.pcolormesh(yv, xv, pivot.values, shading='auto')
                fig.colorbar(c, ax=ax)
                ax.set_xlabel(y_col)
                ax.set_ylabel(x_col)
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Error al graficar: {e}")
