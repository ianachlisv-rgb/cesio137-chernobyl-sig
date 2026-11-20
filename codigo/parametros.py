"""Parámetros del flujo de trabajo, tomados del artículo
"Reconstrucción geoespacial del fallout atmosférico de Chernobyl (1986-2020)".

Los valores marcados con [paper] están escritos en el artículo.
Los marcados con [deducido] se dedujeron comprobando que reproducen las tablas del
artículo (ver verificar_paper.py).
"""

# --- Fuente: central de Chernobyl -------------------------------------------
CHERNOBYL_LON = 30.100   # [paper] 51.389 N, 30.100 E
CHERNOBYL_LAT = 51.389

# --- Decaimiento radiactivo -----------------------------------------------------
T_MEDIO_CS137 = 30.05    # años [paper] (Pearce 2008, NPL)
UMBRAL_CONTAMINADO = 37_000  # Bq/m2 = 37 kBq/m2 [paper]

# --- Proyección de análisis -----------------------------------------------------
# El artículo dice "GRS_1980_Lambert_Azimuthal_Equal_Area" (equivalente, centrada en
# Europa). EPSG:3035 (ETRS89-LAEA) con el centroide de cada país reproduce las 9
# distancias de la Tabla I. [deducido]
CRS_ANALISIS = "EPSG:3035"

# --- Clases de intensidad promedio por país (Bq/m2) [paper] ---------------------
CLASES = [(0, 6_000), (6_000, 28_000), (28_000, 120_000)]
ETIQUETAS_CLASES = ["< 6,000", "6,000 - 28,000", "28,000 - 120,000"]
# La simbología del atlas empieza en 1,000 Bq/m2: lo que está por debajo es "sin dato"
LIMITE_INFERIOR_ATLAS = 1_000      # [paper]
LIMITE_SUPERIOR_SIMBOLOGIA = 120_000  # [paper] viene de la simbología, no de la medición

# --- Datos geográficos ----------------------------------------------------------
# Natural Earth 1:10m, límites de países [paper]
URL_NATURAL_EARTH = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
                     "master/geojson/ne_10m_admin_0_countries.geojson")

# --- Central Nucleoeléctrica Laguna Verde (CNLV) --------------------------------
CNLV_LON = -96.4064   # [deducido] reproduce las 4 filas de la Tabla III
CNLV_LAT = 19.7206
ZVP_KM = 16           # Zona Vía Pluma  [paper]
ZVI_KM = 80           # Zona Vía Ingestión [paper]
ACIMUT_PERFIL_LV = 252   # perfil desde la CNLV hacia el Cofre de Perote [paper]

# Perfil de los Alpes orientales: N-S a lo largo de 12 E, de 49 N a 45.3 N [paper]
ALPES_LON = 12.0
ALPES_LAT_N = 49.0
ALPES_LAT_S = 45.3
PASO_PERFIL_KM = 2    # muestreo cada 2 km con interpolación bilineal [paper]
