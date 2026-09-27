"""Otimização do Foguete 2 (livre, vertical, eletrônica + paraquedas).

Uso: python otimizar_f2.py explorar N  |  python otimizar_f2.py finalistas K
Resultados em foguete2_livre/otimizacao/*.jsonl
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "foguete2_livre" / "otimizacao"
WORKERS = int(os.environ.get("M5_WORKERS", "10"))
NOSE_PARAM = {"HAACK": 0.0, "OGIVE": 1.0, "ELLIPSOID": 0.0, "POWER": 0.5}


def _init():
    global _avaliar
    from avaliacao_f2 import avaliar_f2
    _avaliar = avaliar_f2


def _task(args):
    tid, params = args
    return tid, _avaliar(params, True)


def sugerir(trial) -> dict:
    shape = trial.suggest_categorical("nose_shape", list(NOSE_PARAM))
    root = trial.suggest_int("fin_root", 35, 90)
    tip = round(trial.suggest_float("fin_tip_ratio", 0.0, 1.0) * root, 1)
    sweep = round(trial.suggest_float("fin_sweep_ratio", 0.0, 1.0) * (root - tip), 1)
    return {
        "D": trial.suggest_categorical("D", [26.0, 29.0]),
        "nose_shape": shape, "nose_param": NOSE_PARAM[shape],
        "nose_len": float(trial.suggest_int("nose_len", 60, 150, step=5)),
        "nose_shoulder": 55.0,
        "body_len": float(trial.suggest_int("body_len", 140, 320, step=5)),
        "fin_n": trial.suggest_categorical("fin_n", [3, 4]),
        "fin_root": float(root), "fin_tip": tip, "fin_sweep": sweep,
        "fin_span": float(trial.suggest_int("fin_span", 18, 60)),
        "fin_t": trial.suggest_categorical("fin_t", [1.2, 1.6, 2.0]),
        "ballast_g": trial.suggest_float("ballast_g", 0.0, 10.0, step=0.5),
    }


def explorar(n: int, seed: int = 5) -> None:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    SAIDA.mkdir(parents=True, exist_ok=True)
    arq = SAIDA / "explorar.jsonl"
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(
        seed=seed, multivariate=True, group=True, n_startup_trials=60, constant_liar=True))
    t0, melhor = time.time(), -1e9
    with mp.get_context("spawn").Pool(WORKERS, initializer=_init) as pool, open(arq, "a", encoding="utf-8") as log:
        feitos, lote = 0, WORKERS * 2
        while feitos < n:
            trials = [study.ask() for _ in range(min(lote, n - feitos))]
            for tid, res in pool.imap_unordered(_task, [(t.number, sugerir(t)) for t in trials]):
                study.tell(tid, res["J"])
                res["trial"] = tid
                log.write(json.dumps(res, default=float) + "\n")
                if res.get("viavel") and res["J"] > melhor:
                    melhor = res["J"]
                    pp = res["params"]
                    print(f"[{time.time()-t0:5.0f}s] #{tid} J={res['J']:.1f} apo={res['apogeu_medio']:.0f} "
                          f"min={res['apogeu_min']:.0f} D={pp['D']:.0f} m={res['massa_g']:.0f}g "
                          f"cal={res['cal']:.2f} vara={res['v_vara']:.1f} abre={res['v_abertura']:.1f} "
                          f"desce={res['v_descida']:.1f} chute={res['chute_d']:.0f} L={res['comprimento_mm']:.0f} "
                          f"{pp['nose_shape']} aletas {pp['fin_n']}x{pp['fin_root']:.0f}/{pp['fin_tip']:.0f}/"
                          f"{pp['fin_span']:.0f}/{pp['fin_sweep']:.0f} t{pp['fin_t']} lastro {pp['ballast_g']}",
                          flush=True)
            feitos += len(trials)
            log.flush()
        pool.terminate()


if __name__ == "__main__":
    t0 = time.time()
    if sys.argv[1] == "explorar":
        explorar(int(sys.argv[2]) if len(sys.argv) > 2 else 600)
    print(f"[fim em {time.time()-t0:.0f}s]", flush=True)
    os._exit(0)
