"""Fecha o Foguete 1: CAD -> massas reais -> .ork final -> tabelas, Monte Carlo e gráficos.

Uso: python finalizar_f1.py <params.json> <nome_versao>   (ex.: F1_construtivel_v1)

Passos
  1. gera os STL (Python do sistema) e o massas_cad.json (massa e CG de cada peça impressa)
  2. monta o foguete no OpenRocket com as massas do CAD e reajusta o lastro para a
     margem-alvo (padrão 1,40 cal) — o lastro é o único ajuste fino depois de impresso
  3. tabela de ângulo x vento (motores de 5, 7 e 9 N.s; média)
  4. sensibilidade às tolerâncias de fabricação
  5. Monte Carlo com rajadas, vento sorteado, motor sorteado e erros de montagem
  6. salva o .ork com simulações nomeadas + gráficos + resumo JSON
"""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PY_SISTEMA = "python"          # tem trimesh/manifold3d
CAL_ALVO = float(os.environ.get("M5_CAL_ALVO", "1.40"))
WORKERS = int(os.environ.get("M5_WORKERS", "10"))


def gerar_cad(params: dict, pasta_stl: Path) -> dict:
    from m5lib import F1_PADRAO
    pasta_stl.mkdir(parents=True, exist_ok=True)
    arq = pasta_stl / "params_cad.json"
    # o CAD precisa das cotas fixas também (diâmetro, parede, ombro, guias)
    completos = {**F1_PADRAO, **{k: v for k, v in params.items() if k != "massas_cad"}}
    arq.write_text(json.dumps(completos, indent=1), encoding="utf-8")
    out = subprocess.run([PY_SISTEMA, "-X", "utf8", str(AQUI / "cad_foguetes.py"), "f1", str(arq), str(pasta_stl)],
                         capture_output=True, text=True, check=True).stdout
    subprocess.run([PY_SISTEMA, "-X", "utf8", str(AQUI / "cad_foguetes.py"), "gabaritos", str(pasta_stl / "gabaritos")],
                   capture_output=True, text=True, check=True)
    rel = json.loads(out)
    return {"pecas": rel[:-1], "massas_cad": rel[-1]["massas_cad"]}


def ajustar_lastro(params: dict) -> tuple[dict, dict]:
    from m5lib import build_f1, definir_motor, estabilidade_estatica
    def cal(b):
        doc, meta = build_f1({**params, "ballast_g": b})
        definir_motor(doc, meta, "OBAFOG-M5_NEU_I07")
        return estabilidade_estatica(doc)
    lo, hi = 0.0, 25.0
    if cal(lo)["cal"] >= CAL_ALVO:
        b = 0.0
    else:
        for _ in range(20):
            mid = 0.5 * (lo + hi)
            (lo, hi) = (mid, hi) if cal(mid)["cal"] < CAL_ALVO else (lo, mid)
        b = math.ceil(hi * 2) / 2                       # passo de 0,5 g (balança de cozinha)
    p = {**params, "ballast_g": b}
    return p, cal(b)


# ------------------------- trabalho paralelo -------------------------
def _init():
    global _m
    import m5lib as _mm
    _m = _mm


def _sim(args):
    params, cen_kw = args
    from avaliacao import ALT_LOCAL, TEMP_C
    doc, meta = _m.build_f1(params)
    cen = _m.Cenario(alt_local=ALT_LOCAL, temp_c=TEMP_C, **cen_kw)
    r = _m.simular(doc, meta, cen)
    r.pop("avisos", None)
    return {**cen_kw, **{k: r.get(k) for k in ("perp", "total", "lateral", "apogeu", "v_max", "v_vara",
                                              "stab_min", "aoa_max", "v_impacto", "t_voo", "erro")}}


