"""Convierte observaciones puntuales de Cs-137 (Bq/m2) en un GeoTIFF para zonal_cs137.py.

Pensado para la base de Evangeliou (2025), DOI 10.34355/NILU.00321 (CSV con columnas
LAT, NSflag, LON, EWflag, VALUE). Interpola por distancia inversa (IDW), como hacen los
autores para su malla de 0.1°, pero aquí sobre una malla equivalente (EPSG:3035).

IMPORTANTE: el resultado NO es el atlas de De Cort et al. (1998): es otra interpolación, hecha
con otros puntos y otros parámetros. Sirve para probar el flujo con datos reales; no debe
esperarse que reproduzca las intensidades por país del artículo.

Uso:
  python puntos_a_raster.py --csv DOI00321_data.csv --salida cs137_idw.tif
         [--res 5000] [--k 8] [--potencia 2] [--radio-km 75] [--tope 120000]
Celdas sin ningún punto a menos de --radio-km, o con valor < 1,000 Bq/m2, quedan "sin dato".
--tope recorta el máximo (en el artículo, 120,000 Bq/m2 es el techo de la simbología).
"""
import argparse

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from scipy.spatial import cKDTree

from parametros import CRS_ANALISIS, LIMITE_INFERIOR_ATLAS

# Ventana de la malla en EPSG:3035 (m): Europa central y occidental
X0, X1, Y0, Y1 = 3_000_000, 5_600_000, 1_700_000, 3_700_000


def leer_csv(ruta):
    d = pd.read_csv(ruta)
    d["lat"] = d["LAT"] * d["NSflag"]
    d["lon"] = d["LON"] * d["EWflag"]
    return d[np.isfinite(d["VALUE"]) & (d["VALUE"] > 0)]


def idw(xy, val, res, k=8, potencia=2.0, radio_m=75_000, tope=None):
    nx, ny = int((X1 - X0) / res), int((Y1 - Y0) / res)
    gx = X0 + (np.arange(nx) + 0.5) * res
    gy = Y1 - (np.arange(ny) + 0.5) * res
    GX, GY = np.meshgrid(gx, gy)
    celdas = np.column_stack([GX.ravel(), GY.ravel()])
    arbol = cKDTree(xy)
    dist, idx = arbol.query(celdas, k=k, distance_upper_bound=radio_m)
    v = np.where(np.isfinite(dist), val[np.minimum(idx, len(val) - 1)], np.nan)
    w = np.where(np.isfinite(dist), 1.0 / np.maximum(dist, 1.0) ** potencia, 0.0)
    suma_w = w.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.nansum(np.where(w > 0, v * w, 0.0), axis=1) / suma_w
    z[suma_w == 0] = np.nan
    if tope is not None:
        z = np.minimum(z, tope)
    z[z < LIMITE_INFERIOR_ATLAS] = np.nan
    return z.reshape(ny, nx).astype("float32")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--salida", default="cs137_idw.tif")
    ap.add_argument("--res", type=float, default=5000, help="tamaño de celda (m)")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--potencia", type=float, default=2.0)
    ap.add_argument("--radio-km", type=float, default=75)
    ap.add_argument("--tope", type=float, default=120_000)
    a = ap.parse_args()

    d = leer_csv(a.csv)
    t = Transformer.from_crs(4326, CRS_ANALISIS, always_xy=True)
    x, y = t.transform(d["lon"].to_numpy(), d["lat"].to_numpy())
    xy = np.column_stack([x, y])
    dentro = (xy[:, 0] > X0 - 100_000) & (xy[:, 0] < X1 + 100_000) & \
             (xy[:, 1] > Y0 - 100_000) & (xy[:, 1] < Y1 + 100_000)
    print(f"{dentro.sum()} puntos dentro de la ventana de {len(d)}")
    z = idw(xy[dentro], d["VALUE"].to_numpy()[dentro], a.res, a.k, a.potencia,
            a.radio_km * 1000, a.tope)
    with rasterio.open(a.salida, "w", driver="GTiff", height=z.shape[0], width=z.shape[1],
                       count=1, dtype="float32", crs=CRS_ANALISIS, nodata=-9999.0,
                       transform=from_origin(X0, Y1, a.res, a.res), compress="deflate") as dst:
        dst.write(np.where(np.isfinite(z), z, -9999.0).astype("float32"), 1)
    print(f"Guardado {a.salida}: {np.isfinite(z).sum()} celdas con dato de {z.size}")
