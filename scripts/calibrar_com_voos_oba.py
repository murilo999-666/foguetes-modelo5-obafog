"""Checagem de sanidade da faixa de impulso com os voos mostrados pela OBA.

Âncora (live 208, 1:53-1:54; vídeo 215, 16:55): foguetes de garrafa PET de
500 mL, 4 aletas, motor no gargalo preso com fita, vara de vergalhão 4-5 mm,
~40-45 graus -> "extremamente repetitivo ... acumulando ali nos 100 m" (com vento
forte de cauda); "em outros voos a gente já ultrapassou 150 metros"; um voo de
demonstração de ~80 m. Massa e aletas exatas do foguete deles NÃO são conhecidas,
então varremos uma faixa plausível e vemos qual impulso é compatível.

Saída: tabela alcance x (impulso, formato, massa extra, ângulo).
"""
from __future__ import annotations

import itertools
import json
import os
import time

from m5lib import RAIZ, Cenario, build_pet_oba, definir_motor, estabilidade_estatica, simular


def main() -> None:
    linhas = []
    for extra, alt, recuo, cil in itertools.product([5.0, 20.0, 35.0], [55.0, 70.0, 85.0],
                                                    [0.0, 25.0], [150.0, 290.0]):
        doc, meta = build_pet_oba({"massa_extra_g": extra, "aleta_alt": alt, "aleta_recuo": recuo,
                                   "cilindro": cil})
        definir_motor(doc, meta, "OBAFOG-M5_NEU_I09")
        est = estabilidade_estatica(doc)
        if not (0.9 <= est["cal"] <= 2.6):
            print({"pulado": True, "extra_g": extra, "aleta_alt": alt, "recuo": recuo, "cil": cil,
                   "cal": round(est["cal"], 2)}, flush=True)
            continue
        for imp in ("I07", "I09", "I115"):
            for elev in (40.0, 45.0):
                for vento, de in ((0.0, 0.0), (5.0, 180.0)):
                    r = simular(doc, meta, Cenario(motor=f"OBAFOG-M5_NEU_{imp}", elev_deg=elev,
                                                   vento=vento, vento_de=de, rod_len=1.2,
                                                   alt_local=100.0, temp_c=25.0, turb=0.1))
                    linhas.append({"extra_g": extra, "aleta_alt": alt, "recuo": recuo, "cil": cil, "cal": round(est["cal"], 2),
                                   "massa_g": round(est["massa_g"], 1), "motor": imp,
                                   "elev": elev, "vento": vento, "perp": round(r["perp"], 1),
                                   "apogeu": round(r["apogeu"], 1), "v_vara": round(r.get("v_vara", 0), 1),
                                   "erro": r.get("erro")})
                    print(linhas[-1], flush=True)
    out = RAIZ / "motor" / "calibracao_pet_oba.json"
    out.write_text(json.dumps(linhas, indent=1), encoding="utf-8")
    print("salvo", out)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"[{time.time()-t0:.1f}s]", flush=True)
    os._exit(0)
