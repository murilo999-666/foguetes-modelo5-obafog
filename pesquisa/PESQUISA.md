# Dossiê de pesquisa — dois foguetes com o motor sólido da OBAFOG

Tudo o que fundamenta as decisões de projeto, com a fonte de cada número. Onde não há
fonte, está escrito "estimado" e diz como medir.

## 1. O alvo: Modelo 5 e a 100ª Jornada de Foguetes

- **Modelo 5** = "tubular com propulsão sólida", ensino médio ou superior, lançamento
  **oblíquo**, vence o **maior alcance horizontal** (Regulamento 20ª OBAFOG Modelo 5, p.2–3).
- Formato e material livres, **menos metal**; impressão 3D citada explicitamente (p.2 e p.10).
- **Motor obrigatório** e intocável: o descrito nos vídeos 208 e 210–216 (p.3, p.10).
- Vara de 1,2–1,5 m que não verga; o foguete leva **duas guias** que passam pela vara (p.11).
- Estabilidade (CP−CG)/Dmax "igual ou ligeiramente maior do que 1,0" (p.9–10).
- A etapa escolar mede do ponto de lançamento até onde o foguete parou, em metros inteiros
  arredondados para cima (p.3). O prazo de 2026 era 15/05/2026 (p.5).
- **100ª Jornada de Foguetes, Turma 15** (07–10/12/2026, Barra do Piraí/RJ) é a única turma
  de 2026 com Modelo 5. As equipes **não levam motor**: ele é fabricado no evento com material
  da organização (oficina de motores/teste estático no 2º dia). A organização empresta uma
  **haste de aço de 6 mm x 1,5 m**, fincada no ângulo que a equipe escolher (edital p.15).
- Na Jornada, o alcance é a distância **perpendicular à linha de lançamento** (edital p.13).
  São 2 lançamentos, um por dia, e vale o maior. Foguete não achado até 30 min depois da
  medição fica com zero (p.13–14). Recomendam levar 2 foguetes novos (p.15).
- Análise completa rotulada (PERMITIDO/PROIBIDO/AMBÍGUO): `../regulamento/CONFORMIDADE.md`.

## 2. O motor oficial

Resumo em `../motor/MOTOR.md`. Dados firmes, tirados das legendas automáticas dos vídeos
oficiais (baixadas com `yt-dlp`):

| Dado | Valor | Onde |
|---|---|---|
| Carcaça | PVC marrom soldável 20 mm, 100 mm | regulamento p.11; vídeo 210 |
| Tubeira | cap 20 mm, furo de 7 mm, **não colado** (salta como alívio de pressão) | vídeo 210, 0:11–3:33 e 17:14–18:55 |
| Furo central | molde = parafuso de 5/16" (7,9 mm), 85 mm lisos | vídeos 210 e 216 |
| Propelente | 22 g, compactado em 2 porções de 11 g | regulamento; vídeo 216, 22:30 |
| Fechamento dianteiro | papel-alumínio compactado + cola instantânea + bicarbonato | vídeo 216, 30:00–34:15 |
| **Tempo de queima** | **~1,2 s** (1,2–1,25 s), curvas "muito parecidas" em muitos testes | live 208, 1:28–1:29 |
| Histórico | >1.200 acionamentos sem explosão | live 208, 1:56 |
| Foguetes já usados | de <50 g a 200 g | live 208, 1:55 |
| Desempenho mostrado | garrafas de 500 mL: ~100 m repetidos; >150 m em alguns voos | live 208, 1:53; vídeo 215, 16:55 |
| Fixação no foguete | fita crepe ou esparadrapo | vídeo 215, 7:31; live 208, 1:31 |
| Vara usada pela OBA | vergalhão liso 4–6 mm, 1,5 m, ~15 cm enterrado | vídeo 215, 3:28 |

**Impulso (não publicado)** — limitado por dois trabalhos:

