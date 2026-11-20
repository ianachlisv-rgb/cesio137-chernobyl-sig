"""Estadística zonal del Cs-137 por país + clase de intensidad + distancia (Tabla I, Fig. 3).

Pasos (secciones III-B a III-D del artículo):
  1. Atlas europeo de deposición de Cs-137 (matriz en Bq/m2) -> proyección equivalente.
  2. Intensidad promedio por país (estadística zonal con Natural Earth 1:10m).
  3. Clasificación: < 6,000 | 6,000-28,000 | 28,000-120,000 Bq/m2.
  4. Distancia geodésica a Chernobyl (distancias_paises.py).

IMPORTANTE (sesgo declarado en la sección IV-E del artículo): la simbología del atlas
empieza en 1,000 Bq/m2 y lo que está por debajo es "sin dato". Si esas celdas se
ignoran, el promedio solo considera zonas contaminadas y sale SOBRESTIMADO.
Por eso el script calcula dos promedios:
  media_validas   -> ignora celdas sin dato (lo que describe el artículo)
  media_con_cero  -> cuenta las celdas sin dato dentro del país como 0 (cota inferior)
El valor real queda entre ambos.

Uso:
  python zonal_cs137.py --atlas atlas_cs137.tif [--ne ne_10m_admin_0_countries.geojson]
         [--paises Austria,Germany,...] [--prefijo salida/europa]
El raster del atlas debe estar en Bq/m2 (cualquier CRS; se reproyecta a EPSG:3035).
"""
import argparse
import os

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import raster_geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling

from parametros import (CRS_ANALISIS, CLASES, ETIQUETAS_CLASES, LIMITE_INFERIOR_ATLAS)
from distancias_paises import (cargar_paises, geometria_analisis, distancia_km,
                               PAISES_TABLA_I)


def clasificar(valor):
    """Índice de clase (0,1,2) según los límites del artículo; None si no hay dato."""
    if not np.isfinite(valor):
        return None
    for i, (lo, hi) in enumerate(CLASES):
        if valor < hi:
            return i
    return len(CLASES) - 1


def media_zonal(src, geom_3035, limite_inferior=LIMITE_INFERIOR_ATLAS):
    """Devuelve (media_validas, media_con_cero, n_validas, n_total) para una geometría.

    n_total cuenta TODAS las celdas dentro del país (con o sin dato), para poder medir
    cuánto cubre realmente el atlas.
    """
    fuera, _, ventana = raster_geometry_mask(src, [geom_3035], crop=True, all_touched=False)
    vals = src.read(1, window=ventana).astype(float)
    if src.nodata is not None:
        vals[vals == src.nodata] = np.nan
    vals[vals < limite_inferior] = np.nan           # por debajo de 1,000 = sin dato
    dentro = ~fuera
    validas = np.isfinite(vals) & dentro
    n_total = int(dentro.sum())
    n_val = int(validas.sum())
    if n_val == 0:
        return np.nan, np.nan, 0, n_total
    media_val = float(vals[validas].mean())
    media_cero = float(vals[validas].sum() / n_total)
    return media_val, media_cero, n_val, n_total


def procesar(atlas, paises, nombres_ne):
    filas = []
    with rasterio.open(atlas) as ds:
        with WarpedVRT(ds, crs=CRS_ANALISIS, resampling=Resampling.nearest) as src:
            for n in nombres_ne:
                r = paises[paises["NAME"] == n]
                if r.empty:
                    print(f"  (no se encontró {n} en Natural Earth)")
                    continue
                geom = geometria_analisis(n, r.iloc[0].geometry)
                g3035 = gpd.GeoSeries([geom], crs=4326).to_crs(CRS_ANALISIS).iloc[0]
                m_val, m_cero, n_val, n_tot = media_zonal(src, g3035)
                filas.append({
                    "pais_ne": n,
                    "pais": PAISES_TABLA_I.get(n, n),
                    "distancia_km": distancia_km(geom),
                    "media_validas_Bq_m2": m_val,
                    "media_con_cero_Bq_m2": m_cero,
                    "celdas_validas": n_val,
                    "celdas_pais": n_tot,
                    "clase": (ETIQUETAS_CLASES[clasificar(m_val)]
                              if clasificar(m_val) is not None else "sin dato"),
                })
    return pd.DataFrame(filas).sort_values("distancia_km")


def mapa_clases(df, paises, ruta_png, titulo="Cs-137: intensidad promedio por país (Bq/m²)"):
    """Mapa de vulnerabilidad territorial por país (como la Fig. 3 del artículo).
    Usa la misma geometría del análisis (Francia = solo la parte continental)."""
    colores = ["#fff200", "#f58220", "#d7261e"]
    geoms = []
    for n in df["pais_ne"]:
        g = paises[paises["NAME"] == n].iloc[0].geometry
        geoms.append(geometria_analisis(n, g))
    p = gpd.GeoDataFrame(df[["pais_ne", "clase"]].reset_index(drop=True),
                         geometry=geoms, crs=4326).to_crs(CRS_ANALISIS)
    fig, ax = plt.subplots(figsize=(7, 6))
    for i, et in enumerate(ETIQUETAS_CLASES):
        sub = p[p["clase"] == et]
        if len(sub):
            sub.plot(ax=ax, color=colores[i], edgecolor="k", linewidth=0.4, label=et)
    ax.set_title(titulo)
    ax.legend(title="Clase", loc="lower left")
    ax.set_axis_off()
    fig.savefig(ruta_png, dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--atlas", required=True, help="GeoTIFF del atlas de Cs-137 en Bq/m2")
    ap.add_argument("--ne", help="GeoJSON Natural Earth 10m países")
    ap.add_argument("--paises", help="Nombres Natural Earth separados por coma (por defecto: los 9 de la Tabla I)")
    ap.add_argument("--prefijo", default="resultado_zonal", help="Prefijo de archivos de salida")
    a = ap.parse_args()
    nombres = a.paises.split(",") if a.paises else list(PAISES_TABLA_I)
    pa = cargar_paises(a.ne)
    df = procesar(a.atlas, pa, nombres)
    os.makedirs(os.path.dirname(a.prefijo) or ".", exist_ok=True)
    df.to_csv(a.prefijo + ".csv", index=False)
    mapa_clases(df, pa, a.prefijo + "_mapa_clases.png")
    print(df[["pais", "distancia_km", "media_validas_Bq_m2", "media_con_cero_Bq_m2", "clase"]]
          .round(0).to_string(index=False))
    print(f"\nGuardado: {a.prefijo}.csv y {a.prefijo}_mapa_clases.png")
