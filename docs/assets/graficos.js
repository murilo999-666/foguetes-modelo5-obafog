/* Biblioteca mínima de gráficos em SVG (sem dependências).
   Regras (skill dataviz): linhas de 2px, pontos >= 8px com anel da superfície, grade em
   hairline sólida, texto em tinta (nunca na cor da série), legenda para >= 2 séries,
   dica que não é a única forma de ler o valor (toda figura tem tabela), um eixo só. */
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";

  function svgEl(tag, attrs, pai) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) {
      if (k === "style") Object.assign(e.style, attrs.style);
      else if (k === "text") e.textContent = attrs.text;
      else e.setAttribute(k, attrs[k]);
    }
    if (pai) pai.appendChild(e);
    return e;
  }
  function htmlEl(tag, cls, pai, texto) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (texto !== undefined) e.textContent = texto;
    if (pai) pai.appendChild(e);
    return e;
  }
  const nf = (d) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: d, minimumFractionDigits: 0 });
  function fmt(v, d) { return v == null || isNaN(v) ? "—" : nf(d === undefined ? 1 : d).format(v); }

  function ticksBons(min, max, n) {
    const span = max - min || 1;
    const passo0 = span / Math.max(n, 1);
    const pot = Math.pow(10, Math.floor(Math.log10(passo0)));
    const m = passo0 / pot;
    const passo = (m >= 5 ? 10 : m >= 2 ? 5 : m >= 1 ? 2 : 1) * pot;
    const t = [];
    for (let v = Math.ceil(min / passo) * passo; v <= max + passo * 1e-9; v += passo) t.push(+v.toFixed(10));
    return t;
  }
  function escala(d0, d1, r0, r1) {
    const k = (r1 - r0) / ((d1 - d0) || 1);
    const f = (v) => r0 + (v - d0) * k;
    f.inv = (p) => d0 + (p - r0) / k;
    return f;
  }
  function interp(pts, x) {
    if (!pts.length || x < pts[0][0] || x > pts[pts.length - 1][0]) return null;
    let lo = 0, hi = pts.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (pts[m][0] <= x) lo = m; else hi = m; }
    const [x0, y0] = pts[lo], [x1, y1] = pts[hi];
    return x1 === x0 ? y0 : y0 + (y1 - y0) * (x - x0) / (x1 - x0);
  }

  /* estrutura comum: título, subtítulo, área, legenda, tabela */
  function cartao(alvo, o) {
    const raiz = htmlEl("div", "grafico", alvo);
    if (o.titulo) htmlEl("div", "titulo", raiz, o.titulo);
    if (o.sub) htmlEl("div", "sub", raiz, o.sub);
    const area = htmlEl("div", "", raiz);
    area.style.position = "relative";
    const dica = htmlEl("div", "dica", area);
    const leg = htmlEl("div", "legenda-g", raiz);
    const btn = htmlEl("button", "btn-tabela", raiz, "Ver tabela");
    btn.type = "button";
    const tab = htmlEl("div", "tabela-g tabela-wrap", raiz);
    btn.addEventListener("click", () => {
      const ab = tab.classList.toggle("aberta");
      btn.textContent = ab ? "Esconder tabela" : "Ver tabela";
    });
    return { raiz, area, dica, leg, tab };
  }
  function legenda(leg, itens) {
    leg.textContent = "";
    if (itens.length < 2) { leg.style.display = "none"; return; }
    for (const it of itens) {
      const s = htmlEl("span", "", leg);
      const i = htmlEl("i", it.tipo || "", s);
      i.style.background = it.cor;
      htmlEl("span", "", s, it.nome);
    }
  }
  function tabela(tab, colunas, linhas) {
    tab.textContent = "";
    const t = htmlEl("table", "", tab);
    const tr = htmlEl("tr", "", htmlEl("thead", "", t));
    colunas.forEach((c, i) => htmlEl("th", i ? "num" : "", tr, c));
    const tb = htmlEl("tbody", "", t);
    for (const l of linhas) {
      const r = htmlEl("tr", "", tb);
      l.forEach((v, i) => htmlEl("td", i ? "num" : "", r, typeof v === "number" ? fmt(v, 1) : v));
    }
  }
  function posDica(dica, area, px, py) {
    const w = dica.offsetWidth, h = dica.offsetHeight, W = area.clientWidth;
    let x = px + 14, y = py - h - 10;
    if (x + w > W) x = px - w - 14;
    if (x < 0) x = 0;
    if (y < 0) y = py + 14;
    dica.style.left = x + "px";
    dica.style.top = y + "px";
    dica.style.opacity = 1;
  }
  function linhaDica(dica, cor, valor, nome, tipo) {
    const l = htmlEl("div", "linha", dica);
    const i = htmlEl("i", "", l);
    i.style.background = cor;
    if (tipo === "ponto") { i.style.width = "8px"; i.style.height = "8px"; i.style.borderRadius = "50%"; }
    htmlEl("b", "", l, valor);
    htmlEl("span", "", l, nome);
  }
  function observar(el, desenhar) {
    let largura = 0, t = null;
    const ro = new ResizeObserver((es) => {
      const w = Math.round(es[0].contentRect.width);
      if (w && Math.abs(w - largura) > 2) {
        largura = w;
        clearTimeout(t);
        t = setTimeout(() => desenhar(w), 30);
      }
    });
    ro.observe(el);
  }
  function eixos(g, o, sx, sy, x0, x1, y0, y1, W, H, m) {
    const grade = svgEl("g", { class: "grade-g" }, g);
    const ax = svgEl("g", { class: "eixo" }, g);
    const nx = Math.max(3, Math.floor((W - m.l - m.r) / 90));
    const ny = Math.max(3, Math.floor((H - m.t - m.b) / 55));
    for (const v of ticksBons(y0, y1, ny)) {
      svgEl("line", { x1: m.l, x2: W - m.r, y1: sy(v), y2: sy(v) }, grade);
      svgEl("text", { x: m.l - 8, y: sy(v) + 4, "text-anchor": "end", text: (o.y.fmt || ((a) => fmt(a, 0)))(v) }, ax);
    }
    for (const v of ticksBons(x0, x1, nx)) {
      svgEl("text", { x: sx(v), y: H - m.b + 18, "text-anchor": "middle", text: (o.x.fmt || ((a) => fmt(a, 1)))(v) }, ax);
    }
    svgEl("line", { x1: m.l, x2: W - m.r, y1: sy(y0), y2: sy(y0) }, ax);
    if (o.x.rotulo) svgEl("text", { class: "rot-eixo", x: (m.l + W - m.r) / 2, y: H - 4, "text-anchor": "middle", text: o.x.rotulo }, g);
    if (o.y.rotulo) svgEl("text", { class: "rot-eixo", x: m.l - 44, y: m.t - 12, "text-anchor": "start", text: o.y.rotulo }, g);
  }

  /* ---------------- linhas (várias séries, eixo x numérico) ---------------- */
  function linhas(alvo, o) {
    const c = cartao(alvo, o);
    legenda(c.leg, o.series.map((s) => ({ nome: s.nome, cor: s.cor })));
    if (o.tabela) tabela(c.tab, o.tabela.colunas, o.tabela.linhas);
    else {
      const xs = [...new Set(o.series.flatMap((s) => s.pontos.map((p) => p[0])))].sort((a, b) => a - b);
      const passo = Math.max(1, Math.ceil(xs.length / 40));
      tabela(c.tab, [o.x.rotulo || "x", ...o.series.map((s) => s.nome)],
        xs.filter((_, i) => i % passo === 0).map((x) => [fmt(x, 2), ...o.series.map((s) => interp(s.pontos, x))]));
    }
    function desenhar(W) {
      c.area.querySelectorAll("svg").forEach((s) => s.remove());
      const H = o.altura || Math.max(260, Math.min(380, W * 0.5));
      const m = { l: 52, r: 18, t: 26, b: 42 };
      const todos = o.series.flatMap((s) => s.pontos);
      const x0 = o.x.min !== undefined ? o.x.min : Math.min(...todos.map((p) => p[0]));
      const x1 = o.x.max !== undefined ? o.x.max : Math.max(...todos.map((p) => p[0]));
      let y0 = o.y.min !== undefined ? o.y.min : Math.min(0, ...todos.map((p) => p[1]));
      let y1 = o.y.max !== undefined ? o.y.max : Math.max(...todos.map((p) => p[1])) * 1.08;
      (o.horizontais || []).forEach((h) => { y1 = Math.max(y1, h.y * 1.1); });
      const sx = escala(x0, x1, m.l, W - m.r), sy = escala(y0, y1, H - m.b, m.t);
      const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.titulo || "gráfico" });
      c.area.insertBefore(svg, c.dica);
      const g = svgEl("g", {}, svg);
      eixos(g, o, sx, sy, x0, x1, y0, y1, W, H, m);
      for (const h of o.horizontais || []) {
        svgEl("line", { x1: m.l, x2: W - m.r, y1: sy(h.y), y2: sy(h.y), style: { stroke: "var(--tinta-3)", strokeWidth: 1 } }, g);
        svgEl("text", { class: "rot-dir", x: W - m.r, y: sy(h.y) - 6, "text-anchor": "end", text: h.rotulo }, g);
      }
      for (const v of o.verticais || []) {
        svgEl("line", { x1: sx(v.x), x2: sx(v.x), y1: m.t, y2: H - m.b, style: { stroke: "var(--eixo)", strokeWidth: 1 } }, g);
        const aDireita = sx(v.x) > m.l + (W - m.l - m.r) * 0.7;   // perto da borda: rótulo para dentro
        svgEl("text", { class: "rot-dir", x: sx(v.x) + (aDireita ? -4 : 4), y: m.t + 10 + (v.nivel || 0) * 14,
          "text-anchor": aDireita ? "end" : "start", text: v.rotulo }, g);
      }
      for (const s of o.series) {
        const d = s.pontos.map((p, i) => (i ? "L" : "M") + sx(p[0]).toFixed(1) + "," + sy(p[1]).toFixed(1)).join("");
        svgEl("path", { d, fill: "none", style: { stroke: s.cor, strokeWidth: s.largura || 2, strokeLinejoin: "round", strokeLinecap: "round", opacity: s.opacidade || 1 } }, g);
      }
      // camada de interação: mira vertical + dica com todas as séries
      const mira = svgEl("line", { y1: m.t, y2: H - m.b, style: { stroke: "var(--tinta-3)", strokeWidth: 1, opacity: 0 } }, g);
      const pontos = o.series.map((s) => svgEl("circle", { r: 4.5, style: { fill: s.cor, stroke: "var(--superficie)", strokeWidth: 2, opacity: 0 } }, g));
      const hit = svgEl("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent", tabindex: 0, style: { outline: "none", cursor: "crosshair" } }, svg);
      let xAtual = (x0 + x1) / 2;
      function mostrar(x) {
        xAtual = Math.max(x0, Math.min(x1, x));
        const px = sx(xAtual);
        mira.setAttribute("x1", px); mira.setAttribute("x2", px); mira.style.opacity = 1;
        c.dica.textContent = "";
        htmlEl("div", "cab", c.dica, (o.x.rotuloDica || o.x.rotulo || "x") + ": " + (o.x.fmtDica || o.x.fmt || ((a) => fmt(a, 1)))(xAtual));
        let pyMin = H;
        o.series.forEach((s, i) => {
          const y = interp(s.pontos, xAtual);
          if (y == null) { pontos[i].style.opacity = 0; return; }
          pontos[i].setAttribute("cx", px); pontos[i].setAttribute("cy", sy(y)); pontos[i].style.opacity = 1;
          pyMin = Math.min(pyMin, sy(y));
          linhaDica(c.dica, s.cor, (o.y.fmtDica || ((a) => fmt(a, 1)))(y) + (o.y.unidade ? " " + o.y.unidade : ""), s.nome);
        });
        posDica(c.dica, c.area, px, Math.max(pyMin, m.t + 20));
      }
      function esconder() { mira.style.opacity = 0; pontos.forEach((p) => (p.style.opacity = 0)); c.dica.style.opacity = 0; }
      hit.addEventListener("pointermove", (e) => {
        const r = svg.getBoundingClientRect();
        mostrar(sx.inv((e.clientX - r.left) * (W / r.width)));
      });
      hit.addEventListener("pointerleave", esconder);
      hit.addEventListener("focus", () => mostrar(xAtual));
      hit.addEventListener("blur", esconder);
      hit.addEventListener("keydown", (e) => {
        if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
          e.preventDefault();
          mostrar(xAtual + (e.key === "ArrowRight" ? 1 : -1) * (x1 - x0) / 50);
        }
      });
    }
    observar(c.area, desenhar);
    return c;
  }

  /* ---------------- dispersão (nuvem cinza + até 3 destaques) ---------------- */
  function dispersao(alvo, o) {
    const c = cartao(alvo, o);
    legenda(c.leg, [{ nome: o.nuvem.nome, cor: "var(--tinta-3)", tipo: "ponto" },
      ...o.destaques.map((d) => ({ nome: d.nome, cor: d.cor, tipo: "ponto" }))]);
    tabela(c.tab, ["Projeto", o.x.rotulo, o.y.rotulo],
      o.destaques.map((d) => [d.nome, d.x, d.y]).concat([[o.nuvem.nome + " (n = " + o.nuvem.pontos.length + ")", "—", "—"]]));
    function desenhar(W) {
      c.area.querySelectorAll("svg").forEach((s) => s.remove());
      const H = o.altura || Math.max(280, Math.min(400, W * 0.55));
      const m = { l: 52, r: 18, t: 26, b: 42 };
      const xs = o.nuvem.pontos.map((p) => p[0]).concat(o.destaques.map((d) => d.x));
      const ys = o.nuvem.pontos.map((p) => p[1]).concat(o.destaques.map((d) => d.y));
      const x0 = o.x.min ?? Math.floor(Math.min(...xs) / 5) * 5, x1 = o.x.max ?? Math.ceil(Math.max(...xs) / 5) * 5;
      const y0 = o.y.min ?? Math.floor(Math.min(...ys) / 50) * 50, y1 = o.y.max ?? Math.ceil(Math.max(...ys) / 50) * 50;
      const sx = escala(x0, x1, m.l, W - m.r), sy = escala(y0, y1, H - m.b, m.t);
      const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.titulo || "dispersão" });
      c.area.insertBefore(svg, c.dica);
      const g = svgEl("g", {}, svg);
      eixos(g, o, sx, sy, x0, x1, y0, y1, W, H, m);
      const gn = svgEl("g", {}, g);
      for (const p of o.nuvem.pontos) svgEl("circle", { cx: sx(p[0]), cy: sy(p[1]), r: 2.6, style: { fill: "var(--nuvem)" } }, gn);
      const alvos = [];
      for (const d of o.destaques) {
        svgEl("circle", { cx: sx(d.x), cy: sy(d.y), r: 6.5, style: { fill: d.cor, stroke: "var(--superficie)", strokeWidth: 2 } }, g);
        // rótulo do lado pedido, mas vira de lado (e sobe) se for sair do gráfico
        const larg = d.nome.length * 6.4, px = sx(d.x);
        const esq = d.rotuloEsq ? px - 11 - larg > 2 : px + 11 + larg > W - 2;
        const acima = !!d.rotuloEsq !== esq;
        svgEl("text", { class: "rot-dir", x: px + (esq ? -11 : 11), y: sy(d.y) + (acima ? -10 : 4), "text-anchor": esq ? "end" : "start", text: d.nome }, g);
        alvos.push({ px: sx(d.x), py: sy(d.y), d, destaque: true });
      }
      const hit = svgEl("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" }, svg);
      const anel = svgEl("circle", { r: 7, style: { fill: "none", stroke: "var(--tinta)", strokeWidth: 1.5, opacity: 0 } }, g);
      hit.addEventListener("pointermove", (e) => {
        const r = svg.getBoundingClientRect();
        const px = (e.clientX - r.left) * (W / r.width), py = (e.clientY - r.top) * (H / r.height);
        let melhor = null, dm = 24 * 24;
        for (const a of alvos) { const dd = (a.px - px) ** 2 + (a.py - py) ** 2; if (dd < dm) { dm = dd; melhor = a; } }
        if (!melhor) {
          let dn = 14 * 14;
          for (const p of o.nuvem.pontos) {
            const qx = sx(p[0]), qy = sy(p[1]); const dd = (qx - px) ** 2 + (qy - py) ** 2;
            if (dd < dn) { dn = dd; melhor = { px: qx, py: qy, d: { nome: o.nuvem.nome, x: p[0], y: p[1], cor: "var(--tinta-3)" } }; }
          }
        }
        if (!melhor) { c.dica.style.opacity = 0; anel.style.opacity = 0; return; }
        anel.setAttribute("cx", melhor.px); anel.setAttribute("cy", melhor.py); anel.style.opacity = 1;
        c.dica.textContent = "";
        htmlEl("div", "cab", c.dica, melhor.d.nome);
        linhaDica(c.dica, melhor.d.cor, fmt(melhor.d.y, 0) + " " + (o.y.unidade || ""), o.y.rotuloCurto || o.y.rotulo, "ponto");
        linhaDica(c.dica, melhor.d.cor, fmt(melhor.d.x, 1) + " " + (o.x.unidade || ""), o.x.rotuloCurto || o.x.rotulo, "ponto");
        posDica(c.dica, c.area, melhor.px, melhor.py);
      });
      hit.addEventListener("pointerleave", () => { c.dica.style.opacity = 0; anel.style.opacity = 0; });
    }
    observar(c.area, desenhar);
    return c;
  }

  function colunaPath(x, y, w, h, raio) {
    const r = Math.min(raio, w / 2, h);
    return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
  }

  /* ---------------- histograma ---------------- */
  function histograma(alvo, o) {
    const c = cartao(alvo, o);
    legenda(c.leg, []);
    const b = o.largura_bin;
    const lo = Math.floor(Math.min(...o.valores) / b) * b, hi = Math.ceil(Math.max(...o.valores) / b) * b;
    const bins = [];
    for (let v = lo; v < hi; v += b) bins.push({ a: v, z: v + b, n: 0 });
    for (const v of o.valores) bins[Math.min(bins.length - 1, Math.floor((v - lo) / b))].n++;
    tabela(c.tab, ["Faixa (" + (o.x.unidade || "") + ")", "Voos"], bins.map((k) => [fmt(k.a, 0) + "–" + fmt(k.z, 0), k.n]));
    function desenhar(W) {
      c.area.querySelectorAll("svg").forEach((s) => s.remove());
      const H = o.altura || 280;
      const m = { l: 44, r: 18, t: 30, b: 42 };
      const nmax = Math.max(...bins.map((k) => k.n));
      const sx = escala(lo, hi, m.l, W - m.r), sy = escala(0, nmax * 1.15, H - m.b, m.t);
      const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.titulo || "histograma" });
      c.area.insertBefore(svg, c.dica);
      const g = svgEl("g", {}, svg);
      eixos(g, { x: o.x, y: { rotulo: o.y ? o.y.rotulo : "voos", fmt: (a) => fmt(a, 0) } }, sx, sy, lo, hi, 0, nmax * 1.15, W, H, m);
      const wbar = Math.max(2, sx(lo + b) - sx(lo) - 2);
      for (const k of bins) {
        if (!k.n) continue;
        const x = sx(k.a) + 1, y = sy(k.n), h = sy(0) - y;
        const p = svgEl("path", { d: colunaPath(x, y, wbar, h, 3), style: { fill: o.cor || "var(--s1)", cursor: "pointer" }, tabindex: 0 }, g);
        const mostrar = () => {
          p.style.opacity = 0.8;
          c.dica.textContent = "";
          htmlEl("div", "cab", c.dica, fmt(k.a, 0) + "–" + fmt(k.z, 0) + " " + (o.x.unidade || ""));
          linhaDica(c.dica, o.cor || "var(--s1)", k.n + " voos", "(" + fmt(100 * k.n / o.valores.length, 0) + "%)");
          posDica(c.dica, c.area, x + wbar / 2, y);
        };
        p.addEventListener("pointerenter", mostrar); p.addEventListener("focus", mostrar);
        const sair = () => { p.style.opacity = 1; c.dica.style.opacity = 0; };
        p.addEventListener("pointerleave", sair); p.addEventListener("blur", sair);
      }
      (o.marcas || []).forEach((mk, i) => {
        svgEl("line", { x1: sx(mk.x), x2: sx(mk.x), y1: m.t - 6, y2: H - m.b, style: { stroke: "var(--tinta)", strokeWidth: 1 } }, g);
        svgEl("text", { class: "rot-dir", x: sx(mk.x), y: m.t - 10, "text-anchor": "middle", text: mk.rotulo }, g);
      });
    }
    observar(c.area, desenhar);
    return c;
  }

  /* ---------------- tornado (sensibilidade, divergente em torno de zero) ---------------- */
  function tornado(alvo, o) {
    const c = cartao(alvo, o);
    legenda(c.leg, [{ nome: o.nomeNeg || "piora", cor: "var(--div-neg)", tipo: "barra" }, { nome: o.nomePos || "melhora", cor: "var(--div-pos)", tipo: "barra" }]);
    tabela(c.tab, ["Tolerância", "Variação −", "Variação +"], o.itens.map((it) => [it.rotulo, it.menos, it.mais]));
    function desenhar(W) {
      c.area.querySelectorAll("svg").forEach((s) => s.remove());
      // tela estreita: rótulo em cima das barras, para não cortar o texto à esquerda
      const estreito = W < 560;
      const lin = estreito ? 46 : 30, m = { l: estreito ? 10 : Math.min(230, W * 0.42), r: estreito ? 16 : 44, t: 18, b: 34 };
      const H = m.t + m.b + lin * o.itens.length;
      const lim = Math.max(...o.itens.flatMap((it) => [Math.abs(it.menos), Math.abs(it.mais)])) * 1.15 || 1;
      const sx = escala(-lim, lim, m.l, W - m.r);
      const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.titulo || "sensibilidade" });
      c.area.insertBefore(svg, c.dica);
      const g = svgEl("g", {}, svg);
      const gr = svgEl("g", { class: "grade-g" }, g), ax = svgEl("g", { class: "eixo" }, g);
      for (const v of ticksBons(-lim, lim, 6)) {
        svgEl("line", { x1: sx(v), x2: sx(v), y1: m.t, y2: H - m.b }, gr);
        svgEl("text", { x: sx(v), y: H - m.b + 16, "text-anchor": "middle", text: (v > 0 ? "+" : "") + fmt(v, 0) }, ax);
      }
      svgEl("line", { x1: sx(0), x2: sx(0), y1: m.t - 4, y2: H - m.b, style: { stroke: "var(--tinta-3)", strokeWidth: 1 } }, g);
      svgEl("text", { class: "rot-eixo", x: (m.l + W - m.r) / 2, y: H - 4, "text-anchor": "middle", text: o.rotuloX }, g);
      o.itens.forEach((it, i) => {
        const yc = m.t + lin * i + (estreito ? 30 : lin / 2);
        svgEl("text", { class: "rot-dir", x: estreito ? m.l : m.l - 10, y: estreito ? yc - 15 : yc + 4,
          "text-anchor": estreito ? "start" : "end", text: it.rotulo }, g);
        [["−", it.menos, -1], ["+", it.mais, 1]].forEach(([sin, v, lado]) => {
          const alt = 10, y = yc + (lado < 0 ? -alt - 1 : 1);
          const x = Math.min(sx(0), sx(v)), w = Math.max(1.5, Math.abs(sx(v) - sx(0)));
          const r = svgEl("rect", { x, y, width: w, height: alt, rx: 3, style: { fill: v >= 0 ? "var(--div-pos)" : "var(--div-neg)", cursor: "pointer" }, tabindex: 0 }, g);
          const mostrar = () => {
            c.dica.textContent = "";
            htmlEl("div", "cab", c.dica, it.rotulo + " (" + (lado < 0 ? it.rotMenos : it.rotMais) + ")");
            linhaDica(c.dica, v >= 0 ? "var(--div-pos)" : "var(--div-neg)", (v > 0 ? "+" : "") + fmt(v, 1) + " " + (o.unidade || ""), "no alcance");
            posDica(c.dica, c.area, x + w / 2, y);
          };
          r.addEventListener("pointerenter", mostrar); r.addEventListener("focus", mostrar);
          const sair = () => (c.dica.style.opacity = 0);
          r.addEventListener("pointerleave", sair); r.addEventListener("blur", sair);
        });
      });
    }
    observar(c.area, desenhar);
    return c;
  }

  /* ---------------- colunas (poucas categorias ordenadas) ---------------- */
  function colunas(alvo, o) {
    const c = cartao(alvo, o);
    legenda(c.leg, []);
    tabela(c.tab, [o.x.rotulo, o.y.rotulo], o.itens.map((it) => [it.rotulo, it.valor]));
    function desenhar(W) {
      c.area.querySelectorAll("svg").forEach((s) => s.remove());
      const H = o.altura || 280, m = { l: 48, r: 18, t: 26, b: 46 };
      let ymax = Math.max(...o.itens.map((i) => i.valor)) * 1.15;
      (o.horizontais || []).forEach((h) => (ymax = Math.max(ymax, h.y * 1.15)));
      const sy = escala(0, ymax, H - m.b, m.t);
      const banda = (W - m.l - m.r) / o.itens.length, wb = Math.min(24, banda * 0.5);
      const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.titulo || "colunas" });
      c.area.insertBefore(svg, c.dica);
      const g = svgEl("g", {}, svg);
      const gr = svgEl("g", { class: "grade-g" }, g), ax = svgEl("g", { class: "eixo" }, g);
      for (const v of ticksBons(0, ymax, 5)) {
        svgEl("line", { x1: m.l, x2: W - m.r, y1: sy(v), y2: sy(v) }, gr);
        svgEl("text", { x: m.l - 8, y: sy(v) + 4, "text-anchor": "end", text: fmt(v, 0) }, ax);
      }
      svgEl("line", { x1: m.l, x2: W - m.r, y1: sy(0), y2: sy(0) }, ax);
      if (o.y.rotulo) svgEl("text", { class: "rot-eixo", x: m.l - 40, y: m.t - 12, text: o.y.rotulo }, g);
      for (const h of o.horizontais || []) {
        svgEl("line", { x1: m.l, x2: W - m.r, y1: sy(h.y), y2: sy(h.y), style: { stroke: "var(--tinta-3)", strokeWidth: 1 } }, g);
        svgEl("text", { class: "rot-dir", x: W - m.r, y: sy(h.y) - 6, "text-anchor": "end", text: h.rotulo }, g);
      }
      o.itens.forEach((it, i) => {
        const cx = m.l + banda * (i + 0.5), y = sy(it.valor);
        svgEl("path", { d: colunaPath(cx - wb / 2, y, wb, sy(0) - y, 4), style: { fill: it.cor || "var(--s1)" } }, g);
        svgEl("text", { class: "rot-dir", x: cx, y: y - 6, "text-anchor": "middle", text: fmt(it.valor, 0) + (o.y.unidade ? " " + o.y.unidade : "") }, g);
        svgEl("text", { x: cx, y: H - m.b + 18, "text-anchor": "middle", class: "rot-g", text: it.rotulo }, g);
      });
    }
    observar(c.area, desenhar);
    return c;
  }

  window.Graficos = { linhas, dispersao, histograma, tornado, colunas, fmt };
})();
