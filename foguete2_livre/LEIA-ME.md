# Foguete 2 — livre, com eletrônica e paraquedas

Mesmo motor da OBAFOG (o único motor caseiro com projeto testado centenas de vezes), voo
quase vertical (87°), computador de voo que detecta o apogeu pelo barômetro e solta a ogiva;
uma mola empurra o paraquedas para fora. Sem pólvora. Fora de competição.

**Recomendado: `F2_29mm_v1.ork`** (abra no OpenRocket 24.12; os motores OBAFOG já estão
instalados na pasta de curvas do usuário).

## Números (OpenRocket, massas do CAD, campo a ~300 m de altitude, 25 °C)

| | F2_29mm_v1 (recomendado) | F2_26mm_v1 (desempenho) |
|---|---|---|
| Massa na decolagem | 132 g | 122 g |
| Margem estática (com motor) | 1,85 cal | 1,76 cal |
| Comprimento | 385 mm (ogiva elipsoidal 115 + tubo 170 + lata 100) | 345 mm |
| Paraquedas (octógono, PE 35 µm) | 390 mm → desce a 4,45 m/s | 370 mm → 4,48 m/s |
| Apogeu 5 / **7** / 9 / 11,5 N·s | 58 / **114** / 178 / 258 m | 70 / **136** / 208 / 299 m |
| Saída da vara (1,2 m), nominal / pior | 10,1 / 7,9 m/s | 10,6 / 8,4 m/s |
| Deriva com vento de 0 / 2 / 4 / 6 m/s | 17 / 30 / 53 / 92 m | — |
| Lastro para ficar < 140 m com 9 N·s | **21 g** no bico | não cabe (máx. 16 g) |
| Com 11,5 N·s | nem com 63 g: NOTAM ou campo liberado | idem |

O impulso real do motor decide a altura. **Faça o teste estático antes de voar o Foguete 2**
(`../motor/teste_estatico/`) e use a tabela de lastro do resumo.

## Onde está cada coisa

| Arquivo/pasta | O que é |
|---|---|
| `F2_29mm_v1.ork`, `F2_26mm_v1.ork` | projetos com 6 simulações prontas (nominal, 5, 9, 11,5 N·s, curva progressiva, vento lateral) |
| `F2_*_resumo.json` | todos os números, tabela de lastro, tabela de deriva, massas do CAD |
| `stl/F2_29mm_v1/`, `stl/F2_26mm_v1/` | ogiva com baia, tubo (janela + guia), lata de aletas, berço da eletrônica, pistão |
| `moldes/` | molde do paraquedas em tamanho real (A4) |
| `eletronica/` | esquema, lista, firmware (ESP32-C3), teste SIL |
| `MONTAGEM.md` | impressão, montagem, testes no chão, onde lançar |
| `graficos/` | altitude x tempo por motor |
| `otimizacao/` | as 500 avaliações da busca |

## Recomendações que não estão no regulamento de ninguém (é foguete livre)

- **Haste de 1,8–2 m** para o Foguete 2: a saída da vara com 1,2 m é de 8–10 m/s. Com 2 m
  sobe ~30% (a velocidade cresce com a raiz do comprimento).
- Lançar **levemente contra o vento** e **para longe das pessoas**.
- Motor sempre preso com fita crepe **no tubo** e o cap livre, igual ao Foguete 1.