- *Minifoguete a propelente sólido: aspectos teóricos e propostas experimentais para o
  ensino de física* (Revista Brasileira de Ensino de Física, SciELO). KNSu 65/35 **a frio**,
  KNO3 impuro, 33 g, eletroduto 3/4", 108 mm, furo de 5,6 x 89 mm, bocal de argila. Queima de
  0,70 s, foguete de 226 g, apogeu de 72,8 m, v_max 55 m/s → **v_e ≈ 380 m/s (Isp ≈ 39 s)**.
- Marchi, C. H. (GFCS/UFPR), *Propelente KNSu a frio para minifoguetes: preparo,
  carregamento, estocagem e uso* (2021). KNSu a frio **prensado a 3–10 t**, tubeiras metálicas,
  5–20 bar, 330 testes: **Isp real de 63–82 s**. Massa específica do KNSu prensado:
  1.314–1.556 kg/m³ (70–82% da teórica). O próprio texto diz: "O motor-foguete da MOBFOG/OBA
  usa KNSu a frio."
- Foltran et al. (SAB 2014, UFPR): a velocidade de queima **à pressão atmosférica** cai com
  a compactação, e densidade × velocidade de queima ≈ constante. Isso é coerente com 1,2 s de
  queima numa parede de ~4,5 mm (pressão de câmara baixa, poucos bar).
- **Checagem com os voos da OBA** (`../scripts/calibrar_com_voos_oba.py`): garrafas de 500 mL
  estáveis (1,0–1,6 cal, 130–150 g) dão no OpenRocket 114–162 m com 7 N·s e 158–211 m com
  9 N·s, contra ~100 m reais. O OpenRocket subestima o arrasto de foguete artesanal.
- **Conclusão: nominal 7 N·s (Isp 32 s), faixa 5–11,5 N·s** — motor classe C pela norma
  BAR-2/2020 (5,01–10 N·s). A forma da curva é desconhecida: três envelopes (regressivo,
  neutro, progressivo).

## 3. Física do alcance com um motor fraco

Resultados das simulações (OpenRocket 24.12, 2.800 projetos avaliados, cada um em 9 a 30
cenários de motor e vento):

1. **Área frontal manda.** Uma garrafa de 65 mm tem ~6 vezes a área frontal de um tubo de
   26 mm. Com o mesmo motor, a garrafa típica fica em 100–180 m e o foguete fino passa de 300 m.
2. **Mais leve voa mais longe** (correlação alcance x massa = −0,88 com a margem mínima
   imposta). É a mesma lição do bit07: o lastro só entra na medida exata para a estabilidade.
3. **O motor de 41 g fica na cauda**, então o foguete precisa de CP bem atrás (aletas) ou de
   CG à frente (ogiva longa e ~10 g de lastro). A busca prefere **ogiva longa + corpo curto +
   lastro pequeno**, em vez de corpo comprido.
4. **Ângulo ótimo ~45–50°** sem vento (foguete sai devagar da vara e faz curva de gravidade;
   por isso passa um pouco de 45°). Com vento, o ótimo muda: ver a tabela do guia de lançamento.
5. **Saída da vara lenta (~10–13 m/s)** é o ponto fraco: com vento, o foguete "cata-vento"
   forte. Vento de cauda de 6 m/s com o motor mais fraco pode deixar o foguete quase vertical
   e fazê-lo cair perto da base (0,95 m numa das simulações com rajada). **Não lançar com
   vento de cauda forte.**
6. **A haste de 6 mm verga.** Aço de 6 mm, 1,3 m livres, a 45°: flecha na ponta ≈
   wL⁴/(8EI) ≈ 4 cm e inclinação ≈ 2,5° a menos na ponta (w = 1,54 N/m, E = 200 GPa,
   I = 63,6 mm⁴). Meça o ângulo na metade de cima da haste, ou some ~2° na base.
7. **O OpenRocket ignora a turbulência na semente** (o resultado muda a cada rodada). A
   comparação de projetos foi feita sem turbulência; a dispersão por rajada foi medida à parte
   (Monte Carlo).