def tabela_angulos(pool, params: dict) -> list[dict]:
    ventos = [(0.0, 0.0), (2.0, 0.0), (2.0, 180.0), (4.0, 0.0), (4.0, 180.0), (4.0, 90.0),
              (6.0, 0.0), (6.0, 180.0)]
    elevs = [36, 40, 44, 48, 52, 56, 60]
    motores = ["OBAFOG-M5_NEU_I05", "OBAFOG-M5_NEU_I07", "OBAFOG-M5_NEU_I09"]
    tarefas = [(params, {"motor": m, "elev_deg": float(e), "vento": v, "vento_de": d, "turb": 0.0,
                         "rod_len": 1.2}) for (v, d) in ventos for e in elevs for m in motores]
    res = pool.map(_sim, tarefas)
    tab = []
    for (v, d) in ventos:
        linha = {"vento": v, "de": d, "por_angulo": {}}
        for e in elevs:
            rr = [r for r in res if r["vento"] == v and r["vento_de"] == d and r["elev_deg"] == e]
            linha["por_angulo"][e] = {m.split("_")[-1]: round(r["perp"], 1) for m, r in
                                      zip(motores, sorted(rr, key=lambda r: r["motor"]))}
            linha["por_angulo"][e]["media"] = round(float(np.mean([r["perp"] for r in rr])), 1)
        melhor = max(elevs, key=lambda e: linha["por_angulo"][e]["media"])
        linha["melhor_angulo"] = melhor
        linha["alcance_medio_no_melhor"] = linha["por_angulo"][melhor]["media"]
        tab.append(linha)
    return tab


def sensibilidade(pool, params: dict, elev: float) -> list[dict]:
    """Queda de alcance (motor nominal, sem vento) e de margem com cada tolerância."""
    from m5lib import build_f1, definir_motor, estabilidade_estatica
    tol = {"nose_len": 2.0, "body_len": 2.0, "fin_root": 1.0, "fin_tip": 1.0, "fin_span": 1.0,
           "fin_sweep": 1.0, "fin_t": 0.2, "ballast_g": 1.0}
    casos = [("nominal", params)]
    for k, d in tol.items():
        for s in (-1, 1):
            pp = dict(params)
            pp[k] = max(pp[k] + s * d, 0.0)
            casos.append((f"{k} {'+' if s > 0 else '-'}{d:g}", pp))
    mc = params.get("massas_cad")
    if mc:
        for s in (-1, 1):
            pp = dict(params)
            pp["massas_cad"] = {k: {**v, "massa_g": v["massa_g"] * (1 + 0.08 * s)} for k, v in mc.items()}
            casos.append((f"peças impressas {'+' if s > 0 else '-'}8% de massa", pp))
    for s in (-1, 1):
        casos.append((f"cap {'+' if s > 0 else '-'}1,5 g", {**params, "cap_g": 5.0 + 1.5 * s}))
    tarefas = [(pp, {"motor": "OBAFOG-M5_NEU_I07", "elev_deg": elev, "vento": 0.0, "vento_de": 0.0,
                     "turb": 0.0, "rod_len": 1.2}) for _, pp in casos]
    res = pool.map(_sim, tarefas)
    out = []
    for (nome, pp), r in zip(casos, res):
        doc, meta = build_f1(pp)
        definir_motor(doc, meta, "OBAFOG-M5_NEU_I07")
        e = estabilidade_estatica(doc)
        out.append({"caso": nome, "perp": round(r["perp"], 1), "cal": round(e["cal"], 3),
                    "massa_g": round(e["massa_g"], 1)})
    return out


def monte_carlo(pool, params: dict, tabela: list[dict], n: int = 200, semente: int = 7) -> list[dict]:
    rnd = random.Random(semente)
    motores = [("NEU", 0.40), ("REG", 0.30), ("PRO", 0.30)]
    impulsos = [("I05", 0.20), ("I07", 0.45), ("I09", 0.25), ("I115", 0.10)]

    def sorteia(lst):
        x, acc = rnd.random(), 0.0
        for nome, pr in lst:
            acc += pr
            if x <= acc:
                return nome
        return lst[-1][0]

    def angulo_da_tabela(v, de):
        # a equipe mede o vento e usa a tabela: componente ao longo do lançamento
        # (positiva = de frente), arredondada para a linha mais próxima (0/2/4/6 m/s)
        w = v * math.cos(math.radians(de))
        if abs(w) < 1.0:
            linha = next(l for l in tabela if l["vento"] == 0.0)
        else:
            lado = 0.0 if w > 0 else 180.0
            cand = [l for l in tabela if l["de"] == lado and l["vento"] > 0]
            linha = min(cand, key=lambda l: abs(l["vento"] - abs(w)))
        return float(linha["melhor_angulo"])

    tarefas = []
    for i in range(n):
        v = rnd.uniform(0.0, 5.0)
        de = rnd.uniform(0.0, 360.0)
        elev = angulo_da_tabela(v, de) + rnd.gauss(0.0, 1.5)
        pp = dict(params)
        pp["ballast_g"] = max(0.0, params["ballast_g"] + rnd.gauss(0.0, 0.4))
        pp["fin_t"] = params["fin_t"] + rnd.gauss(0.0, 0.08)
        pp["cap_g"] = 5.0 + rnd.gauss(0.0, 0.8)
        if params.get("massas_cad"):
            f = 1 + rnd.gauss(0.0, 0.04)
            pp["massas_cad"] = {k: {**vv, "massa_g": vv["massa_g"] * f} for k, vv in params["massas_cad"].items()}
        motor = f"OBAFOG-M5_{sorteia(motores)}_{sorteia(impulsos)}"
        tarefas.append((pp, {"motor": motor, "elev_deg": elev, "vento": v, "vento_de": de, "turb": 0.15,
                             "rod_len": rnd.uniform(1.1, 1.3), "seed": i}))
    return pool.map(_sim, tarefas)


