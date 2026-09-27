# Revisão crítica do projeto (skill engineering-reviewer)

Feita no fim, procurando erro de propósito. Onde achei problema, está dito o que era, a
evidência e o que mudou.

## Escopo

Revisado: regulamento x Foguete 1; modelo do motor; física e restrições da otimização;
estrutura das aletas (flutter); imprimibilidade de todas as peças; transmissão de empuxo e
cap livre; eletrônica e firmware do Foguete 2 (inclusive o teste SIL); segurança e espaço aéreo.
Fora do alcance: o motor físico (curva real), as peças impressas reais (massa e folga), o
vento no dia, a eletrônica montada.

## Bloqueantes — achados e JÁ CORRIGIDOS

| Problema | Evidência | Correção |
|---|---|---|
| **Aleta com bordo de fuga subindo** (ex.: 13 mm ao longo de 44 mm de envergadura): impressa em pé, a borda fica a ~74° da vertical e sai caída sem suporte | geometria das aletas da 1ª variante construível; a regra de impressão da avaliação estava com a desigualdade invertida | **bordo de fuga reto** (enflechamento = raiz − ponta) nos dois foguetes; regra corrigida em `scripts/avaliacao.py`. Bônus: o CP foi para trás, o lastro caiu e a nota subiu de 308 para ~321 |
| Estimativa antiga do motor: 2469 psi numa carcaça de PVC | `_arquivo_estimativa_2026-08-28/` | arquivada; motor novo tratado como caixa-preta com dados dos vídeos oficiais |
| Firmware não detectava o pouso em 210 de 480 casos (ruído zerava o contador) | teste SIL | rejeição de pico no Kalman + velocidade suavizada + tempo máximo de descida → 480/480 |
| Backup por tempo (7 s) abria **antes** do apogeu com o motor de 11,5 N·s (apogeu aos 7,8 s) | teste SIL | backup em 8,5 s |
| Foguete 2 de 26 mm: com motor de 9 N·s passa de 150 m e **não cabe** lastro suficiente | tabela de lastro | recomendado o de 29 mm (21 g resolvem) |
| **STL da lata e do pistão não-manifold** depois que o fatiador funde vértices (~220 e ~140 arestas ruins) | auditoria com `trimesh.load(process=True)`: faces coincidentes (furo subtraído com o mesmo raio dos anéis; disco e saia do pistão dividindo a parede) | subtração redundante removida, pistão em perfil único; **31 de 31 STL estanques, 0 aresta ruim** |
| STL antigo esquecido na pasta da variante A (`F1_tubo_corpo_v1.stl`, de antes do bordo de fuga reto; a versão final não tem tubo) | listagem da pasta | apagado |

## Importantes (não impedem, mas custam alcance ou confiabilidade)

1. **O impulso do motor não é conhecido** (faixa de projeto 5–11,5 N·s). Muda o alcance do
   Foguete 1 de ~200 a ~450 m. Na Jornada o motor é feito no evento, sem chance de medir antes.
   → Teste estático na escola (bancada em `motor/teste_estatico/`) e voos de teste para
   calibrar, como foi feito com o motor de vinagre.
2. **O OpenRocket provavelmente é otimista.** Na calibração com as garrafas da OBA ele deu mais
   alcance que o real. O foguete impresso e pintado é bem mais "limpo" que uma garrafa, mas
   espere algo **10–30% abaixo** da simulação até o primeiro voo real dizer o contrário.
3. **Haste de 6 mm verga e chicoteia.** Flecha estática de ~4 cm e 2,5° na ponta (refeito:
   w = 1,54 N/m, EI = 12,7 N·m², L = 1,3 m); com o foguete passando, mais uns graus. Medir o
   ângulo na metade de cima (transferidor em `foguete1_obafog/moldes/`).
4. **Saída da vara lenta** (12–13 m/s nominal, ~8,5 m/s no pior motor) → sensível a vento.
   Vento de cauda forte com motor fraco pode fazer o foguete empinar e cair perto (0,95 m numa
   simulação com rajada). Usar a tabela de ângulo x vento; se puder, esperar a rajada passar.
5. **Altura de impressão da ogiva da variante A: 220 mm.** Impressora mais baixa → variante B
   (ogiva de 150 mm, 165 mm de altura).
6. **Pouso balístico a ~40 m/s**: a ogiva quebra com frequência. Levar reservas.
7. **Calor do motor no PLA**: lata em **PETG**, fita crepe no tubo, tirar o motor logo.
8. **Cap maior que o corpo** viraria o Dmax do regulamento e aumentaria o arrasto: medir o cap
   (o projeto supõe 24,6 mm < 26 mm).
9. **Foguete 2**: servo precisa aceitar 1S (3,7–4,2 V) — conferir o modelo comprado; saída da
   vara de 8–10 m/s → haste de 1,8–2 m.

## Verifiquei e está OK

- Regulamento: motor intocado, sem metal (lastro de massa epóxi), duas guias, margem 1,4 cal
  (Dmax = corpo de 26 mm), lançamento oblíquo. Tudo com página citada em `regulamento/CONFORMIDADE.md`.
- Margem estática com o motor e **com as massas reais do CAD** (não as do OpenRocket), e a
  mínima em voo ≥ 1,0 cal no cenário nominal.
- **Flutter** refeito à mão para a aleta final (NACA TN 4197): V_flutter ≈ 264 m/s em PLA
  (G = 1,0 GPa) e ≈ 221 m/s em PETG (0,7 GPa), contra ~120 m/s no cenário mais rápido →
  fator ≥ 1,8.
- Empuxo pela borda do tubo de PVC num batente cônico; cap 3 mm atrás da lata, sem contato.
- STL estanques, em milímetros, sem suporte (tetos cônicos, anéis com chanfro, cunha na guia).
- Firmware: compila sem aviso (`--warnings all`), 84% da flash, 30% da RAM; diferença de
  `millis()` em `uint32_t` (sobrevive ao estouro); nenhuma checagem de sensor trava a placa.
- Teste SIL do firmware com as trajetórias finais do OpenRocket: 480/480.
- Espaço aéreo: limite de 150 m (BAR-2/2020) tratado no Foguete 2 com a tabela de lastro.

## Não consegui verificar (falta dado)

- Curva de empuxo real do motor → teste estático.
- Massas e folgas reais das peças impressas → balança e gabaritos.
- Cotas exatas do cap e do cano que a Jornada vai fornecer → paquímetro no evento.
- Arrasto real da superfície impressa e pintada → primeiro voo.
- Dimensões dos módulos eletrônicos que você comprar → medir antes de imprimir o berço.