## 4. Estabilidade

- Margem estática = (CP − CG)/D, com D = maior diâmetro do corpo (norma BAR-2/2020 e
  regulamento). O cap do motor (~24,6 mm) é menor que o corpo de 26 mm, então não vira o Dmax.
- CP calculado pelo `BarrowmanCalculator` do próprio OpenRocket (não à mão: no bit07 a
  conta manual errou 0,72 cal).
- Faixa de projeto: **1,35 a 2,0 cal**, com margem para o erro de massa e CG da impressão
  (a sensibilidade está no resumo de cada foguete).

## 5. Estrutura

- **Flutter** (NACA TN 4197, forma divulgada pela Apogee), com G de peça impressa
  conservador (PLA 1,0 GPa; PETG 0,7 GPa), pressão de 380 m de altitude: todas as aletas
  aprovadas têm V_flutter ≥ 1,5 x a maior velocidade simulada (motor de 11,5 N·s regressivo).
- **O OpenRocket não vê fragilidade.** Sem restrição, a busca leva a aleta para 18 mm de raiz
  e 1,2 mm de espessura. Por isso existe a **variante construível** (raiz ≥ 28 mm, espessura
  ≥ 1,6 mm, envergadura ≤ 45 mm).
- **Pouso balístico a ~40 m/s**: a ogiva quebra com frequência. Imprima ogivas de reserva
  (~7 g, ~1 h cada).
- **Calor**: queima de 1,2 s, mas o cano de PVC esquenta depois. PLA amolece a partir de
  ~60 °C, PETG ~80 °C. A lata tem **vão de ar** entre o cano e a casca (só os anéis encostam),
  e a fita crepe no cano isola. Tire o motor logo depois de achar o foguete.
- **Cap livre**: o empuxo passa pela borda do tubo de PVC, que encosta num batente cônico.
  O cap fica 3 mm atrás da lata e nada encosta nele.

## 6. Impressão 3D

- Peças impressas **em pé** (eixo do foguete na vertical): a flexão da aleta fica no plano da
  camada, a guia sai redonda, sem suporte (tetos cônicos e cunhas de 45°).
- Paredes de 0,8 mm (2 perímetros de 0,4 mm), aletas de 1,6–2,0 mm.
- Massas calculadas do próprio STL (volume x densidade: PLA 1,24 g/cm³, PETG 1,27 g/cm³) e
  **devolvidas ao OpenRocket** como massa e CG de cada componente.
- **Gabaritos antes do foguete**: anéis de 20,3–20,9 mm para o cano e guias de 6,8–8,0 mm para
  a haste. O FDM fecha furo ~0,1–0,2 mm, e cada impressora é diferente.

## 7. Foguete 2: recuperação e eletrônica

- **Sem pólvora**: servo + mola. Detalhes, números de datasheet (ESP32-C3 23–28 mA; BMP280
  ±0,12 hPa relativo) e o teste SIL (480/480 aprovados) em
  `../foguete2_livre/eletronica/ELETRONICA.md`.
- **Paraquedas** de polietileno (saco de lixo grosso, ~35 µm), Cd ≈ 0,8, dimensionado para
  ~4,5 m/s de descida: D = √(8·m·g / (π·ρ·Cd·v²)).
- **Altura e espaço aéreo**: a norma BAR-2/2020 (Associação Brasileira de Minifoguetes)
  orienta pedir **NOTAM** ao CINDACTA se o apogeu estimado passar de **150 m em área rural**
  (300 m em área urbana). O Foguete 2 faz 130 m com 7 N·s, mas 200 m com 9 N·s. Por isso há a
  tabela de lastro para limitar o apogeu depois do teste estático.

## 8. Segurança

