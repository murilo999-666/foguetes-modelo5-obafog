"""Compara, NO MESMO CONJUNTO S2, o ótimo teórico (busca livre), a variante construível e o
MODELO-HUMANO; salva o .ork do teórico para referência.

Uso: python comparar_f1.py
Saída: foguete1_obafog/comparacao_S2.json e F1_teorico_v1.ork
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
OTM = RAIZ / "foguete1_obafog" / "otimizacao"


def _init():
    global _av
    from avaliacao import avaliar_f1
    _av = avaliar_f1


def _t(args):
    nome, p = args
    return nome, _av(p, "S2")


def carregar(arq: Path) -> list[dict]:
    return [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]


def unicos(rows, k):
    vistos, out = set(), []
    for r in sorted((r for r in rows if r.get("viavel")), key=lambda r: r["J"], reverse=True):
        ch = tuple(sorted((a, round(b, 0) if isinstance(b, float) else b) for a, b in r["params"].items()))
        if ch not in vistos:
            vistos.add(ch)
            out.append(r["params"])
        if len(out) >= k:
            break
    return out


def main() -> None:
    from otimizar_f1 import humano_ajustado
    livres = carregar(OTM / "explorar_S1.jsonl") + carregar(OTM / "explorar_S1_v2.jsonl")
    constr = carregar(OTM / "construtivel_S2.jsonl")
    tarefas = [(f"livre_{i}", p) for i, p in enumerate(unicos(livres, 12))]
    tarefas += [(f"construtivel_{i}", p) for i, p in enumerate(unicos(constr, 6))]
    tarefas.append(("humano", humano_ajustado()))
    t0 = time.time()
    with mp.get_context("spawn").Pool(int(os.environ.get("M5_WORKERS", "10")), initializer=_init) as pool:
        res = dict(pool.map(_t, tarefas))
        pool.terminate()
    tab = []
    for nome, r in res.items():
        tab.append({"nome": nome, "J": r["J"], "viavel": r.get("viavel"), "motivo": r.get("motivo"),
                    **{k: r.get(k) for k in ("perp_media", "perp_min", "perp_nominal", "cal", "massa_g",
                                             "massa_seca_g", "v_vara", "v_vara_pior", "flutter_fs",
                                             "comprimento_mm")},
                    "params": r["params"]})
    tab.sort(key=lambda r: r["J"], reverse=True)
    (RAIZ / "foguete1_obafog" / "comparacao_S2.json").write_text(json.dumps(tab, indent=1, default=float),
                                                                 encoding="utf-8")
    for r in tab:
        p = r["params"]
        print(f"{r['nome']:16s} J={r['J']:7.1f} med={r.get('perp_media') or 0:5.0f} min={r.get('perp_min') or 0:5.0f} "
              f"nom={r.get('perp_nominal') or 0:5.0f} cal={r.get('cal') or 0:4.2f} m={r.get('massa_g') or 0:5.1f} "
              f"aletas {p['fin_n']}x{p['fin_root']:.0f}/{p['fin_tip']:.0f}/{p['fin_span']:.0f} t{p['fin_t']} "
              f"{r.get('motivo') or ''}")
    # salva o melhor livre como referência
    from avaliacao import ALT_LOCAL, TEMP_C
    from m5lib import Cenario, build_f1, salvar_com_simulacoes
    melhor_livre = next(r for r in tab if r["nome"].startswith("livre") and r["viavel"])
    doc, meta = build_f1(melhor_livre["params"], nome="Foguete 1 - OTIMO TEORICO (aleta fragil, so referencia)")
    e = float(melhor_livre["params"]["elev"])
    salvar_com_simulacoes(doc, meta, [
        (f"NOMINAL 7 N.s {e:.0f} graus", Cenario(motor="OBAFOG-M5_NEU_I07", elev_deg=e, turb=0.0,
                                                  alt_local=ALT_LOCAL, temp_c=TEMP_C)),
        ("Pessimista 5 N.s", Cenario(motor="OBAFOG-M5_NEU_I05", elev_deg=e, turb=0.0,
                                     alt_local=ALT_LOCAL, temp_c=TEMP_C))],
        RAIZ / "foguete1_obafog" / "F1_teorico_v1.ork", motor_selecionado="OBAFOG-M5_NEU_I07")
    print(f"[fim em {time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
    os._exit(0)