def salvar_ork(params: dict, elev: float, caminho: Path) -> list[dict]:
    from avaliacao import ALT_LOCAL, TEMP_C
    from m5lib import Cenario, build_f1, salvar_com_simulacoes
    doc, meta = build_f1(params, nome="Foguete 1 - OBAFOG Modelo 5 (construtivel)")
    base = dict(elev_deg=elev, rod_len=1.2, turb=0.0, alt_local=ALT_LOCAL, temp_c=TEMP_C)
    cen = [
        (f"NOMINAL 7 N.s, {elev:.0f} graus, sem vento", Cenario(motor="OBAFOG-M5_NEU_I07", **base)),
        ("Pessimista 5 N.s", Cenario(motor="OBAFOG-M5_NEU_I05", **base)),
        ("Otimista 9 N.s", Cenario(motor="OBAFOG-M5_NEU_I09", **base)),
        ("Teto 11,5 N.s (checagem de flutter/velocidade)", Cenario(motor="OBAFOG-M5_REG_I115", **base)),
        ("7 N.s curva progressiva (pior saida da vara)", Cenario(motor="OBAFOG-M5_PRO_I07", **base)),
        ("7 N.s curva regressiva", Cenario(motor="OBAFOG-M5_REG_I07", **base)),
        ("7 N.s vento 4 m/s de frente", Cenario(motor="OBAFOG-M5_NEU_I07", vento=4.0, vento_de=0.0,
                                                  **{k: v for k, v in base.items()})),
        ("7 N.s vento 4 m/s de cauda", Cenario(motor="OBAFOG-M5_NEU_I07", vento=4.0, vento_de=180.0,
                                                 **{k: v for k, v in base.items()})),
        ("7 N.s vento 4 m/s lateral", Cenario(motor="OBAFOG-M5_NEU_I07", vento=4.0, vento_de=90.0,
                                                **{k: v for k, v in base.items()})),
    ]
    res = salvar_com_simulacoes(doc, meta, cen, caminho, motor_selecionado="OBAFOG-M5_NEU_I07")
    return [{"nome": r["nome"], **{k: (round(r[k], 2) if isinstance(r.get(k), float) else r.get(k))
                                   for k in ("perp", "total", "apogeu", "v_max", "mach_max", "v_vara",
                                             "stab_min", "aoa_max", "v_impacto", "t_voo", "massa_g")}}
            for r in res]


