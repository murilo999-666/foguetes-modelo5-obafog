# Foguete 2 — montagem

Versões (mesmo projeto, dois diâmetros; escolha uma):

| Versão | Para quem | Arquivos |
|---|---|---|
| **F2_29mm_v1** (recomendada) | primeira eletrônica: mais espaço na baia, LiPo comum de 250 mAh, paraquedas dobra sem aperto | `F2_29mm_v1.ork`, `stl/F2_29mm_v1/` |
| F2_26mm_v1 | desempenho: ~20% mais apogeu (136 contra 114 m no motor nominal), usa a mesma lata/luva do Foguete 1, mas a baia é apertada (LiPo estreita, ~12 x 30 mm) | `F2_26mm_v1.ork`, `stl/F2_26mm_v1/` |

Números de cada versão (massa, margem, apogeu por motor, tabela de lastro, deriva):
`F2_<versão>_resumo.json`.

## 1. Imprimir

Antes de tudo, os **gabaritos** de `../foguete1_obafog/stl/<versão F1>/gabaritos/`:
anéis de luva (o cano entra com 1 volta de fita crepe sem forçar) e guias (deslizam soltas na
haste). Se o gabarito de 20,7 mm é o que serve, ajuste `LUVA_ID` em `scripts/cad_foguetes.py`
e gere de novo.

| Peça | Orientação | Material | Ajustes do fatiador |
|---|---|---|---|
| `F2_ogiva_baia_v1.stl` | em pé, ombro na mesa | PLA ou PETG | 2 perímetros (0,8 mm), 0% preenchimento, sem topo/fundo, camada 0,2 |
| `F2_tubo_corpo_v1.stl` | em pé (guia e janela para cima) | PLA ou PETG | 2 perímetros, 0% preenchimento, sem topo/fundo |
| `F2_lata_aletas_v1.stl` | em pé, traseira na mesa | **PETG de preferência** (calor do motor) | 3 perímetros, 30% preenchimento, brim de 3 mm |
| `F2_berco_eletronica_v1.stl` | em pé, antepara na mesa | PLA | 3 perímetros, 30% |
| `F2_pistao_v1.stl` | disco na mesa | PLA | 2 perímetros, 100% no disco |

Todas as peças foram modeladas para imprimir **sem suporte** (tetos cônicos, cunha de 45°
embaixo da guia dianteira). Pese cada peça: a massa do CAD está no resumo; diferença maior que
10% muda a margem — corrija no `.ork` (Componente → Sobrescrever massa).

## 2. Paraquedas

1. Imprima `moldes/molde_gomo_paraquedas_390mm.pdf` (29 mm) ou `_370mm.pdf` (26 mm) em tamanho real (confira a régua de 100 mm).
2. Corte o octógono num saco de lixo grosso (~35 µm) usando o molde 8 vezes em volta do centro.
3. Reforce os 8 cantos com um quadradinho de fita adesiva dos dois lados.
4. 8 linhas de nylon do comprimento indicado no molde; cada uma presa num canto com fita
   dobrada por cima (ou nó passando por um furo feito com agulha quente no reforço).
5. Junte as 8 pontas num nó e prenda num **destorcedor de pesca** (opcional, evita enrolar) e
   no cordão de choque, a ~1/3 do comprimento a partir da ogiva.
6. Dobre em "Z" (metade, metade, enrole as linhas em volta). Talco ajuda a não grudar.

## 3. Cordão de choque, mola e pistão

- Cordão elástico de 3 mm, **1,2 m**: uma ponta no **olhal da lata** (em cima da antepara
  cônica), passa pelo furo do pistão, outra ponta no **olhal da antepara do berço**.
- Mola de compressão por cima da antepara da lata, pistão por cima da mola, paraquedas
  dobrado por cima do pistão. A mola deve empurrar a ogiva para fora com folga quando a trava
  solta (teste do item 6). Força ~5–10 N comprimida é suficiente para uma ogiva de ~40 g.

## 4. Eletrônica no berço

Veja `eletronica/ELETRONICA.md` (ligação, orçamento de corrente, firmware).

- Servo no bolso do berço, com o braço saindo pela **fenda do ombro** da ogiva.
- ESP32-C3 nos trilhos, USB virado para trás (acesso tirando o berço).
- BMP280 **coberto com um pedaço de espuma escura** (luz e rajada atrapalham o barômetro).
- Bateria presa com fita dupla-face; **fios soldados**, sem conector solto na linha da bateria
  (conector que solta na aceleração = paraquedas que não abre).
- Chave liga/desliga acessível tirando a ogiva.

## 5. Encaixe da ogiva e trava

- A **nervura** do ombro entra no **entalhe** do topo do tubo: assim a fenda do ombro fica
  alinhada com a **janela** do tubo.
- Travado, o braço do servo entra ~2 mm na janela. Ajuste `SERVO_TRAVA_US` e `SERVO_SOLTA_US`
  no firmware até o braço entrar e sair sem esforço.
- A janela também é a tomada de ar do barômetro. Não cubra com fita.

## 6. Testes no chão (antes de qualquer voo)

1. **Ejeção**: foguete montado, paraquedas dobrado, "Destravar" pela página do Wi-Fi: a ogiva
   tem de sair e puxar o paraquedas. **10 vezes seguidas sem falhar.**
2. **Barômetro**: ruído medido na página entre 0,1 e 0,4 m.
3. **Sem disparo falso**: armado, suba e desça uma escada (5–10 m): não pode abrir.
4. **Margem estática**: pendure o foguete montado, **com motor**, num barbante e ache o
   ponto de equilíbrio (CG). Compare com o CG do `.ork` (±5 mm). O CP está no `.ork`.
5. **Bateria** acima de 3,9 V.

## 7. Onde e como lançar

- Haste de 6 mm (ou maior), 1,5 m, **87° (quase vertical), levemente contra o vento** e para
  longe das pessoas.
- **Altura**: com o motor nominal (7 N·s) o apogeu fica abaixo de 150 m. Com motor mais forte
  passa disso. A norma BAR-2/2020 pede NOTAM acima de 150 m em área rural. Depois do teste
  estático, veja a **tabela de lastro** no resumo: ela diz quantos gramas de massa epóxi pôr no
  bico para ficar abaixo de 140 m, ou avisa quando nem o lastro máximo resolve.
- **Campo**: a deriva com vento de 4 m/s passa de 50 m (tabela de deriva no resumo). Campo de
  futebol vazio, sem fios e sem árvores altas.
- Público a pelo menos metade do apogeu esperado (protocolo da OBA, vídeo 215); todos com
  proteção nos olhos; adulto responsável junto.
