# O motor oficial da OBAFOG (Modelo 5)

Os dois foguetes usam **o mesmo motor**: o motor de propelente sólido descrito pela
OBAFOG, que a equipe da OBA diz ter acionado mais de 1.200 vezes sem explosão (live 208,
1:56). Para a OBAFOG ele é obrigatório e **não pode ser alterado em nada**. Para o
foguete livre, ele é a escolha certa pelo mesmo motivo: é o único motor caseiro com
projeto testado centenas de vezes. Aumentar o motor, trocar o cano ou colar o cap é
exatamente o que a OBA avisa que pode explodir (regulamento, p.3).

**Como fabricar o motor: siga os vídeos oficiais 210 a 216, com o professor.** Este
documento não repete a receita. Ele trata o motor como uma **caixa-preta** que precisa
entrar no foguete e no OpenRocket.

## O que se sabe (dado firme)

| Dado | Valor | Fonte |
|---|---|---|
| Carcaça | cano PVC marrom soldável 20 mm, 100 mm de comprimento | regulamento 2026 p.11; vídeo 210 |
| Tubeira | cap soldável 20 mm, furo central de 7 mm (broca 9/32") | vídeo 210, 0:11–3:33 |
| Cap | **não é colado**: salta se a pressão subir (válvula de alívio) | vídeo 210, 17:14–18:55; live 208 |
| Propelente | 22 g, compactado, com furo central | regulamento p.11 |
| Furo central | feito com parafuso de 5/16" (7,9 mm), 85 mm de parte lisa | vídeos 210 e 216 |
| Fechamento dianteiro | bolinha de papel-alumínio compactada + cola + bicarbonato | vídeo 216, 30:00–34:15 |
| Tempo de queima | **~1,2 s** (1,2 a 1,25 s) | live 208, 1:29:35 (muitos testes em balança) |
| Repetibilidade | "todos os motores tinham a curva … muito parecida" | live 208, 1:28:00 |
| Ignição | squib (fósforo elétrico) enfiado até o fundo do furo, 9 V, fio ≥ 20–25 m | vídeos 215/216 |
| Foguetes que já voaram com ele | de menos de 50 g até 200 g | live 208, 1:55 |
| Desempenho mostrado | garrafas de 500 mL: ~100 m repetidos; às vezes > 150 m | live 208, 1:53; vídeo 215, 16:55 |

## O que NÃO se sabe (e como foi tratado)

**A curva de empuxo não é publicada.** Ela aparece rapidamente na live, mas sem números.
Então o impulso foi limitado por medições publicadas de motores parecidos:

| Referência | O que mediu | Isp |
|---|---|---|
| RBEF, "Minifoguete a propelente sólido…" (KNSu 65/35 a frio, KNO3 impuro, 33 g, eletroduto 3/4", bocal de argila) | v_e = 380 m/s derivada do voo (apogeu 72,8 m, 226 g) | ~39 s |
| Marchi / GFCS-UFPR 2021 (KNSu a frio **prensado a 3–10 t**, tubeira metálica, 5–20 bar) | 330 testes | 63–82 s |
| Motor da OBA (compactado por queda de peso, tubeira = furo em plástico que erode) | não publicado | **abaixo dos dois** |

E foi feita uma checagem com os voos que a OBA mostra (`scripts/calibrar_com_voos_oba.py`):
garrafas de 500 mL estáveis no OpenRocket dão 114–162 m com 7 N·s e 158–211 m com 9 N·s,
contra ~100 m reais. Como o OpenRocket costuma **subestimar** o arrasto de foguete
artesanal (fita, coifa rombuda, aleta torta), a conclusão honesta é:

> **impulso nominal = 7 N·s (Isp 32 s); faixa de projeto 5 a 11,5 N·s.**
> Pela classificação da norma BAR-2/2020 é um motor **classe C** (5,01–10 N·s), que
> pode cair na B ou chegar na D. Em código NAR, algo como **C6-P** (P = sem carga de ejeção).

A forma da curva também não é conhecida, então há três envelopes:

| Envelope | Formato | Pico (7 N·s) | O que muda no voo |
|---|---|---|---|
| **REG** | pico no início, depois cai | 11,5 N | sai da vara mais rápido |
| **NEU** | patamar | 7,0 N | caso central |
| **PRO** | começa fraco, cresce | 8,9 N (no fim) | **pior saída da vara** |

Arquivos em `eng/`: `OBAFOG-M5_<envelope>_<impulso>.eng`, com impulsos I05, I07, I09 e I115
(5; 7; 9; 11,5 N·s), mais `NEU_I07_tb10` e `NEU_I07_tb14` (queima de 1,0 e 1,4 s). Todos têm
22 g de propelente e 35,9 g **sem o cap**. O cap (~5 g) entra no foguete como um componente
de massa atrás da lata, porque o CG real do motor fica atrás do centro geométrico e isso
muda a margem em ~0,1 cal.

`gerar_motores.py` gera a família inteira (não precisa de OpenRocket).

## Massas e cotas a conferir na balança e no paquímetro

| Item | Valor usado | Por que importa |
|---|---|---|
| Diâmetro externo do cano | 20,0 mm | folga da luva (gabaritos de 20,3 a 20,9 mm) |
| Diâmetro externo do cap | 24,6 mm | tem de ser **menor que o corpo** (26 mm), senão vira o Dmax |
| Comprimento do cap | 18 mm | define o balanço do motor atrás da lata |
| Massa do cap | 5 g | CG do motor |
| Massa do motor carregado (sem cap) | 35,9 g | massa de decolagem e CG |
| Massa do motor queimado | ~14 g + resíduo | CG depois da queima |

## Como medir de verdade: teste de resistência e teste estático

A norma BAR-2/2020 manda esta ordem, e ela faz sentido:

1. **Teste de resistência** — o motor queima preso numa base, **sem instrumento**. Serve
   para ver se ele funciona sem anomalia, medir o tempo de queima filmando (celular a
   60 fps dá ±0,02 s) e pesar o resíduo. Faça com o professor, no mesmo protocolo de
   segurança do lançamento (fio de 25 m, protetor facial, ninguém perto).
2. **Teste estático** — o motor empurra uma célula de carga. Mede a curva de empuxo.
   Pasta `teste_estatico/`:
   - `bancada_estatica.ino` — Arduino Uno/Nano + HX711 + célula de carga de 5 kg;
   - `para_eng.py` — transforma as medições num `.eng` do OpenRocket (média de vários motores).
3. **Teste de voo** — só com motor aprovado nos dois anteriores.

Com 3 a 5 testes estáticos, a faixa de 5 a 11,5 N·s vira um número com ±10%, e a
simulação do alcance fica tão boa quanto a do motor de vinagre depois da calibração.
