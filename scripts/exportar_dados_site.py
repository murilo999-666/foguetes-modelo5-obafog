"""Junta os resultados num dados.js para os gráficos interativos da página.

Uso (venv do orx, precisa do OpenRocket):  python exportar_dados_site.py <pasta_site>
"""
from __future__ import annotations

import csv
import json
import multiprocessing as mp
import os
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent


def ler_eng(caminho: Path) -> list[list[float]]:
    pts = [[0.0, 0.0]]
    for linha in caminho.read_text(encoding="ascii").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith(";") or linha[0].isalpha():
            continue
        t, f = map(float, linha.split()[:2])
        pts.append([round(t, 4), round(f, 3)])
    return pts


def reduz(xs, ys, n=140):
    xs, ys = np.asarray(xs), np.asarray(ys)
    if len(xs) <= n:
        return [[round(float(a), 2), round(float(b), 2)] for a, b in zip(xs, ys)]
    idx = np.unique(np.concatenate([np.linspace(0, len(xs) - 1, n).astype(int), [int(np.argmax(ys))]]))
    return [[round(float(xs[i]), 2), round(float(ys[i]), 2)] for i in idx]


def carregar_jsonl(arq: Path) -> list[dict]:
    return [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    site = Path(sys.argv[1])
    import finalizar_f1 as fin
    from avaliacao import ALT_LOCAL, TEMP_C, avaliar_f1
    from m5lib import Cenario, build_f1, simular

    D: dict = {}
    # ---------------- motor ----------------
    eng = RAIZ / "motor" / "eng"
    D["motores"] = {f"{s}_{i}": ler_eng(eng / f"OBAFOG-M5_{s}_{i}.eng")
                    for s in ("NEU", "REG", "PRO") for i in ("I05", "I07", "I09", "I115")}
    cal = json.loads((RAIZ / "motor" / "calibracao_pet_oba.json").read_text(encoding="utf-8"))
    D["calib_pet"] = []
    for imp, ns in (("I07", 7.0), ("I09", 9.0), ("I115", 11.5)):
        v = [r["perp"] for r in cal if r["motor"] == imp and r["elev"] == 45.0 and r["vento"] == 0.0]
        D["calib_pet"].append({"impulso": ns, "min": min(v), "media": float(np.mean(v)), "max": max(v), "n": len(v)})

    # ---------------- Foguete 1 ----------------
    rA = json.loads((RAIZ / "foguete1_obafog" / "F1_construtivel_v1_resumo.json").read_text(encoding="utf-8"))
    rB = json.loads((RAIZ / "foguete1_obafog" / "F1_construtivel_v1B_ogiva_curta_resumo.json").read_text(encoding="utf-8"))
    pA = rA["params"]
    doc, meta = build_f1(pA)
    elev = float(rA["elev_recomendada_sem_vento"])
    D["f1_trajetorias"] = {}
    for m in ("NEU_I05", "NEU_I07", "NEU_I09", "REG_I115"):
        r = simular(doc, meta, Cenario(motor=f"OBAFOG-M5_{m}", elev_deg=elev, turb=0.0,
                                       alt_local=ALT_LOCAL, temp_c=TEMP_C), keep_series=True)
        s = r["series"]
        dist = np.hypot(s["x"], s["y"])
        D["f1_trajetorias"][m] = {"pontos": reduz(dist, s["alt"]), "alcance": round(r["perp"], 1),
                                  "apogeu": round(r["apogeu"], 1), "v_max": round(r["v_max"], 1)}
    D["f1_angulos"] = rA["tabela_angulos"]
    D["f1_sensibilidade"] = [s for s in rA["sensibilidade"] if not s["caso"].startswith("body_len")]
    D["f1_sims"] = rA["simulacoes_no_ork"]
    D["f1B_sims"] = rB["simulacoes_no_ork"]
    D["f1_resumo"] = {"A": {k: rA[k] for k in ("estabilidade", "monte_carlo", "elev_recomendada_sem_vento")},
                      "B": {k: rB[k] for k in ("estabilidade", "monte_carlo", "elev_recomendada_sem_vento")},
                      "A_params": {k: v for k, v in pA.items() if k != "massas_cad"},
                      "B_params": {k: v for k, v in rB["params"].items() if k != "massas_cad"},
                      "A_cad": rA["cad"], "B_cad": rB["cad"]}
    # Monte Carlo bruto (a finalização guardou só os percentis)
    with mp.get_context("spawn").Pool(10, initializer=fin._init) as pool:
        mc = fin.monte_carlo(pool, pA, rA["tabela_angulos"], n=200, semente=7)
        pool.terminate()
    D["f1_monte_carlo"] = [round(r["perp"], 1) for r in mc if r.get("perp") is not None]

    # otimização: nuvem S1 (mesmo conjunto de cenários para todos os pontos)
    otm = RAIZ / "foguete1_obafog" / "otimizacao"
    nuvem = [r for arq in ("explorar_S1.jsonl", "explorar_S1_v2.jsonl") for r in carregar_jsonl(otm / arq)
             if r.get("viavel")]
    D["otm_nuvem"] = [[round(r["massa_g"], 1), round(r["perp_media"], 1)] for r in nuvem]
    melhor = max(nuvem, key=lambda r: r["J"])
    from otimizar_f1 import humano_ajustado
    # referência "humana": a aleta dela precisaria de suporte na impressão (tudo bem, é só comparação)
    hum = avaliar_f1({**humano_ajustado(), "aceita_suporte": True}, "S1")
    if "massa_g" not in hum:
        raise SystemExit(f"humano reprovado no S1: {hum.get('motivo')}")
    # o foguete que vai ser impresso: com as massas do CAD (as mesmas do .ork final)
    constr = avaliar_f1({**pA, "cal_min_extra": 1.2}, "S1")
    if "perp_media" not in constr:
        raise SystemExit(f"construtível reprovado no S1: {constr.get('motivo')} cal={constr.get('cal')}")
    D["otm_destaques"] = {
        "teorico": [round(melhor["massa_g"], 1), round(melhor["perp_media"], 1)],
        "construtivel": [round(constr["massa_g"], 1), round(constr["perp_media"], 1)],
        "humano": [round(hum["massa_g"], 1), round(hum["perp_media"], 1)]}
    xs = np.array([p[0] for p in D["otm_nuvem"]]); ys = np.array([p[1] for p in D["otm_nuvem"]])
    D["otm_correlacao"] = round(float(np.corrcoef(xs, ys)[0, 1]), 2)
    D["otm_n"] = {"total": sum(len(carregar_jsonl(otm / a)) for a in
                               ("explorar_S1.jsonl", "explorar_S1_v2.jsonl", "construtivel_S2.jsonl")) + 16,
                  "viaveis_S1": len(nuvem)}
    D["comparacao_S2"] = json.loads((RAIZ / "foguete1_obafog" / "comparacao_S2.json").read_text(encoding="utf-8"))[:1] \
        + [r for r in json.loads((RAIZ / "foguete1_obafog" / "otimizacao" / "bf_reto_S2.json").read_text(encoding="utf-8"))[:1]] \
        + [r for r in json.loads((RAIZ / "foguete1_obafog" / "comparacao_S2.json").read_text(encoding="utf-8")) if r["nome"] == "humano"]

    # ---------------- Foguete 2 ----------------
    r29 = json.loads((RAIZ / "foguete2_livre" / "F2_29mm_v1_resumo.json").read_text(encoding="utf-8"))
    r26 = json.loads((RAIZ / "foguete2_livre" / "F2_26mm_v1_resumo.json").read_text(encoding="utf-8"))
    D["f2_resumo"] = {"29": {k: r29[k] for k in ("estabilidade", "tabela_lastro", "tabela_deriva", "simulacoes_no_ork")},
                      "26": {k: r26[k] for k in ("estabilidade", "tabela_lastro", "tabela_deriva", "simulacoes_no_ork")},
                      "29_params": {k: v for k, v in r29["params"].items() if k != "massas_cad"},
                      "29_cad": r29["cad"]}
    sil = RAIZ / "foguete2_livre" / "eletronica" / "sil"
    D["f2_altitude"] = {}
    for m in ("NEU_I05", "NEU_I07", "NEU_I09", "NEU_I115"):
        t, h = [], []
        with open(sil / "trajetorias" / f"traj_{m}_v0.csv", encoding="utf-8") as f:
            for linha in f:
                if linha[0] in "#t":
                    continue
                a, b = linha.split(",")
                t.append(float(a)); h.append(float(b))
        D["f2_altitude"][m] = {"pontos": reduz(t, h, 160), "apogeu": round(max(h), 1)}
    # exemplo do SIL (firmware real rodando no PC)
    rows = list(csv.DictReader(open(sil / "exemplo_log_I07.csv", encoding="utf-8")))
    ex = [r for i, r in enumerate(rows) if i % 5 == 0 and float(r["t_s"]) <= 36]
    D["sil_exemplo"] = {"t": [round(float(r["t_s"]), 2) for r in ex],
                        "real": [round(float(r["h_real"]), 2) for r in ex],
                        "bruto": [round(float(r["h_bruto"]), 2) for r in ex],
                        "filtrado": [round(float(r["h_filtrado"]), 2) for r in ex]}
    ev = {}
    for i in range(1, len(rows)):
        a, b = int(rows[i - 1]["estado"]), int(rows[i]["estado"])
        if a != b:
            ev[{2: "decolagem detectada", 3: "paraquedas comandado", 4: "pouso detectado"}.get(b, str(b))] = \
                round(float(rows[i]["t_s"]), 2)
    D["sil_eventos"] = ev
    res = carregar_jsonl(sil / "resultado_sil.jsonl")
    D["sil_resumo"] = {"casos": len(res), "aprovados": sum(r["aprovado"] for r in res), "por_traj": []}
    for traj in sorted({r["traj"] for r in res}):
        rr = [r for r in res if r["traj"] == traj]
        D["sil_resumo"]["por_traj"].append({
            "traj": traj, "apogeu": rr[0]["apogeu_real"],
            "atraso_medio": round(float(np.mean([r["atraso_abertura"] for r in rr])), 2),
            "atraso_max": round(max(r["atraso_abertura"] for r in rr), 2),
            "v_max": round(max(abs(r["v_vertical_abertura"]) for r in rr), 1),
            "aprovados": sum(r["aprovado"] for r in rr), "n": len(rr)})
    (site / "assets").mkdir(parents=True, exist_ok=True)
    (site / "assets" / "dados.js").write_text("window.DADOS = " + json.dumps(D, ensure_ascii=False) + ";\n",
                                              encoding="utf-8")
    print("ok", round((site / "assets" / "dados.js").stat().st_size / 1024), "kB",
          "| MC:", len(D["f1_monte_carlo"]), "| nuvem:", len(D["otm_nuvem"]), "| corr:", D["otm_correlacao"],
          "| destaques:", D["otm_destaques"], "| eventos SIL:", ev)


if __name__ == "__main__":
    main()
    os._exit(0)
