"""Avaliação do Foguete 2 (livre): voo quase vertical, paraquedas por mola + trava de servo.

NOTA (metros):
    J = 0,7 * apogeu médio + 0,3 * apogeu mínimo   (motores 5 / 7 / 9 N.s e formato PRO, sem vento)
        - 20 m por m/s de saída da vara abaixo de 11 m/s (nominal)
        - 40 m por calibre abaixo de 1,4 cal
RESTRIÇÕES DURAS:
    1,2 <= margem estática com motor <= 2,6 cal; mínima em voo >= 1,0 cal
    saída da vara >= 8,5 m/s (nominal) e >= 6,5 m/s (pior motor)
    velocidade na abertura do paraquedas <= 12 m/s (nominal e com 4 m/s de vento)
    descida 3,0-6,0 m/s; impacto <= 6,5 m/s
    baia do paraquedas cabe no tubo (volume do pacote + cordão + pistão + mola)
O diâmetro do paraquedas não é otimizado: é calculado para ~4,5 m/s de descida.
"""
from __future__ import annotations

import math
import traceback
from typing import Any

import numpy as np

from m5lib import Cenario, build_f2, definir_motor, estabilidade_estatica, simular

ALT_LOCAL = 300.0          # campo genérico (ajuste para o local real)
TEMP_C = 25.0
RHO = 1.14
V_DESCIDA_ALVO = 4.5
MOTOR_NOMINAL = "OBAFOG-M5_NEU_I07"
MOTORES = ["OBAFOG-M5_NEU_I05", "OBAFOG-M5_NEU_I07", "OBAFOG-M5_NEU_I09", "OBAFOG-M5_PRO_I07"]


def diametro_paraquedas(massa_descida_g: float, cd: float = 0.8, v: float = V_DESCIDA_ALVO) -> float:
    area = 2 * massa_descida_g * 1e-3 * 9.81 / (RHO * cd * v * v)
    return math.ceil(math.sqrt(4 * area / math.pi) * 1000 / 10) * 10    # mm, múltiplo de 10


def baia_necessaria(D: float, chute_d: float, shock_len: float = 1200.0) -> float:
    """Comprimento (mm) de tubo para paraquedas dobrado + cordão + pistão + mola."""
    r_int = D / 2 - 0.8
    area = math.pi * r_int ** 2                              # mm2
    vol_pe = math.pi / 4 * chute_d ** 2 * 0.035              # lona PE 35 um (mm3)
    vol_pacote = vol_pe * 4.0 + 6 * chute_d * 0.8            # fator de dobra + linhas
    vol_cordao = shock_len * math.pi / 4 * 3.0 ** 2 * 1.6    # elástico 3 mm enrolado
    return (vol_pacote + vol_cordao) / area + 10.0 + 18.0    # + pistão + mola comprimida


def _cen(motor: str, vento: float = 0.0, de: float = 90.0) -> Cenario:
    return Cenario(motor=motor, elev_deg=87.0, vento=vento, vento_de=de, rod_len=1.2,
                   turb=0.0, alt_local=ALT_LOCAL, temp_c=TEMP_C, t_max=120.0)


