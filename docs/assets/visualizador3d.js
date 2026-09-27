// Visualizador 3D dos STL reais (three.js). Peças montadas na posição de voo; motor e cap
// desenhados como cilindros. Se o WebGL ou o módulo falhar, a página mostra as imagens.
import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

function corVar(nome, reserva) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  return v || reserva;
}

export async function iniciarVisualizador(raiz, opcoes) {
  const canvasBox = raiz.querySelector(".palco");
  const info = raiz.querySelector(".info3d .pecas");
  const man = await (await fetch(opcoes.manifesto)).json();
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  canvasBox.appendChild(renderer.domElement);
  const cena = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 2, 1, 5000);
  const controles = new OrbitControls(camera, renderer.domElement);
  controles.enableDamping = true;
  controles.autoRotate = true;
  controles.autoRotateSpeed = 1.2;
  cena.add(new THREE.HemisphereLight(0xffffff, 0x8a8a80, 1.1));
  const sol = new THREE.DirectionalLight(0xffffff, 1.6);
  sol.position.set(300, 500, 400);
  cena.add(sol);
  const sol2 = new THREE.DirectionalLight(0xffffff, 0.6);
  sol2.position.set(-300, -200, -300);
  cena.add(sol2);

  const loader = new STLLoader();
  const cache = {};
  let grupo = null, pecasAtuais = [], explosao = 0, mostrarMotor = true, tagAtual = null;

  function material(cor) {
    return new THREE.MeshStandardMaterial({ color: new THREE.Color(cor), roughness: 0.55, metalness: 0.0 });
  }
  async function carregar(arq) {
    if (!cache[arq]) cache[arq] = await loader.loadAsync(opcoes.pasta + arq);
    return cache[arq];
  }
  function posicionar() {
    pecasAtuais.forEach((p, i) => { p.mesh.position.z = p.z + explosao * p.ordem; });
    if (grupo && grupo.userData.motor) grupo.userData.motor.visible = mostrarMotor;
  }
  async function montar(tag) {
    tagAtual = tag;
    raiz.querySelectorAll("button[data-tag]").forEach((b) => b.classList.toggle("ativo", b.dataset.tag === tag));
    const def = man[tag];
    if (grupo) cena.remove(grupo);
    grupo = new THREE.Group();
    pecasAtuais = [];
    const cores = { "#eb6834": corVar("--s2", "#eb6834"), "#f2a57f": "#f2a57f", "#2a78d6": corVar("--s1", "#2a78d6") };
    for (let i = 0; i < def.pecas.length; i++) {
      const p = def.pecas[i];
      const geo = await carregar(p.arquivo);
      geo.computeVertexNormals();
      const mesh = new THREE.Mesh(geo, material(cores[p.cor] || p.cor));
      grupo.add(mesh);
      pecasAtuais.push({ mesh, z: p.z, ordem: i });
    }
    // motor: cano de PVC (cinza) + cap (tubeira, bege) — o cap fica fora da lata, com folga
    const motor = new THREE.Group();
    const [z0, z1, r] = def.motor.tubo;
    const tubo = new THREE.Mesh(new THREE.CylinderGeometry(r, r, z1 - z0, 48), material("#8d8d88"));
    tubo.rotation.x = Math.PI / 2; tubo.position.z = (z0 + z1) / 2;
    const [c0, c1, rc] = def.motor.cap;
    const cap = new THREE.Mesh(new THREE.CylinderGeometry(rc, rc, c1 - c0, 48), material("#c9b98f"));
    cap.rotation.x = Math.PI / 2; cap.position.z = (c0 + c1) / 2;
    motor.add(tubo, cap);
    grupo.add(motor);
    grupo.userData.motor = motor;
    grupo.rotation.y = -Math.PI / 2;          // eixo do foguete na horizontal, ogiva à esquerda
    cena.add(grupo);
    posicionar();
    enquadrar(def.comprimento_mm);
    info.textContent = def.pecas.map((p) => `${p.nome}: ${String(p.massa_g).replace(".", ",")} g`).join(" · ");
  }
  function enquadrar(L) {
    const caixa = new THREE.Box3().setFromObject(grupo);
    const centro = caixa.getCenter(new THREE.Vector3());
    controles.target.copy(centro);
    // distância para o foguete inteiro caber na largura (tela de celular é estreita)
    const vfov = camera.fov * Math.PI / 180;
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
    const dist = ((L || 400) / 2) / Math.tan(hfov / 2) * 1.3;
    camera.position.set(centro.x + dist * 0.25, centro.y + dist * 0.35, centro.z + dist);
    camera.near = dist / 50; camera.far = dist * 20; camera.updateProjectionMatrix();
    controles.update();
  }
  let larguraAnterior = 0;
  function redimensionar() {
    const w = canvasBox.clientWidth, h = canvasBox.clientHeight || 520;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    // reenquadra só quando a largura muda de verdade (girar o celular), não a cada rolagem
    if (grupo && tagAtual && Math.abs(w - larguraAnterior) > 40) enquadrar(man[tagAtual].comprimento_mm);
    larguraAnterior = w;
  }
  new ResizeObserver(redimensionar).observe(canvasBox);
  raiz.querySelectorAll("button[data-tag]").forEach((b) => b.addEventListener("click", () => montar(b.dataset.tag)));
  const giro = raiz.querySelector("[data-acao=girar]");
  giro.addEventListener("click", () => { controles.autoRotate = !controles.autoRotate; giro.classList.toggle("ativo", controles.autoRotate); });
  giro.classList.add("ativo");
  raiz.querySelector("[data-acao=explodir]").addEventListener("input", (e) => { explosao = +e.target.value; posicionar(); });
  raiz.querySelector("[data-acao=motor]").addEventListener("change", (e) => { mostrarMotor = e.target.checked; posicionar(); });
  new MutationObserver(() => tagAtual && montar(tagAtual)).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  redimensionar();
  await montar(opcoes.inicial);
  (function laco() {
    requestAnimationFrame(laco);
    controles.update();
    renderer.render(cena, camera);
  })();
}
