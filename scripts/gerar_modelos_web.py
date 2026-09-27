"""STL leves para o visualizador 3D da página (mesmas cotas, menos triângulos) + manifesto."""
import json, sys
from pathlib import Path
import cad_foguetes as cad

RAIZ = Path(__file__).resolve().parents[1]
cad.SEG = 56
cad.N_PERFIL = 70

def massas_impressao(pasta_stl: Path) -> dict:
    """Massa de cada peça pelo STL de impressão (a do resumo), não pela malha leve da página."""
    resumo = pasta_stl.parents[1] / f"{pasta_stl.name}_resumo.json"
    cad_lista = json.loads(resumo.read_text(encoding="utf-8")).get("cad", [])
    return {tipo: round(c["massa_g"], 1) for c in cad_lista for tipo in ("lata", "tubo", "ogiva") if tipo in c["arquivo"]}

def gerar(pasta_stl: Path, fog: str, saida: Path, tag: str) -> dict:
    p = json.loads((pasta_stl / "params_cad.json").read_text(encoding="utf-8"))
    Lfc = p.get("fincan_len", 100.0)
    pecas = []
    mi = massas_impressao(pasta_stl)
    def exp(m, nome, dz, cor, rotulo):
        arq = saida / f"{tag}_{nome}.stl"
        info = cad.exportar(m, arq, p.get("material", "PLA"))
        pecas.append({"arquivo": arq.name, "z": dz, "cor": cor, "nome": rotulo, "massa_g": mi.get(nome, info["massa_g"])})
    exp(cad.lata_aletas(p, olhal=(fog == "f2")), "lata", 0.0, "#eb6834", "Lata de aletas (luva do motor + guias)")
    topo = Lfc
    if p["body_len"] > 1:
        exp(cad.tubo_corpo(p, janela_trava=(fog == "f2")), "tubo", Lfc, "#f2a57f", "Tubo do corpo")
        topo = Lfc + p["body_len"]
    og = cad.ogiva_f2(p) if fog == "f2" else cad.ogiva(p)
    exp(og, "ogiva", topo - p["nose_shoulder"], "#2a78d6", "Ogiva")
    return {"tag": tag, "pecas": pecas,
            "motor": {"tubo": [-18.0, 82.0, 10.0], "cap": [-21.0, -3.0, 12.3]},
            "comprimento_mm": topo + p["nose_len"] + 21}

if __name__ == "__main__":
    saida = Path(sys.argv[1])
    saida.mkdir(parents=True, exist_ok=True)
    man = {}
    for pasta, fog, tag in (("foguete1_obafog/stl/F1_construtivel_v1", "f1", "F1_A"),
                            ("foguete1_obafog/stl/F1_construtivel_v1B_ogiva_curta", "f1", "F1_B"),
                            ("foguete2_livre/stl/F2_29mm_v1", "f2", "F2_29"),
                            ("foguete2_livre/stl/F2_26mm_v1", "f2", "F2_26")):
        man[tag] = gerar(RAIZ / pasta, fog, saida, tag)
    (saida / "modelos.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    for f in sorted(saida.glob("*.stl")):
        print(f.name, round(f.stat().st_size / 1024), "kB")
