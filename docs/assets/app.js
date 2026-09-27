/* Monta gráficos, tabelas e números da página a partir de window.DADOS (dados.js). */
(function () {
  "use strict";
  const D = window.DADOS, G = window.Graficos;
  // casas decimais fixas: numa coluna de tabela, "11,0" e "13,3" alinham; "11" e "13,3" não
  const fmt = (v, d = 1) => (v == null || isNaN(v)) ? "—" : new Intl.NumberFormat("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  const nomeSim = (n) => n.replace(/N\.s/g, "N·s").replace(/ graus/g, "°").replace(/saida/g, "saída").replace(/^NOMINAL/, "Nominal");
  const $ = (s) => document.querySelector(s);
  const RAMPA = ["var(--r1)", "var(--r2)", "var(--r3)", "var(--r4)"];
  const IMP = { I05: "5 N·s", I07: "7 N·s (nominal)", I09: "9 N·s", I115: "11,5 N·s" };

  /* ---------- tema ---------- */
  const btnTema = $("#tema");
  function aplicarTema(t) {
    if (t) document.documentElement.setAttribute("data-theme", t);
    const escuro = document.documentElement.getAttribute("data-theme") === "dark" ||
      (!document.documentElement.hasAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    btnTema.textContent = escuro ? "☀ Claro" : "☾ Escuro";
  }
  try { const t = localStorage.getItem("tema"); if (t) aplicarTema(t); } catch (e) { /* sem armazenamento */ }
  aplicarTema();
  btnTema.addEventListener("click", () => {
    const escuro = btnTema.textContent.includes("Claro");
    const novo = escuro ? "light" : "dark";
    aplicarTema(novo);
    try { localStorage.setItem("tema", novo); } catch (e) { /* ok */ }
  });

  /* ---------- utilidades de tabela ---------- */
  function tabelaHTML(alvo, colunas, linhas, destaque) {
    const w = document.createElement("div"); w.className = "tabela-wrap";
    const t = document.createElement("table");
    const trh = t.createTHead().insertRow();
    colunas.forEach((c, i) => { const th = document.createElement("th"); th.textContent = c; if (i) th.className = "num"; trh.appendChild(th); });
    const tb = t.createTBody();
    linhas.forEach((l, k) => {
      const tr = tb.insertRow();
      if (destaque && destaque(k, l)) tr.className = "melhor";
      l.forEach((v, i) => { const td = tr.insertCell(); td.textContent = v; if (i) td.className = "num"; });
    });
    w.appendChild(t); alvo.appendChild(w);
  }
  const m = (v, d = 0) => fmt(v, d) + " m";

  /* ---------- números do topo ---------- */
  const A = D.f1_resumo.A, nomA = D.f1_sims[0], f2 = D.f2_resumo["29"], nom2 = f2.simulacoes_no_ork[0];
  const tiles = [
    ["Alcance simulado, Foguete 1", m(nomA.perp), "motor nominal de 7 N·s, a " + fmt(A.elev_recomendada_sem_vento, 0) + "°"],
    ["Faixa no Monte Carlo", fmt(A.monte_carlo.p10, 0) + "–" + fmt(A.monte_carlo.p90, 0) + " m", "10% a 90% de 200 voos sorteados"],
    ["Massa do Foguete 1", fmt(A.estabilidade.massa_g, 0) + " g", "com motor; margem " + fmt(A.estabilidade.cal, 2) + " cal"],
    ["Apogeu, Foguete 2", m(nom2.apogeu), "paraquedas desce a " + fmt(nom2.v_descida, 1) + " m/s"],
    ["Firmware no simulador", D.sil_resumo.aprovados + "/" + D.sil_resumo.casos, "casos aprovados (abertura no apogeu)"],
    ["Projetos avaliados", "~" + fmt(Math.round(D.otm_n.total / 50) * 50, 0), fmt(D.otm_n.viaveis_S1, 0) + " viáveis no conjunto de 9 cenários"],
  ];
  const tb = $("#tiles");
  for (const [r, v, s] of tiles) {
    const d = document.createElement("div"); d.className = "tile";
    [["rotulo", r], ["valor", v], ["sub", s]].forEach(([c, t]) => { const e = document.createElement("div"); e.className = c; e.textContent = t; d.appendChild(e); });
    tb.appendChild(d);
  }

  /* ---------- motor ---------- */
  G.linhas($("#g-motor-impulso"), {
    titulo: "Família de curvas de empuxo — impulso", sub: "Envelope neutro, queima de 1,2 s (medida pela OBA). O impulso real não é publicado.",
    series: ["I05", "I07", "I09", "I115"].map((k, i) => ({ nome: IMP[k], cor: RAMPA[i], pontos: D.motores["NEU_" + k] })),
    x: { rotulo: "tempo (s)", fmt: (v) => fmt(v, 1), fmtDica: (v) => fmt(v, 2) + " s", rotuloDica: "t" },
    y: { rotulo: "empuxo (N)", unidade: "N" }, altura: 280,
  });
  G.linhas($("#g-motor-formato"), {
    titulo: "Formato da curva (7 N·s)", sub: "Regressivo sai da vara mais rápido; progressivo é o pior caso de saída.",
    series: [["REG", "regressivo", "var(--s1)"], ["NEU", "neutro", "var(--s2)"], ["PRO", "progressivo", "var(--s3)"]]
      .map(([k, n, c]) => ({ nome: n, cor: c, pontos: D.motores[k + "_I07"] })),
    x: { rotulo: "tempo (s)", fmt: (v) => fmt(v, 1), fmtDica: (v) => fmt(v, 2) + " s", rotuloDica: "t" },
    y: { rotulo: "empuxo (N)", unidade: "N" }, altura: 280,
  });
  G.linhas($("#g-calib"), {
    titulo: "Checagem com os voos da OBA", sub: "Garrafas PET de 500 mL estáveis simuladas no OpenRocket (45°, sem vento) contra os ~100 m que a OBA mostra.",
    series: [
      { nome: "média das " + D.calib_pet[0].n + " garrafas", cor: "var(--s1)", pontos: D.calib_pet.map((c) => [c.impulso, c.media]) },
      { nome: "a que foi mais longe", cor: "var(--s2)", pontos: D.calib_pet.map((c) => [c.impulso, c.max]) },
      { nome: "a que foi menos longe", cor: "var(--s3)", pontos: D.calib_pet.map((c) => [c.impulso, c.min]) },
    ],
    horizontais: [{ y: 100, rotulo: "voos reais mostrados pela OBA: ~100 m" }],
    x: { rotulo: "impulso total (N·s)", min: 6.5, max: 12, fmt: (v) => fmt(v, 0), fmtDica: (v) => fmt(v, 1) + " N·s", rotuloDica: "impulso" },
    y: { rotulo: "alcance (m)", min: 0, unidade: "m" }, altura: 280,
  });

  /* ---------- Foguete 1 ---------- */
  const B = D.f1_resumo.B;
  tabelaHTML($("#t-f1-comparativo"), ["", "Variante A (recomendada)", "Variante B (ogiva curta)"], [
    ["Peças impressas", "2 (ogiva + lata)", "3 (ogiva + tubo + lata)"],
    ["Ogiva", "série de potência, " + fmt(D.f1_resumo.A_params.nose_len, 0) + " mm", "elipsoidal, " + fmt(D.f1_resumo.B_params.nose_len, 0) + " mm"],
    ["Altura de impressão da ogiva", fmt(D.f1_resumo.A_cad.find((c) => c.arquivo.includes("ogiva")).altura_mm, 0) + " mm", fmt(D.f1_resumo.B_cad.find((c) => c.arquivo.includes("ogiva")).altura_mm, 0) + " mm"],
    ["Aletas (raiz / ponta / envergadura, mm)", D.f1_resumo.A_params.fin_n + " × " + [D.f1_resumo.A_params.fin_root, D.f1_resumo.A_params.fin_tip, D.f1_resumo.A_params.fin_span].map((v) => fmt(v, 0)).join(" / "),
      D.f1_resumo.B_params.fin_n + " × " + [D.f1_resumo.B_params.fin_root, D.f1_resumo.B_params.fin_tip, D.f1_resumo.B_params.fin_span].map((v) => fmt(v, 0)).join(" / ")],
    ["Lastro de massa epóxi no bico", fmt(D.f1_resumo.A_params.ballast_g, 1) + " g", fmt(D.f1_resumo.B_params.ballast_g, 1) + " g"],
    ["Massa na decolagem (com motor)", fmt(A.estabilidade.massa_g, 1) + " g", fmt(B.estabilidade.massa_g, 1) + " g"],
    ["Margem estática com motor / motor queimado", fmt(A.estabilidade.cal, 2) + " / " + fmt(A.estabilidade.cal_burnout, 2) + " cal", fmt(B.estabilidade.cal, 2) + " / " + fmt(B.estabilidade.cal_burnout, 2) + " cal"],
    ["Alcance, 7 N·s, sem vento", m(D.f1_sims[0].perp), m(D.f1B_sims[0].perp)],
    ["Alcance, 5 / 9 N·s", m(D.f1_sims[1].perp) + " / " + m(D.f1_sims[2].perp), m(D.f1B_sims[1].perp) + " / " + m(D.f1B_sims[2].perp)],
    ["Monte Carlo P10 / mediana / P90", [A.monte_carlo.p10, A.monte_carlo.p50, A.monte_carlo.p90].map((v) => fmt(v, 0)).join(" / ") + " m",
      [B.monte_carlo.p10, B.monte_carlo.p50, B.monte_carlo.p90].map((v) => fmt(v, 0)).join(" / ") + " m"],
  ]);
  tabelaHTML($("#t-f1-sims"), ["Simulação guardada no .ork", "Alcance", "Apogeu", "Vel. máx.", "Saída da vara", "Estab. mín. em voo"],
    D.f1_sims.map((s) => [nomeSim(s.nome), m(s.perp), m(s.apogeu), fmt(s.v_max, 0) + " m/s", fmt(s.v_vara, 1) + " m/s", fmt(s.stab_min, 2) + " cal"]));
  const traj = D.f1_trajetorias;
  G.linhas($("#g-f1-traj"), {
    titulo: "Trajetórias do Foguete 1 (variante A, " + fmt(A.elev_recomendada_sem_vento, 0) + "°, sem vento)",
    sub: "Altitude contra distância percorrida, para os quatro impulsos da faixa de projeto.",
    series: [["NEU_I05", "5 N·s"], ["NEU_I07", "7 N·s (nominal)"], ["NEU_I09", "9 N·s"], ["REG_I115", "11,5 N·s"]]
      .map(([k, n], i) => ({ nome: n + " — " + fmt(traj[k].alcance, 0) + " m", cor: RAMPA[i], pontos: traj[k].pontos })),
    x: { rotulo: "distância (m)", min: 0, fmt: (v) => fmt(v, 0), fmtDica: (v) => fmt(v, 0) + " m", rotuloDica: "distância" },
    y: { rotulo: "altitude (m)", min: 0, unidade: "m" },
  });
  function serieAngulos(ventos) {
    return ventos.map(([v, de], i) => {
      const l = D.f1_angulos.find((a) => a.vento === v && a.de === de);
      const ks = Object.keys(l.por_angulo).map(Number).sort((a, b) => a - b);
      return { nome: v === 0 ? "sem vento" : fmt(v, 0) + " m/s", cor: RAMPA[i], pontos: ks.map((k) => [k, l.por_angulo[String(k)].media]) };
    });
  }
  const eixoAng = { rotulo: "ângulo da haste acima do horizonte (°)", fmt: (v) => fmt(v, 0) + "°", fmtDica: (v) => fmt(v, 0) + "°", rotuloDica: "ângulo" };
  G.linhas($("#g-f1-ang-frente"), {
    titulo: "Vento de frente", sub: "Quanto mais vento contra, mais alto o ângulo.",
    series: serieAngulos([[0, 0], [2, 0], [4, 0], [6, 0]]), x: eixoAng, y: { rotulo: "alcance médio (m)", unidade: "m", min: 280 }, altura: 280,
  });
  G.linhas($("#g-f1-ang-cauda"), {
    titulo: "Vento de cauda", sub: "Com vento a favor, o ótimo desce para ~40°.",
    series: serieAngulos([[0, 0], [2, 180], [4, 180], [6, 180]]), x: eixoAng, y: { rotulo: "alcance médio (m)", unidade: "m", min: 280 }, altura: 280,
  });
  tabelaHTML($("#t-f1-angulos"), ["Vento na direção do lançamento", "Ângulo recomendado", "Alcance médio simulado"],
    D.f1_angulos.map((a) => [a.vento === 0 ? "calmo" : fmt(a.vento, 0) + " m/s " + (a.de === 0 ? "de frente" : a.de === 180 ? "de cauda" : "lateral"),
      a.melhor_angulo + "°", m(a.alcance_medio_no_melhor)]), (k, l) => l[0] === "calmo");
  const mc = D.f1_monte_carlo;
  G.histograma($("#g-f1-mc"), {
    titulo: "Monte Carlo: 200 voos simulados com tudo sorteado",
    sub: "Vento de 0 a 5 m/s de qualquer direção, com rajadas; ângulo escolhido pela tabela, com erro de ±1,5°; massas e lastro com erro de fabricação. Os quatro montes são os quatro impulsos sorteados: 5, 7, 9 e 11,5 N·s (e 3 formatos de curva).",
    valores: mc, largura_bin: 25, x: { rotulo: "alcance perpendicular (m)", unidade: "m", fmt: (v) => fmt(v, 0) }, y: { rotulo: "voos" },
    marcas: [{ x: A.monte_carlo.p10, rotulo: "P10 " + fmt(A.monte_carlo.p10, 0) }, { x: A.monte_carlo.p50, rotulo: "mediana " + fmt(A.monte_carlo.p50, 0) },
      { x: A.monte_carlo.p90, rotulo: "P90 " + fmt(A.monte_carlo.p90, 0) }],
  });
  const dz = D.otm_destaques;
  G.dispersao($("#g-otm"), {
    titulo: "Otimização: " + fmt(D.otm_n.viaveis_S1, 0) + " projetos viáveis (mesmo conjunto de cenários)",
    sub: "Cada ponto é um foguete completo simulado com 3 motores × 3 ventos. Correlação alcance × massa: " + fmt(D.otm_correlacao, 2) + " — mais leve voa mais longe. O ponto azul usa as massas medidas no CAD; os outros, as estimadas pelo OpenRocket.",
    nuvem: { nome: "projetos viáveis", pontos: D.otm_nuvem },
    destaques: [
      { nome: "construtível (escolhido)", x: dz.construtivel[0], y: dz.construtivel[1], cor: "var(--s1)" },
      { nome: "ótimo teórico (aleta frágil)", x: dz.teorico[0], y: dz.teorico[1], cor: "var(--s2)", rotuloEsq: true },
      { nome: "projeto feito à mão", x: dz.humano[0], y: dz.humano[1], cor: "var(--s3)" },
    ],
    x: { rotulo: "massa na decolagem (g)", unidade: "g", rotuloCurto: "massa", fmt: (v) => fmt(v, 0) },
    y: { rotulo: "alcance médio (m)", unidade: "m", rotuloCurto: "alcance médio" },
  });
  tabelaHTML($("#t-comparacao"), ["Projeto (conjunto completo S2: 5 motores × 6 ventos)", "Média", "Pior caso", "Nominal", "Massa", "Margem"],
    D.comparacao_S2.map((r) => [r.nome.startsWith("livre") ? "ótimo teórico (aleta 18 × 1,2 mm)" : r.nome === "humano" ? "projeto feito à mão" : "construtível — variante A",
      m(r.perp_media), m(r.perp_min), m(r.perp_nominal), fmt(r.massa_g, 1) + " g", fmt(r.cal, 2) + " cal"]), (k, l) => l[0].startsWith("construtível"));
  const rotulos = { nose_len: "comprimento da ogiva ±2 mm", fin_root: "raiz da aleta ±1 mm", fin_tip: "ponta da aleta ±1 mm",
    fin_span: "envergadura ±1 mm", fin_sweep: "enflechamento ±1 mm", fin_t: "espessura da aleta ±0,2 mm", ballast_g: "lastro ±1 g",
    "peças impressas": "massa das peças impressas ±8%", cap: "massa do cap do motor ±1,5 g" };
  const nominal = D.f1_sensibilidade.find((s) => s.caso === "nominal").perp;
  const grupos = {};
  for (const s of D.f1_sensibilidade) {
    if (s.caso === "nominal") continue;
    const neg = / -/.test(s.caso);
    const base = s.caso.split(/ [+-]/)[0];
    const g = grupos[base] || (grupos[base] = { rotulo: rotulos[base] || base, menos: 0, mais: 0, rotMenos: "para menos", rotMais: "para mais" });
    if (neg) g.menos = s.perp - nominal; else g.mais = s.perp - nominal;
  }
  const itensSens = Object.values(grupos).sort((a, b) => Math.max(Math.abs(b.menos), Math.abs(b.mais)) - Math.max(Math.abs(a.menos), Math.abs(a.mais)));
  G.tornado($("#g-sens"), {
    titulo: "Tolerância de fabricação: quanto cada erro muda o alcance",
    sub: "Motor nominal, sem vento. Alcance nominal " + m(nominal) + ". Nenhuma tolerância realista passa de ±8 m.",
    itens: itensSens, unidade: "m", rotuloX: "variação do alcance (m)", nomeNeg: "diminui o alcance", nomePos: "aumenta o alcance",
  });

  /* ---------- Foguete 2 ---------- */
  const f2alt = D.f2_altitude;
  G.linhas($("#g-f2-alt"), {
    titulo: "Foguete 2: altitude × tempo (29 mm, 87°)", sub: "Paraquedas comandado depois do apogeu; descida a ~4,5 m/s. Acima de 150 m a norma BAR-2 pede NOTAM.",
    series: ["NEU_I05", "NEU_I07", "NEU_I09", "NEU_I115"].map((k, i) => ({ nome: IMP[k.split("_")[1]] + " — " + fmt(f2alt[k].apogeu, 0) + " m", cor: RAMPA[i], pontos: f2alt[k].pontos })),
    horizontais: [{ y: 150, rotulo: "150 m (limite sem NOTAM em área rural)" }],
    x: { rotulo: "tempo (s)", min: 0, fmt: (v) => fmt(v, 0), fmtDica: (v) => fmt(v, 1) + " s", rotuloDica: "t" },
    y: { rotulo: "altitude (m)", min: 0, unidade: "m" },
  });
  tabelaHTML($("#t-f2-sims"), ["Simulação guardada no .ork", "Apogeu", "Vel. máx.", "Saída da vara", "Abertura", "Descida", "Deriva"],
    f2.simulacoes_no_ork.map((s) => [nomeSim(s.nome), m(s.apogeu), fmt(s.v_max, 0) + " m/s", fmt(s.v_vara, 1) + " m/s", fmt(s.v_abertura, 1) + " m/s", fmt(s.v_descida, 1) + " m/s", m(s.total)]));
  tabelaHTML($("#t-f2-lastro"), ["Motor medido na bancada", "Apogeu sem lastro extra", "Lastro para ficar < 140 m", "Saída da vara"],
    f2.tabela_lastro.map((l) => [IMP[l.motor], m(l.apogeu_sem_lastro_extra, 0),
      l.lastro_extra_g === null ? "não cabe: NOTAM ou campo liberado" : l.lastro_extra_g ? fmt(l.lastro_extra_g, 0) + " g" : "nenhum", fmt(l.v_vara_com_lastro, 1) + " m/s"]));
  G.colunas($("#g-f2-deriva"), {
    titulo: "Deriva até o pouso (motor nominal)", sub: "Tamanho de campo necessário: o paraquedas voa com o vento.",
    itens: f2.tabela_deriva.map((d) => ({ rotulo: fmt(d.vento, 0) + " m/s", valor: d.deriva_m })),
    x: { rotulo: "vento" }, y: { rotulo: "deriva (m)", unidade: "m" }, altura: 260,
  });
  const ex = D.sil_exemplo;
  const ev = D.sil_eventos;
  G.linhas($("#g-sil"), {
    titulo: "O firmware real rodando no PC contra o voo do OpenRocket (7 N·s)",
    sub: "Pressão com ruído de barômetro e picos; o filtro de Kalman do firmware estima altitude e velocidade e decide a abertura.",
    series: [
      { nome: "leitura do barômetro (com ruído)", cor: "var(--tinta-3)", pontos: ex.t.map((t, i) => [t, ex.bruto[i]]), largura: 1, opacidade: 0.7 },
      { nome: "altitude real (OpenRocket)", cor: "var(--s1)", pontos: ex.t.map((t, i) => [t, ex.real[i]]), largura: 6, opacidade: 0.45 },
      { nome: "estimativa do firmware (Kalman)", cor: "var(--s2)", pontos: ex.t.map((t, i) => [t, ex.filtrado[i]]) },
    ],
    verticais: Object.entries(ev).map(([n, t], i) => ({ x: t, rotulo: n + " (" + fmt(t, 1) + " s)", nivel: i })),
    x: { rotulo: "tempo (s)", min: -1, fmt: (v) => fmt(v, 0), fmtDica: (v) => fmt(v, 2) + " s", rotuloDica: "t" },
    y: { rotulo: "altitude (m)", unidade: "m" },
  });
  tabelaHTML($("#t-sil"), ["Trajetória (motor, vento)", "Apogeu", "Abertura após apogeu (média / máx)", "|v| na abertura (máx)", "Aprovados"],
    D.sil_resumo.por_traj.map((r) => [r.traj.replace("traj_", "").replace("_v", " · vento ").replace("NEU_", "").replace("I05", "5 N·s").replace("I07", "7 N·s").replace("I09", "9 N·s").replace("I115", "11,5 N·s").replace("PRO_", "progr. ").replace("REG_", "regr. ") + " m/s",
      m(r.apogeu), fmt(r.atraso_medio, 2) + " / " + fmt(r.atraso_max, 2) + " s", fmt(r.v_max, 1) + " m/s", r.aprovados + "/" + r.n]));

  /* ---------- 3D (com recuo para imagens) ---------- */
  const v3d = $("#v3d");
  import("./visualizador3d.js").then((mod) => mod.iniciarVisualizador(v3d, { manifesto: "modelos/modelos.json", pasta: "modelos/", inicial: "F1_A" }))
    .catch((e) => {
      console.warn("3D indisponível:", e);
      v3d.querySelector(".palco").style.display = "none";
      v3d.querySelector(".ctrl").style.display = "none";
      v3d.querySelector(".fallback").hidden = false;
    });
})();
