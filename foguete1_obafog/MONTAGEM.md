# Foguete 1 (OBAFOG) — montagem

As cotas e massas exatas da versão final estão em `F1_construtivel_v1_resumo.json`
(seção `cad` = massa e altura de cada STL; `params` = geometria; `estabilidade` = margem).

## 0. Antes de imprimir o foguete: gabaritos (15 minutos)

Pasta `stl/F1_construtivel_v1/gabaritos/`:

| Gabarito | Como testar | O que fazer com o resultado |
|---|---|---|
| `gab_luva_motor_ID20.3..20.9` | um cano de PVC 20 mm com **1 volta de fita crepe** tem de entrar sem forçar e sem folga | se o bom for outro que não o de 20,7 mm, ajuste `LUVA_ID` em `scripts/cad_foguetes.py` e gere de novo |
| `gab_guia_haste6_ID6.8..8.0` | deslizar na haste de 6 mm **solto**, sem prender em nenhum ponto | o foguete usa 7,65 mm; se prender, suba |

Meça também com paquímetro: **diâmetro do cano** (20,0 mm?) e **diâmetro do cap**
(tem de ser **menor que 26 mm**, o corpo). Se o cap tiver mais que 25,5 mm, avise: o corpo
precisa crescer.

## 1. Imprimir

| Peça | Orientação | Material | Fatiador |
|---|---|---|---|
| `F1_ogiva_v1.stl` | em pé, ombro na mesa | PLA ou PETG | 2 perímetros (0,8 mm), 0% preenchimento, sem topo/fundo, camada 0,15–0,2 |
| `F1_tubo_corpo_v1.stl` | em pé, guia para cima | PLA ou PETG | 2 perímetros, 0% preenchimento, sem topo/fundo |
| `F1_lata_aletas_v1.stl` | em pé, traseira na mesa | **PETG de preferência** | 3 perímetros, 30% preenchimento, brim 3 mm, camada 0,2 |

- Nenhuma peça precisa de suporte: teto da luva cônico (45°), anel dianteiro chanfrado,
  cunha de 45° embaixo da guia dianteira.
- A aleta sai **junto** com a lata: alinhamento garantido, e a flexão da aleta fica no plano
  da camada (a direção forte).
- **Altura de impressão**: confira no resumo (`altura_mm` da ogiva). Se a sua impressora não
  alcança, use a variante B (ogiva mais curta) indicada no `LEIA-ME.md`.
- Pese cada peça: diferença maior que 10% em relação ao CAD muda a margem.

## 2. Colar corpo e lata COM A HASTE (alinha as duas guias)

1. Lixe levemente o ombro da lata e o interior do tubo.
2. Enfie **as duas guias numa haste de 6 mm** (a mesma da Jornada serve) e encaixe o tubo no
   ombro da lata **com a haste passando pelas duas guias**.
3. Cole (cola instantânea ou epóxi) com a haste no lugar. As guias ficam colineares.

## 3. Lastro no bico (massa epóxi, nunca metal)

1. Pese a massa indicada no resumo (`params.ballast_g`), com passo de 0,5 g.
2. Misture a massa epóxi, role num cilindro fino, empurre até a **ponta** da ogiva com uma
   vareta de ~8 mm e soque. O modelo supõe a massa encostada na ponta (profundidade de
   enchimento no resumo, `lastro_prof_mm`).
3. Espere curar antes de encaixar a ogiva.

## 4. Pintura e identificação

- Spray **laranja ou rosa fluorescente** (achar no gramado; o edital zera foguete não achado).
  A tinta entra no modelo como ~3 g.
- Escreva escola, equipe e telefone **por dentro** da ogiva.

## 5. Conferência final (sem motor e com motor)

1. Monte tudo e pese **sem motor**: compare com `estabilidade.massa_seca_g − 14 g` do resumo
   (o resumo inclui o motor vazio).
2. Com um **motor de treino** (cano de 100 mm com cap e ~22 g de areia colada, mesma massa do
   motor carregado), ache o CG equilibrando o foguete num barbante. Compare com `cg_mm` do
   resumo: diferença de até ±5 mm é aceitável. CG mais para trás = menos margem → mais lastro.
3. Guias deslizam soltas na haste.

## 6. Motor no dia

- 1 volta de fita crepe **no tubo de PVC**, nunca no cap. O tubo entra na lata até **encostar
  no batente cônico** (é por ali que o empuxo passa).
- O cap fica 3 mm atrás da lata, **sem encostar em nada** e **sem cola, sem fita**: ele é a
  válvula de segurança do motor.
- Depois do voo, tire o motor logo (PVC quente amolece PLA).
