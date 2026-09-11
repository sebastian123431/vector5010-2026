# Herramienta generada automáticamente por Vector
# Descripción: Código generado para: generame un codigo en base a la ubicacion meteorologia en si y centrate en aprox
# Fecha de creación: 2026-09-10T17:54:17.428211

import pandas as pd

# Datos Meteorológicos (simulados - reemplázalos con tus datos reales)
data = {'Ubicación': ['Vicuña', 'Santiago'],
        'Temperatura (°C)': [15, 20],
        'Humedad (%)': [60, 70]}

df = pd.DataFrame(data)


# Calcular la probabilidad de lluvia por zona (basado en la temperatura y humedad)
def calcular_probabilidad_lluvia(temperatura, humedad):
    if temperatura < 15:
        return 0.2  # Probabilidad baja si es frío
    elif temperatura > 20:
        return 0.8 # Probabilidad alta si es calor
    else:
        return 0.5   #Probabilidad moderada

# Aplicar la función a cada zona
df['Probabilidad_lluvia'] = df['Ubicación'].apply(calcular_probabilidad_lluvia)


print(df[['Ubicación', 'Probabilidade_lluvia']]) # Muestra los resultados en un dataframe