def graficos(params: dict, elev: float, tabela, mc, pasta: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from avaliacao import ALT_LOCAL, TEMP_C
    from m5lib import Cenario, build_f1, simular
    pasta.mkdir(parents=True, exist_ok=True)
    doc, meta = build_f1(params)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for m, cor in (("NEU_I05", "#1b9e77"), ("NEU_I07", "#d95f02"), ("NEU_I09", "#7570b3"), ("REG_I115", "#e7298a")):
        r = simular(doc, meta, Cenario(motor=f"OBAFOG-M5_{m}", elev_deg=elev, turb=0.0,
                                       alt_local=ALT_LOCAL, temp_c=TEMP_C), keep_series=True)
        s = r["series"]
        dist = np.hypot(s["x"], s["y"])
        ax.plot(dist, s["alt"], color=cor, label=f"{m.replace('_', ' ')}: {r['perp']:.0f} m")
    ax.set_xlabel("distância (m)"); ax.set_ylabel("altitude (m)")
    ax.set_title(f"Foguete 1 — trajetórias a {elev:.0f}° sem vento"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_aspect("equal", adjustable="datalim")
    fig.tight_layout(); fig.savefig(pasta / "trajetorias.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    for l in tabela:
        es = sorted(l["por_angulo"])
        lbl = f"{l['vento']:.0f} m/s " + ("frente" if l["de"] == 0 else "cauda" if l["de"] == 180 else "lateral")
        if l["vento"] == 0:
            lbl = "sem vento"
        ax.plot(es, [l["por_angulo"][e]["media"] for e in es], marker="o", ms=3, label=lbl)
    ax.set_xlabel("ângulo da vara acima do horizonte (graus)"); ax.set_ylabel("alcance médio perpendicular (m)")
    ax.set_title("Alcance x ângulo (média de 5, 7 e 9 N·s)"); ax.grid(alpha=0.3); ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(pasta / "alcance_x_angulo.png", dpi=150); plt.close(fig)

    per = np.array([r["perp"] for r in mc if r.get("perp") is not None])
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.hist(per, bins=30, color="#d95f02", alpha=0.85)
    for q, ls in ((10, ":"), (50, "-"), (90, ":")):
        ax.axvline(np.percentile(per, q), color="k", ls=ls, lw=1)
    ax.set_xlabel("alcance perpendicular (m)"); ax.set_ylabel("voos simulados")
    ax.set_title(f"Monte Carlo ({len(per)} voos): P10 {np.percentile(per, 10):.0f} m, "
                 f"mediana {np.median(per):.0f} m, P90 {np.percentile(per, 90):.0f} m")
    fig.tight_layout(); fig.savefig(pasta / "monte_carlo.png", dpi=150); plt.close(fig)


def main() -> None:
    params = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    versao = sys.argv[2] if len(sys.argv) > 2 else "F1_final"
    pasta = RAIZ / "foguete1_obafog"
    t0 = time.time()
    cad = gerar_cad(params, pasta / "stl" / versao)
    params = {**params, "massas_cad": cad["massas_cad"]}
    params, est = ajustar_lastro(params)
    # o lastro mudou: STL não muda (lastro é massa epóxi), massas do CAD continuam válidas
    print(f"[{time.time()-t0:.0f}s] CAD ok; lastro ajustado para {params['ballast_g']} g -> "
          f"{est['cal']:.2f} cal, {est['massa_g']:.1f} g", flush=True)
    elev0 = float(params["elev"])
    with mp.get_context("spawn").Pool(WORKERS, initializer=_init) as pool:
        tabela = tabela_angulos(pool, params)
        l0 = next(l for l in tabela if l["vento"] == 0.0)
        elev = float(l0["melhor_angulo"])
        print(f"[{time.time()-t0:.0f}s] tabela de ângulos ok (melhor sem vento: {elev:.0f} graus)", flush=True)
        sens = sensibilidade(pool, params, elev)
        print(f"[{time.time()-t0:.0f}s] sensibilidade ok", flush=True)
        mc = monte_carlo(pool, params, tabela)
        print(f"[{time.time()-t0:.0f}s] Monte Carlo ok", flush=True)
        pool.terminate()
    params["elev"] = elev
    sims = salvar_ork(params, elev, pasta / f"{versao}.ork")
    graficos(params, elev, tabela, mc, pasta / "graficos" / versao)
    per = np.array([r["perp"] for r in mc if r.get("perp") is not None])
    resumo = {"versao": versao, "params": params, "estabilidade": est, "elev_otimizada_na_busca": elev0,
              "elev_recomendada_sem_vento": elev, "cad": cad["pecas"], "simulacoes_no_ork": sims,
              "tabela_angulos": tabela, "sensibilidade": sens,
              "monte_carlo": {"n": int(per.size), "p10": float(np.percentile(per, 10)),
                              "p50": float(np.median(per)), "p90": float(np.percentile(per, 90)),
                              "min": float(per.min()), "max": float(per.max()),
                              "frac_abaixo_100m": float((per < 100).mean()),
                              "frac_abaixo_30m": float((per < 30).mean())}}
    (pasta / f"{versao}_resumo.json").write_text(json.dumps(resumo, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: resumo[k] for k in ("estabilidade", "elev_recomendada_sem_vento", "monte_carlo")},
                     indent=1, default=float))
    for s in sims:
        print(s)
    print(f"[fim em {time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
    os._exit(0)
