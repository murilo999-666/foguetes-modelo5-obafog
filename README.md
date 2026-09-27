# Dois foguetes com o motor sólido da OBAFOG

**Página do projeto: https://murilo999-666.github.io/foguetes-modelo5-obafog/**
(gráficos, vistas do OpenRocket, modelos 3D que giram, estimativas e o plano até a Jornada)

Um foguete de alcance para o Modelo 5 da OBAFOG (100ª Jornada de Foguetes, Turma 15,
dezembro de 2026) e um foguete livre com computador de voo e paraquedas. Os dois usam o motor
sólido oficial da OBAFOG e são impressos em 3D.

| | Foguete 1 — OBAFOG Modelo 5 | Foguete 2 — livre |
|---|---|---|
| Objetivo | maior alcance horizontal | voo vertical com eletrônica e paraquedas |
| Simulado com o motor nominal (7 N·s) | 384 m de alcance, a 44° | 114 m de apogeu, descida a 4,5 m/s |
| Arquivo principal | `foguete1_obafog/F1_construtivel_v1.ork` | `foguete2_livre/F2_29mm_v1.ork` |
| Resumo | [foguete1_obafog/LEIA-ME.md](foguete1_obafog/LEIA-ME.md) | [foguete2_livre/LEIA-ME.md](foguete2_livre/LEIA-ME.md) |

Os números vêm de simulação no OpenRocket 24.12. A OBA não publica o impulso do motor: a faixa
de projeto vai de 5 a 11,5 N·s, e o teste estático (bancada em `motor/teste_estatico/`) é o
próximo passo para trocar a faixa por um número medido.

## Onde está cada coisa

- [LEIA-ME.md](LEIA-ME.md): índice do projeto e como abrir os arquivos
- [regulamento/CONFORMIDADE.md](regulamento/CONFORMIDADE.md): o regulamento regra por regra, com a página citada
- [pesquisa/PESQUISA.md](pesquisa/PESQUISA.md): dossiê de pesquisa com as fontes
- [motor/](motor/): modelo do motor, curvas `.eng` e bancada de teste estático
- [foguete1_obafog/](foguete1_obafog/) e [foguete2_livre/](foguete2_livre/): `.ork`, STL, moldes, montagem, eletrônica e firmware
- [scripts/](scripts/): o código que gerou os números (OpenRocket via Python, CAD, otimização)
- [REVISAO.md](REVISAO.md): revisão crítica do projeto
- [docs/](docs/): o código da página

Os PDFs de terceiros usados na pesquisa não foram republicados aqui; os links para eles estão
em `pesquisa/PESQUISA.md`.

## Segurança

O motor deve ser feito exatamente como nos vídeos oficiais da OBA, com o professor. Este
repositório não traz a receita do propelente e não recomenda nenhuma alteração no motor.

---

Projeto de Murilo ([@murilo999-666](https://github.com/murilo999-666)). Pesquisa, simulações,
CAD e código desenvolvidos com auxílio do Claude, a IA da Anthropic.
