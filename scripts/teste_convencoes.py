"""Verifica as convenções da m5lib contra o OpenRocket (rodar 1x após mudanças)."""
from __future__ import annotations

import math

from m5lib import Cenario, Ctx, build_f1, definir_motor, estabilidade_estatica, simular

TESTE = {"body_len": 250, "fin_span": 45, "fin_root": 65, "fin_tip": 25, "fin_sweep": 40, "ballast_g": 5}


def main() -> None:
    doc, meta = build_f1(TESTE)
    definir_motor(doc, meta, "OBAFOG-M5_NEU_I09")
    c = Ctx.get()
    print("componentes:")
    for comp in c.b.iter_components(doc):
        try:
            m = float(comp.getMass()) * 1000
        except Exception:
            m = float("nan")
        print(f"  {str(comp.getName())[:48]:48s} {m:7.2f} g")
    est = estabilidade_estatica(doc)
    print("estatica:", {k: round(v, 2) if isinstance(v, float) else v for k, v in est.items()})

    # 1) azimute: 90 graus deve cair a leste (x > 0), 0 graus ao norte (y > 0)
    for az in (0.0, 90.0):
        r = simular(doc, meta, Cenario(azim_deg=az, turb=0.0))
        print(f"azim {az:5.1f}: perp {r['perp']:7.1f}  total {r['total']:7.1f}  lateral {r['lateral']:6.1f}")

    # 2) vento: 'vento_de' = 180 (cauda) vs 0 (frente); lateral 90
    for de in (0.0, 180.0, 90.0):
        r = simular(doc, meta, Cenario(vento=5.0, vento_de=de, turb=0.0))
        print(f"vento 5 m/s de {de:5.1f}: perp {r['perp']:7.1f} lateral {r['lateral']:7.1f} "
              f"apogeu {r['apogeu']:6.1f} aoa_max {r['aoa_max']}")

    # 3) série completa nominal
    r = simular(doc, meta, Cenario())
    print("nominal:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()
                       if k != "avisos"})
    print("avisos:", r["avisos"])


if __name__ == "__main__":
    import os, sys, time
    t0 = time.time()
    main()
    print(f"[ok em {time.time()-t0:.1f} s]", flush=True)
    sys.stdout.flush()
    os._exit(0)
