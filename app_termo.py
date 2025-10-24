# ============================================================
# app_termo.py  —  TermoTables (CoolProp)
# Estado general (2 entradas) + Saturación (1 entrada + Q)
# Unidades amigables: °C, kPa, kJ/kg, etc. (conversión interna)
# ============================================================

import streamlit as st
import pandas as pd
from CoolProp.CoolProp import PropsSI

st.set_page_config(page_title="TermoTables - CoolProp", layout="wide")

st.title("📘 TermoTables — Propiedades Termodinámicas (CoolProp)")
st.write("""
Obtén propiedades de **agua, refrigerantes y gases** usando **CoolProp**.
- **Estado general:** ingresa 2 propiedades independientes (p. ej., T y P).
- **Saturación:** ingresa P **o** T y una **calidad (Q)**: 0 = líquido saturado, 1 = vapor saturado.
""")

with st.expander("🧮 Guía rápida de propiedades (símbolo, unidad, descripción)"):
    st.markdown("""
| Símbolo | Unidad (SI) | Descripción breve |
|---|---|---|
| **T** | K | Temperatura |
| **P** | Pa | Presión |
| **D** | kg/m³ | Densidad |
| **H** | J/kg | Entalpía específica |
| **S** | J/kg·K | Entropía específica |
| **V** | m³/kg | Volumen específico |
| **CP** | J/kg·K | Calor específico a P constante |
| **CV** | J/kg·K | Calor específico a V constante |
""")

# --------------------------
# Utilidades
# --------------------------
UNITS_OUT = {
    "T": "K", "P": "Pa", "D": "kg/m³", "H": "J/kg", "S": "J/kg·K",
    "V": "m³/kg", "CP": "J/kg·K", "CV": "J/kg·K"
}
DESC = {
    "T": "Temperatura",
    "P": "Presión",
    "D": "Densidad",
    "H": "Entalpía específica",
    "S": "Entropía específica",
    "V": "Volumen específico",
    "CP": "Calor específico a P constante",
    "CV": "Calor específico a V constante",
}
OUT_KEYS = {  # mapeo símbolo -> clave CoolProp
    "T": "T", "P": "P", "D": "Dmass", "H": "Hmass", "S": "Smass",
    "V": "Vmass", "CP": "Cpmass", "CV": "Cvmass"
}
IN_KEYS = {   # mapeo símbolo -> clave CoolProp input
    "T": "T", "P": "P", "H": "Hmass", "D": "Dmass"
}

def to_SI(symbol: str, value: float, unit: str) -> float:
    """Convierte valor ingresado en unidad amigable a SI para CoolProp."""
    if symbol == "T":
        return value + 273.15 if unit == "°C" else value
    if symbol == "P":
        return value * 1_000 if unit == "kPa" else value
    if symbol == "H":
        return value * 1_000 if unit == "kJ/kg" else value
    # D en kg/m³ ya es SI
    return value

# --------------------------
# UI Fluido
# --------------------------
st.subheader("1) Fluido")
common_fluids = [
    "Water", "Air", "R134a", "R22", "R410A", "R32", "CO2", "Ammonia",
    "Methane", "Propane", "Butane", "Ethanol", "Oxygen", "Nitrogen"
]
fluid = st.selectbox("Selecciona fluido", common_fluids, index=0)
custom = st.text_input("Otro fluido (opcional)", "")
if custom.strip():
    fluid = custom.strip()

# --------------------------
# Modo de cálculo
# --------------------------
st.subheader("2) Modo de cálculo")
mode = st.radio("Elige un modo", ["Estado general (2 entradas)", "Saturación (1 entrada + Q)"])

# --------------------------
# Entradas
# --------------------------
st.subheader("3) Entradas")