- Vídeo obrigatório da OBA: "Segurança em primeiro lugar" (https://youtu.be/Bp6O71fHFIg).
- Protocolo da OBA (vídeo 215): zonas verde/amarela/vermelha; público a pelo menos metade do
  apogeu esperado; fio de ignição de 20–25 m; máscara/protetor facial; supervisão de adulto.
- Sequência de testes da BAR-2/2020: **teste de resistência** (queima presa, sem instrumento)
  → **teste estático** (com célula de carga) → **voo**. Motor só voa se passou nos dois.
- **Não alterar o motor** (maior, outro cano, cap colado). O GFCS/UFPR, com prensa, tubeiras
  metálicas e anos de prática, relata "vários acidentes, sem vítimas, durante a queima de
  KNSu em motores-foguete nas fases de testes em solo". Motor maior é projeto para fazer com
  um grupo experiente (o próprio GFCS/UFPR, do Festival Baranoff).

## Fontes

- OBA/OBAFOG — Regulamento da 20ª OBAFOG, Modelo 5 (17/02/2026):
  http://www.oba.org.br/sisglob/sisglob_arquivos/2026/REGULAMENTO%20DA%2020%C2%AA%20OBAFOG%20PARA%20O%20MODELO%205%20-%202026-compactado.pdf
- OBA/OBAFOG — Regulamento da 20ª OBAFOG, Modelo 7 (placa eletrônica exclusiva da OBA):
  https://sistema.oba.org.br/sisglob/sisglob_arquivos/2026/REGULAMENTO%20DA%2020%C2%AA%20OBAFOG%20PARA%20O%20MODELO%207%20-%202026-compactado.pdf
- Edital da 100ª Jornada de Foguetes, Turma 15 (08/06/2026) — arquivo local `EDITAL-TURMA-15.pdf`.
- Vídeos oficiais da OBA: 208 https://youtu.be/K09RnU6daIM · 210 https://youtu.be/HOY6TW5Y5a4 ·
  212 https://youtu.be/Dfe2eF72smU · 214 https://youtu.be/KAxPLGZrsJU ·
  215 https://youtu.be/xJjJKmWx2xI · 216 https://youtu.be/QO-kHBZBfBs ·
  Segurança https://youtu.be/Bp6O71fHFIg · OpenRocket https://youtu.be/CfT25FJbSuo
- Minifoguete a propelente sólido: aspectos teóricos e propostas experimentais para o ensino
  de física — Revista Brasileira de Ensino de Física: https://scielo.br/j/rbef/a/dTQnxcQT6TGhnkYmMx4H6Sx/?lang=pt
- Marchi, C. H. — Propelente KNSu a frio para minifoguetes (GFCS/UFPR, 2021):
  http://ftp.demec.ufpr.br/foguete/Divulgacao/2021_Propelente_KNSu_a_frio_para%20minifoguetes_preparo_carregamento_estocagem_e_uso_Marchi.pdf
- Foltran, A. C. et al. — Medição da velocidade de queima à pressão atmosférica do propelente
  KNSu (SAB 2014): http://ftp.demec.ufpr.br/foguete/Trabalhos/2014_Foltran_Moro_Silva_Ferreira_Araki_Marchi_SAB_2014.pdf
- Associação Brasileira de Minifoguetes — Norma BAR-2/2020 (nomenclatura; NOTAM; testes):
  http://ftp.demec.ufpr.br/foguete/apostila/norma-BAR-2-2020_versao_2020-12-03.pdf
- Marchi, C. H. — Capítulo 3, Estabilidade (apostila citada pelo regulamento):
  http://ftp.demec.ufpr.br/foguete/apostila/Capitulo_03_Estabilidade.pdf
- Espressif — ESP32-C3 Series Datasheet (consumo em modem-sleep): https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf
- Bosch Sensortec — BMP280 Datasheet rev 1.26: https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf
- NACA TN 4197 (flutter de painel), na forma da Apogee Components (Peak of Flight #291/#411).
- Niskanen, S. — Development of an Open Source model rocket simulation software (OpenRocket,
  documentação técnica: Barrowman estendido, modelos de arrasto).
