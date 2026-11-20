"""Demo con datos SINTÉTICOS para comprobar que el flujo completo corre sin el atlas real.

Genera (en ../ejemplo_sintetico/):
  atlas_sintetico.tif  campo inventado de Cs-137 en EPSG:3035 (zonas calientes alrededor de
                       Baviera/Austria/Rep. Checa; por debajo de 1,000 Bq/m2 = sin dato)
  dem_sintetico.tif    relieve inventado en lat/lon (cordillera E-O cerca de 47 N y una rampa
                       hacia el OSO de la central de Laguna Verde)
y ejecuta estadística zonal y perfiles sobre ellos.

LOS NÚMEROS DE ESTE DEMO NO SON DEL ATLAS NI DEL ARTÍCULO: solo prueban que el código corre.
Uso:  python demo_sintetico.py [--ne ruta/ne_10m_admin_0_countries.geojson]
"""
import argparse
import os

import numpy as np
import rasterio
from rasterio.transform import from_origin

import zonal_cs137 as zc
import perfiles_laguna_verde as lv
from distancias_paises import cargar_paises, PAISES_TABLA_I
from parametros import CNLV_LON, CNLV_LAT

SALIDA = os.path.join(os.path.dirname(__file__), "..", "ejemplo_sintetico")


def crear_atlas(ruta, rng):
    # EPSG:3035 (m). Ventana aproximada de Europa central.
    x0, y1, px = 3_800_000, 3_300_000, 5_000
    ncol, nfil = 360, 300
    x = x0 + (np.arange(ncol) + 0.5) * px
    y = y1 - (np.arange(nfil) + 0.5) * px
    X, Y = np.meshgrid(x, y)
    from pyproj import Transformer
    t = Transformer.from_crs(4326, 3035, always_xy=True)
    campo = np.zeros_like(X)
    # (lon, lat, amplitud Bq/m2, radio m): focos inventados
    for lon, lat, amp, rad in [(12.0, 48.3, 90_000, 150_000), (14.5, 47.3, 70_000, 120_000),
                               (15.5, 49.5, 30_000, 140_000), (8.5, 46.5, 25_000, 90_000),
                               (13.0, 51.0, 12_000, 150_000), (2.0, 47.0, 2_500, 200_000)]:
        cx, cy = t.transform(lon, lat)
        campo += amp * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * rad ** 2))
    campo *= rng.lognormal(0, 0.15, campo.shape)
    campo = np.clip(campo, 0, 120_000).astype("float32")
    campo[campo < 1_000] = -9999.0
    with rasterio.open(ruta, "w", driver="GTiff", height=nfil, width=ncol, count=1,
                       dtype="float32", crs="EPSG:3035", nodata=-9999.0,
                       transform=from_origin(x0, y1, px, px)) as dst:
        dst.write(campo, 1)


def crear_dem(ruta):
    res = 0.05
    lon = np.arange(-98.0, 16.0, res)
    lat = np.arange(50.0, 18.0, -res)
    LON, LAT = np.meshgrid(lon, lat)
    z = np.zeros_like(LON)
    # cordillera alpina inventada: E-O alrededor de 47 N, cresta ~2,800 m
    z += 2800 * np.exp(-((LAT - 47.0) / 0.9) ** 2) * np.exp(-((LON - 11.0) / 7.0) ** 2)
    # rampa inventada al OSO de Laguna Verde hasta ~2,500 m
    d = np.hypot((LON - CNLV_LON) * np.cos(np.radians(19.7)), LAT - CNLV_LAT) * 111.0
    z += np.where(LON < CNLV_LON, np.clip(d * 30, 0, 2500), 0) * (LAT > 18) * (LON > -98)
    with rasterio.open(ruta, "w", driver="GTiff", height=z.shape[0], width=z.shape[1], count=1,
                       dtype="float32", crs="EPSG:4326",
                       transform=from_origin(lon[0] - res / 2, lat[0] + res / 2, res, res)) as dst:
        dst.write(z.astype("float32"), 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--ne", help="GeoJSON de Natural Earth 10m (países)")
    a = ap.parse_args()
    os.makedirs(SALIDA, exist_ok=True)
    atlas = os.path.join(SALIDA, "atlas_sintetico.tif")
    dem = os.path.join(SALIDA, "dem_sintetico.tif")
    crear_atlas(atlas, np.random.default_rng(1986))
    crear_dem(dem)

    paises = cargar_paises(a.ne)
    df = zc.procesar(atlas, paises, list(PAISES_TABLA_I))
    df.to_csv(os.path.join(SALIDA, "zonal_sintetico.csv"), index=False)
    zc.mapa_clases(df, paises, os.path.join(SALIDA, "mapa_clases_sintetico.png"),
                  titulo="DATOS SINTÉTICOS (demo): intensidad promedio por país")
    print("\nZonal sobre atlas SINTÉTICO:")
    print(df[["pais", "distancia_km", "media_validas_Bq_m2", "media_con_cero_Bq_m2", "clase"]]
          .round(0).to_string(index=False))

    dA, zA = lv.perfil_meridiano(dem, lv.ALPES_LON, lv.ALPES_LAT_N, lv.ALPES_LAT_S)
    dB, zB = lv.perfil_acimut(dem, CNLV_LON, CNLV_LAT, lv.ACIMUT_PERFIL_LV, 150)
    lv.figura(dA, zA, dB, zB, os.path.join(SALIDA, "perfiles_sintetico.png"),
              titulo="RELIEVE SINTÉTICO (demo)")
    print("\nPerfiles sobre DEM SINTÉTICO guardados en ejemplo_sintetico/perfiles_sintetico.png")
