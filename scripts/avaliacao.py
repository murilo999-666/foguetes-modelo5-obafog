"""Avaliação robusta do Foguete 1 (OBAFOG Modelo 5): cenários + nota.

A MESMA nota é usada na exploração (conjunto S1, menos cenários) e na escolha
final (S2, todos os cenários). Lição do bit07: pré-filtro com outra função de
nota seleciona a população errada.

NOTA (em "metros equivalentes"):
    J = 0,75 * média(alcance perp) + 0,25 * mínimo(alcance perp)
        - 15 m por m/s de saída da vara abaixo de 13 m/s (motor nominal)
        - 60 m por calibre de margem estática abaixo de 1,4 cal (tolerância de montagem)
RESTRIÇÕES DURAS (reprovou = J muito negativo, proporcional à violação):
    1,2 <= margem estática com motor <= 2,5 cal   (regulamento: "igual ou pouco maior que 1")
    estabilidade mínima em voo (nominal, sem vento) >= 1,0 cal
    saída da vara >= 11 m/s (nominal) e >= 7 m/s (pior motor: PRO 5 N.s)
    flutter: V_flutter >= 1,5 x V_max do cenário mais rápido (REG 11,5 N.s)
    aleta sem balanço para trás (enflechamento + ponta <= raiz), comprimento <= 650 mm
"""
from __future__ import annotations

import math
import traceback
from typing import Any

import numpy as np

from m5lib import (Cenario, build_f1, definir_motor, estabilidade_estatica, simular)

# pressão/temperatura da pista (Barra do Piraí ~380 m, tarde de dezembro)
ALT_LOCAL = 380.0
TEMP_C = 28.0
P_LOCAL = 101325.0 * (1 - 2.25577e-5 * ALT_LOCAL) ** 5.25588
A_SOM = math.sqrt(1.4 * 287.05 * (TEMP_C + 273.15))

# módulo de cisalhamento conservador para peça IMPRESSA (menor que o do material maciço)
G_IMPRESSO = {"PLA": 1.0e9, "PETG": 0.70e9}

MOTOR_NOMINAL = "OBAFOG-M5_NEU_I07"
CONJUNTOS = {
    # exploração: 3 impulsos x (sem vento, 4 m/s de frente, 4 m/s de cauda)
    "S1": {"motores": ["OBAFOG-M5_NEU_I05", "OBAFOG-M5_NEU_I07", "OBAFOG-M5_NEU_I09"],
           "ventos": [(0.0, 0.0), (4.0, 0.0), (4.0, 180.0)]},
    # escolha final: 5 motores (impulso e formato) x 6 ventos
    "S2": {"motores": ["OBAFOG-M5_NEU_I05", "OBAFOG-M5_NEU_I07", "OBAFOG-M5_NEU_I09",
                       "OBAFOG-M5_REG_I07", "OBAFOG-M5_PRO_I07"],
           "ventos": [(0.0, 0.0), (3.0, 0.0), (3.0, 180.0), (3.0, 90.0), (4.5, 0.0), (4.5, 180.0)]},
}


def flutter_fs(p: dict, v_max: float) -> tuple[float, float]:
    """Fator de segurança de flutter (NACA TN 4197, forma da Apogee)."""
    root, tip, span, t = p["fin_root"] * 1e-3, p["fin_tip"] * 1e-3, p["fin_span"] * 1e-3, p["fin_t"] * 1e-3
    area = (root + tip) / 2 * span
    ar = span ** 2 / area
    lam = tip / root
    tc = t / root
    g = G_IMPRESSO.get(p.get("material", "PLA"), 1.0e9)
    denom = 1.337 * ar ** 3 * P_LOCAL * (lam + 1) / (2 * (ar + 2) * tc ** 3)
    vf = A_SOM * math.sqrt(g / denom)
    return vf, vf / max(v_max, 1.0)


def _cen(motor: str, elev: float, vento: float, de: float, seed: int = 7) -> Cenario:
    # turbulência ZERO na comparação entre projetos: com turbulência o OpenRocket
    # 24.12 ignora a semente (teste_determinismo.py) e a nota vira sorteio. A
    # dispersão por rajada é medida depois, só no projeto final (Monte Carlo).
    return Cenario(motor=motor, elev_deg=elev, vento=vento, vento_de=de, rod_len=1.2,
                   turb=0.0, alt_local=ALT_LOCAL, temp_c=TEMP_C, seed=seed)


