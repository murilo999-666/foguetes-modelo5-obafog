"""Exporta trajetórias (t, altitude) do Foguete 2 para o teste SIL do firmware.

Uso: python exportar_trajetorias_f2.py [params.json]
Sem argumento, pega o melhor projeto viável de foguete2_livre/otimizacao/explorar.jsonl.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from avaliacao_f2 import ALT_LOCAL, TEMP_C, diametro_paraquedas
from m5lib import RAIZ, Cenario, build_f2, definir_motor, estabilidade_estatica, simular

SAIDA = RAIZ / "foguete2_livre" / "eletronica" / "sil" / "trajetorias"


def melhor_params() -> dict:
    rows = [json.loads(l) for l in (RAIZ / "foguete2_livre" / "otimizacao" / "explorar.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]
    best = max((r for r in rows if r.get("viavel")), key=lambda r: r["J"])
    p = dict(best["params"])
    return p


def main() -> None:
    p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if len(sys.argv) > 1 else melhor_params()
    doc, meta = build_f2(p)
    definir_motor(doc, meta, "OBAFOG-M5_NEU_I07")
    if "chute_d" not in p:
        p["chute_d"] = diametro_paraquedas(estabilidade_estatica(doc)["massa_seca_g"])
        p["chute_line_len"] = p["chute_d"]
        doc, meta = build_f2(p)
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "params_f2.json").write_text(json.dumps(p, indent=1), encoding="utf-8")
    casos = [(m, v) for m in ("NEU_I05", "NEU_I07", "NEU_I09", "NEU_I115", "PRO_I07", "REG_I07")
             for v in (0.0, 4.0)]
    for m, vento in casos:
        r = simular(doc, meta, Cenario(motor=f"OBAFOG-M5_{m}", elev_deg=87.0, vento=vento,
                                       vento_de=90.0, turb=0.0, alt_local=ALT_LOCAL, temp_c=TEMP_C,
                                       t_max=150.0), keep_series=True)
        s = r["series"]
        nome = f"traj_{m}_v{int(vento)}.csv"
        with open(SAIDA / nome, "w", encoding="utf-8") as f:
            f.write(f"# OpenRocket: apogeu {r['apogeu']:.1f} m t_apo {r['t_apogeu']:.2f} s "
                    f"abertura(OR) {r['t_abertura']} s v_descida {r.get('v_descida')}\n")
            f.write("t_s,altitude_m\n")
            for t, h in zip(s["t"], s["alt"]):
                f.write(f"{t:.4f},{h:.3f}\n")
        print(nome, f"apogeu {r['apogeu']:.1f} m em {r['t_apogeu']:.2f} s, voo {r['t_voo']:.1f} s", flush=True)


if __name__ == "__main__":
    main()
    os._exit(0)
