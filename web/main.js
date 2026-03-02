const RHO = 1.225, G = 9.81, DT = 0.04, WORLD_H = 35;

const plane = { mass: 0.6, wingArea: 0.22, liftCoeff: 1.0, dragCoeff: 0.06, control: 0.16 };
const sling = { strength: 30.0, eff: 0.9 };
const levels = [
  { id: 1, target: 220, obstacles: [{x1:90,x2:110,h:6},{x1:165,x2:190,h:8}], coinInterval: 40, bonus: 80 },
  { id: 2, target: 320, obstacles: [{x1:70,x2:95,h:5},{x1:175,x2:210,h:10},{x1:260,x2:285,h:8}], coinInterval:45, bonus:110 },
  { id: 3, target: 430, obstacles: [{x1:110,x2:140,h:7},{x1:210,x2:245,h:11},{x1:320,x2:355,h:9}], coinInterval:50, bonus:150 },
];

let levelIdx = 0, coins = 0, running = false, nextCoin = 40, gained = 0;
let state = {x:0,y:1.2,vx:0,vy:0,t:0};

const c = document.getElementById('game');
const ctx = c.getContext('2d');
const hud = document.getElementById('hud');
const msg = document.getElementById('msg');

const angle = document.getElementById('angle');
const power = document.getElementById('power');
const attack = document.getElementById('attack');
const angleVal = document.getElementById('angleVal');
const powerVal = document.getElementById('powerVal');
const attackVal = document.getElementById('attackVal');

angle.oninput = () => angleVal.textContent = angle.value;
power.oninput = () => powerVal.textContent = power.value;
attack.oninput = () => attackVal.textContent = attack.value;

function resetLevel(i) {
  levelIdx = i;
  state = {x:0,y:1.2,vx:0,vy:0,t:0};
  running = false;
  gained = 0;
  nextCoin = levels[levelIdx].coinInterval;
  msg.textContent = `第 ${levels[levelIdx].id} 关准备就绪`;
}

function step(attackInput) {
  const speed = Math.max(0.01, Math.min(80, Math.hypot(state.vx, state.vy)));
  const vxh = state.vx / speed, vyh = state.vy / speed;
  const cl = Math.max(0.2, plane.liftCoeff + attackInput * plane.control);
  const lift = 0.5 * RHO * speed * speed * plane.wingArea * cl;
  const drag = 0.5 * RHO * speed * speed * plane.wingArea * plane.dragCoeff;

  const fx = -vyh * lift - vxh * drag;
  const fy = vxh * lift - vyh * drag - plane.mass * G;
  const ax = Math.max(-40, Math.min(40, fx / plane.mass));
  const ay = Math.max(-45, Math.min(45, fy / plane.mass));

  state = { x: state.x + state.vx*DT, y: state.y + state.vy*DT, vx: state.vx + ax*DT, vy: state.vy + ay*DT, t: state.t + DT };
}

function collides(ob) { return state.x >= ob.x1 && state.x <= ob.x2 && state.y < ob.h; }

function updateHUD() {
  const lv = levels[levelIdx];
  hud.textContent = `关卡 ${lv.id}/${levels.length} | 金币 ${coins} | x=${state.x.toFixed(1)}m y=${state.y.toFixed(1)}m vx=${state.vx.toFixed(1)}m/s`;
}

function worldToCanvas(x,y) {
  const camX = Math.max(0, state.x - 140);
  return [ (x-camX)*3, c.height - y*(c.height/WORLD_H) ];
}

function draw() {
  ctx.clearRect(0,0,c.width,c.height);
  ctx.fillStyle = '#3a8d2f';
  ctx.fillRect(0,c.height-3,c.width,3);

  for (let i=0;i<c.width;i+=80){ ctx.strokeStyle='#cfe8f8'; ctx.beginPath(); ctx.moveTo(i,0); ctx.lineTo(i,c.height); ctx.stroke(); }

  const lv = levels[levelIdx];
  for (const ob of lv.obstacles) {
    const [x1,y1] = worldToCanvas(ob.x1,0), [x2,y2] = worldToCanvas(ob.x2,ob.h);
    if (x2 < 0 || x1 > c.width) continue;
    ctx.fillStyle = '#8b3d2f';
    ctx.fillRect(x1,y2,x2-x1,y1-y2);
  }

  const [tx] = worldToCanvas(lv.target,0);
  ctx.strokeStyle = '#ff6a00'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(tx,0); ctx.lineTo(tx,c.height); ctx.stroke();

  const [px,py] = worldToCanvas(state.x,state.y);
  const a = Math.atan2(state.vy, Math.max(0.01,state.vx)), s = 14;
  const nose = [px + Math.cos(a)*s, py - Math.sin(a)*s];
  const left = [px + Math.cos(a+2.5)*s*0.8, py - Math.sin(a+2.5)*s*0.8];
  const right = [px + Math.cos(a-2.5)*s*0.8, py - Math.sin(a-2.5)*s*0.8];
  ctx.fillStyle = '#1f6fff'; ctx.strokeStyle='#0d3d99'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.moveTo(...nose); ctx.lineTo(...left); ctx.lineTo(...right); ctx.closePath(); ctx.fill(); ctx.stroke();

  updateHUD();
}

function endLevel(pass, text) {
  running = false;
  coins += gained;
  msg.textContent = `${text}（本关金币 +${gained}）`;
  if (pass) {
    if (levelIdx + 1 < levels.length) resetLevel(levelIdx + 1);
    else { msg.textContent = `恭喜通关！总金币 ${coins}`; resetLevel(0); }
  }
}

function loop() {
  if (!running) return;
  step(Number(attack.value)/100);
  const lv = levels[levelIdx];

  if (!Number.isFinite(state.x+state.y+state.vx+state.vy)) return endLevel(false, '数值异常');
  if (state.y <= 0) return endLevel(false, `坠地 x=${state.x.toFixed(1)}m`);
  for (const ob of lv.obstacles) if (collides(ob)) return endLevel(false, '撞上障碍物');

  while (state.x >= nextCoin) { gained += 10; nextCoin += lv.coinInterval; }
  if (state.x >= lv.target) { gained += lv.bonus; return endLevel(true, '过关成功'); }
  if (state.t > 90) return endLevel(false, '超时失败');

  draw();
  requestAnimationFrame(loop);
}

document.getElementById('launch').onclick = () => {
  if (running) return;
  state = {x:0,y:1.2,vx:0,vy:0,t:0};
  gained = 0;
  nextCoin = levels[levelIdx].coinInterval;
  const speed = sling.strength * sling.eff * (Number(power.value)/100);
  const rad = Number(angle.value) * Math.PI / 180;
  state.vx = speed * Math.cos(rad);
  state.vy = speed * Math.sin(rad);
  running = true;
  msg.textContent = '已发射...';
  loop();
};

document.getElementById('upPlane').onclick = () => {
  if (coins < 120) return msg.textContent = '金币不足';
  coins -= 120; plane.wingArea *= 1.08; plane.liftCoeff *= 1.06; plane.dragCoeff *= 0.95; plane.mass *= 0.98; plane.control *= 1.05;
  draw();
};

document.getElementById('upSling').onclick = () => {
  if (coins < 90) return msg.textContent = '金币不足';
  coins -= 90; sling.strength *= 1.12; sling.eff = Math.min(1.0, sling.eff + 0.03);
  draw();
};

resetLevel(0);
draw();
