"""Biblioteca do projeto Modelo 5 (motor sólido oficial da OBAFOG).

Constrói foguetes PARAMÉTRICOS do zero no OpenRocket 24.12 (via a ponte JPype
do orx) e simula cenários. As cotas usadas aqui são as mesmas que vão para os
STL (scripts/gerar_stl_*.py), então simulação e peça impressa não divergem.

Convenções (verificadas em scripts/teste_convencoes.py):
  - ângulo de lançamento: graus ACIMA DO HORIZONTE (45 = oblíquo; 90 = vertical).
    O OpenRocket usa ângulo a partir da vertical: rod_angle = 90 - elevação.
  - direção do lançamento (azimute): 0 = norte, 90 = leste.
  - vento: velocidade média + direção DE ONDE SOPRA, relativa ao lançamento
    ("cauda" = empurra o foguete para frente).
  - alcance "perp": projeção do ponto de queda na direção do lançamento (é como a
    Jornada de Foguetes mede); "total": distância do ponto de lançamento (como a
    etapa escolar da OBAFOG mede).

Unidades dos dicionários de parâmetros: mm e g (legível); tudo vira SI aqui.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ORX_SRC = r"C:\Users\muril\openrocket-optimizer\src"
if ORX_SRC not in sys.path:
    sys.path.insert(0, ORX_SRC)

import jpype  # noqa: E402

from orx.bridge.orjava import J, OrBridge  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]           # .../modelo5_solido
MOTOR_DIR = RAIZ / "motor" / "eng"

MM = 1e-3
G = 1e-3

# ----------------------------------------------------------------------------
# Materiais (densidade de peça impressa com paredes sólidas)
# ----------------------------------------------------------------------------
BULK = {                       # kg/m3
    "PLA": 1240.0,
    "PETG": 1270.0,
    "PVC": 1400.0,
    "PET_garrafa": 1380.0,
    "PS_chapa": 1050.0,
    "massa_epoxi": 1700.0,     # Durepoxi (lastro não metálico)
}
SURFACE = {"PE_35um": 0.033, "ripstop": 0.045}     # kg/m2 (paraquedas)
LINE = {"linha_nylon": 0.0003, "cordao_2mm": 0.0020, "elastico_3mm": 0.0025}  # kg/m

# motor: cotas físicas (vídeos 210/216 e regulamento) -> ver motor/MOTOR.md
MOTOR_OD = 20.0          # mm, cano PVC soldável 20
MOTOR_LEN = 103.0        # mm, tubo 100 + fundo do cap
CAP_OD = 24.6            # mm, conferir com paquímetro (varia por fabricante)
CAP_LEN = 18.0           # mm, bolsa 15 + fundo 3
CAP_MASS = 5.0           # g, conferir na balança
MOTOR_BARE = 85.0        # mm de tubo exposto à frente do cap (100 - 15 de bolsa)
FOLGA_CAP = 3.0          # mm entre a traseira do foguete e o cap: o cap tem de poder saltar


class Ctx:
    """Guarda a ponte e as classes Java já resolvidas (1 JVM por processo)."""

    _inst: "Ctx | None" = None

    def __init__(self) -> None:
        self.b = OrBridge()
        p = "info.openrocket.core."
        self.Rocket = J(p + "rocketcomponent.Rocket")
        self.AxialStage = J(p + "rocketcomponent.AxialStage")
        self.NoseCone = J(p + "rocketcomponent.NoseCone")
        self.BodyTube = J(p + "rocketcomponent.BodyTube")
        self.Transition = J(p + "rocketcomponent.Transition")
        self.InnerTube = J(p + "rocketcomponent.InnerTube")
        self.CenteringRing = J(p + "rocketcomponent.CenteringRing")
        self.Bulkhead = J(p + "rocketcomponent.Bulkhead")
        self.TubeCoupler = J(p + "rocketcomponent.TubeCoupler")
        self.LaunchLug = J(p + "rocketcomponent.LaunchLug")
        self.TrapezoidFinSet = J(p + "rocketcomponent.TrapezoidFinSet")
        self.MassComponent = J(p + "rocketcomponent.MassComponent")
        self.Parachute = J(p + "rocketcomponent.Parachute")
        self.ShockCord = J(p + "rocketcomponent.ShockCord")
        self.Shape = J(p + "rocketcomponent.Transition$Shape")
        self.AxialMethod = J(p + "rocketcomponent.position.AxialMethod")
        self.CrossSection = J(p + "rocketcomponent.FinSet$CrossSection")
        self.Finish = J(p + "rocketcomponent.ExternalComponent$Finish")
        self.DeployEvent = J(p + "rocketcomponent.DeploymentConfiguration$DeployEvent")
        self.Material = J(p + "material.Material")
        self.MType = J(p + "material.Material$Type")
        self.MCType = J(p + "rocketcomponent.MassComponent$MassComponentType")
        self.DocFactory = J(p + "document.OpenRocketDocumentFactory")
        self.Simulation = J(p + "document.Simulation")
        self.FlightDataType = J(p + "simulation.FlightDataType")
        self.EventType = J(p + "simulation.FlightEvent$Type")
        self.Barrowman = J(p + "aerodynamics.BarrowmanCalculator")
        self.FlightConditions = J(p + "aerodynamics.FlightConditions")
        self.WarningSet = J(p + "logging.WarningSet")
        self.MassCalculator = J(p + "masscalc.MassCalculator")

    @classmethod
    def get(cls) -> "Ctx":
        if cls._inst is None:
            cls._inst = Ctx()
        return cls._inst

    # ---- materiais ----
    def bulk(self, nome: str):
        return self.Material.newMaterial(self.MType.BULK, nome, BULK[nome], True)

    def surface(self, nome: str):
        return self.Material.newMaterial(self.MType.SURFACE, nome, SURFACE[nome], True)

    def line(self, nome: str):
        return self.Material.newMaterial(self.MType.LINE, nome, LINE[nome], True)


# ----------------------------------------------------------------------------
# utilidades de montagem
# ----------------------------------------------------------------------------

def _mass(c: Ctx, parent, nome: str, massa_g: float, comprimento_mm: float,
          raio_mm: float, metodo: str = "TOP", offset_mm: float = 0.0,
          tipo: str = "MASSCOMPONENT"):
    m = c.MassComponent()
    m.setName(nome)
    m.setComponentMass(massa_g * G)
    m.setLength(max(comprimento_mm, 0.1) * MM)
    m.setRadius(max(raio_mm, 0.1) * MM)
    m.setMassComponentType(getattr(c.MCType, tipo))
    parent.addChild(m)
    m.setAxialMethod(getattr(c.AxialMethod, metodo))
    m.setAxialOffset(offset_mm * MM)
    return m


def nose_inner_radius_at(c: Ctx, nose, x_m: float) -> float:
    return max(float(nose.getRadius(x_m)) - float(nose.getThickness()), 0.0)


def lastro_na_ponta(c: Ctx, nose, massa_g: float, densidade: float = BULK["massa_epoxi"],
                    n_discos: int = 8, nome: str = "Lastro massa epoxi") -> float:
    """Enche o bico da ogiva com massa epóxi até somar massa_g.

    Discretizado em discos no raio local (um único cilindro erra o CG em ~1,5 cm,
    lição do bit03). Devolve a profundidade de enchimento em mm."""
    if massa_g <= 0:
        return 0.0
    L = float(nose.getLength())
    xs = np.linspace(0, L * 0.9, 400)
    areas = np.array([math.pi * nose_inner_radius_at(c, nose, x) ** 2 for x in xs])
    vol = np.concatenate([[0.0], np.cumsum((areas[1:] + areas[:-1]) / 2 * np.diff(xs))])
    alvo = massa_g * G / densidade
    if alvo > vol[-1]:
        raise ValueError(f"lastro {massa_g:.1f} g não cabe na ogiva (máx {vol[-1]*densidade/G:.1f} g)")
    prof = float(np.interp(alvo, vol, xs))
    edges = np.linspace(0.0, prof, n_discos + 1)
    for i in range(n_discos):
        a, bb = edges[i], edges[i + 1]
        mid = 0.5 * (a + bb)
        r = nose_inner_radius_at(c, nose, mid)
        v = float(np.interp(bb, xs, vol) - np.interp(a, xs, vol))
        _mass(c, nose, f"{nome} {i+1}/{n_discos}", v * densidade / G, (bb - a) / MM,
              max(r, 1e-4) / MM, "TOP", a / MM)
    return prof / MM


def _fins(c: Ctx, parent, p: dict, material: str, finish):
    f = c.TrapezoidFinSet()
    f.setName("Aletas")
    f.setFinCount(int(p["fin_n"]))
    f.setRootChord(p["fin_root"] * MM)
    f.setTipChord(p["fin_tip"] * MM)
    f.setHeight(p["fin_span"] * MM)
    f.setSweep(p["fin_sweep"] * MM)
    f.setThickness(p["fin_t"] * MM)
    f.setCrossSection(c.CrossSection.ROUNDED)
    f.setMaterial(c.bulk(material))
    f.setFinish(finish)
    f.setFilletRadius(p.get("fin_fillet", 2.0) * MM)
    f.setFilletMaterial(c.bulk(material))
    parent.addChild(f)
    f.setAxialMethod(c.AxialMethod.BOTTOM)
    f.setAxialOffset(-p.get("fin_offset", 0.0) * MM)
    return f


def _lug(c: Ctx, parent, nome: str, comp_mm: float, p: dict, ang_rad: float,
         metodo: str, offset_mm: float, material: str, finish):
    lug = c.LaunchLug()
    lug.setName(nome)
    lug.setOuterRadius((p["lug_id"] / 2 + p["lug_wall"]) * MM)
    lug.setThickness(p["lug_wall"] * MM)
    lug.setLength(comp_mm * MM)
    lug.setMaterial(c.bulk(material))
    lug.setFinish(finish)
    parent.addChild(lug)
    lug.setAngleOffset(ang_rad)
    lug.setAxialMethod(getattr(c.AxialMethod, metodo))
    lug.setAxialOffset(offset_mm * MM)
    return lug


def _motor_mount(c: Ctx, fincan, p: dict, material: str):
    """Luva do motor + anel de empuxo, dentro da lata de aletas.

    O empuxo passa pela BORDA DIANTEIRA DO TUBO de PVC, que encosta no anel.
    O cap (tubeira) fica FORA do foguete, com folga, porque ele não é colado e
    precisa poder saltar se a pressão subir (vídeo 210). Nunca apoiar no cap."""
    id_luva = p.get("mount_id", 20.5)
    parede = p.get("mount_wall", 0.8)
    comp_luva = MOTOR_BARE - FOLGA_CAP                      # 82 mm
    mt = c.InnerTube()
    mt.setName("Luva do motor")
    mt.setOuterRadius((id_luva / 2 + parede) * MM)
    mt.setThickness(parede * MM)
    mt.setLength(comp_luva * MM)
    mt.setMaterial(c.bulk(material))
    fincan.addChild(mt)
    mt.setAxialMethod(c.AxialMethod.BOTTOM)
    mt.setAxialOffset(0.0)
    mt.setMotorMount(True)
    mt.setMotorOverhang((MOTOR_LEN - comp_luva) * MM)       # motor passa 21 mm da traseira

    anel = c.CenteringRing()
    anel.setName("Anel de empuxo (encosta na borda do tubo PVC)")
    anel.setOuterRadiusAutomatic(False)
    anel.setInnerRadiusAutomatic(False)
    anel.setOuterRadius((p["D"] / 2 - p["wall"]) * MM)
    anel.setInnerRadius(p.get("thrust_ring_id", 12.0) / 2 * MM)
    anel.setLength(p.get("thrust_ring_t", 3.0) * MM)
    anel.setMaterial(c.bulk(material))
    fincan.addChild(anel)
    anel.setAxialMethod(c.AxialMethod.BOTTOM)
    anel.setAxialOffset(-comp_luva * MM)

    # nervuras/raízes internas das aletas entre a luva e a casca (impressas juntas)
    _mass(c, fincan, "Nervuras internas + raizes", p.get("ribs_g", 1.2), comp_luva,
          p["D"] / 2 - 1.0, "BOTTOM", 0.0)
    # cap do motor: fica atrás da lata, centrado a (folga + cap/2) da traseira
    # BOTTOM + offset positivo = fundo do componente atrás do fundo da lata
    _mass(c, fincan, "Cap do motor (tubeira, ~5 g)", p.get("cap_g", CAP_MASS), CAP_LEN,
          CAP_OD / 2, "BOTTOM", FOLGA_CAP + CAP_LEN)
    return mt


def _sobrescrever(comp, massa_g: float, cg_mm: float | None = None) -> None:
    comp.setMassOverridden(True)
    comp.setOverrideMass(max(massa_g, 0.0) * G)
    if cg_mm is not None:
        comp.setCGOverridden(True)
        comp.setOverrideCGX(cg_mm * MM)


def aplicar_massas_cad(doc, mc: dict) -> None:
    """Troca as massas calculadas pelo OpenRocket pelas do CAD (massa e CG de cada
    peça impressa, vindos de cad_foguetes.py -> massas_cad.json). As peças que
    fisicamente fazem parte da lata impressa (luva, anel, nervuras, ombro) viram 0."""
    c = Ctx.get()
    comps = {str(x.getName()): x for x in c.b.iter_components(doc)}

    def achar(prefixo):
        for nome, comp in comps.items():
            if nome.startswith(prefixo):
                return comp
        return None

    if "ogiva" in mc:
        _sobrescrever(achar("Ogiva"), mc["ogiva"]["massa_g"], mc["ogiva"]["cg_mm"])
    if "tubo_corpo" in mc and achar("Tubo do corpo") is not None:
        _sobrescrever(achar("Tubo do corpo"), mc["tubo_corpo"]["massa_g"], mc["tubo_corpo"]["cg_mm"])
        for nome in ("Guia dianteira", "Ombro de encaixe"):
            if achar(nome) is not None:
                _sobrescrever(achar(nome), 0.0)
    _sobrescrever(achar("Lata de aletas"), mc["lata_estrutura"]["massa_g"], mc["lata_estrutura"]["cg_mm"])
    _sobrescrever(achar("Aletas"), mc["aletas"]["massa_g"], mc["aletas"]["cg_mm"])
    if "tubo_corpo" in mc:
        _sobrescrever(achar("Guia traseira"), mc["guia_traseira"]["massa_g"], mc["guia_traseira"]["cg_mm"])
    else:
        # sem tubo do corpo: as duas guias saem na lata; a massa das duas vai na traseira
        # (o CG informado já é o das duas juntas, medido a partir da frente da guia traseira)
        _sobrescrever(achar("Guia traseira"), mc["guia_traseira"]["massa_g"], mc["guia_traseira"]["cg_mm"])
        if achar("Guia dianteira") is not None:
            _sobrescrever(achar("Guia dianteira"), 0.0)
    for nome in ("Luva do motor", "Anel de empuxo", "Nervuras internas"):
        if achar(nome) is not None:
            _sobrescrever(achar(nome), 0.0)
    if "berco" in mc and achar("Berco impresso") is not None:
        _sobrescrever(achar("Berco impresso"), mc["berco"]["massa_g"])
    if "pistao" in mc and achar("Mola + pistao") is not None:
        # pistão impresso + mola comprada (~2 g)
        _sobrescrever(achar("Mola + pistao"), mc["pistao"]["massa_g"] + 2.0)


def definir_motor(doc, meta: dict, motor: str) -> Any:
    """Coloca o motor na luva numa configuração de voo própria e a SELECIONA
    (a estabilidade estática e a simulação passam a enxergar o motor)."""
    c = Ctx.get()
    rocket = doc.getRocket()
    mount = c.b.find_component(doc, meta["mount"])
    caminho = motor if motor.endswith(".eng") else str(MOTOR_DIR / f"{motor}.eng")
    # uma configuração de voo POR MOTOR: simulações salvas no mesmo .ork não se
    # desatualizam quando outra simulação troca de motor
    fcids = meta.setdefault("fcids", {})
    fcid = fcids.get(caminho)
    if fcid is None:
        fcid = J("info.openrocket.core.rocketcomponent.FlightConfigurationId")()
        rocket.createFlightConfiguration(fcid)
        mc = J("info.openrocket.core.motor.MotorConfiguration")(mount, fcid)
        mc.setMotor(c.b.load_motor_file(caminho))
        mount.setMotorConfig(mc, fcid)
        fcids[caminho] = fcid
    rocket.setSelectedConfiguration(fcid)
    meta["fcid"] = fcid
    meta["motor_atual"] = caminho
    return fcid


def _novo_doc(c: Ctx, nome: str):
    rocket = c.Rocket()
    rocket.setName(nome)
    stage = c.AxialStage()
    stage.setName("Estagio unico")
    rocket.addChild(stage)
    doc = c.DocFactory.createDocumentFromRocket(rocket)
    return doc, rocket, stage


# ----------------------------------------------------------------------------
# FOGUETE 1 — OBAFOG Modelo 5 (alcance oblíquo, sem recuperação)
# ----------------------------------------------------------------------------
F1_PADRAO: dict[str, Any] = {
    "D": 26.0, "wall": 0.8, "material": "PLA", "finish": "NORMAL",
    "nose_shape": "HAACK", "nose_param": 0.0, "nose_len": 110.0, "nose_t": 0.8,
    "nose_shoulder": 15.0,
    "body_len": 150.0,
    "fincan_len": 100.0,
    "fin_n": 3, "fin_root": 70.0, "fin_tip": 30.0, "fin_span": 35.0, "fin_sweep": 40.0,
    "fin_t": 2.0, "fin_offset": 0.0, "fin_fillet": 2.0,
    "ballast_g": 0.0,
    "lug_id": 7.5, "lug_wall": 1.0, "lug_front_len": 15.0, "lug_rear_len": 20.0,
    "misc_g": 3.0,          # tinta + cola + fita no motor
}


def build_f1(p_in: dict | None = None, nome: str = "Foguete 1 - OBAFOG Modelo 5"):
    c = Ctx.get()
    p = {**F1_PADRAO, **(p_in or {})}
    doc, rocket, stage = _novo_doc(c, nome)
    fin = getattr(c.Finish, p["finish"])
    R = p["D"] / 2 * MM

    nose = c.NoseCone()
    nose.setName("Ogiva")
    nose.setShapeType(getattr(c.Shape, p["nose_shape"]))
    if p["nose_shape"] in ("HAACK", "POWER", "PARABOLIC"):
        nose.setShapeParameter(float(p["nose_param"]))
    nose.setLength(p["nose_len"] * MM)
    nose.setBaseRadius(R)
    nose.setThickness(p["nose_t"] * MM)
    nose.setAftShoulderLength(p["nose_shoulder"] * MM)
    nose.setAftShoulderRadius(R - p["wall"] * MM - 0.15 * MM)
    nose.setAftShoulderThickness(p["nose_t"] * MM)
    nose.setMaterial(c.bulk(p["material"]))
    nose.setFinish(fin)
    stage.addChild(nose)
    prof = lastro_na_ponta(c, nose, p["ballast_g"])

    corpo = None
    if p["body_len"] > 1.0:
        corpo = c.BodyTube()
        corpo.setName("Tubo do corpo")
        corpo.setOuterRadius(R)
        corpo.setThickness(p["wall"] * MM)
        corpo.setLength(p["body_len"] * MM)
        corpo.setMaterial(c.bulk(p["material"]))
        corpo.setFinish(fin)
        stage.addChild(corpo)

    lata = c.BodyTube()
    lata.setName("Lata de aletas")
    lata.setOuterRadius(R)
    lata.setThickness(p["wall"] * MM)
    lata.setLength(p["fincan_len"] * MM)
    lata.setMaterial(c.bulk(p["material"]))
    lata.setFinish(fin)
    stage.addChild(lata)
    mount = _motor_mount(c, lata, p, p["material"])
    _fins(c, lata, p, p["material"], fin)

    # luva de encaixe entre corpo e lata (impressa como ombro da lata)
    if corpo is not None:
        cp = c.TubeCoupler()
        cp.setName("Ombro de encaixe corpo-lata")
        cp.setOuterRadius(R - p["wall"] * MM - 0.15 * MM)
        cp.setThickness(0.8 * MM)
        cp.setLength(15 * MM)
        cp.setMaterial(c.bulk(p["material"]))
        corpo.addChild(cp)
        cp.setAxialMethod(c.AxialMethod.BOTTOM)
        cp.setAxialOffset(0.0)

    # guias da vara (haste de aço 6 mm da Jornada): uma na lata, outra na frente
    n = int(p["fin_n"])
    ang = math.pi / n                      # a meio caminho entre duas aletas
    _lug(c, lata, "Guia traseira", p["lug_rear_len"], p, ang, "BOTTOM", 0.0, p["material"], fin)
    frente = corpo if corpo is not None else lata
    _lug(c, frente, "Guia dianteira", p["lug_front_len"], p, ang, "TOP", 5.0,
         p["material"], fin)

    _mass(c, frente, "Tinta + cola + fita do motor", p["misc_g"],
          (p["body_len"] if corpo is not None else p["fincan_len"]) * 0.8, p["D"] / 2 - 1,
          "MIDDLE", 0.0)
    if p.get("massas_cad"):
        aplicar_massas_cad(doc, p["massas_cad"])
    meta = {"lastro_prof_mm": prof, "mount": "Luva do motor", "params": p}
    return doc, meta


# ----------------------------------------------------------------------------
# FOGUETE 2 — livre: vertical, eletrônica na ogiva, paraquedas por mola + servo
# ----------------------------------------------------------------------------
F2_PADRAO: dict[str, Any] = {
    "D": 32.0, "wall": 0.8, "material": "PLA", "finish": "NORMAL",
    "nose_shape": "OGIVE", "nose_param": 1.0, "nose_len": 110.0, "nose_t": 0.8,
    "nose_shoulder": 55.0,            # a baia de eletrônica mora no ombro da ogiva
    "body_len": 190.0,                # baia do paraquedas + mola
    "fincan_len": 100.0,
    "fin_n": 3, "fin_root": 75.0, "fin_tip": 30.0, "fin_span": 40.0, "fin_sweep": 45.0,
    "fin_t": 2.0, "fin_offset": 0.0, "fin_fillet": 2.0,
    "ballast_g": 0.0,
    "lug_id": 7.5, "lug_wall": 1.0, "lug_front_len": 15.0, "lug_rear_len": 20.0,
    "misc_g": 3.0,
    # eletrônica (g) — ver foguete2_livre/eletronica/BOM.md
    "av_mcu_g": 2.0,       # ESP32-C3 SuperMini
    "av_baro_g": 1.0,      # BMP280 (ou BMP390)
    "av_bat_g": 5.5,       # LiPo 1S ~250 mAh
    "av_servo_g": 3.7,     # micro servo 3,7 g
    "av_buzzer_g": 1.5,
    "av_fios_g": 3.0,
    "av_sled_g": 4.0,      # berço impresso
    # recuperação
    "chute_d": 400.0,      # mm
    "chute_cd": 0.8,
    "chute_lines": 6, "chute_line_len": 400.0,
    "shock_len": 1200.0,   # mm de cordão
    "spring_g": 3.0,       # mola + pistão
    "deploy_delay": 1.0,   # s depois do apogeu (filtro + servo + mola)
}


def build_f2(p_in: dict | None = None, nome: str = "Foguete 2 - livre (eletronica + paraquedas)"):
    c = Ctx.get()
    p = {**F2_PADRAO, **(p_in or {})}
    doc, rocket, stage = _novo_doc(c, nome)
    fin = getattr(c.Finish, p["finish"])
    R = p["D"] / 2 * MM

    nose = c.NoseCone()
    nose.setName("Ogiva (com baia de eletronica no ombro)")
    nose.setShapeType(getattr(c.Shape, p["nose_shape"]))
    if p["nose_shape"] in ("HAACK", "POWER", "PARABOLIC", "OGIVE"):
        nose.setShapeParameter(float(p["nose_param"]))
    nose.setLength(p["nose_len"] * MM)
    nose.setBaseRadius(R)
    nose.setThickness(p["nose_t"] * MM)
    nose.setAftShoulderLength(p["nose_shoulder"] * MM)
    nose.setAftShoulderRadius(R - p["wall"] * MM - 0.2 * MM)
    nose.setAftShoulderThickness(1.0 * MM)
    nose.setAftShoulderCapped(True)             # tampa do ombro = ponto do cordão
    nose.setMaterial(c.bulk(p["material"]))
    nose.setFinish(fin)
    stage.addChild(nose)
    prof = lastro_na_ponta(c, nose, p["ballast_g"])

    # eletrônica: dentro do ombro (que se estende para trás da base da ogiva).
    # posições relativas à PONTA (TOP) da ogiva; o ombro começa em nose_len.
    L = p["nose_len"]; S = p["nose_shoulder"]
    r_in = p["D"] / 2 - 2.0
    av = [("Bateria LiPo 1S", p["av_bat_g"], L - 5, 30, "BATTERY"),
          ("ESP32-C3 SuperMini", p["av_mcu_g"], L + 5, 23, "FLIGHTCOMPUTER"),
          ("Barometro BMP280", p["av_baro_g"], L + 20, 15, "ALTIMETER"),
          ("Buzzer", p["av_buzzer_g"], L - 15, 12, "TRACKER"),
          ("Micro servo (trava)", p["av_servo_g"], L + S - 22, 20, "RECOVERYHARDWARE"),
          ("Fios e conectores", p["av_fios_g"], L + 10, S, "MASSCOMPONENT"),
          ("Berco impresso", p["av_sled_g"], L - 10, S + 10, "MASSCOMPONENT")]
    for nome_c, m, x, comp, tipo in av:
        _mass(c, nose, nome_c, m, comp, r_in * 0.6, "TOP", x - comp / 2, tipo)

    corpo = c.BodyTube()
    corpo.setName("Tubo do corpo (baia do paraquedas)")
    corpo.setOuterRadius(R)
    corpo.setThickness(p["wall"] * MM)
    corpo.setLength(p["body_len"] * MM)
    corpo.setMaterial(c.bulk(p["material"]))
    corpo.setFinish(fin)
    stage.addChild(corpo)

    cp = c.TubeCoupler()
    cp.setName("Ombro de encaixe corpo-lata")
    cp.setOuterRadius(R - p["wall"] * MM - 0.15 * MM)
    cp.setThickness(0.8 * MM)
    cp.setLength(15 * MM)
    cp.setMaterial(c.bulk(p["material"]))
    corpo.addChild(cp)
    cp.setAxialMethod(c.AxialMethod.BOTTOM)
    cp.setAxialOffset(0.0)

    # paraquedas logo abaixo do ombro da ogiva; mola/pistão no fundo da baia
    ch = c.Parachute()
    ch.setName("Paraquedas")
    ch.setDiameter(p["chute_d"] * MM)
    ch.setCDAutomatic(False)
    ch.setCD(p["chute_cd"])
    ch.setMaterial(c.surface("PE_35um"))
    ch.setLineCount(int(p["chute_lines"]))
    ch.setLineLength(p["chute_line_len"] * MM)
    ch.setLineMaterial(c.line("linha_nylon"))
    ch.setLength(45 * MM)
    ch.setRadiusAutomatic(True)
    corpo.addChild(ch)
    ch.setAxialMethod(c.AxialMethod.TOP)
    ch.setAxialOffset((S + 5) * MM)
    dep = ch.getDeploymentConfigurations().getDefault()
    dep.setDeployEvent(c.DeployEvent.APOGEE)
    dep.setDeployDelay(float(p["deploy_delay"]))

    sc = c.ShockCord()
    sc.setName("Cordao de choque")
    sc.setCordLength(p["shock_len"] * MM)
    sc.setMaterial(c.line("elastico_3mm"))
    sc.setLength(25 * MM)
    sc.setRadiusAutomatic(True)
    corpo.addChild(sc)
    sc.setAxialMethod(c.AxialMethod.TOP)
    sc.setAxialOffset((S + 50) * MM)

    _mass(c, corpo, "Mola + pistao", p["spring_g"], 30, p["D"] / 2 - 1.5, "TOP", S + 75)

    lata = c.BodyTube()
    lata.setName("Lata de aletas")
    lata.setOuterRadius(R)
    lata.setThickness(p["wall"] * MM)
    lata.setLength(p["fincan_len"] * MM)
    lata.setMaterial(c.bulk(p["material"]))
    lata.setFinish(fin)
    stage.addChild(lata)
    # motor tem 20 mm; neste foguete de 32 mm a luva precisa de parede grossa
    # (casca + nervuras): o anel de empuxo continua na borda do tubo PVC.
    _motor_mount(c, lata, {**p, "ribs_g": p.get("ribs_g", 2.5)}, p["material"])
    _fins(c, lata, p, p["material"], fin)

    n = int(p["fin_n"])
    ang = math.pi / n
    _lug(c, lata, "Guia traseira", p["lug_rear_len"], p, ang, "BOTTOM", 0.0, p["material"], fin)
    _lug(c, corpo, "Guia dianteira", p["lug_front_len"], p, ang, "TOP", 5.0,
         p["material"], fin)
    _mass(c, corpo, "Tinta + cola + fita do motor", p["misc_g"], p["body_len"] * 0.8,
          p["D"] / 2 - 1, "MIDDLE", 0.0)
    if p.get("massas_cad"):
        aplicar_massas_cad(doc, p["massas_cad"])
    meta = {"lastro_prof_mm": prof, "mount": "Luva do motor", "params": p}
    return doc, meta


# ----------------------------------------------------------------------------
# Garrafa PET 500 mL "típica da OBA" (só para calibrar o impulso com os ~100 m)
# ----------------------------------------------------------------------------
PET_PADRAO = {"massa_extra_g": 20.0, "n_aletas": 4, "aleta_raiz": 80.0, "aleta_ponta": 35.0,
              "aleta_alt": 70.0, "aleta_t": 1.0, "aleta_recuo": 20.0, "cilindro": 150.0}


def build_pet_oba(p_in: dict | None = None):
    """Garrafa lisa de 500 mL (Ø65, ~20 g) com coifa de outra garrafa, 4 aletas de
    chapa plástica 1 mm, motor encaixado no gargalo e preso com fita (vídeos 216/215)."""
    c = Ctx.get()
    p = {**PET_PADRAO, **(p_in or {})}
    doc, rocket, stage = _novo_doc(c, "Garrafa PET 500 mL tipica OBA (calibracao)")
    fin = c.Finish.NORMAL
    R = 32.5 * MM
    nose = c.NoseCone()
    nose.setName("Coifa (topo de outra garrafa)")
    nose.setShapeType(c.Shape.OGIVE)
    nose.setLength(90 * MM)
    nose.setBaseRadius(R)
    nose.setThickness(0.4 * MM)
    nose.setMaterial(c.bulk("PET_garrafa"))
    nose.setFinish(fin)
    stage.addChild(nose)
    corpo = c.BodyTube()
    corpo.setName("Garrafa 500 mL (cilindro)")
    corpo.setOuterRadius(R)
    corpo.setThickness(0.35 * MM)
    corpo.setLength(p["cilindro"] * MM)       # 150 = 1 garrafa; ~290 = 2 garrafas emendadas
    corpo.setMaterial(c.bulk("PET_garrafa"))
    corpo.setFinish(fin)
    stage.addChild(corpo)
    ombro = c.Transition()
    ombro.setName("Ombro e gargalo")
    ombro.setShapeType(c.Shape.OGIVE)
    ombro.setForeRadius(R)
    ombro.setAftRadius(12.5 * MM)
    ombro.setLength(55 * MM)
    ombro.setThickness(0.6 * MM)
    ombro.setMaterial(c.bulk("PET_garrafa"))
    ombro.setFinish(fin)
    stage.addChild(ombro)
    gargalo = c.BodyTube()
    gargalo.setName("Gargalo (motor dentro)")
    gargalo.setOuterRadius(12.5 * MM)
    gargalo.setThickness(1.5 * MM)
    gargalo.setLength(20 * MM)
    gargalo.setMaterial(c.bulk("PET_garrafa"))
    stage.addChild(gargalo)
    mt = c.InnerTube()
    mt.setName("Luva do motor")
    mt.setOuterRadius(10.9 * MM)
    mt.setThickness(0.9 * MM)
    mt.setLength(20 * MM)
    mt.setMaterial(c.bulk("PET_garrafa"))
    gargalo.addChild(mt)
    mt.setAxialMethod(c.AxialMethod.BOTTOM)
    mt.setMotorMount(True)
    mt.setMotorOverhang(8 * MM)
    _mass(c, gargalo, "Cap do motor", CAP_MASS, CAP_LEN, CAP_OD / 2, "BOTTOM",
          8 + CAP_LEN / 2)
    # aleta de formato livre (a trapezoidal não pode ser filha de transição no OR 24.12);
    # a raiz acompanha a inclinação do ombro, como no bit07
    f = J("info.openrocket.core.rocketcomponent.FreeformFinSet")()
    f.setName("Aletas")
    f.setFinCount(int(p["n_aletas"]))
    Coordinate = J("info.openrocket.core.util.Coordinate")
    raiz, ponta, alt = p["aleta_raiz"] * MM, p["aleta_ponta"] * MM, p["aleta_alt"] * MM
    incl = -(32.5 - 12.5) / 55.0            # dr/dx do ombro
    pts = [Coordinate(0.0, 0.0, 0.0), Coordinate(raiz - ponta, alt, 0.0),
           Coordinate(raiz, alt, 0.0), Coordinate(raiz, incl * raiz, 0.0)]
    f.setThickness(p["aleta_t"] * MM)
    f.setMaterial(c.bulk("PS_chapa"))
    # aletas PRESAS NO OMBRO (transição): o OpenRocket usa o raio local, que é o
    # que dá a elas o crédito aerodinâmico real (lição do bit07)
    ombro.addChild(f)
    f.setPoints(jpype.JArray(Coordinate)(pts))
    f.setAxialMethod(c.AxialMethod.TOP)
    f.setAxialOffset(p["aleta_recuo"] * MM)
    lug = c.LaunchLug()
    lug.setName("Tubinho guia (capa de pasta)")
    lug.setOuterRadius(4 * MM)
    lug.setThickness(0.3 * MM)
    lug.setLength(120 * MM)
    corpo.addChild(lug)
    lug.setAngleOffset(math.pi / 4)
    _mass(c, nose, "Lastro/fita/cola", p["massa_extra_g"], 30, 15, "TOP", 45)
    return doc, {"mount": "Luva do motor", "params": p}


# ----------------------------------------------------------------------------
# simulação
# ----------------------------------------------------------------------------
@dataclass
class Cenario:
    motor: str = "OBAFOG-M5_NEU_I09"      # nome do .eng em motor/eng/ (ou caminho)
    elev_deg: float = 45.0                 # graus acima do horizonte
    azim_deg: float = 0.0                  # direção do lançamento
    rod_len: float = 1.2                   # m de guia efetiva
    vento: float = 0.0                     # m/s média
    vento_de: float = 0.0                  # graus relativos: 0 = de frente (contra), 180 = de cauda
    turb: float = 0.10                     # intensidade de turbulência
    alt_local: float = 380.0               # m (Barra do Piraí ~380 m)
    temp_c: float = 28.0
    seed: int = 1
    dt: float = 0.01
    t_max: float = 60.0
    exigir_estavel: bool = True
    cal_minima_para_simular: float = 0.4

    def motor_path(self) -> str:
        m = self.motor
        if m.endswith(".eng") and Path(m).exists():
            return m
        return str(MOTOR_DIR / f"{m}.eng")


def _series(branch, c: Ctx, nome: str) -> np.ndarray:
    v = branch.get(getattr(c.FlightDataType, nome))
    if v is None:
        return np.array([])
    return np.array([float(x) for x in v], dtype=float)


def estabilidade_estatica(doc, mach: float = 0.3) -> dict:
    """CP, CG e margem (cal) no lançamento, como a janela do OpenRocket mostra."""
    c = Ctx.get()
    rocket = doc.getRocket()
    config = rocket.getSelectedConfiguration()
    conds = c.FlightConditions(config)
    conds.setMach(mach)
    conds.setAOA(0.0)
    ws = c.WarningSet()
    cp = c.Barrowman().getCP(config, conds, ws)
    mc = c.MassCalculator.calculateLaunch(config)
    cg = mc.getCM()
    ref = float(conds.getRefLength())
    xcp, xcg = float(cp.x), float(cg.x)
    mb = c.MassCalculator.calculateBurnout(config)
    xcg_b = float(mb.getCM().x)
    return {"cp_mm": xcp / MM, "cg_mm": xcg / MM, "cg_burnout_mm": xcg_b / MM,
            "ref_mm": ref / MM, "cal": (xcp - xcg) / ref, "cal_burnout": (xcp - xcg_b) / ref,
            "massa_g": float(mc.getMass()) / G, "massa_seca_g": float(mb.getMass()) / G,
            "cna": float(cp.weight)}


def simular(doc, meta: dict, cen: Cenario, keep_series: bool = False, limpar: bool = True,
            nome: str | None = None) -> dict:
    c = Ctx.get()
    b = c.b
    if limpar:
        # getSimulations() devolve uma CÓPIA: iterar sobre a foto, nunca "while size>0"
        for antiga in list(doc.getSimulations()):
            doc.removeSimulation(antiga)
    fcid = definir_motor(doc, meta, cen.motor_path())
    sim = c.Simulation(doc, doc.getRocket())
    sim.setFlightConfigurationId(fcid)
    sim.setName(nome or f"{cen.motor} {cen.elev_deg:.0f}graus vento {cen.vento:.0f}")
    doc.addSimulation(sim)
    o = sim.getOptions()
    o.setLaunchIntoWind(False)
    o.setLaunchRodLength(cen.rod_len)
    o.setLaunchRodAngle(math.radians(90.0 - cen.elev_deg))
    o.setLaunchRodDirection(math.radians(cen.azim_deg))
    o.setWindSpeedAverage(cen.vento)
    o.setWindTurbulenceIntensity(cen.turb)
    # direção do vento no OpenRocket = de onde sopra (verificado em teste_convencoes.py)
    o.setWindDirection(math.radians((cen.azim_deg + cen.vento_de) % 360.0))
    o.setLaunchAltitude(cen.alt_local)
    o.setISAAtmosphere(False)
    o.setLaunchTemperature(cen.temp_c + 273.15)
    o.setLaunchPressure(101325.0 * (1 - 2.25577e-5 * cen.alt_local) ** 5.25588)
    o.setTimeStep(cen.dt)
    o.setMaxSimulationTime(cen.t_max)
    o.setRandomSeed(int(cen.seed))
    if cen.exigir_estavel:
        est = estabilidade_estatica(doc)
        if est["cal"] < cen.cal_minima_para_simular:
            # foguete que tomba deixa o integrador lentíssimo e o resultado não serve
            return {"erro": "instavel", "cal": est["cal"], "perp": 0.0, "total": 0.0,
                    "apogeu": 0.0, "massa_g": est["massa_g"]}
    b.run_simulation(sim)
    data = sim.getSimulatedData()
    br = data.getBranch(0)
    t = _series(br, c, "TYPE_TIME")
    x = _series(br, c, "TYPE_POSITION_X")
    y = _series(br, c, "TYPE_POSITION_Y")
    alt = _series(br, c, "TYPE_ALTITUDE")
    vel = _series(br, c, "TYPE_VELOCITY_TOTAL")
    stab = _series(br, c, "TYPE_STABILITY")
    aoa = _series(br, c, "TYPE_AOA")
    mach = _series(br, c, "TYPE_MACH_NUMBER")
    az = math.radians(cen.azim_deg)
    ux, uy = math.sin(az), math.cos(az)          # x = leste, y = norte
    xf, yf = float(x[-1]), float(y[-1])
    perp = xf * ux + yf * uy
    lateral = -xf * uy + yf * ux

    def ev(nome):
        e = br.getFirstEvent(getattr(c.EventType, nome))
        return float(e.getTime()) if e is not None else None

    t_apo = ev("APOGEE") or float(t[np.nanargmax(alt)])
    t_rod = ev("LAUNCHROD")
    # margem só com velocidade suficiente: perto do apogeu de um voo vertical a
    # velocidade vai a zero e o número deixa de ter sentido físico
    ok = (np.isfinite(stab) & (t <= t_apo) & (vel > 12.0)) if stab.size == t.size else np.zeros(t.size, bool)
    if t_rod is not None:
        ok &= t >= t_rod
    sub = ((t <= t_apo) & np.isfinite(aoa) & (vel > 10)) if aoa.size == t.size else np.zeros(t.size, bool)
    out = {
        "perp": perp, "total": math.hypot(xf, yf), "lateral": lateral,
        "apogeu": float(data.getMaxAltitude()),
        "v_max": float(data.getMaxVelocity()),
        "mach_max": float(np.nanmax(mach)) if mach.size else None,
        "v_vara": float(data.getLaunchRodVelocity()),
        "t_apogeu": t_apo, "t_voo": float(data.getFlightTime()),
        "t_queima": ev("BURNOUT"),
        "v_impacto": float(data.getGroundHitVelocity()),
        "v_abertura": float(data.getDeploymentVelocity()) if ev("RECOVERY_DEVICE_DEPLOYMENT") else None,
        "t_abertura": ev("RECOVERY_DEVICE_DEPLOYMENT"),
        "stab_min": float(np.nanmin(stab[ok])) if ok.any() else None,
        "stab_max": float(np.nanmax(stab[ok])) if ok.any() else None,
        "aoa_max": float(np.degrees(np.nanmax(np.abs(aoa[sub])))) if sub.any() else None,
        "massa_g": float(_series(br, c, "TYPE_MASS")[0]) / G,
        "avisos": [str(w) for w in sim.getSimulatedWarnings()] if sim.getSimulatedWarnings() else [],
    }
    # velocidade de descida (paraquedas): média nos últimos 30 % da queda
    if out["t_abertura"] is not None:
        vz = _series(br, c, "TYPE_VELOCITY_Z")
        dsc = t > (out["t_abertura"] + 1.5)
        if dsc.any():
            out["v_descida"] = float(-np.nanmean(vz[dsc]))
    if keep_series:
        out["series"] = {"t": t, "x": x, "y": y, "alt": alt, "vel": vel, "stab": stab,
                         "aoa": aoa, "mach": mach}
    return out


def salvar_com_simulacoes(doc, meta: dict, cenarios: list[tuple[str, Cenario]],
                          caminho: Path | str, motor_selecionado: str | None = None) -> list[dict]:
    """Roda e GUARDA várias simulações nomeadas no .ork (abre no OpenRocket já com
    os resultados). Cada motor tem a sua configuração de voo."""
    c = Ctx.get()
    for antiga in list(doc.getSimulations()):
        doc.removeSimulation(antiga)
    res = []
    for nome, cen in cenarios:
        r = simular(doc, meta, cen, limpar=False, nome=nome)
        r["nome"] = nome
        res.append(r)
    if motor_selecionado:
        definir_motor(doc, meta, motor_selecionado)
    c.b.save_document(doc, str(caminho))
    return res
