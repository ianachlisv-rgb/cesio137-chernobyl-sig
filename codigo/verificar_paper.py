"""Comprueba que el código reproduce las cifras publicadas en el artículo.

Verifica (sin necesitar el atlas de Cs-137 ni el DEM):
  - Tabla I   : distancias geodésicas Chernobyl -> centroide de cada país
  - Tabla II  : decaimiento 1986 / 2020 / 2026
  - Texto     : año en que el pico baja del umbral de 37 kBq/m2 (~2037) y factores de decaimiento
  - Tabla III : distancia, acimut y zona PERE de sitios de referencia de Laguna Verde

Uso:  python verificar_paper.py [--ne ruta/ne_10m_admin_0_countries.geojson]
Termina con código distinto de 0 si algo no coincide.
"""
import argparse
import sys

from parametros import LIMITE_SUPERIOR_SIMBOLOGIA
import decaimiento
import distancias_paises as dp
import perfiles_laguna_verde as lv

# Valores del artículo
TABLA_II = {  # referencia: (2020, 2026) en Bq/m2
    "Pico máximo": (54_775, 47_695),
    "Límite de clase superior": (12_781, 11_129),
    "Límite de clase inferior": (2_739, 2_385),
    "Mínimo cartografiado": (456, 397),
}
TABLA_III = {  # sitio: (km, acimut, zona)
    "Xalapa": (56, 250, "ZVI"),
    "Veracruz (puerto)": (67, 155, "ZVI"),
    "Cofre de Perote": (82, 252, "Límite ZVI"),
    "Pico de Orizaba": (119, 230, "Fuera"),
}

fallos = 0


def chequeo(nombre, ok, detalle=""):
    global fallos
    print(f"[{'OK ' if ok else 'FALLA'}] {nombre} {detalle}")
    if not ok:
        fallos += 1


def main(ruta_ne):
    # --- Tabla II ---
    tab = decaimiento.tabla_ii()
    for nombre, (e20, e26) in TABLA_II.items():
        _, c20, c26 = tab[nombre]
        chequeo(f"Tabla II · {nombre}", round(c20) == e20 and round(c26) == e26,
                f"(calculado {c20:,.0f} / {c26:,.0f}; artículo {e20:,} / {e26:,})")
    t = decaimiento.anios_hasta_umbral(LIMITE_SUPERIOR_SIMBOLOGIA)
    chequeo("Texto · pico < 37 kBq/m2 hacia 2037 (51 años)", round(t) == 51 and round(1986 + t) == 2037,
            f"(t = {t:.1f} años -> {1986 + t:.0f})")
    chequeo("Texto · 45.6 % del inventario en 2020", round(100 * decaimiento.factor(34), 1) == 45.6,
            f"({100 * decaimiento.factor(34):.1f} %)")

    # --- Tabla I ---
    paises = dp.cargar_paises(ruta_ne)
    df = dp.calcular(paises, list(dp.TABLA_I_KM))
    for _, r in df.iterrows():
        esperado = dp.TABLA_I_KM[r["pais_ne"]]
        chequeo(f"Tabla I · {dp.PAISES_TABLA_I[r['pais_ne']]}", round(r["distancia_km"]) == esperado,
                f"(calculado {r['distancia_km']:.1f} km; artículo {esperado:,} km)")

    # --- Tabla III ---
    for n, d, az, z in lv.tabla_iii():
        e_d, e_az, e_z = TABLA_III[n]
        chequeo(f"Tabla III · {n}", round(d) == e_d and round(az) == e_az and z == e_z,
                f"(calculado {d:.0f} km, {az:.0f}°, {z}; artículo {e_d} km, {e_az}°, {e_z})")

    print(f"\n{'Todo coincide con el artículo.' if fallos == 0 else f'{fallos} comprobación(es) fallaron.'}")
    return fallos


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--ne", help="GeoJSON de Natural Earth 10m (países); si falta se descarga")
    sys.exit(1 if main(ap.parse_args().ne) else 0)
