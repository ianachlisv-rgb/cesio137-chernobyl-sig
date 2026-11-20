"""Perfiles topográficos comparativos y geometría de la CNLV (Tabla III, Fig. 6).

Perfiles (sección III-F del artículo), con interpolación bilineal cada 2 km:
  (a) Alpes orientales: transecto N-S a lo largo de 12 E, de 49 N a 45.3 N.
  (b) Laguna Verde: desde la central hacia el WSW (acimut 252°) hacia el Cofre de Perote.
El artículo usa ETOPO1 reescalada a 10' (suaviza cumbres).

Uso:
  python perfiles_laguna_verde.py --solo-tabla                  # Tabla III, sin DEM
  python perfiles_laguna_verde.py --dem etopo1_10min.tif [--salida perfiles.png]
El DEM debe ser un GeoTIFF en lat/lon (EPSG:4326), elevaciones en metros.
"""
import argparse

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pyproj import Geod
from rasterio.windows import from_bounds
from scipy.ndimage import map_coordinates

from parametros import (CNLV_LON, CNLV_LAT, ZVP_KM, ZVI_KM, ACIMUT_PERFIL_LV, ALPES_LON,
                        ALPES_LAT_N, ALPES_LAT_S, PASO_PERFIL_KM)

GEOD = Geod(ellps="WGS84")

# Sitios de referencia (Tabla III): nombre -> (lon, lat). Coordenadas aproximadas.
SITIOS = {
    "Xalapa": (-96.9102, 19.5438),
    "Veracruz (puerto)": (-96.1342, 19.1738),
    "Cofre de Perote": (-97.1494, 19.4936),
    "Pico de Orizaba": (-97.2700, 19.0300),
}


def zona_pere(dist_km):
    if dist_km <= ZVP_KM:
        return "ZVP"
    if dist_km < ZVI_KM - 3:
        return "ZVI"
    if dist_km <= ZVI_KM + 3:
        return "Límite ZVI"
    return "Fuera"


def tabla_iii():
    """Distancia, acimut y zona PERE de cada sitio respecto a la CNLV."""
    filas = []
    for n, (lo, la) in SITIOS.items():
        az, _, d = GEOD.inv(CNLV_LON, CNLV_LAT, lo, la)
        filas.append((n, d / 1000.0, az % 360, zona_pere(d / 1000.0)))
    return filas


def muestrear(dem_path, lons, lats):
    """Elevación por interpolación bilineal en los puntos dados."""
    with rasterio.open(dem_path) as ds:
        pad = 2 * max(ds.res)
        w = from_bounds(lons.min() - pad, lats.min() - pad, lons.max() + pad, lats.max() + pad,
                        ds.transform).round_offsets().round_lengths()
        arr = ds.read(1, window=w, boundless=True, fill_value=np.nan).astype(float)
        if ds.nodata is not None:
            arr[arr == ds.nodata] = np.nan
        t = ds.window_transform(w)
    col = (lons - t.c) / t.a - 0.5
    fila = (lats - t.f) / t.e - 0.5
    return map_coordinates(arr, [fila, col], order=1, mode="nearest")


def perfil_acimut(dem, lon0, lat0, acimut, largo_km, paso_km=PASO_PERFIL_KM):
    d = np.arange(0, largo_km + paso_km, paso_km, dtype=float)
    lons, lats, _ = GEOD.fwd(np.full_like(d, lon0), np.full_like(d, lat0),
                             np.full_like(d, acimut), d * 1000.0)
    return d, muestrear(dem, np.asarray(lons), np.asarray(lats))


def perfil_meridiano(dem, lon, lat_n, lat_s, paso_km=PASO_PERFIL_KM):
    largo = GEOD.inv(lon, lat_n, lon, lat_s)[2] / 1000.0
    d = np.arange(0, largo + paso_km, paso_km, dtype=float)
    lons, lats, _ = GEOD.fwd(np.full_like(d, lon), np.full_like(d, lat_n),
                             np.full_like(d, 180.0), d * 1000.0)
    return d, muestrear(dem, np.asarray(lons), np.asarray(lats))


def pendiente_media(d, z, d_inicio=0.0):
    """Ascenso (m), distancia (km) y pendiente media (m/km) desde d_inicio hasta la cota máxima."""
    i0 = int(np.argmin(np.abs(d - d_inicio)))
    imax = i0 + int(np.nanargmax(z[i0:]))
    ascenso = z[imax] - z[i0]
    dist = d[imax] - d[i0]
    return ascenso, dist, ascenso / dist if dist > 0 else np.nan, z[imax]


def figura(dA, zA, dB, zB, ruta, titulo=None):
    fig, ax = plt.subplots(2, 1, figsize=(7, 6.4))
    if titulo:
        fig.suptitle(titulo, color="crimson", fontweight="bold")
    ax[0].fill_between(dA, zA, color="#9ecae1"); ax[0].plot(dA, zA, "b", lw=1)
    ax[0].set_title("(a) Alpes orientales: transecto N-S a lo largo de 12°E")
    ax[0].set_xlabel("Distancia desde 49°N (km)"); ax[0].set_ylabel("Altitud (m)")
    ax[1].fill_between(dB, zB, color="#fdd0a2"); ax[1].plot(dB, zB, color="#d94801", lw=1)
    ax[1].axvline(ZVI_KM, color="r", ls="--", label=f"Límite ZVI ({ZVI_KM} km)")
    ax[1].set_title(f"(b) Laguna Verde: transecto hacia el OSO (acimut {ACIMUT_PERFIL_LV}°)")
    ax[1].set_xlabel("Distancia desde la central (km)"); ax[1].set_ylabel("Altitud (m)")
    ax[1].legend()
    fig.tight_layout(); fig.savefig(ruta, dpi=200); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dem", help="GeoTIFF lat/lon (ETOPO1 a 10' en el artículo)")
    ap.add_argument("--solo-tabla", action="store_true", help="Solo la Tabla III (sin DEM)")
    ap.add_argument("--salida", default="perfiles.png")
    a = ap.parse_args()

    print("Tabla III - sitios respecto a la CNLV")
    print(f"{'Sitio':20s}{'Dist (km)':>10s}{'Acimut':>8s}  Zona PERE")
    for n, d, az, z in tabla_iii():
        print(f"{n:20s}{d:10.0f}{az:8.0f}  {z}")
    if a.solo_tabla or not a.dem:
        raise SystemExit(0)

    dA, zA = perfil_meridiano(a.dem, ALPES_LON, ALPES_LAT_N, ALPES_LAT_S)
    dB, zB = perfil_acimut(a.dem, CNLV_LON, CNLV_LAT, ACIMUT_PERFIL_LV, 150)
    # Alpes: el artículo mide el ascenso desde 48 N hasta la cresta suavizada
    d48 = GEOD.inv(ALPES_LON, ALPES_LAT_N, ALPES_LON, 48.0)[2] / 1000.0
    asc, dist, pend, zmax = pendiente_media(dA, zA, d_inicio=d48)
    print(f"\nAlpes (48°N -> cresta): +{asc:,.0f} m en {dist:.0f} km = {pend:.0f} m/km (cota máx. {zmax:,.0f} m)")
    asc, dist, pend, zmax = pendiente_media(dB, zB)
    print(f"Laguna Verde -> cresta: +{asc:,.0f} m en {dist:.0f} km = {pend:.0f} m/km (cota máx. {zmax:,.0f} m)")
    figura(dA, zA, dB, zB, a.salida)
    print(f"Figura: {a.salida}")