def avaliar_f1(params: dict, conjunto: str = "S1", guardar_cenarios: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"params": dict(params), "conjunto": conjunto}
    try:
        p = dict(params)
        viol = 0.0
        if p["fin_tip"] > p["fin_root"] + 1e-6:
            viol += p["fin_tip"] - p["fin_root"]
        if p["fin_sweep"] + p["fin_tip"] > p["fin_root"] + 0.5:
            viol += p["fin_sweep"] + p["fin_tip"] - p["fin_root"]
        # bordo de fuga tem de ficar DEITADO na mesa (impressão em pé, traseira embaixo):
        # qualquer subida dele ao longo da envergadura é um balanço muito além de 45 graus
        # (ex.: 13 mm em 44 mm de envergadura = 74 graus da vertical). A primeira versão
        # desta regra estava invertida e deixou passar aletas que precisariam de suporte.
        recuo_te = p["fin_root"] - p["fin_sweep"] - p["fin_tip"]
        if recuo_te > 0.5 and not p.get("aceita_suporte", False):
            viol += recuo_te / 5
        comp_total = p["nose_len"] + p["body_len"] + p.get("fincan_len", 100.0)
        out["comprimento_mm"] = comp_total
        if comp_total > 650:
            viol += (comp_total - 650) / 10
        if viol > 0:
            out.update(J=-2000 - 10 * viol, viavel=False, motivo="geometria")
            return out
        try:
            doc, meta = build_f1(p)
        except ValueError as e:                     # lastro não cabe na ogiva
            out.update(J=-2000, viavel=False, motivo=f"montagem: {e}")
            return out
        definir_motor(doc, meta, MOTOR_NOMINAL)
        est = estabilidade_estatica(doc)
        out.update(cal=est["cal"], cal_queimado=est["cal_burnout"], massa_g=est["massa_g"],
                   massa_seca_g=est["massa_seca_g"], cp_mm=est["cp_mm"], cg_mm=est["cg_mm"],
                   lastro_prof_mm=meta["lastro_prof_mm"])
        cal_min = float(p.get("cal_min_extra", 1.2))
        if est["cal"] < cal_min or est["cal"] > 2.5:
            d = (cal_min - est["cal"]) if est["cal"] < cal_min else (est["cal"] - 2.5)
            out.update(J=-1000 - 300 * d, viavel=False, motivo="margem estatica")
            return out

        elev = float(p["elev"])
        cfg = CONJUNTOS[conjunto]
        perps, detalhes = [], []
        nominal = None
        for motor in cfg["motores"]:
            for vento, de in cfg["ventos"]:
                r = simular(doc, meta, _cen(motor, elev, vento, de))
                if r.get("erro"):
                    out.update(J=-1000, viavel=False, motivo=r["erro"])
                    return out
                perps.append(r["perp"])
                if guardar_cenarios:
                    detalhes.append({"motor": motor, "vento": vento, "de": de,
                                     **{k: r[k] for k in ("perp", "total", "lateral", "apogeu",
                                                          "v_max", "v_vara", "stab_min", "aoa_max",
                                                          "v_impacto", "t_voo")}})
                if motor == MOTOR_NOMINAL and vento == 0.0:
                    nominal = r
        # cenários extremos (1 simulação cada)
        rapido = simular(doc, meta, _cen("OBAFOG-M5_REG_I115", elev, 0.0, 0.0))
        lento = simular(doc, meta, _cen("OBAFOG-M5_PRO_I05", elev, 0.0, 0.0))
        vf, fs = flutter_fs(p, rapido["v_max"])
        perps = np.array(perps)
        media, minimo, desvio = float(perps.mean()), float(perps.min()), float(perps.std())
        out.update(perp_media=media, perp_min=minimo, perp_max=float(perps.max()),
                   perp_desvio=desvio, perp_nominal=nominal["perp"], apogeu_nominal=nominal["apogeu"],
                   v_vara=nominal["v_vara"], v_vara_pior=lento["v_vara"],
                   stab_min_voo=nominal["stab_min"], v_max=rapido["v_max"],
                   mach_max=rapido["mach_max"], v_impacto=nominal["v_impacto"],
                   flutter_v=vf, flutter_fs=fs, aoa_max_nominal=nominal["aoa_max"],
                   t_voo=nominal["t_voo"])
        if guardar_cenarios:
            out["cenarios"] = detalhes
        # restrições duras de voo
        viol = 0.0
        if nominal["stab_min"] is None or nominal["stab_min"] < 1.0:
            viol += 1.0 - (nominal["stab_min"] or 0.0)
        if nominal["v_vara"] < 11.0:
            viol += (11.0 - nominal["v_vara"]) / 2
        if lento["v_vara"] < 7.0:
            viol += (7.0 - lento["v_vara"]) / 2
        if fs < 1.5:
            viol += 1.5 - fs
        robusto = 0.75 * media + 0.25 * minimo
        pen = 15.0 * max(0.0, 13.0 - nominal["v_vara"]) + 60.0 * max(0.0, 1.4 - est["cal"])
        out["alcance_robusto"] = robusto
        out["penalidade"] = pen
        if viol > 0:
            out.update(J=-500 - 200 * viol + 0.1 * robusto, viavel=False, motivo="restricao de voo")
            return out
        out.update(J=robusto - pen, viavel=True, motivo="")
        return out
    except Exception as e:  # nunca derrubar o lote
        out.update(J=-3000, viavel=False, motivo=f"erro: {e}", tb=traceback.format_exc()[-800:])
        return out
