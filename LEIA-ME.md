# Dois foguetes com o motor sólido da OBAFOG

Projeto de 26/09/2026. Os dois foguetes usam o **mesmo motor**: o motor de propelente sólido
oficial da OBAFOG (cano PVC 20 x 100 mm, 22 g, cap com furo de 7 mm). É o único motor caseiro
com projeto testado centenas de vezes, e fazê-lo exatamente como nos vídeos é obrigatório
para a OBAFOG.

| | Foguete 1 — OBAFOG Modelo 5 | Foguete 2 — livre |
|---|---|---|
| Objetivo | maior alcance horizontal | voo vertical com eletrônica e paraquedas |
| Onde | 100ª Jornada de Foguetes, Turma 15 (07–10/12/2026) e 21ª OBAFOG | campo aberto, fora de competição |
| Recuperação | nenhuma (mede onde parou) | paraquedas soltado por servo + mola, sem pólvora |
| Arquivo principal | `foguete1_obafog/F1_construtivel_v1.ork` | `foguete2_livre/F2_29mm_v1.ork` |
| Resumo | `foguete1_obafog/LEIA-ME.md` | `foguete2_livre/LEIA-ME.md` |

## Como abrir

1. **OpenRocket 24.12** → Arquivo → Abrir → o `.ork`. As simulações já vêm rodadas; clique em
   "Executar simulações" para refazer. Os motores OBAFOG (`OBAFOG-M5_*`) já estão instalados em
   `%APPDATA%\OpenRocket\ThrustCurves\OBAFOG-Modelo5\`. Se o OpenRocket reclamar de motor,
   aponte "Opções → Curvas de empuxo do usuário" para `motor/eng/`.
2. **STL**: `foguete1_obafog/stl/...` e `foguete2_livre/stl/...`, já na orientação de impressão.
   Comece pelos **gabaritos**.
3. **Firmware do Foguete 2**: `foguete2_livre/eletronica/firmware/computador_voo/` (Arduino IDE,
   placa "ESP32C3 Dev Module", USB CDC On Boot: Enabled).

## Estrutura

```
modelo5_solido/
├── LEIA-ME.md                 este arquivo
├── LISTA_DE_COMPRAS.md        custos estimados (Foguete 1 ~R$ 10 cada; Foguete 2 ~R$ 110–150)
├── regulamento/CONFORMIDADE.md  regra por regra, rotulada, + e-mail de dúvidas para a organização
├── pesquisa/PESQUISA.md       dossiê com todas as fontes (vídeos da OBA, RBEF, UFPR, BAR-2)
├── motor/                     MOTOR.md, curvas .eng (5 a 11,5 N·s), bancada de teste estático
├── foguete1_obafog/           .ork, STL, moldes, montagem, checklist da Jornada, otimização
├── foguete2_livre/            .ork, STL, eletrônica (firmware + teste SIL), paraquedas, montagem
├── scripts/                   tudo o que gerou os números (OpenRocket via orx, CAD, otimização)
└── docs/                      a página do projeto (GitHub Pages)
```

## O que ainda depende de medição (e muda os números)

1. **Impulso do motor.** Não é publicado. A faixa de projeto é **5 a 11,5 N·s, nominal 7 N·s**
   (ver `motor/MOTOR.md`). Com a bancada de `motor/teste_estatico/` e 3 a 5 motores, rode
   `para_eng.py`, abra o `.ork` e troque o motor por `OBAFOG-M5_MEDIDO`.
2. **Cotas do cano e do cap** (paquímetro) e **folgas da sua impressora** (gabaritos).
3. **Massas reais** das peças impressas (balança de 0,1 g) — sobrescreva no `.ork` se diferirem.

## Ordem sugerida até a Jornada (10 semanas)

| Semana | O que fazer |
|---|---|
| 1 | Professor confirma a inscrição na Turma 15 (prazo 20/10) e manda o e-mail de dúvidas (`regulamento/`). Imprimir gabaritos. |
| 2 | Fazer motores com o professor (vídeos 210–216); **teste de resistência**; montar a bancada estática. |
| 3 | **Teste estático** de 3–5 motores → curva medida → re-simular. Imprimir 1 Foguete 1 de teste. |
| 4–5 | Voos de teste do Foguete 1 na escola (ângulos 45° e 50°); anotar alcance real e comparar. |
| 6 | Imprimir os 3–4 foguetes definitivos; pintar; pesar; conferir CG. |
| 7–9 | Foguete 2: eletrônica na bancada, SIL, teste de ejeção, primeiro voo com motor medido. |
| 10 | Checklist da Jornada; apresentação de 5 min (o edital pede slides com fotos dos lançamentos). |
