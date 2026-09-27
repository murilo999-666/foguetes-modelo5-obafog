"""Fecha o Foguete 2: CAD -> massas reais -> .ork final -> tabelas de lastro/deriva, gráficos.

Uso: python finalizar_f2.py <params.json> <nome_versao>

Tabela de lastro: com o motor medido na bancada, quanto de massa epóxi pôr no bico para
o apogeu ficar abaixo de 140 m (a norma BAR-2/2020 pede NOTAM acima de 150 m em área
rural). Tabela de deriva: distância do pouso com vento de 0 a 6 m/s (tamanho do campo).
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
TETO_APOGEU = 140.0


def gerar_cad(params: dict, pasta_stl: Path) -> dict:
    from m5lib import F2_PADRAO
    pasta_stl.mkdir(parents=True, exist_ok=True)
    arq = pasta_stl / "params_cad.json"
    completos = {**F2_PADRAO, **{k: v for k, v in params.items() if k != "massas_cad"}}
    arq.write_text(json.dumps(completos, indent=1), encoding="utf-8")
    out = subprocess.run(["python", "-X", "utf8", str(AQUI / "cad_foguetes.py"), "f2", str(arq), str(pasta_stl)],
                         capture_output=True, text=True, check=True).stdout
    rel = json.loads(out)
    return {"pecas": rel[:-1], "massas_cad": rel[-1]["massas_cad"]}


def main() -> None:
    from avaliacao_f2 import ALT_LOCAL, TEMP_C, diametro_paraquedas
    from m5lib import (Cenario, build_f2, definir_motor, estabilidade_estatica, salvar_com_simulacoes,
                       simular)
    params = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    versao = sys.argv[2] if len(sys.argv) > 2 else "F2_final"
    pasta = RAIZ / "foguete2_livre"
    t0 = time.time()
    cad = gerar_cad(params, pasta / "stl" / versao)
    params = {**params, "massas_cad": cad["massas_cad"]}
    doc, meta = build_f2(params)
    definir_motor(doc, meta, "OBAFOG-M5_NEU_I07")
    est = estabilidade_estatica(doc)
    params["chute_d"] = diametro_paraquedas(est["massa_seca_g"])
    params["chute_line_len"] = params["chute_d"]
    doc, meta = build_f2(params)
    definir_motor(doc, meta, "OBAFOG-M5_NEU_I07")
    est = estabilidade_estatica(doc)
    print(f"[{time.time()-t0:.0f}s] CAD ok: {est['massa_g']:.1f} g, {est['cal']:.2f} cal, "
          f"paraquedas {params['chute_d']:.0f} mm", flush=True)

    def cen(motor, vento=0.0, de=90.0, **kw):
        return Cenario(motor=motor, elev_deg=87.0, vento=vento, vento_de=de, turb=0.0,
                       alt_local=ALT_LOCAL, temp_c=TEMP_C, t_max=150.0, **kw)

    # tabela de lastro para limitar o apogeu
    lastro = []
    b0 = params.get("ballast_g", 0.0)

    def voo_com(imp, b):
        try:
            d, m = build_f2({**params, "ballast_g": b0 + b})
        except ValueError:                       # não cabe no bico da ogiva
            return None
        return simular(d, m, cen(f"OBAFOG-M5_NEU_{imp}"))

    # capacidade do bico: maior lastro extra que ainda cabe
    cap_lo, cap_hi = 0.0, 80.0
    for _ in range(12):
        mid = 0.5 * (cap_lo + cap_hi)
        try:
            build_f2({**params, "ballast_g": b0 + mid})
            cap_lo = mid
        except ValueError:
            cap_hi = mid
    cap = math.floor(cap_lo)
    for imp in ("I05", "I07", "I09", "I115"):
        r0 = voo_com(imp, 0.0)
        linha = {"motor": imp, "apogeu_sem_lastro_extra": round(r0["apogeu"], 1),
                 "lastro_extra_g": 0.0, "v_vara_com_lastro": round(r0["v_vara"], 1)}
        if r0["apogeu"] > TETO_APOGEU:
            rc = voo_com(imp, cap)
            if rc is None or rc["apogeu"] > TETO_APOGEU:
                linha["lastro_extra_g"] = None
                linha["obs"] = (f"nem com {cap:.0f} g (o máximo que cabe no bico) fica abaixo de "
                                f"{TETO_APOGEU:.0f} m: precisa NOTAM ou campo liberado")
            else:
                lo, hi = 0.0, float(cap)
                for _ in range(12):
                    mid = 0.5 * (lo + hi)
                    (lo, hi) = (mid, hi) if voo_com(imp, mid)["apogeu"] > TETO_APOGEU else (lo, mid)
                linha["lastro_extra_g"] = math.ceil(hi)
                linha["v_vara_com_lastro"] = round(voo_com(imp, math.ceil(hi))["v_vara"], 1)
        lastro.append(linha)
        print("lastro", linha, flush=True)

    # deriva com vento (motor nominal)
    deriva = []
    for v in (0.0, 2.0, 4.0, 6.0):
        r = simular(doc, meta, cen("OBAFOG-M5_NEU_I07", v, 90.0))
        deriva.append({"vento": v, "deriva_m": round(r["total"], 1), "apogeu": round(r["apogeu"], 1),
                       "t_voo": round(r["t_voo"], 1), "v_abertura": r.get("v_abertura")})
    print("deriva", deriva, flush=True)

    cens = [("NOMINAL 7 N.s, 87 graus, sem vento", cen("OBAFOG-M5_NEU_I07")),
            ("Pessimista 5 N.s", cen("OBAFOG-M5_NEU_I05")),
            ("Otimista 9 N.s (passa de 150 m: ver tabela de lastro)", cen("OBAFOG-M5_NEU_I09")),
            ("Teto 11,5 N.s", cen("OBAFOG-M5_REG_I115")),
            ("7 N.s progressiva (pior saida da vara)", cen("OBAFOG-M5_PRO_I07")),
            ("7 N.s vento lateral 4 m/s", cen("OBAFOG-M5_NEU_I07", 4.0, 90.0))]
    sims = salvar_com_simulacoes(doc, meta, cens, pasta / f"{versao}.ork", motor_selecionado="OBAFOG-M5_NEU_I07")
    sims = [{"nome": r["nome"], **{k: (round(r[k], 2) if isinstance(r.get(k), float) else r.get(k))
                                   for k in ("apogeu", "v_max", "v_vara", "stab_min", "v_abertura",
                                             "v_descida", "v_impacto", "t_voo", "total", "massa_g")}}
            for r in sims]
    # gráfico altitude x tempo
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    (pasta / "graficos").mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for m, cor in (("NEU_I05", "#1b9e77"), ("NEU_I07", "#d95f02"), ("NEU_I09", "#7570b3")):
        r = simular(doc, meta, cen(f"OBAFOG-M5_{m}"), keep_series=True)
        s = r["series"]
        ax.plot(s["t"], s["alt"], color=cor, label=f"{m.replace('_', ' ')}: apogeu {r['apogeu']:.0f} m")
        if r.get("t_abertura"):
            ax.axvline(r["t_abertura"], color=cor, ls=":", lw=1)
    ax.axhline(150, color="k", ls="--", lw=0.8)
    ax.text(1, 153, "150 m: acima disso, NOTAM (BAR-2/2020, área rural)", fontsize=7)
    ax.set_xlabel("tempo (s)"); ax.set_ylabel("altitude (m)")
    ax.set_title("Foguete 2 — voo quase vertical (87°), paraquedas 1 s depois do apogeu")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(pasta / "graficos" / f"{versao}_altitude_x_tempo.png", dpi=150); plt.close(fig)
    resumo = {"versao": versao, "params": params, "estabilidade": est, "cad": cad["pecas"],
              "simulacoes_no_ork": sims, "tabela_lastro": lastro, "tabela_deriva": deriva}
    (pasta / f"{versao}_resumo.json").write_text(json.dumps(resumo, indent=1, default=float), encoding="utf-8")
    for s in sims:
        print(s)
    print(f"[fim em {time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
    os._exit(0)
