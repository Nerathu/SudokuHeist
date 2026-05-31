const canvas = document.getElementById("fxCanvas");
const ctx = canvas.getContext("2d");
let particles = [];

export function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

function loop() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  particles = particles.filter((p) => p.life > 0);
  particles.forEach((p) => {
    p.x += p.vx;
    p.y += p.vy;
    p.life -= 1;
    p.vy += 0.08;
    ctx.globalAlpha = p.life / 40;
    ctx.fillStyle = p.color;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.globalAlpha = 1;
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

export function burst(x, y, color = "#ffd166", count = 18) {
  for (let i = 0; i < count; i++) {
    particles.push({
      x,
      y,
      vx: (Math.random() - 0.5) * 6,
      vy: (Math.random() - 0.5) * 6 - 2,
      life: 30 + Math.random() * 20,
      size: 2 + Math.random() * 4,
      color,
    });
  }
}

export function screenShake() {
  document.body.classList.add("shake");
  setTimeout(() => document.body.classList.remove("shake"), 400);
}

export function handleEvents(events) {
  if (!events?.length) return;
  events.forEach((ev) => {
    if (ev.type === "jackpot") {
      screenShake();
      burst(window.innerWidth / 2, window.innerHeight / 3, "#06d6a0", 40);
    }
    if (ev.type === "row_complete" || ev.type === "block_complete") {
      burst(window.innerWidth / 2, 120, "#ffd166", 12);
    }
    if (ev.type === "heart_lost") {
      screenShake();
    }
    if (ev.type === "ante_won") {
      burst(window.innerWidth / 2, window.innerHeight / 2, "#ef476f", 30);
    }
    if (ev.type === "cell_correct" && ev.row != null) {
      const grid = document.getElementById("sudokuGrid");
      const cell = grid?.children[ev.row * 9 + ev.col];
      if (cell) {
        const rect = cell.getBoundingClientRect();
        burst(rect.left + rect.width / 2, rect.top + rect.height / 2, "#4cc9f0", 8);
      }
    }
  });
}
