# Scripts — como refazer tudo

Dois Pythons:
- **venv do orx** (`C:\Users\muril\openrocket-optimizer\.venv\Scripts\python.exe`): tudo que usa
  o OpenRocket 24.12 (JPype). Rodar sempre com `-u -X utf8`.
- **Python do sistema** (`python`): CAD (`trimesh` + `manifold3d`), moldes em PDF, imagens.

| Script | Python | O que faz |
|---|---|---|
| `m5lib.py` | venv | biblioteca: constrói os foguetes do zero no OpenRocket (F1, F2, garrafa PET da OBA), motor por configuração de voo, simula cenários, aplica massas do CAD |
| `teste_convencoes.py` | venv | confere azimute, direção do vento e margem estática (rodar depois de mexer na m5lib) |
| `teste_determinismo.py` | venv | mostra que a turbulência do OpenRocket ignora a semente |
| `calibrar_com_voos_oba.py` | venv | garrafas PET de 500 mL x impulso — checagem da faixa do motor |
| `avaliacao.py` / `otimizar_f1.py` | venv | nota robusta e otimização do Foguete 1 (`explorar N`, `humano`; modo construtível por variável de ambiente `M5_MODO=construtivel M5_CONJ=S2`) |
| `avaliar_bf_reto.py` | venv | versões com bordo de fuga reto (imprimível sem suporte) dos melhores construtíveis |
| `comparar_f1.py` | venv | teórico x construtível x humano no mesmo conjunto de cenários; salva `F1_teorico_v1.ork` |
| `finalizar_f1.py <params.json> <versao>` | venv | CAD → massas reais → lastro para 1,40 cal → tabela de ângulos → sensibilidade → Monte Carlo → `.ork` + gráficos + resumo |
| `avaliacao_f2.py` / `otimizar_f2.py` | venv | nota e otimização do Foguete 2 |
| `finalizar_f2.py <params.json> <versao>` | venv | CAD → `.ork` → tabelas de lastro (limite de 150 m) e de deriva → gráfico |
| `exportar_trajetorias_f2.py` | venv | trajetórias do F2 para o teste SIL do firmware |
| `verificar_orks.py` | venv | abre cada `.ork` do disco e roda de novo todas as simulações salvas |
| `cad_foguetes.py f1\|f2\|gabaritos\|massas` | sistema | STL paramétricos e `massas_cad.json` |
| `gerar_moldes.py <D_paraquedas>` | sistema | molde do paraquedas e transferidor da haste (PDF A4, 1:1) |
| `render_previews.py` | sistema | imagem de cada foguete montado |
| `render_openrocket.py <pasta>` | venv, com `ORX_JVM_OPTS=-Djava.awt.headless=false` | vistas lateral e traseira desenhadas pelo próprio OpenRocket (CG, CP, massas), em PNG |
| `exportar_dados_site.py <pasta da página>` | venv | números e curvas da página → `assets/dados.js` |
| `gerar_modelos_web.py <pasta>` | sistema | STL leves para o visualizador 3D da página + `modelos.json` (massas do STL de impressão) |

A página do projeto fica em `../docs/` (GitHub Pages). Depois de mudar um foguete, atualize com
`exportar_dados_site.py ../docs`, `gerar_modelos_web.py ../docs/modelos` e
`render_openrocket.py ../docs/img`.

Os motores são gerados por `../motor/gerar_motores.py` (Python do sistema, só numpy). A curva
medida na bancada entra por `../motor/teste_estatico/para_eng.py`.

Mudou uma cota fixa (diâmetro do cap, folga da impressora)? Edite `m5lib.py`/`cad_foguetes.py`,
rode `finalizar_f1.py`/`finalizar_f2.py` com o `params` da versão e depois `verificar_orks.py`.
