"""Distancia geodésica Chernobyl -> centroide de cada país (Tabla I del artículo).

Pasos (sección III-D del artículo):
  1. Límites de países Natural Earth 1:10m.
  2. Proyección equivalente (LAEA) y centroide del polígono de cada país.
     Francia: solo territorio metropolitano continental (sin Córcega ni ultramar).
  3. Distancia geodésica sobre el elipsoide WGS84 desde Chernobyl (51.389 N, 30.100 E).

Uso:
  python distancias_paises.py [--ne ruta/ne_10m_admin_0_countries.geojson] [--salida distancias.csv]
Sin --ne, descarga el archivo desde GitHub (≈13 MB) y lo guarda en ../datos/.
"""
import argparse
import os
import urllib.request

import geopandas as gpd
import pandas as pd
from pyproj import Geod
from shapely.geometry import MultiPolygon

from parametros import (CHERNOBYL_LON, CHERNOBYL_LAT, CRS_ANALISIS, URL_NATURAL_EARTH)

# Nombre en Natural Earth -> nombre en la Tabla I
PAISES_TABLA_I = {
    "Czechia": "República Checa", "Austria": "Austria", "Slovenia": "Eslovenia",
    "Germany": "Alemania", "Italy": "Italia", "Switzerland": "Suiza",
    "Luxembourg": "Luxemburgo", "Belgium": "Bélgica", "France": "Francia",
}
# Valores publicados en la Tabla I (km)
TABLA_I_KM = {"Czechia": 1061, "Austria": 1230, "Slovenia": 1265, "Germany": 1375,
              "Italy": 1660, "Switzerland": 1671, "Luxembourg": 1704,
              "Belgium": 1779, "France": 2079}

GEOD = Geod(ellps="WGS84")


def cargar_paises(ruta=None):
    """Lee Natural Earth 10m; si no existe localmente lo descarga."""
    if ruta is None:
        ruta = os.path.join(os.path.dirname(__file__), "..", "datos",
                            "ne_10m_admin_0_countries.geojson")
    if not os.path.exists(ruta):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        print("Descargando Natural Earth 1:10m ...")
        urllib.request.urlretrieve(URL_NATURAL_EARTH, ruta)
    return gpd.read_file(ruta)


def geometria_analisis(nombre_ne, geom):
    """Geometría usada para el centroide. Francia = solo la parte continental."""
    if nombre_ne == "France":
        partes = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
        # el polígono más grande dentro de Europa occidental (excluye Guayana, Córcega...)
        europeas = [p for p in partes if -6 < p.centroid.x < 10 and p.centroid.y > 41]
        return max(europeas, key=lambda p: p.area)
    return geom


def distancia_km(geom, crs=CRS_ANALISIS):
    """Distancia geodésica WGS84 (km) de Chernobyl al centroide (calculado en `crs`)."""
    centro = gpd.GeoSeries([geom], crs=4326).to_crs(crs).centroid.to_crs(4326).iloc[0]
    return GEOD.inv(CHERNOBYL_LON, CHERNOBYL_LAT, centro.x, centro.y)[2] / 1000.0


def calcular(paises, nombres_ne):
    filas = []
    for n in nombres_ne:
        r = paises[paises["NAME"] == n]
        if r.empty:
            continue
        geom = geometria_analisis(n, r.iloc[0].geometry)
        filas.append({"pais_ne": n, "distancia_km": distancia_km(geom)})
    return pd.DataFrame(filas)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--ne", help="GeoJSON de Natural Earth 10m (países)")
    ap.add_argument("--salida", default="distancias.csv")
    a = ap.parse_args()
    p = cargar_paises(a.ne)
    df = calcular(p, list(PAISES_TABLA_I))
    df["pais"] = df["pais_ne"].map(PAISES_TABLA_I)
    df["tabla_I_km"] = df["pais_ne"].map(TABLA_I_KM)
    df["dif_km"] = df["distancia_km"] - df["tabla_I_km"]
    df = df.sort_values("distancia_km")
    df.to_csv(a.salida, index=False)
    print(df[["pais", "distancia_km", "tabla_I_km", "dif_km"]].round(1).to_string(index=False))
