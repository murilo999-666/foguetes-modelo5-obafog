"""Versões com BORDO DE FUGA RETO (deitado na mesa: imprime sem suporte) dos melhores
construtíveis: enflechamento = raiz - ponta, lastro reajustado para 1,40 cal, nota em S2."""
import json, os, time, math, multiprocessing as mp
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[1]

def _init():
    global _av, _m
    from avaliacao import avaliar_f1
    import m5lib
    _av, _m = avaliar_f1, m5lib

def lastro_para(p, alvo=1.40):
    lo, hi = 0.0, 25.0
    def cal(b):
        d, m = _m.build_f1({**p, "ballast_g": b}); _m.definir_motor(d, m, "OBAFOG-M5_NEU_I07")
        return _m.estabilidade_estatica(d)["cal"]
    if cal(0.0) >= alvo: return 0.0
    for _ in range(18):
        mid = 0.5*(lo+hi); (lo, hi) = (mid, hi) if cal(mid) < alvo else (lo, mid)
    return math.ceil(hi*2)/2

def _t(args):
    nome, p = args
    p = dict(p); p["fin_sweep"] = p["fin_root"] - p["fin_tip"]; p.pop("cal_min_extra", None)
    p["ballast_g"] = lastro_para(p)
    r = _av({**p, "cal_min_extra": 1.35}, "S2")
    return nome, p, r

def main():
    rows = [json.loads(l) for l in open(RAIZ/"foguete1_obafog/otimizacao/construtivel_S2.jsonl", encoding="utf-8")]
    v = sorted([r for r in rows if r.get("viavel")], key=lambda r: r["J"], reverse=True)
    vistos, cand = set(), []
    for r in v:
        ch = (r["params"]["nose_shape"], r["params"]["nose_len"], r["params"]["body_len"], r["params"]["fin_n"], r["params"]["fin_root"])
        if ch in vistos: continue
        vistos.add(ch); cand.append((f"c{len(cand)}_J{r['J']:.0f}", r["params"]))
        if len(cand) >= 16: break
    with mp.get_context("spawn").Pool(10, initializer=_init) as pool:
        res = pool.map(_t, cand); pool.terminate()
    out = []
    for nome, p, r in sorted(res, key=lambda x: x[2]["J"], reverse=True):
        out.append({"nome": nome, "J": r["J"], "viavel": r.get("viavel"), "motivo": r.get("motivo"),
                    "perp_media": r.get("perp_media"), "perp_min": r.get("perp_min"), "perp_nominal": r.get("perp_nominal"),
                    "cal": r.get("cal"), "massa_g": r.get("massa_g"), "params": p})
        print(f"{nome:12s} J={r['J']:7.1f} med={r.get('perp_media') or 0:5.0f} min={r.get('perp_min') or 0:5.0f} nom={r.get('perp_nominal') or 0:5.0f} cal={r.get('cal') or 0:4.2f} m={r.get('massa_g') or 0:5.1f} | {p['nose_shape']} {p['nose_len']:.0f} corpo {p['body_len']:.0f} {p['fin_n']}x{p['fin_root']:.0f}/{p['fin_tip']:.0f}/{p['fin_span']:.0f}/s{p['fin_sweep']:.0f} lastro {p['ballast_g']} {p['elev']:.0f}° {r.get('motivo') or ''}", flush=True)
    (RAIZ/"foguete1_obafog/otimizacao/bf_reto_S2.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")

if __name__ == "__main__":
    t0 = time.time(); main(); print(f"[{time.time()-t0:.0f}s]"); os._exit(0)
