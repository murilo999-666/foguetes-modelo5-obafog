"""Roda o firmware (voo.h compilado no PC) contra todas as trajetórias do OpenRocket.

Uso (Python do sistema):  python rodar_sil.py
Precisa de teste_voo.exe compilado:
    python -m ziglang c++ -std=c++17 -O2 -Wall -Wextra teste_voo.cpp -o teste_voo.exe
e das trajetórias em trajetorias/ (scripts/exportar_trajetorias_f2.py).

Critérios de aprovação (cada caso):
  - nenhuma decolagem falsa nos 60 s armado no chão (com rajadas de pressão)
  - abertura depois do apogeu real e no máximo 1,5 s depois (ou por tempo, se nada mais)
  - velocidade vertical real na abertura <= 12 m/s (em módulo)
  - pouso detectado
"""
from __future__ import annotations

import itertools
import json
import subprocess
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).parent
EXE = AQUI / "teste_voo.exe"


def rodar(traj: Path, ruido: float, semente: int, picos: int, falha: int, log: Path | None = None) -> dict:
    args = [str(EXE), str(traj), str(ruido), str(semente), str(picos), str(falha)]
    if log:
        args.append(str(log))
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()
    return json.loads(out.replace("\\", "/"))


def main() -> None:
    trajs = sorted((AQUI / "trajetorias").glob("traj_*.csv"))
    res = []
    for traj, ruido, picos, falha, sem in itertools.product(trajs, (3.0, 8.0), (0, 1), (0, 1), range(1, 6)):
        r = rodar(traj, ruido, sem, picos, falha)
        r["traj"] = traj.stem
        ok_chao = r["falso_no_chao"] == 0
        atraso = r["atraso_abertura"]
        ok_hora = (-0.6 <= atraso <= 1.5) or r["motivo"] == "tempo"
        ok_vel = abs(r["v_vertical_abertura"]) <= 12.0
        ok_pouso = r["t_pouso_detectado"] > 0
        r["aprovado"] = ok_chao and ok_hora and ok_vel and ok_pouso
        r["falhas"] = [n for n, ok in (("decolagem falsa", ok_chao), ("hora", ok_hora),
                                         ("velocidade", ok_vel), ("pouso", ok_pouso)) if not ok]
        res.append(r)
    (AQUI / "resultado_sil.jsonl").write_text("\n".join(json.dumps(r) for r in res), encoding="utf-8")
    n = len(res)
    aprov = sum(r["aprovado"] for r in res)
    print(f"casos: {n} | aprovados: {aprov} ({100*aprov/n:.1f}%)")
    print("motivos de abertura:", dict(Counter(r["motivo"] for r in res)))
    print("falhas:", dict(Counter(f for r in res for f in r["falhas"])))
    print(f"\n{'trajetória':22s} {'apogeu':>7s} {'atraso médio':>13s} {'atraso máx':>11s} {'|v| máx':>8s} {'aprov':>6s}")
    for traj in sorted({r["traj"] for r in res}):
        rr = [r for r in res if r["traj"] == traj]
        at = [r["atraso_abertura"] for r in rr]
        vv = [abs(r["v_vertical_abertura"]) for r in rr]
        print(f"{traj:22s} {rr[0]['apogeu_real']:7.1f} {sum(at)/len(at):13.2f} {max(at):11.2f} "
              f"{max(vv):8.1f} {sum(r['aprovado'] for r in rr):3d}/{len(rr)}")
    for r in res:
        if not r["aprovado"]:
            print("REPROVADO:", r["traj"], "ruido", r["ruido_Pa"], "picos", r["picos"], "falha", r["falha"],
                  "->", r["falhas"], "atraso", r["atraso_abertura"], "motivo", r["motivo"])
    # um log detalhado para gráfico
    rodar(AQUI / "trajetorias" / "traj_NEU_I07_v0.csv", 3.0, 1, 1, 0, AQUI / "exemplo_log_I07.csv")


if __name__ == "__main__":
    main()
