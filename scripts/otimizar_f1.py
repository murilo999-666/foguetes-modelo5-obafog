"""Otimização do Foguete 1 (OBAFOG Modelo 5) — Optuna TPE + pool de JVMs.

Uso:
  python otimizar_f1.py explorar  N   -> N avaliações no conjunto S1
  python otimizar_f1.py finalistas K  -> reavalia os K melhores de S1 no conjunto S2
  python otimizar_f1.py humano        -> avalia o MODELO-HUMANO (S1 e S2)

Resultados em foguete1_obafog/otimizacao/*.jsonl (1 linha por avaliação).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "foguete1_obafog" / "otimizacao"
WORKERS = int(os.environ.get("M5_WORKERS", "10"))

NOSE_PARAM = {"HAACK": 0.0, "OGIVE": 1.0, "ELLIPSOID": 0.0, "POWER": 0.5}

# MODELO-HUMANO: projetado por física/pesquisa ANTES de ver qualquer resultado da busca.
# Ogiva Von Kármán ~4 calibres (mínimo arrasto de pressão), 3 aletas trapezoidais
# enflechadas (menos arrasto que 4), corpo que põe o CP ~1,5 cal atrás do CG com o
# motor pesado na cauda, lastro pequeno, 45 graus (o "manual").
HUMANO = {"nose_shape": "HAACK", "nose_param": 0.0, "nose_len": 100.0, "body_len": 200.0,
          "fin_n": 3, "fin_root": 70.0, "fin_tip": 25.0, "fin_span": 38.0, "fin_sweep": 40.0,
          "fin_t": 1.6, "ballast_g": 6.0, "elev": 45.0}


def _init():
    global _avaliar
    from avaliacao import avaliar_f1
    _avaliar = avaliar_f1


def _task(args):
    tid, params, conj = args
    return tid, _avaliar(params, conj)


def sugerir(trial) -> dict:
    shape = trial.suggest_categorical("nose_shape", list(NOSE_PARAM))
    root = trial.suggest_int("fin_root", 18, 70)
    tip = round(trial.suggest_float("fin_tip_ratio", 0.0, 1.0) * root, 1)
    sweep = round(trial.suggest_float("fin_sweep_ratio", 0.0, 1.0) * (root - tip), 1)
    return {
        "nose_shape": shape, "nose_param": NOSE_PARAM[shape],
        "nose_len": float(trial.suggest_int("nose_len", 80, 240, step=5)),
        "body_len": float(trial.suggest_int("body_len", 0, 220, step=5)),
        "fin_n": trial.suggest_categorical("fin_n", [3, 4]),
        "fin_root": float(root), "fin_tip": tip, "fin_sweep": sweep,
        "fin_span": float(trial.suggest_int("fin_span", 20, 70)),
        "fin_t": trial.suggest_categorical("fin_t", [1.2, 1.6, 2.0]),
        "ballast_g": trial.suggest_float("ballast_g", 0.0, 25.0, step=0.5),
        "elev": float(trial.suggest_int("elev", 38, 60)),
    }


def sugerir_construtivel(trial) -> dict:
    """Variante CONSTRUTÍVEL: aleta que sobrevive a manuseio e pouso (raiz >= 28 mm,
    espessura >= 1,6 mm, envergadura <= 45 mm), cotas inteiras em mm."""
    shape = trial.suggest_categorical("nose_shape", list(NOSE_PARAM))
    root = trial.suggest_int("fin_root", 28, 60)
    tip = float(round(trial.suggest_float("fin_tip_ratio", 0.0, 1.0) * root))
    sweep = float(round(trial.suggest_float("fin_sweep_ratio", 0.0, 1.0) * (root - tip)))
    return {
        "nose_shape": shape, "nose_param": NOSE_PARAM[shape],
        "nose_len": float(trial.suggest_int("nose_len", 80, 220, step=5)),
        "body_len": float(trial.suggest_int("body_len", 0, 200, step=5)),
        "fin_n": trial.suggest_categorical("fin_n", [3, 4]),
        "fin_root": float(root), "fin_tip": tip, "fin_sweep": sweep,
        "fin_span": float(trial.suggest_int("fin_span", 20, 45)),
        "fin_t": trial.suggest_categorical("fin_t", [1.6, 2.0]),
        "ballast_g": trial.suggest_float("ballast_g", 0.0, 22.0, step=0.5),
        "elev": float(trial.suggest_int("elev", 40, 56)),
        "cal_min_extra": 1.35,
    }


def explorar(n: int, seed: int = 11) -> None:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    SAIDA.mkdir(parents=True, exist_ok=True)
    arq = SAIDA / os.environ.get("M5_ARQ", "explorar_S1.jsonl")
    sampler = optuna.samplers.TPESampler(seed=seed, multivariate=True, group=True,
                                         n_startup_trials=80, constant_liar=True)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.enqueue_trial({"nose_shape": "HAACK", "fin_root": 70, "fin_tip_ratio": 25 / 70,
                         "fin_sweep_ratio": 40 / 45, "nose_len": 100, "body_len": 200, "fin_n": 3,
                         "fin_span": 38, "fin_t": 1.6, "ballast_g": 6.0, "elev": 45})
    t0 = time.time()
    melhor = -1e9
    with mp.get_context("spawn").Pool(WORKERS, initializer=_init) as pool, open(arq, "a", encoding="utf-8") as log:
        feitos = 0
        lote = WORKERS * 2
        while feitos < n:
            trials = [study.ask() for _ in range(min(lote, n - feitos))]
            modo = os.environ.get("M5_MODO", "livre")
            fn = sugerir_construtivel if modo == "construtivel" else sugerir
            conj = os.environ.get("M5_CONJ", "S1")
            tarefas = [(t.number, fn(t), conj) for t in trials]
            for tid, res in pool.imap_unordered(_task, tarefas):
                study.tell(tid, res["J"])
                res["trial"] = tid
                log.write(json.dumps(res, default=float) + "\n")
                if res.get("viavel") and res["J"] > melhor:
                    melhor = res["J"]
                    pp = res["params"]
                    print(f"[{time.time()-t0:6.0f}s] #{tid} J={res['J']:.1f} media={res['perp_media']:.0f} "
                          f"min={res['perp_min']:.0f} cal={res['cal']:.2f} m={res['massa_g']:.0f}g "
                          f"vara={res['v_vara']:.1f} elev={pp['elev']:.0f} {pp['nose_shape']} "
                          f"L={res['comprimento_mm']:.0f} aletas {pp['fin_n']}x{pp['fin_root']:.0f}/"
                          f"{pp['fin_tip']:.0f}/{pp['fin_span']:.0f}/{pp['fin_sweep']:.0f} t{pp['fin_t']} "
                          f"lastro {pp['ballast_g']}g", flush=True)
            feitos += len(trials)
            log.flush()
            if feitos % 100 < lote:
                vi = sum(1 for t in study.trials if t.value is not None and t.value > -400)
                print(f"   ... {feitos}/{n} avaliados, {vi} viáveis, {time.time()-t0:.0f}s", flush=True)
        pool.terminate()


def carregar(arq: Path) -> list[dict]:
    return [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]


def finalistas(k: int) -> None:
    rows = [r for arq in sorted(SAIDA.glob("explorar_S1*.jsonl")) for r in carregar(arq) if r.get("viavel")]
    rows.sort(key=lambda r: r["J"], reverse=True)
    vistos, top = set(), []
    for r in rows:                                   # sem clones
        chave = tuple(round(float(v), 0) if isinstance(v, (int, float)) else v
                      for k2, v in sorted(r["params"].items()))
        if chave in vistos:
            continue
        vistos.add(chave)
        top.append(r["params"])
        if len(top) >= k:
            break
    top.append(humano_ajustado())
    arq = SAIDA / "finalistas_S2.jsonl"
    t0 = time.time()
    with mp.get_context("spawn").Pool(WORKERS, initializer=_init) as pool, open(arq, "w", encoding="utf-8") as log:
        for i, (tid, res) in enumerate(pool.imap_unordered(_task, [(i, p, "S2") for i, p in enumerate(top)])):
            res["idx"] = tid
            res["humano"] = (tid == len(top) - 1)
            log.write(json.dumps(res, default=float) + "\n")
            print(f"[{time.time()-t0:5.0f}s] {i+1}/{len(top)} idx{tid} J={res['J']:.1f} "
                  f"{'HUMANO' if res['humano'] else ''} {res.get('motivo','')}", flush=True)
        pool.terminate()


def humano_ajustado() -> dict:
    """O que um projetista faz na janela do OpenRocket: mantém a geometria e sobe o
    lastro até a margem de ~1,5 cal (a versão fixada de antemão deu 0,90 cal)."""
    from m5lib import build_f1, definir_motor, estabilidade_estatica
    lo, hi = 0.0, 25.0
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        doc, meta = build_f1({**HUMANO, "ballast_g": mid})
        definir_motor(doc, meta, "OBAFOG-M5_NEU_I07")
        if estabilidade_estatica(doc)["cal"] < 1.5:
            lo = mid
        else:
            hi = mid
    return {**HUMANO, "ballast_g": round(hi * 2) / 2}


def humano() -> None:
    from avaliacao import avaliar_f1
    h = humano_ajustado()
    print("MODELO-HUMANO ajustado:", h)
    for conj in ("S1", "S2"):
        r = avaliar_f1(h, conj)
        print(conj, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k != "params"})


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "explorar"
    t0 = time.time()
    if modo == "explorar":
        explorar(int(sys.argv[2]) if len(sys.argv) > 2 else 1000)
    elif modo == "finalistas":
        finalistas(int(sys.argv[2]) if len(sys.argv) > 2 else 40)
    elif modo == "humano":
        humano()
    print(f"[fim em {time.time()-t0:.0f}s]", flush=True)
    os._exit(0)
