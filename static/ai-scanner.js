/**
 * AI Face Scanner — премиальный визуал сканирования лица
 * CSS + SVG + JS (Вариант 2)
 * 
 * 4 этапа:
 *   1. Инициализация — сборка лица из точек (0–0.5s)
 *   2. Сканирование — sweep линия + точки анализа + wireframe (0.5–2s)
 *   3. Анализ — подписи по очереди (2–3s)
 *   4. Результат — архетип, совпадение, прогресс-бар (3–4s)
 */

const AI_SCANNER_STYLE = `
.ai-scanner-overlay {
  position: fixed;
  inset: 0;
  background: rgba(5, 8, 14, 0.92);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
}

.ai-scanner-container {
  position: relative;
  width: 320px;
  height: 420px;
}

/* ——— Сетка фона (два слоя) ——— */
.ai-scanner-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(79, 195, 247, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79, 195, 247, 0.05) 1px, transparent 1px);
  background-size: 24px 24px;
  mask-image: radial-gradient(ellipse at center, black 40%, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 40%, transparent 70%);
  animation: scanner-grid-drift 4s linear infinite;
}

.ai-scanner-bg-grid-2 {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(124, 77, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(124, 77, 255, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  transform: rotate(15deg);
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 65%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 65%);
}

@keyframes scanner-grid-drift {
  0% { transform: translate(0, 0); }
  50% { transform: translate(4px, 4px); }
  100% { transform: translate(0, 0); }
}

/* ——— SVG-холст ——— */
.ai-scanner-svg {
  position: relative;
  width: 100%;
  height: 100%;
  z-index: 1;
}

/* ——— ЭТАП 1: Сборка лица из точек ——— */
.ai-face-point {
  transition: all 0.3s ease-out;
}

.ai-face-point-hidden {
  opacity: 0;
  r: 0;
}

/* ——— ЭТАП 2: Sweep линия ——— */
.ai-sweep-line {
  stroke: rgba(79, 195, 247, 0.7);
  stroke-width: 2;
  filter: drop-shadow(0 0 8px rgba(79, 195, 247, 0.5));
}

.ai-sweep-glow {
  fill: url(#sweepGradient);
  opacity: 0.3;
}

/* ——— Точки анализа (глаза + рот) ——— */
.ai-analysis-dot {
  animation: dot-pulse 1.2s ease-in-out infinite;
}

.ai-analysis-dot-outer {
  animation: ring-rotate 3s linear infinite;
}

@keyframes dot-pulse {
  0% { r: 5; opacity: 0.6; }
  50% { r: 7; opacity: 1; }
  100% { r: 5; opacity: 0.6; }
}

@keyframes ring-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ——— Wireframe ——— */
.ai-wireframe {
  opacity: 0;
  stroke: rgba(79, 195, 247, 0.15);
  stroke-width: 1;
  fill: none;
  transition: opacity 0.8s ease;
}

.ai-wireframe.visible {
  opacity: 1;
}

/* ——— HUD линии (к точкам) ——— */
.ai-hud-line {
  stroke: rgba(79, 195, 247, 0.2);
  stroke-width: 0.5;
  stroke-dasharray: 4 4;
}

/* ——— Угловые рамки ——— */
.ai-corner-frame {
  fill: none;
  stroke: rgba(79, 195, 247, 0.3);
  stroke-width: 1.5;
}

/* ——— ЭТАП 3: Текст анализа ——— */
.ai-status-text {
  position: absolute;
  bottom: -40px;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  letter-spacing: 2px;
  color: rgba(79, 195, 247, 0.8);
  text-shadow: 0 0 10px rgba(79, 195, 247, 0.3);
}

.ai-status-text span {
  display: inline-block;
  opacity: 0;
  transform: translateY(8px);
  transition: all 0.5s ease;
}

.ai-status-text span.visible {
  opacity: 1;
  transform: translateY(0);
}

/* ——— ЭТАП 4: Результат ——— */
.ai-result-container {
  position: absolute;
  bottom: -50px;
  left: 50%;
  transform: translateX(-50%);
  width: 300px;
  text-align: center;
  opacity: 0;
  transition: opacity 0.6s ease;
}

.ai-result-container.visible {
  opacity: 1;
}

.ai-result-archetype {
  font-family: 'Courier New', monospace;
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #4FC3F7, #7C4DFF);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 3px;
  margin-bottom: 8px;
}

.ai-result-match {
  font-size: 14px;
  color: rgba(79, 195, 247, 0.8);
  margin-bottom: 12px;
  font-family: 'Courier New', monospace;
}

.ai-progress-bar-bg {
  width: 100%;
  height: 4px;
  background: rgba(79, 195, 247, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.ai-progress-bar-fill {
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #4FC3F7, #7C4DFF);
  border-radius: 2px;
  transition: width 1.5s ease;
  box-shadow: 0 0 12px rgba(79, 195, 247, 0.4);
}

/* ——— Glitch при старте ——— */
@keyframes glitch {
  0% { transform: translate(0); opacity: 1; filter: none; }
  10% { transform: translate(-2px, 1px) skewX(5deg); filter: hue-rotate(90deg); opacity: 0.8; }
  20% { transform: translate(2px, -1px) skewX(-5deg); filter: hue-rotate(-90deg); opacity: 0.9; }
  30% { transform: translate(0); filter: none; opacity: 1; }
}

.ai-glitch {
  animation: glitch 0.3s ease;
}

/* ——— Микро-движение лица (дыхание) ——— */
@keyframes face-breathe {
  0% { transform: scaleY(1); }
  50% { transform: scaleY(1.005); }
  100% { transform: scaleY(1); }
}

.ai-face-group {
  transform-origin: center center;
}

/* ——— Кнопка закрытия ——— */
.ai-close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1001;
  background: transparent;
  border: 1px solid rgba(79, 195, 247, 0.3);
  color: rgba(79, 195, 247, 0.7);
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.ai-close-btn:hover {
  background: rgba(79, 195, 247, 0.1);
  border-color: rgba(79, 195, 247, 0.6);
}
`;