def avaliar_f2(params: dict, guardar: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"params": dict(params)}
    try:
        p = dict(params)
        # 1a passada: massa de descida para dimensionar o paraquedas
        doc, meta = build_f2(p)
        definir_motor(doc, meta, MOTOR_NOMINAL)
        est = estabilidade_estatica(doc)
        p["chute_d"] = diametro_paraquedas(est["massa_seca_g"])
        p["chute_line_len"] = p["chute_d"]
        baia = baia_necessaria(p["D"], p["chute_d"])
        out.update(chute_d=p["chute_d"], baia_mm=baia)
        if p["body_len"] < p["nose_shoulder"] + baia:
            out.update(J=-2000 - (p["nose_shoulder"] + baia - p["body_len"]), viavel=False,
                       motivo="paraquedas nao cabe")
            return out
        if p["fin_sweep"] + p["fin_tip"] > p["fin_root"] + 0.5:
            out.update(J=-2000, viavel=False, motivo="geometria")
            return out
        doc, meta = build_f2(p)
        definir_motor(doc, meta, MOTOR_NOMINAL)
        est = estabilidade_estatica(doc)
        out.update(cal=est["cal"], massa_g=est["massa_g"], massa_seca_g=est["massa_seca_g"],
                   comprimento_mm=p["nose_len"] + p["body_len"] + p.get("fincan_len", 100.0))
        if est["cal"] < 1.2 or est["cal"] > 2.6:
            d = (1.2 - est["cal"]) if est["cal"] < 1.2 else (est["cal"] - 2.6)
            out.update(J=-1000 - 300 * d, viavel=False, motivo="margem estatica")
            return out
        apos, res = [], {}
        for m in MOTORES:
            r = simular(doc, meta, _cen(m))
            if r.get("erro"):
                out.update(J=-1000, viavel=False, motivo=r["erro"])
                return out
            res[m] = r
            apos.append(r["apogeu"])
        vento = simular(doc, meta, _cen(MOTOR_NOMINAL, 4.0, 90.0))
        nom = res[MOTOR_NOMINAL]
        pior = res["OBAFOG-M5_PRO_I07"]
        fraco = res["OBAFOG-M5_NEU_I05"]
        apos = np.array(apos)
        out.update(apogeu_medio=float(apos.mean()), apogeu_min=float(apos.min()),
                   apogeu_nominal=nom["apogeu"], v_vara=nom["v_vara"],
                   v_vara_pior=min(pior["v_vara"], fraco["v_vara"]),
                   stab_min_voo=nom["stab_min"], v_abertura=nom.get("v_abertura"),
                   v_abertura_vento=vento.get("v_abertura"), v_descida=nom.get("v_descida"),
                   v_impacto=nom["v_impacto"], deriva_4ms=vento["total"], t_voo=nom["t_voo"],
                   v_max=res["OBAFOG-M5_NEU_I09"]["v_max"], apogeu_vento=vento["apogeu"])
        if guardar:
            out["cenarios"] = {m: {k: r[k] for k in ("apogeu", "v_vara", "v_abertura", "v_descida",
                                                     "v_impacto", "t_voo", "stab_min", "total")
                                   if k in r} for m, r in res.items()}
        viol = 0.0
        if (nom["stab_min"] or 0) < 1.0:
            viol += 1.0 - (nom["stab_min"] or 0)
        if nom["v_vara"] < 8.5:
            viol += (8.5 - nom["v_vara"]) / 2
        if out["v_vara_pior"] < 6.5:
            viol += (6.5 - out["v_vara_pior"]) / 2
        for va in (nom.get("v_abertura"), vento.get("v_abertura")):
            if va is None or va > 12.0:
                viol += ((va or 30.0) - 12.0) / 5
        vd = nom.get("v_descida") or 99
        if not (3.0 <= vd <= 6.0):
            viol += abs(vd - 4.5) / 3
        if nom["v_impacto"] > 6.5:
            viol += (nom["v_impacto"] - 6.5) / 3
        rob = 0.7 * float(apos.mean()) + 0.3 * float(apos.min())
        pen = 20.0 * max(0.0, 11.0 - nom["v_vara"]) + 40.0 * max(0.0, 1.4 - est["cal"])
        out["apogeu_robusto"] = rob
        if viol > 0:
            out.update(J=-500 - 200 * viol + 0.1 * rob, viavel=False, motivo="restricao de voo")
            return out
        out.update(J=rob - pen, viavel=True, motivo="")
        return out
    except Exception as e:
        out.update(J=-3000, viavel=False, motivo=f"erro: {e}", tb=traceback.format_exc()[-800:])
        return out
