"""Decaimiento radiactivo del Cs-137 (Ec. 1 del artículo):  A(t) = A0 * 2^(-t / T1/2).

Solo decae físicamente: no incluye migración en el suelo, erosión ni absorción por
vegetación (limitación declarada en el artículo).

Uso:  python decaimiento.py
"""
import math
from parametros import (T_MEDIO_CS137, UMBRAL_CONTAMINADO,
                        LIMITE_SUPERIOR_SIMBOLOGIA, LIMITE_INFERIOR_ATLAS)


def factor(t_anios, t_medio=T_MEDIO_CS137):
    """Fracción del inventario inicial que queda tras t_anios (desde mayo de 1986)."""
    return 2.0 ** (-t_anios / t_medio)


def actividad(a0, t_anios, t_medio=T_MEDIO_CS137):
    return a0 * factor(t_anios, t_medio)


def anios_hasta_umbral(a0, umbral=UMBRAL_CONTAMINADO, t_medio=T_MEDIO_CS137):
    """Años (desde 1986) para que a0 baje hasta el umbral; None si ya está por debajo."""
    if a0 <= umbral:
        return None
    return t_medio * math.log2(a0 / umbral)


def tabla_ii(referencias=None, anios=(2020, 2026), origen=1986):
    """Reproduce la Tabla II del artículo: valores de referencia en 1986, 2020 y 2026."""
    if referencias is None:
        referencias = {
            "Pico máximo": LIMITE_SUPERIOR_SIMBOLOGIA,
            "Límite de clase superior": 28_000,
            "Límite de clase inferior": 6_000,
            "Mínimo cartografiado": LIMITE_INFERIOR_ATLAS,
        }
    filas = {}
    for nombre, a0 in referencias.items():
        filas[nombre] = [a0] + [actividad(a0, a - origen) for a in anios]
    return filas


def figura(ruta_png, anio_ini=1986, anio_fin=2080):
    """Decaimiento físico del pico y de los límites de clase (como la Fig. 4), escala log."""
    import numpy as np
    import matplotlib.pyplot as plt
    t = np.linspace(0, anio_fin - anio_ini, 400)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for nombre, a0, c in [("Pico: 120,000", 120_000, "tab:blue"),
                          ("Límite de clase: 28,000", 28_000, "tab:orange"),
                          ("Límite de clase: 6,000", 6_000, "tab:green")]:
        ax.semilogy(anio_ini + t, actividad(a0, t), color=c, label=nombre)
    ax.axhline(UMBRAL_CONTAMINADO, color="k", ls=":", label="Umbral zona contaminada: 37,000")
    ax.set_xlabel("Año"); ax.set_ylabel("Actividad de Cs-137 (Bq/m²)")
    ax.legend(fontsize=8); ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout(); fig.savefig(ruta_png, dpi=200); plt.close(fig)


if __name__ == "__main__":
    import sys
    if "--figura" in sys.argv:
        figura("decaimiento.png")
        print("Figura: decaimiento.png")
    print(f"Factor 2020 (t=34 a): {factor(34):.3f}   Factor 2026 (t=40 a): {factor(40):.3f}")
    print(f"\n{'Referencia':26s}{'1986':>10s}{'2020':>10s}{'2026':>10s}   (Bq/m2)")
    for n, (a, b, c) in tabla_ii().items():
        print(f"{n:26s}{a:10,.0f}{b:10,.0f}{c:10,.0f}")
    t = anios_hasta_umbral(LIMITE_SUPERIOR_SIMBOLOGIA)
    print(f"\nEl pico de 120,000 Bq/m2 baja de 37,000 Bq/m2 en {t:.1f} años -> {1986 + t:.0f}")