def input_with_units(label_symbol: str):
    """Devuelve valor en SI a partir de inputs con selector de unidades."""
    if label_symbol == "T":
        unit = st.selectbox(f"Unidad de T", ["°C", "K"], key=f"uT_{st.session_state.get('uid',0)}")
        val = st.number_input(f"T ({unit})", value=25.0 if unit=="°C" else 298.15, key=f"vT_{st.session_state.get('uid',0)}")
        return to_SI("T", val, unit)
    if label_symbol == "P":
        unit = st.selectbox(f"Unidad de P", ["kPa", "Pa"], key=f"uP_{st.session_state.get('uid',0)}")
        val = st.number_input(f"P ({unit})", value=101.325 if unit=="kPa" else 101325.0, key=f"vP_{st.session_state.get('uid',0)}")
        return to_SI("P", val, unit)
    if label_symbol == "H":
        unit = st.selectbox(f"Unidad de H", ["kJ/kg", "J/kg"], key=f"uH_{st.session_state.get('uid',0)}")
        val = st.number_input(f"H ({unit})", value=200.0 if unit=="kJ/kg" else 200000.0, key=f"vH_{st.session_state.get('uid',0)}")
        return to_SI("H", val, unit)
    if label_symbol == "D":
        unit = "kg/m³"
        val = st.number_input(f"D ({unit})", value=1.0, key=f"vD_{st.session_state.get('uid',0)}")
        return val
    raise ValueError("Símbolo no soportado")

outputs = st.multiselect(
    "Propiedades a obtener",
    ["T","P","D","H","S","V","CP","CV"],
    default=["T","P","D","H"]
)

if mode == "Estado general (2 entradas)":
    col1, col2 = st.columns(2)
    with col1:
        var1 = st.selectbox("Variable 1", ["T","P","H","D"], index=0)
        st.session_state["uid"] = 1
        val1_SI = input_with_units(var1)
    with col2:
        var2 = st.selectbox("Variable 2", ["P","T","H","D"], index=0)
        st.session_state["uid"] = 2
        val2_SI = input_with_units(var2)

    if st.button("Calcular (Estado general)"):
        try:
            res = {}
            k1 = IN_KEYS[var1]; k2 = IN_KEYS[var2]
            for out in outputs:
                res[out] = PropsSI(OUT_KEYS[out], k1, float(val1_SI), k2, float(val2_SI), fluid)
            df = pd.DataFrame({
                "Propiedad": [DESC[o] for o in res.keys()],
                "Símbolo": list(res.keys()),
                "Valor (SI)": list(res.values()),
                "Unidad": [UNITS_OUT[o] for o in res.keys()]
            })
            st.success(f"✅ Cálculo exitoso para **{fluid}** (Estado general)")
            st.dataframe(df, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error: {e}\n• Verifica que el par de entradas sea físicamente válido para **{fluid}**.\n• Si estás usando un punto de **saturación**, prueba el modo Saturación.")

else:
    # Saturación: usa P o T + Q
    sat_by = st.selectbox("Variable de saturación", ["P","T"], help="Elige si das P o T para saturación")
    if sat_by == "P":
        st.session_state["uid"] = 3
        P_SI = input_with_units("P")
        # T_sat a esa P (opcional mostrar)
        try:
            T_sat = PropsSI("T", "P", P_SI, "Q", 0, fluid)
            st.info(f"T_sat ≈ {T_sat - 273.15:.3f} °C a {P_SI/1000:.3f} kPa")
        except Exception:
            pass
        Q = st.slider("Calidad (Q)", 0.0, 1.0, 0.0, help="0 = líquido sat., 1 = vapor sat.")
        in1_key, in1_val = "P", P_SI
    else:
        st.session_state["uid"] = 4
        T_SI = input_with_units("T")
        try:
            P_sat = PropsSI("P", "T", T_SI, "Q", 0, fluid)
            st.info(f"P_sat ≈ {P_sat/1000:.3f} kPa a {T_SI-273.15:.3f} °C")
        except Exception:
            pass
        Q = st.slider("Calidad (Q)", 0.0, 1.0, 1.0, help="0 = líquido sat., 1 = vapor sat.")
        in1_key, in1_val = "T", T_SI

    if st.button("Calcular (Saturación)"):
        try:
            res = {}
            for out in outputs:
                res[out] = PropsSI(OUT_KEYS[out], in1_key, float(in1_val), "Q", float(Q), fluid)
            df = pd.DataFrame({
                "Propiedad": [DESC[o] for o in res.keys()],
                "Símbolo": list(res.keys()),
                "Valor (SI)": list(res.values()),
                "Unidad": [UNITS_OUT[o] for o in res.keys()]
            })
            st.success(f"✅ Cálculo exitoso para **{fluid}** (Saturación, Q={Q:.2f})")
            st.dataframe(df, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error: {e}\n• Verifica que la P/T de saturación esté dentro del rango del fluido.")
