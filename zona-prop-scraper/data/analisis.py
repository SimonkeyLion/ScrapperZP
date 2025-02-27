
import pandas as pd

# 1) Carga del CSV (cambia 'departamentos.csv' si tu archivo se llama distinto)
df = pd.read_csv('departamentos-alquiler-coghlan-saavedra-con-balcon-1-ambiente-2025-02-26-09-41-30.csv')

# 2) Echa un primer vistazo a los datos
print("Primeras filas del DataFrame:")
print(df.head(), "\n")

print("Información general del DataFrame:")
print(df.info(), "\n")

# 3) Estadísticas descriptivas de las variables numéricas
print("Estadísticas descriptivas:")
print(df.describe(), "\n")

# 4) Precio promedio
precio_promedio = df['precio'].mean()
print(f"Precio promedio: {precio_promedio:.2f}")

# 5) m2 promedio
m2_promedio = df['m2'].mean()
print(f"m2 promedio: {m2_promedio:.2f}")

# 6) Calculamos la relación global (precio promedio / m2 promedio)
ratio_global = precio_promedio / m2_promedio
print(f"Precio promedio / m2 promedio: {ratio_global:.2f}")

# 7) Calculamos la columna precio_por_m2 para cada fila
df['precio_por_m2'] = df['precio'] / df['m2']
precio_promedio_por_m2 = df['precio_por_m2'].mean()
print(f"Precio promedio por m2 (promediando cada propiedad): {precio_promedio_por_m2:.2f}")

# 8) Agrupar por barrio para ver precio/m2 promedio
#    Solo si tu archivo tiene una columna llamada 'barrio'
if 'barrio' in df.columns:
    df_grouped = df.groupby('barrio')['precio_por_m2'].mean().reset_index()
    df_grouped = df_grouped.sort_values(by='precio_por_m2', ascending=False)
    
    print("\nPrecio promedio por m2 agrupado por barrio:")
    print(df_grouped)