/* ——— Inject стилей ——— */
(function() {
  if (!document.getElementById('ai-scanner-style')) {
    const style = document.createElement('style');
    style.id = 'ai-scanner-style';
    style.textContent = AI_SCANNER_STYLE;
    document.head.appendChild(style);
  }
})();

/**
 * Запуск AI-сканера.
 * @param {Function} onComplete — колбэк с результатом: ({ archetype, match, analysis })
 */
function runAIFaceScanner(onComplete) {
  // Создаём оверлей
  const overlay = document.createElement('div');
  overlay.className = 'ai-scanner-overlay';
  overlay.id = 'ai-scanner-overlay';

  // Кнопка закрытия
  const closeBtn = document.createElement('button');
  closeBtn.className = 'ai-close-btn';
  closeBtn.textContent = '✕ отмена';
  closeBtn.onclick = () => {
    overlay.remove();
  };
  overlay.appendChild(closeBtn);

  const container = document.createElement('div');
  container.className = 'ai-scanner-container';

  // Сетки
  const bgGrid = document.createElement('div');
  bgGrid.className = 'ai-scanner-bg-grid';
  container.appendChild(bgGrid);

  const bgGrid2 = document.createElement('div');
  bgGrid2.className = 'ai-scanner-bg-grid-2';
  container.appendChild(bgGrid2);

  // SVG
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('viewBox', '0 0 320 420');
  svg.setAttribute('class', 'ai-scanner-svg');

  // Defs
  const defs = document.createElementNS(svgNS, 'defs');

  // Sweep gradient
  const sweepGrad = document.createElementNS(svgNS, 'linearGradient');
  sweepGrad.id = 'sweepGradient';
  sweepGrad.setAttribute('x1', '0');
  sweepGrad.setAttribute('y1', '0');
  sweepGrad.setAttribute('x2', '0');
  sweepGrad.setAttribute('y2', '1');
  const stop1 = document.createElementNS(svgNS, 'stop');
  stop1.setAttribute('offset', '0%');
  stop1.setAttribute('stop-color', 'rgba(79,195,247,0)');
  const stop2 = document.createElementNS(svgNS, 'stop');
  stop2.setAttribute('offset', '50%');
  stop2.setAttribute('stop-color', 'rgba(79,195,247,0.3)');
  const stop3 = document.createElementNS(svgNS, 'stop');
  stop3.setAttribute('offset', '100%');
  stop3.setAttribute('stop-color', 'rgba(79,195,247,0)');
  sweepGrad.append(stop1, stop2, stop3);
  defs.appendChild(sweepGrad);

  // Glow filter
  const filter = document.createElementNS(svgNS, 'filter');
  filter.id = 'faceGlow';
  filter.setAttribute('x', '-20%');
  filter.setAttribute('y', '-20%');
  filter.setAttribute('width', '140%');
  filter.setAttribute('height', '140%');
  const feGauss = document.createElementNS(svgNS, 'feGaussianBlur');
  feGauss.setAttribute('stdDeviation', '3');
  feGauss.setAttribute('result', 'blur');
  const feMerge = document.createElementNS(svgNS, 'feMerge');
  const mn1 = document.createElementNS(svgNS, 'feMergeNode');
  mn1.setAttribute('in', 'blur');
  const mn2 = document.createElementNS(svgNS, 'feMergeNode');
  mn2.setAttribute('in', 'SourceGraphic');
  feMerge.append(mn1, mn2);
  filter.append(feGauss, feMerge);
  defs.appendChild(filter);

  svg.appendChild(defs);

  // ——— Угловые рамки ———
  const cornerSize = 20;
  const corners = [
    [20, 30], [300, 30], [20, 390], [300, 390]
  ];
  corners.forEach(([x, y], i) => {
    const isLeft = x === 20;
    const isTop = y === 30;
    const h = isTop ? cornerSize : -cornerSize;
    const v = isLeft ? cornerSize : -cornerSize;
    const line1 = document.createElementNS(svgNS, 'line');
    line1.setAttribute('x1', x);
    line1.setAttribute('y1', y);
    line1.setAttribute('x2', x + v);
    line1.setAttribute('y2', y);
    line1.setAttribute('class', 'ai-corner-frame');
    const line2 = document.createElementNS(svgNS, 'line');
    line2.setAttribute('x1', x);
    line2.setAttribute('y1', y);
    line2.setAttribute('x2', x);
    line2.setAttribute('y2', y + h);
    line2.setAttribute('class', 'ai-corner-frame');
    svg.appendChild(line1);
    svg.appendChild(line2);
  });

  // ——— WIREFRAME (сетка лица) ———
  const wireframe = document.createElementNS(svgNS, 'path');
  wireframe.setAttribute('d', facePath()); // функция ниже
  wireframe.setAttribute('class', 'ai-wireframe');
  wireframe.id = 'ai-wireframe';
  svg.appendChild(wireframe);

  // ——— Лицо (outline) ——— групппа
  const faceGroup = document.createElementNS(svgNS, 'g');
  faceGroup.setAttribute('class', 'ai-face-group');
  faceGroup.setAttribute('filter', 'url(#faceGlow)');

  // Основной контур лица
  const faceOutline = document.createElementNS(svgNS, 'path');
  const fp = facePath();
  faceOutline.setAttribute('d', fp);
  faceOutline.setAttribute('fill', 'none');
  faceOutline.setAttribute('stroke', '#4FC3F7');
  faceOutline.setAttribute('stroke-width', '1.5');
  faceOutline.setAttribute('opacity', '0');
  faceOutline.id = 'ai-face-outline';
  faceGroup.appendChild(faceOutline);

  // Внутренние детали: глаза, рот, брови
  const eyeL = eyePath(100, 165);
  const eyeR = eyePath(200, 165);
  const mouth = mouthPath();

  [eyeL, eyeR].forEach((d, i) => {
    const outer = document.createElementNS(svgNS, 'ellipse');
    const pos = i === 0 ? [100, 165] : [200, 165];
    outer.setAttribute('cx', pos[0]);
    outer.setAttribute('cy', pos[1]);
    outer.setAttribute('rx', '18');
    outer.setAttribute('ry', '10');
    outer.setAttribute('fill', 'none');
    outer.setAttribute('stroke', '#4FC3F7');
    outer.setAttribute('stroke-width', '1');
    outer.setAttribute('class', 'ai-analysis-dot-outer');
    outer.setAttribute('opacity', '0');
    outer.id = `ai-eye-outer-${i}`;
    faceGroup.appendChild(outer);

    // Внутренняя точка (пульсирует)
    const dot = document.createElementNS(svgNS, 'circle');
    dot.setAttribute('cx', pos[0]);
    dot.setAttribute('cy', pos[1]);
    dot.setAttribute('r', '5');
    dot.setAttribute('fill', '#7C4DFF');
    dot.setAttribute('class', 'ai-analysis-dot');
    dot.setAttribute('opacity', '0');
    dot.id = `ai-eye-dot-${i}`;
    faceGroup.appendChild(dot);
  });

  // Рот
  const mouthPathEl = document.createElementNS(svgNS, 'path');
  mouthPathEl.setAttribute('d', mouth);
  mouthPathEl.setAttribute('fill', 'none');
  mouthPathEl.setAttribute('stroke', '#4FC3F7');
  mouthPathEl.setAttribute('stroke-width', '1');
  mouthPathEl.setAttribute('opacity', '0');
  mouthPathEl.id = 'ai-mouth';
  faceGroup.appendChild(mouthPathEl);

  // Брови
  ['browL', 'browR'].forEach((id, i) => {
    const brow = document.createElementNS(svgNS, 'line');
    const xBase = i === 0 ? 85 : 185;
    brow.setAttribute('x1', xBase);
    brow.setAttribute('y1', '135');
    brow.setAttribute('x2', xBase + 30);
    brow.setAttribute('y2', '135');
    brow.setAttribute('stroke', '#4FC3F7');
    brow.setAttribute('stroke-width', '1.2');
    brow.setAttribute('opacity', '0');
    brow.setAttribute('stroke-linecap', 'round');
    brow.id = id;
    faceGroup.appendChild(brow);
  });

  // Нос
  const nose = document.createElementNS(svgNS, 'line');
  nose.setAttribute('x1', '150');
  nose.setAttribute('y1', '175');
  nose.setAttribute('x2', '150');
  nose.setAttribute('y2', '230');
  nose.setAttribute('stroke', '#4FC3F7');
  nose.setAttribute('stroke-width', '1');
  nose.setAttribute('opacity', '0');
  nose.setAttribute('stroke-linecap', 'round');
  nose.id = 'ai-nose';
  faceGroup.appendChild(nose);

  svg.appendChild(faceGroup);

  // ——— Sweep линия ———
  const sweepGroup = document.createElementNS(svgNS, 'g');
  sweepGroup.id = 'ai-sweep-group';
  sweepGroup.setAttribute('opacity', '0');

  const sweepRect = document.createElementNS(svgNS, 'rect');
  sweepRect.setAttribute('x', '20');
  sweepRect.setAttribute('y', '30');
  sweepRect.setAttribute('width', '280');
  sweepRect.setAttribute('height', '360');
  sweepRect.setAttribute('class', 'ai-sweep-glow');
  sweepGroup.appendChild(sweepRect);

  const sweepLine = document.createElementNS(svgNS, 'line');
  sweepLine.setAttribute('x1', '20');
  sweepLine.setAttribute('x2', '300');
  sweepLine.setAttribute('y1', '30');
  sweepLine.setAttribute('y2', '30');
  sweepLine.setAttribute('class', 'ai-sweep-line');
  sweepLine.id = 'ai-sweep-line';
  sweepGroup.appendChild(sweepLine);

  svg.appendChild(sweepGroup);

  // ——— Точки анализа (глаза, рот, центр) ——— дополнительные HUD круги
  const hudCircles = [
    [100, 165, 'HUD-глаз-L'],
    [200, 165, 'HUD-глаз-R'],
    [150, 280, 'HUD-рот'],
  ];
  hudCircles.forEach(([cx, cy]) => {
    const c = document.createElementNS(svgNS, 'circle');
    c.setAttribute('cx', cx);
    c.setAttribute('cy', cy);
    c.setAttribute('r', '22');
    c.setAttribute('fill', 'none');
    c.setAttribute('stroke', 'rgba(79,195,247,0.15)');
    c.setAttribute('stroke-width', '0.8');
    c.setAttribute('stroke-dasharray', '3 3');
    c.setAttribute('opacity', '0');
    c.classList.add('ai-hud-ring');
    svg.appendChild(c);
  });

  container.appendChild(svg);

  // ——— Текст статуса ———
  const statusEl = document.createElement('div');
  statusEl.className = 'ai-status-text';
  statusEl.id = 'ai-status-text';
  container.appendChild(statusEl);

  // ——— Результат ———
  const resultEl = document.createElement('div');
  resultEl.className = 'ai-result-container';
  resultEl.id = 'ai-result-container';
  resultEl.innerHTML = `
    <div class="ai-result-archetype" id="ai-result-archetype"></div>
    <div class="ai-result-match" id="ai-result-match"></div>
    <div class="ai-progress-bar-bg">
      <div class="ai-progress-bar-fill" id="ai-progress-fill"></div>
    </div>
  `;
  container.appendChild(resultEl);

  overlay.appendChild(container);
  document.body.appendChild(overlay);

  // ==========================================
  // ЗАПУСК АНИМАЦИИ
  // ==========================================
  const outline = faceOutline;
  const dots = [document.getElementById('ai-eye-dot-0'), document.getElementById('ai-eye-dot-1')];
  const eyeOuters = [document.getElementById('ai-eye-outer-0'), document.getElementById('ai-eye-outer-1')];
  const mouthEl = document.getElementById('ai-mouth');

  function setOpacity(el, val) { if (el) el.setAttribute('opacity', val); }

  // ——— ЭТАП 1: Инициализация (0–0.5s) ———
  setTimeout(() => {
    overlay.querySelector('.ai-scanner-container').classList.add('ai-glitch');
    setTimeout(() => {
      overlay.querySelector('.ai-scanner-container').classList.remove('ai-glitch');
    }, 300);
  }, 50);

  setTimeout(() => {
    setOpacity(outline, '0.3');
    setOpacity(nose, '0.2');
    setOpacity(mouthEl, '0.2');
    document.getElementById('browL')?.setAttribute('opacity', '0.2');
    document.getElementById('browR')?.setAttribute('opacity', '0.2');
    dots.forEach(d => setOpacity(d, '0.4'));
    eyeOuters.forEach(e => setOpacity(e, '0.3'));
  }, 100);

  setTimeout(() => {
    setOpacity(outline, '0.8');
    setOpacity(nose, '0.6');
    setOpacity(mouthEl, '0.6');
    document.getElementById('browL')?.setAttribute('opacity', '0.5');
    document.getElementById('browR')?.setAttribute('opacity', '0.5');
    dots.forEach(d => setOpacity(d, '0.8'));
    eyeOuters.forEach(e => setOpacity(e, '0.7'));
    // HUD rings
    document.querySelectorAll('.ai-hud-ring').forEach(el => el.setAttribute('opacity', '0.4'));
  }, 400);

  // ——— ЭТАП 2: Сканирование (0.5–2s) ———
  setTimeout(() => {
    // Sweep линия
    sweepGroup.setAttribute('opacity', '1');
    const sweepY = document.getElementById('ai-sweep-line');
    const sweepG = sweepGroup.querySelector('.ai-sweep-glow');

    let sweepIteration = 0;
    function animateSweep() {
      setTimeout(() => {
        sweepG.setAttribute('y', '30');
        sweepG.setAttribute('height', '360');
        // Используем transform с transition
        sweepY.style.transition = 'transform 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        sweepY.style.transform = 'translateY(360px)';
        sweepG.style.transition = 'transform 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        sweepG.style.transform = 'translateY(360px)';

        setTimeout(() => {
          sweepY.style.transition = 'transform 0s';
          sweepY.style.transform = 'translateY(0)';
          sweepG.style.transition = 'transform 0s';
          sweepG.style.transform = 'translateY(0)';
          sweepIteration++;
          if (sweepIteration < 2) {
            animateSweep();
          } else {
            // Финальный проход медленнее
            setTimeout(() => {
              sweepY.style.transition = 'transform 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
              sweepY.style.transform = 'translateY(360px)';
              sweepG.style.transition = 'transform 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
              sweepG.style.transform = 'translateY(360px)';
            }, 400);
          }
        }, 800);
      }, 50);
    }
    animateSweep();

    // Wireframe
    document.getElementById('ai-wireframe').classList.add('visible');

    // Старт микро-движения лица
    faceGroup.style.animation = 'face-breathe 4s ease-in-out infinite';
  }, 500);

  // ——— ЭТАП 3: Анализ (2–3s) ———
  const statusMessages = [
    'Detecting facial structure...',
    'Analyzing emotion...',
    'Matching casting profile...',
    'Finalizing assessment...',
  ];

  statusMessages.forEach((msg, i) => {
    const delay = 2000 + i * 400;
    setTimeout(() => {
      const el = document.getElementById('ai-status-text');
      const span = document.createElement('span');
      span.textContent = msg;
      el.innerHTML = '';
      el.appendChild(span);
      // Запускаем анимацию появления
      requestAnimationFrame(() => span.classList.add('visible'));
    }, delay);
  });

  // ——— ЭТАП 4: Результат (3.5s) ———
  setTimeout(() => {
    sweepGroup.setAttribute('opacity', '0.3');

    // Генерируем результат
    const archetypes = [
      'Бунтарь', 'Герой', 'Мудрец', 'Исследователь',
      'Простодушный', 'Маг', 'Любовник', 'Шут',
      'Правитель', 'Творец', 'Заботливый', 'Славный малый'
    ];
    const matches = [72, 78, 83, 85, 87, 91, 94, 96];

    const result = {
      archetype: archetypes[Math.floor(Math.random() * archetypes.length)],
      match: matches[Math.floor(Math.random() * matches.length)],
      analysis: 'Complete'
    };

    document.getElementById('ai-result-container').classList.add('visible');
    document.getElementById('ai-result-archetype').textContent = `🧬 ${result.archetype}`;
    document.getElementById('ai-result-match').textContent = `Совпадение: ${result.match}%`;

    // Анимация прогресс-бара
    setTimeout(() => {
      document.getElementById('ai-progress-fill').style.width = result.match + '%';
    }, 200);

    // Убираем текст статуса
    setTimeout(() => {
      const st = document.getElementById('ai-status-text');
      if (st) st.style.opacity = '0';
    }, 500);

    // Колбэк через 1.5с (чтобы пользователь увидел результат)
    setTimeout(() => {
      if (onComplete) onComplete(result);
    }, 1500);
  }, 3800);
}

/**
 * Генерация path для лица (стилизованный портрет).
 */
function facePath() {
  // Голова: овал
  const head = 'M 150 60 C 90 60 40 100 40 180 C 40 260 70 330 100 360 C 120 380 135 390 150 390 C 165 390 180 380 200 360 C 230 330 260 260 260 180 C 260 100 210 60 150 60 Z';

  // Уши
  const earL = 'M 40 160 C 30 160 25 170 25 185 C 25 195 30 205 40 205';
  const earR = 'M 260 160 C 270 160 275 170 275 185 C 275 195 270 205 260 205';

  // Шея
  const neckL = 'M 115 370 L 110 410';
  const neckR = 'M 185 370 L 190 410';

  return `${head} ${earL} ${earR} ${neckL} ${neckR}`;
}

function eyePath(cx, cy) {
  return `M ${cx - 18} ${cy} Q ${cx} ${cy - 12} ${cx + 18} ${cy} Q ${cx} ${cy + 12} ${cx - 18} ${cy}`;
}

function mouthPath() {
  return 'M 120 290 Q 150 305 180 290 M 140 300 Q 150 308 160 300';
}
