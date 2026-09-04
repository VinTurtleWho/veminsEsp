/**
 * VeminsESP // Web UI Studio & Visual Designer
 * Full-featured interactive canvas overlay & Dear ImGui mod menu designer.
 */

// Global State
const state = {
  config: {
    minimap: {
      posX: 0,
      posY: 0,
      width: 342,
      height: 342,
      rotationDegrees: 315,
      radarZoom: 2.0,
      alpha: 0.0,
      invertY: true,
      autoCampFlip: true,
      heroIconSize: 16
    },
    camera: {
      showTopCdBar: true,
      topCdBarPosY: 28,
      topCdBarScale: 1.0,
      scaleX: 38.0,
      scaleY: 27.0,
      hudOffsetY: 65.0,
      camOffsetX: 0.0,
      camOffsetY: 0.0,
      hpBarScale: 1.0
    },
    layers: {
      enemies: true,
      allies: false,
      arrows: true,
      minions: true,
      monsters: true,
      hpBars: true,
      skillCd: true,
      distance: true,
      edgeRadar: true
    }
  },
  design: {
    theme: 'imgui_slate',
    windowBg: '#1E1E24',
    headerBg: '#2A2B36',
    borderColor: '#3F4152',
    accentCyan: '#00E5FF',
    accentGreen: '#00E676',
    buttonBg: '#2A2C38',
    textPrimary: '#EEEEF2',
    textSecondary: '#A0A2B0',
    cardWidth: 290,
    headerHeight: 32,
    borderRadius: 4,
    fontSize: 11
  },
  localHero: {
    x: 0.0,
    y: 0.0,
    camp: 1, // 1 = Blue (315°), 2 = Red (135°)
    heading: 45.0
  },
  enemies: [
    { id: 1, name: "Chou", heroId: 26, x: 12.0, y: 15.0, hp: 0.75, dist: 14.2, fourSkills: false, skills: [0, 4.5, 12.0], spell: 42.0 },
    { id: 2, name: "Zhask", heroId: 46, x: -8.0, y: 22.0, hp: 0.90, dist: 23.4, fourSkills: true, skills: [0, 0, 7.8, 28.0], spell: 0 },
    { id: 3, name: "Beatrix", heroId: 105, x: 18.0, y: -10.0, hp: 0.45, dist: 21.0, fourSkills: true, skills: [2.1, 0, 16.4, 0], spell: 65.0 },
    { id: 4, name: "Fanny", heroId: 17, x: 35.0, y: 28.0, hp: 0.60, dist: 45.0, fourSkills: false, skills: [0, 1.2, 0], spell: 12.0 },
    { id: 5, name: "Lunox", heroId: 68, x: -25.0, y: -18.0, hp: 0.82, dist: 31.5, fourSkills: true, skills: [0, 3.4, 0, 19.5], spell: 0 }
  ],
  isStealth: false,
  isCollapsed: false,
  isDraggingPuck: false,
  isDraggingWindow: false,
  fps: 120,
  latency: 0.4
};

// DOM References
const dom = {
  canvas: document.getElementById('gameCanvas'),
  ctx: document.getElementById('gameCanvas')?.getContext('2d'),
  miniCanvas: document.getElementById('miniSandboxCanvas'),
  miniCtx: document.getElementById('miniSandboxCanvas')?.getContext('2d'),
  topCdBar: document.getElementById('topCdBarContainer'),
  puck: document.getElementById('floatingTriggerPuck'),
  modMenu: document.getElementById('imguiModMenu'),
  modMenuHeader: document.getElementById('modMenuHeader'),
  modMenuBody: document.getElementById('modMenuContentBody'),
  sidebar: document.getElementById('designerSidebar'),
  modal: document.getElementById('modalExportXml'),
  xmlOutput: document.getElementById('xmlOutputBlock'),
  toast: document.getElementById('toastNotification')
};

// =========================================================================
// INITIALIZATION
// =========================================================================
async function init() {
  await fetchConfig();
  await fetchDesign();
  initUIBindings();
  initDraggables();
  renderTopCdBar();
  startSimulationLoop();
  showToast("✓ Studio Ready: Connected to VeminsESP Engine");
}

async function fetchConfig() {
  try {
    const res = await fetch('/api/config');
    if (res.ok) {
      const data = await res.json();
      if (data.minimap) {
        state.config.minimap.posX = data.minimap.pos_x ?? state.config.minimap.posX;
        state.config.minimap.posY = data.minimap.pos_y ?? state.config.minimap.posY;
        state.config.minimap.width = data.minimap.width ?? state.config.minimap.width;
        state.config.minimap.height = data.minimap.height ?? state.config.minimap.height;
        state.config.minimap.rotationDegrees = data.minimap.rotation_degrees ?? state.config.minimap.rotationDegrees;
        state.config.minimap.radarZoom = data.minimap.radar_zoom ?? state.config.minimap.radarZoom;
        state.config.minimap.invertY = data.minimap.invert_y ?? state.config.minimap.invertY;
        state.config.minimap.autoCampFlip = data.minimap.auto_camp_flip ?? state.config.minimap.autoCampFlip;
      }
      syncInputsFromConfig();
    }
  } catch (e) {
    console.warn("Using default config:", e);
  }
}

async function fetchDesign() {
  try {
    const res = await fetch('/api/design');
    if (res.ok) {
      const data = await res.json();
      Object.assign(state.design, data);
      applyDesignToCss();
    }
  } catch (e) {
    console.warn("Using default design:", e);
  }
}

// =========================================================================
// UI CONTROLS BINDING
// =========================================================================
function initUIBindings() {
  // Mode switcher
  document.getElementById('btnViewDual')?.addEventListener('click', () => setViewMode('dual'));
  document.getElementById('btnViewOverlay')?.addEventListener('click', () => setViewMode('overlay'));
  document.getElementById('btnViewFloating')?.addEventListener('click', () => setViewMode('floating'));
  document.getElementById('btnViewDashboard')?.addEventListener('click', () => setViewMode('dashboard'));

  // Header actions
  document.getElementById('btnToggleInspector')?.addEventListener('click', toggleDesignerSidebar);
  document.getElementById('btnCloseInspector')?.addEventListener('click', toggleDesignerSidebar);
  document.getElementById('btnExportXml')?.addEventListener('click', openExportXmlModal);
  document.getElementById('btnCloseModal')?.addEventListener('click', closeExportXmlModal);
  document.getElementById('btnCopyXml')?.addEventListener('click', copyXmlToClipboard);
  document.getElementById('btnFeedbackModal')?.addEventListener('click', () => {
    toggleDesignerSidebar(true);
    document.getElementById('txtDesignFeedback')?.focus();
  });

  // 1-Tap 180° Map Flip button
  document.getElementById('btnModFlipMap')?.addEventListener('click', () => {
    const cur = state.config.minimap.rotationDegrees;
    const next = (cur >= 225 && cur <= 360) ? 135 : 315;
    state.config.minimap.rotationDegrees = next;
    state.localHero.camp = (next === 315) ? 1 : 2;
    syncInputsFromConfig();
    showToast(`⟲ Minimap rotation flipped to ${next}° (Camp ${state.localHero.camp})`);
  });

  // Minimize / Collapse
  document.getElementById('btnModMinimize')?.addEventListener('click', () => {
    state.isCollapsed = !state.isCollapsed;
    const body = dom.modMenuBody;
    const btn = document.getElementById('btnModMinimize');
    if (body) {
      body.style.display = state.isCollapsed ? 'none' : 'flex';
      btn.textContent = state.isCollapsed ? '□' : '—';
    }
  });

  // Stealth Ghost Mode
  document.getElementById('btnModStealth')?.addEventListener('click', toggleStealthMode);

  // Close to Puck
  document.getElementById('btnModClose')?.addEventListener('click', () => {
    if (dom.modMenu) dom.modMenu.style.display = 'none';
    if (dom.puck) dom.puck.style.display = 'flex';
  });

  // Puck Click
  dom.puck?.addEventListener('click', (e) => {
    if (state.isDraggingPuck) return;
    if (dom.modMenu) dom.modMenu.style.display = 'flex';
  });

  // Tabs
  document.querySelectorAll('.imgui-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.imgui-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const targetId = 'panel' + btn.dataset.tab.charAt(0).toUpperCase() + btn.dataset.tab.slice(1);
      document.getElementById(targetId)?.classList.add('active');
    });
  });

  // Presets
  document.getElementById('btnPresetStd')?.addEventListener('click', () => applyPreset('std'));
  document.getElementById('btnPresetDiamond')?.addEventListener('click', () => applyPreset('diamond'));
  document.getElementById('btnPresetNotch')?.addEventListener('click', () => applyPreset('notch'));
  document.getElementById('btnPresetWide')?.addEventListener('click', () => applyPreset('wide'));
  document.getElementById('btnForce120')?.addEventListener('click', () => {
    showToast("⚡ Locked Display Refresh Rate to 120Hz");
  });

  // Quick Angles
  document.querySelectorAll('.angle-btn').forEach(b => {
    b.addEventListener('click', () => {
      const ang = parseInt(b.dataset.angle, 10);
      state.config.minimap.rotationDegrees = ang;
      syncInputsFromConfig();
    });
  });

  // Step buttons (- / +)
  document.querySelectorAll('.step-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const step = parseInt(btn.dataset.step, 10);
      const target = document.getElementById(btn.dataset.target);
      if (target) {
        target.value = Math.max(parseInt(target.min, 10), Math.min(parseInt(target.max, 10), parseInt(target.value, 10) + step));
        target.dispatchEvent(new Event('input'));
      }
    });
  });

  // Sliders binding
  bindSlider('sbMinimapX', 'valMinimapX', '', v => state.config.minimap.posX = v);
  bindSlider('sbMinimapY', 'valMinimapY', '', v => state.config.minimap.posY = v);
  bindSlider('sbMinimapSize', 'valMinimapSize', '', v => state.config.minimap.width = state.config.minimap.height = v);
  bindSlider('sbMinimapAlpha', 'valMinimapAlpha', '%', v => state.config.minimap.alpha = v / 100);
  bindSlider('sbMinimapRotation', 'valMinimapRotation', '°', v => state.config.minimap.rotationDegrees = v);
  bindSlider('sbMinimapZoom', 'valMinimapZoom', '%', v => state.config.minimap.radarZoom = v / 100);
  bindSlider('sbHeroSize', 'valHeroSize', '', v => state.config.minimap.heroIconSize = v);

  bindSlider('sbTopCdBarY', 'valTopCdBarY', '', v => {
    state.config.camera.topCdBarPosY = v;
    if (dom.topCdBar) dom.topCdBar.style.top = `${v}px`;
  });
  bindSlider('sbTopCdBarScale', 'valTopCdBarScale', '%', v => {
    state.config.camera.topCdBarScale = v / 100;
    if (dom.topCdBar) dom.topCdBar.style.transform = `translateX(-50%) scale(${v / 100})`;
  });

  bindOffsetSlider('sbCamOffsetX', 'valCamOffsetX', v => state.config.camera.camOffsetX = v);
  bindOffsetSlider('sbCamOffsetY', 'valCamOffsetY', v => state.config.camera.camOffsetY = v);
  bindSlider('sbHudLift', 'valHudLift', '', v => state.config.camera.hudOffsetY = v);
  bindSlider('sbHpScale', 'valHpScale', '%', v => state.config.camera.hpBarScale = v / 100);

  // Switches
  bindSwitch('switchInvertY', v => state.config.minimap.invertY = v);
  bindSwitch('switchAutoCampFlip', v => state.config.minimap.autoCampFlip = v);
  bindSwitch('switchTopCdBar', v => {
    state.config.camera.showTopCdBar = v;
    if (dom.topCdBar) dom.topCdBar.style.display = v ? 'flex' : 'none';
  });

  // Layers switches
  bindSwitch('swEnemies', v => state.config.layers.enemies = v);
  bindSwitch('swAllies', v => state.config.layers.allies = v);
  bindSwitch('swArrows', v => state.config.layers.arrows = v);
  bindSwitch('swMinions', v => state.config.layers.minions = v);
  bindSwitch('swMonsters', v => state.config.layers.monsters = v);
  bindSwitch('swHpBars', v => state.config.layers.hpBars = v);
  bindSwitch('swSkillCd', v => state.config.layers.skillCd = v);
  bindSwitch('swDistance', v => state.config.layers.distance = v);
  bindSwitch('swEdgeRadar', v => state.config.layers.edgeRadar = v);

  // Save config action
  document.getElementById('btnSaveSysConfig')?.addEventListener('click', saveConfigToServer);
  document.getElementById('btnResetSysDefaults')?.addEventListener('click', resetToFactoryDefaults);

  // Studio Theme Selector
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyThemePreset(btn.dataset.theme);
    });
  });

  // Live Color Pickers
  bindColorPicker('colWindowBg', '--window-bg', 'windowBg');
  bindColorPicker('colHeaderBg', '--header-bg', 'headerBg');
  bindColorPicker('colBorder', '--border-color', 'borderColor');
  bindColorPicker('colAccentCyan', '--accent-cyan', 'accentCyan');
  bindColorPicker('colAccentGreen', '--accent-green', 'accentGreen');
  bindColorPicker('colButtonBg', '--button-bg', 'buttonBg');
  bindColorPicker('colTextPrimary', '--text-primary', 'textPrimary');
  bindColorPicker('colTextSecondary', '--text-secondary', 'textSecondary');

  // Studio Dimension Sliders
  document.getElementById('sbWinWidth')?.addEventListener('input', (e) => {
    const val = e.target.value;
    document.getElementById('lblWinWidth').textContent = `${val}px`;
    document.documentElement.style.setProperty('--card-width', `${val}px`);
    state.design.cardWidth = parseInt(val, 10);
  });

  document.getElementById('sbHeaderHeight')?.addEventListener('input', (e) => {
    const val = e.target.value;
    document.getElementById('lblHeaderHeight').textContent = `${val}px`;
    document.documentElement.style.setProperty('--header-height', `${val}px`);
    state.design.headerHeight = parseInt(val, 10);
  });

  document.getElementById('sbRadius')?.addEventListener('input', (e) => {
    const val = e.target.value;
    document.getElementById('lblRadius').textContent = `${val}px`;
    document.documentElement.style.setProperty('--border-radius', `${val}px`);
    state.design.borderRadius = parseInt(val, 10);
  });

  document.getElementById('sbFontSize')?.addEventListener('input', (e) => {
    const val = e.target.value;
    document.getElementById('lblFontSize').textContent = `${val}px`;
    document.documentElement.style.setProperty('--font-size', `${val}px`);
    state.design.fontSize = parseInt(val, 10);
  });

  // LO's Feedback submission
  document.getElementById('btnSubmitFeedback')?.addEventListener('click', submitFeedback);
  document.getElementById('btnSaveDesignStudio')?.addEventListener('click', saveDesignToServer);
  document.getElementById('btnResetDesignStudio')?.addEventListener('click', resetDesignToDefault);
}

function bindSlider(id, labelId, unit, cb) {
  const el = document.getElementById(id);
  const lbl = document.getElementById(labelId);
  if (!el || !lbl) return;
  el.addEventListener('input', () => {
    const val = parseInt(el.value, 10);
    lbl.textContent = `${val}${unit}`;
    cb(val);
  });
}

function bindOffsetSlider(id, labelId, cb) {
  const el = document.getElementById(id);
  const lbl = document.getElementById(labelId);
  if (!el || !lbl) return;
  el.addEventListener('input', () => {
    const offset = parseInt(el.value, 10) - 200;
    lbl.textContent = offset.toString();
    cb(offset);
  });
}

function bindSwitch(id, cb) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('change', () => cb(el.checked));
}

function bindColorPicker(id, cssVar, designKey) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('input', () => {
    document.documentElement.style.setProperty(cssVar, el.value);
    state.design[designKey] = el.value;
  });
}

// =========================================================================
// DRAGGING WINDOW & PUCK
// =========================================================================
function initDraggables() {
  const mod = dom.modMenu;
  const header = dom.modMenuHeader;
  const puck = dom.puck;
  const screen = document.getElementById('deviceScreen');

  let startX = 0, startY = 0;
  let initLeft = 0, initTop = 0;

  // Window drag
  header?.addEventListener('mousedown', (e) => {
    state.isDraggingWindow = true;
    startX = e.clientX;
    startY = e.clientY;
    initLeft = mod.offsetLeft;
    initTop = mod.offsetTop;
    document.addEventListener('mousemove', onWindowDrag);
    document.addEventListener('mouseup', onWindowDragEnd);
  });

  function onWindowDrag(e) {
    if (!state.isDraggingWindow) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    mod.style.left = `${Math.max(0, Math.min(screen.clientWidth - mod.clientWidth, initLeft + dx))}px`;
    mod.style.top = `${Math.max(0, Math.min(screen.clientHeight - 40, initTop + dy))}px`;
  }

  function onWindowDragEnd() {
    state.isDraggingWindow = false;
    document.removeEventListener('mousemove', onWindowDrag);
    document.removeEventListener('mouseup', onWindowDragEnd);
  }

  // Puck drag
  puck?.addEventListener('mousedown', (e) => {
    state.isDraggingPuck = false;
    startX = e.clientX;
    startY = e.clientY;
    initLeft = puck.offsetLeft;
    initTop = puck.offsetTop;

    function onPuckMove(ev) {
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;
      if (Math.hypot(dx, dy) > 4) {
        state.isDraggingPuck = true;
      }
      puck.style.left = `${Math.max(0, Math.min(screen.clientWidth - puck.clientWidth, initLeft + dx))}px`;
      puck.style.top = `${Math.max(0, Math.min(screen.clientHeight - puck.clientHeight, initTop + dy))}px`;
    }

    function onPuckUp() {
      document.removeEventListener('mousemove', onPuckMove);
      document.removeEventListener('mouseup', onPuckUp);
      // Snap to nearest edge
      const mid = screen.clientWidth / 2;
      const curLeft = puck.offsetLeft;
      puck.style.left = (curLeft < mid) ? '6px' : `${screen.clientWidth - puck.clientWidth - 6}px`;
    }

    document.addEventListener('mousemove', onPuckMove);
    document.addEventListener('mouseup', onPuckUp);
  });
}

// =========================================================================
// TOP CD BAR (DYNAMIC 3 VS 4 ABILITIES)
// =========================================================================
function renderTopCdBar() {
  const container = dom.topCdBar;
  if (!container) return;
  container.innerHTML = '';

  state.enemies.forEach(enemy => {
    const card = document.createElement('div');
    card.className = `enemy-card ${enemy.fourSkills ? 'four-skills' : ''}`;

    // Avatar + name
    const topRow = document.createElement('div');
    topRow.className = 'card-hero-row';
    topRow.innerHTML = `
      <div class="hero-avatar-circle">
        <img src="/assets/heroes/${enemy.heroId}.png" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'20\\' height=\\'20\\'><rect fill=\\'%23333\\' width=\\'20\\' height=\\'20\\'/><text fill=\\'%23fff\\' font-size=\\'10\\' x=\\'5\\' y=\\'15\\'>${enemy.name[0]}</text></svg>'">
      </div>
      <div class="card-hero-info">
        <div class="hero-name-label">${enemy.name}</div>
        <div class="hp-bar-track">
          <div class="hp-bar-fill" style="width: ${enemy.hp * 100}%"></div>
        </div>
      </div>
    `;
    card.appendChild(topRow);

    // Skills row
    const skillsRow = document.createElement('div');
    skillsRow.className = 'card-skills-row';

    // Render skill badges: exactly 3 or 4 skills depending on hero
    enemy.skills.forEach((cd, idx) => {
      const badge = document.createElement('div');
      const isUlt = (idx === enemy.skills.length - 1);
      badge.className = `skill-badge ${isUlt ? 'ult' : ''}`;
      badge.innerHTML = `
        <img src="/assets/skills/${enemy.heroId}/skill${idx + 1}.png" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'14\\' height=\\'14\\'><rect fill=\\'%23222\\' width=\\'14\\' height=\\'14\\'/><text fill=\\'%2300e5ff\\' font-size=\\'8\\' x=\\'4\\' y=\\'10\\'>${idx + 1}</text></svg>'">
        ${cd > 0 ? `<div class="skill-cd-sweep">${cd.toFixed(0)}</div>` : ''}
      `;
      skillsRow.appendChild(badge);
    });

    // Battle Spell badge
    const spellBadge = document.createElement('div');
    spellBadge.className = 'skill-badge spell';
    spellBadge.innerHTML = `
      <img src="/assets/skills/${enemy.heroId}/spell.png" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'14\\' height=\\'14\\'><rect fill=\\'%23112233\\' width=\\'14\\' height=\\'14\\'/><text fill=\\'%23ffd600\\' font-size=\\'8\\' x=\\'3\\' y=\\'10\\'>S</text></svg>'">
      ${enemy.spell > 0 ? `<div class="skill-cd-sweep">${enemy.spell.toFixed(0)}</div>` : ''}
    `;
    skillsRow.appendChild(spellBadge);

    card.appendChild(skillsRow);
    container.appendChild(card);
  });
}

// =========================================================================
// GAME CANVAS RENDERING ENGINE
// =========================================================================
function startSimulationLoop() {
  let lastTime = performance.now();

  function loop(currentTime) {
    const dt = (currentTime - lastTime) / 1000;
    lastTime = currentTime;

    // Simulate cooldown countdowns
    state.enemies.forEach(e => {
      e.skills = e.skills.map(cd => Math.max(0, cd - dt * 0.5));
      if (e.spell > 0) e.spell = Math.max(0, e.spell - dt * 0.5);
    });

    renderCanvas();
    renderMiniCanvas();

    requestAnimationFrame(loop);
  }

  requestAnimationFrame(loop);
}

function renderCanvas() {
  const canvas = dom.canvas;
  const ctx = dom.ctx;
  if (!canvas || !ctx) return;

  const W = canvas.width;
  const H = canvas.height;

  // 1. Clear & draw simulated MLBB River/Grass map background
  ctx.fillStyle = "#0A0D14";
  ctx.fillRect(0, 0, W, H);

  // Subtle tactical grid
  ctx.strokeStyle = "#141824";
  ctx.lineWidth = 1;
  const gridSize = 60;
  for (let x = 0; x < W; x += gridSize) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let y = 0; y < H; y += gridSize) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  // 2. Render 3D In-World Combat HUD over enemies
  const cam = state.config.camera;
  const layers = state.config.layers;
  const screenCx = W / 2 + cam.camOffsetX;
  const screenCy = H / 2 + cam.camOffsetY;

  state.enemies.forEach(enemy => {
    // 45° Axonometric Projection (fixed yaw decoupled from minimap rotation)
    const ISO_FACTOR = 0.70710678;
    const dx = enemy.x - state.localHero.x;
    const dy = enemy.y - state.localHero.y;

    const isoX = (dx - dy) * ISO_FACTOR;
    const isoY = (dx + dy) * ISO_FACTOR;

    const screenX = screenCx + (isoX * cam.scaleX);
    const screenY = screenCy - (isoY * cam.scaleY) - cam.hudOffsetY;

    // Draw hero dot on ground
    ctx.fillStyle = "#FF3B47";
    ctx.beginPath();
    ctx.arc(screenX, screenY + cam.hudOffsetY, 12, 0, Math.PI * 2);
    ctx.fill();

    // Draw in-world overhead HP bar & skill pills
    if (layers.hpBars) {
      const barW = 80 * cam.hpBarScale;
      const barH = 7;
      const barX = screenX - barW / 2;
      const barY = screenY;

      // Label (Name + Distance)
      ctx.fillStyle = "#FFF";
      ctx.font = "bold 13px 'JetBrains Mono'";
      ctx.textAlign = "center";
      const distTxt = layers.distance ? ` [${enemy.dist.toFixed(1)}m]` : '';
      ctx.fillText(`${enemy.name}${distTxt}`, screenX, barY - 6);

      // HP Bar Track
      ctx.fillStyle = "rgba(0,0,0,0.8)";
      ctx.fillRect(barX, barY, barW, barH);
      ctx.strokeStyle = "#3F4152";
      ctx.strokeRect(barX, barY, barW, barH);

      // HP Fill
      ctx.fillStyle = enemy.hp > 0.3 ? "#00E676" : "#FF3B47";
      ctx.fillRect(barX + 1, barY + 1, (barW - 2) * enemy.hp, barH - 2);

      // Cooldown pill indicators
      if (layers.skillCd) {
        const pillY = barY + barH + 4;
        const count = enemy.skills.length;
        const pillW = 12;
        const totalW = count * 14;
        let startPillX = screenX - totalW / 2;

        enemy.skills.forEach((cd, idx) => {
          ctx.fillStyle = cd > 0 ? "#FFD600" : "#00E5FF";
          ctx.beginPath();
          ctx.arc(startPillX + idx * 14 + 6, pillY + 6, 5, 0, Math.PI * 2);
          ctx.fill();
        });
      }
    }
  });

  // 3. Render Top-Left Minimap Layer
  renderMinimapCanvas(ctx);
}

function renderMinimapCanvas(ctx) {
  const m = state.config.minimap;
  const layers = state.config.layers;

  ctx.save();
  ctx.translate(m.posX, m.posY);

  // Background box
  ctx.fillStyle = `rgba(14, 16, 23, ${m.alpha})`;
  ctx.fillRect(0, 0, m.width, m.height);
  ctx.strokeStyle = "#00E5FF";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(0, 0, m.width, m.height);

  // Rotate about minimap center
  const cx = m.width / 2;
  const cy = m.height / 2;
  ctx.translate(cx, cy);

  // Auto-camp rotation logic
  let rot = m.rotationDegrees;
  if (m.autoCampFlip) {
    rot = (state.localHero.camp === 1) ? 315 : 135;
  }
  ctx.rotate((rot * Math.PI) / 180);

  // Minimap Arena Border (rotated square/diamond)
  const arenaSize = (m.width * 0.85) * (m.radarZoom / 2.0);
  ctx.strokeStyle = "rgba(0, 229, 255, 0.35)";
  ctx.strokeRect(-arenaSize / 2, -arenaSize / 2, arenaSize, arenaSize);

  // River line
  ctx.strokeStyle = "rgba(0, 229, 255, 0.2)";
  ctx.beginPath();
  ctx.moveTo(-arenaSize / 2, arenaSize / 2);
  ctx.lineTo(arenaSize / 2, -arenaSize / 2);
  ctx.stroke();

  // Local Hero (Center Blue Dot)
  ctx.fillStyle = "#00E5FF";
  ctx.beginPath();
  ctx.arc(0, 0, m.heroIconSize * 0.7, 0, Math.PI * 2);
  ctx.fill();

  // Local direction arrow
  if (layers.arrows) {
    ctx.strokeStyle = "#00E5FF";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(15, -15);
    ctx.stroke();
  }

  // Enemy Hero Dots on Minimap
  if (layers.enemies) {
    state.enemies.forEach(e => {
      const normX = (e.x / 52.0) * (arenaSize / 2);
      const normY = (e.y / 52.0) * (arenaSize / 2) * (m.invertY ? -1 : 1);

      ctx.fillStyle = "#FF3B47";
      ctx.beginPath();
      ctx.arc(normX, normY, m.heroIconSize * 0.6, 0, Math.PI * 2);
      ctx.fill();

      // Mini Hero icon letter
      ctx.fillStyle = "#FFF";
      ctx.font = "bold 9px 'JetBrains Mono'";
      ctx.textAlign = "center";
      ctx.fillText(e.name[0], normX, normY + 3);

      // Enemy velocity arrow
      if (layers.arrows) {
        ctx.strokeStyle = "#FF3B47";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(normX, normY);
        ctx.lineTo(normX + 10, normY + (m.invertY ? -10 : 10));
        ctx.stroke();
      }
    });
  }

  ctx.restore();
}

function renderMiniCanvas() {
  const canvas = dom.miniCanvas;
  const ctx = dom.miniCtx;
  if (!canvas || !ctx) return;

  ctx.fillStyle = "#0D0F16";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = "rgba(0, 229, 255, 0.4)";
  ctx.strokeRect(10, 10, canvas.width - 20, canvas.height - 20);

  ctx.fillStyle = "#00E5FF";
  ctx.font = "10px 'JetBrains Mono'";
  ctx.fillText(`ROTATION: ${state.config.minimap.rotationDegrees}°`, 20, 30);
  ctx.fillText(`POS: (${state.config.minimap.posX}, ${state.config.minimap.posY})`, 20, 50);
  ctx.fillText(`SIZE: ${state.config.minimap.width}x${state.config.minimap.height}`, 20, 70);
  ctx.fillText(`AUTO-CAMP FLIP: ${state.config.minimap.autoCampFlip ? 'ON (315°/135°)' : 'OFF'}`, 20, 90);
}

// =========================================================================
// HAND-DESIGN STUDIO / THEME ENGINE
// =========================================================================
function applyThemePreset(theme) {
  document.body.className = `theme-${theme.replace('_', '-')}`;
  state.design.theme = theme;

  const presets = {
    imgui_slate: { bg: '#1E1E24', hdr: '#2A2B36', bdr: '#3F4152', cyan: '#00E5FF', btn: '#2A2C38' },
    cyber_neon: { bg: '#0B0E17', hdr: '#141A29', bdr: '#00E5FF', cyan: '#00FFFF', btn: '#162033' },
    oled_midnight: { bg: '#000000', hdr: '#121212', bdr: '#262626', cyan: '#00E5FF', btn: '#1A1A1A' },
    blood_crimson: { bg: '#1A0D0E', hdr: '#2B1214', bdr: '#5C1E23', cyan: '#FF3B47', btn: '#331618' },
    matrix_green: { bg: '#0A140D', hdr: '#122417', bdr: '#1F4528', cyan: '#00FF66', btn: '#16301D' },
    titanium: { bg: '#25262B', hdr: '#2E3036', bdr: '#484B54', cyan: '#70C0E8', btn: '#35373E' }
  };

  const p = presets[theme];
  if (p) {
    document.getElementById('colWindowBg').value = p.bg;
    document.getElementById('colHeaderBg').value = p.hdr;
    document.getElementById('colBorder').value = p.bdr;
    document.getElementById('colAccentCyan').value = p.cyan;
    document.getElementById('colButtonBg').value = p.btn;

    document.documentElement.style.setProperty('--window-bg', p.bg);
    document.documentElement.style.setProperty('--header-bg', p.hdr);
    document.documentElement.style.setProperty('--border-color', p.bdr);
    document.documentElement.style.setProperty('--accent-cyan', p.cyan);
    document.documentElement.style.setProperty('--button-bg', p.btn);
  }
}

function applyDesignToCss() {
  const d = state.design;
  const root = document.documentElement;
  root.style.setProperty('--window-bg', d.windowBg);
  root.style.setProperty('--header-bg', d.headerBg);
  root.style.setProperty('--border-color', d.borderColor);
  root.style.setProperty('--accent-cyan', d.accentCyan);
  root.style.setProperty('--accent-green', d.accentGreen);
  root.style.setProperty('--button-bg', d.buttonBg);
  root.style.setProperty('--text-primary', d.textPrimary);
  root.style.setProperty('--text-secondary', d.textSecondary);
  root.style.setProperty('--card-width', `${d.cardWidth}px`);
  root.style.setProperty('--header-height', `${d.headerHeight}px`);
  root.style.setProperty('--border-radius', `${d.borderRadius}px`);
  root.style.setProperty('--font-size', `${d.fontSize}px`);

  // Sync color pickers
  document.getElementById('colWindowBg').value = d.windowBg;
  document.getElementById('colHeaderBg').value = d.headerBg;
  document.getElementById('colBorder').value = d.borderColor;
  document.getElementById('colAccentCyan').value = d.accentCyan;
  document.getElementById('colAccentGreen').value = d.accentGreen;
  document.getElementById('colButtonBg').value = d.buttonBg;
  document.getElementById('colTextPrimary').value = d.textPrimary;
  document.getElementById('colTextSecondary').value = d.textSecondary;

  document.getElementById('sbWinWidth').value = d.cardWidth;
  document.getElementById('lblWinWidth').textContent = `${d.cardWidth}px`;
  document.getElementById('sbHeaderHeight').value = d.headerHeight;
  document.getElementById('lblHeaderHeight').textContent = `${d.headerHeight}px`;
  document.getElementById('sbRadius').value = d.borderRadius;
  document.getElementById('lblRadius').textContent = `${d.borderRadius}px`;
  document.getElementById('sbFontSize').value = d.fontSize;
  document.getElementById('lblFontSize').textContent = `${d.fontSize}px`;
}

function toggleDesignerSidebar(forceOpen) {
  const sidebar = dom.sidebar;
  if (!sidebar) return;
  if (typeof forceOpen === 'boolean') {
    sidebar.classList.toggle('open', forceOpen);
  } else {
    sidebar.classList.toggle('open');
  }
}

async function submitFeedback() {
  const txt = document.getElementById('txtDesignFeedback')?.value.trim();
  if (!txt) {
    showToast("⚠️ Please enter your design notes first");
    return;
  }

  try {
    const payload = {
      timestamp: new Date().toISOString(),
      theme: state.design.theme,
      notes: txt,
      currentConfig: state.config,
      currentDesign: state.design
    };
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast("🚀 Feedback submitted to ENI! I will integrate your changes.");
      document.getElementById('txtDesignFeedback').value = '';
    } else {
      showToast("❌ Failed to send feedback");
    }
  } catch (e) {
    showToast(`❌ Error: ${e.message}`);
  }
}

async function saveDesignToServer() {
  try {
    const res = await fetch('/api/design', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.design)
    });
    if (res.ok) {
      showToast("💾 Design saved successfully!");
    }
  } catch (e) {
    showToast(`❌ Save error: ${e.message}`);
  }
}

async function saveConfigToServer() {
  try {
    const payload = {
      screen: { width: 2400.0, height: 1080.0 },
      minimap: {
        pos_x: state.config.minimap.posX,
        pos_y: state.config.minimap.posY,
        width: state.config.minimap.width,
        height: state.config.minimap.height,
        rotation_degrees: state.config.minimap.rotationDegrees,
        radar_zoom: state.config.minimap.radarZoom,
        alpha: state.config.minimap.alpha,
        invert_y: state.config.minimap.invertY,
        auto_camp_flip: state.config.minimap.autoCampFlip
      },
      camera: {
        scale_x: state.config.camera.scaleX,
        scale_y: state.config.camera.scaleY,
        hud_offset_y: state.config.camera.hudOffsetY,
        cam_offset_x: state.config.camera.camOffsetX,
        cam_offset_y: state.config.camera.camOffsetY,
        show_top_cd_bar: state.config.camera.showTopCdBar,
        top_cd_bar_pos_y: state.config.camera.topCdBarPosY,
        top_cd_bar_scale: state.config.camera.topCdBarScale
      }
    };
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast("✓ Config saved to minimap_config.json");
    }
  } catch (e) {
    showToast(`❌ Error saving config: ${e.message}`);
  }
}

function openExportXmlModal() {
  const d = state.design;
  const xml = `<!-- res/values/colors.xml -->
<color name="imgui_bg">${d.windowBg}</color>
<color name="imgui_header">${d.headerBg}</color>
<color name="imgui_border">${d.borderColor}</color>
<color name="imgui_accent_cyan">${d.accentCyan}</color>
<color name="imgui_button">${d.buttonBg}</color>
<color name="imgui_text_primary">${d.textPrimary}</color>
<color name="imgui_text_secondary">${d.textSecondary}</color>

<!-- res/drawable/bg_imgui_window.xml -->
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="@color/imgui_bg" />
    <stroke android:width="1dp" android:color="@color/imgui_border" />
    <corners android:radius="${d.borderRadius}dp" />
</shape>

<!-- layout_floating_mod_menu.xml snippet -->
<LinearLayout
    android:id="@+id/modMenuCardRoot"
    android:layout_width="${d.cardWidth}dp"
    android:layout_height="wrap_content"
    android:background="@drawable/bg_imgui_window">
    <LinearLayout
        android:id="@+id/modMenuHeader"
        android:layout_height="${d.headerHeight}dp"
        android:background="@drawable/bg_imgui_header" />
</LinearLayout>`;

  if (dom.xmlOutput) dom.xmlOutput.textContent = xml;
  if (dom.modal) dom.modal.classList.add('show');
}

function closeExportXmlModal() {
  if (dom.modal) dom.modal.classList.remove('show');
}

function copyXmlToClipboard() {
  const xml = dom.xmlOutput?.textContent;
  if (xml) {
    navigator.clipboard.writeText(xml);
    showToast("📋 XML copied to clipboard!");
  }
}

function resetDesignToDefault() {
  applyThemePreset('imgui_slate');
  showToast("↺ Reset design to Dear ImGui Slate");
}

function resetToFactoryDefaults() {
  state.config.minimap = {
    posX: 0,
    posY: 0,
    width: 342,
    height: 342,
    rotationDegrees: 315,
    radarZoom: 2.0,
    alpha: 0.0,
    invertY: true,
    autoCampFlip: true,
    heroIconSize: 16
  };
  syncInputsFromConfig();
  showToast("↺ Reset minimap to LO's verified working settings");
}

function applyPreset(name) {
  if (name === 'std') {
    state.config.minimap.posX = 0;
    state.config.minimap.posY = 0;
    state.config.minimap.width = 342;
    state.config.minimap.height = 342;
    state.config.minimap.rotationDegrees = 315;
  } else if (name === 'diamond') {
    state.config.minimap.posX = 75;
    state.config.minimap.posY = 15;
    state.config.minimap.width = 340;
    state.config.minimap.height = 340;
    state.config.minimap.rotationDegrees = 45;
  } else if (name === 'notch') {
    state.config.minimap.posX = 110;
    state.config.minimap.posY = 20;
    state.config.minimap.width = 280;
    state.config.minimap.height = 280;
  } else if (name === 'wide') {
    state.config.minimap.posX = 120;
    state.config.minimap.posY = 25;
    state.config.minimap.width = 380;
    state.config.minimap.height = 380;
  }
  syncInputsFromConfig();
  showToast(`Loaded Preset: ${name.toUpperCase()}`);
}

function syncInputsFromConfig() {
  const m = state.config.minimap;
  setSliderVal('sbMinimapX', 'valMinimapX', m.posX, '');
  setSliderVal('sbMinimapY', 'valMinimapY', m.posY, '');
  setSliderVal('sbMinimapSize', 'valMinimapSize', m.width, '');
  setSliderVal('sbMinimapAlpha', 'valMinimapAlpha', Math.round(m.alpha * 100), '%');
  setSliderVal('sbMinimapRotation', 'valMinimapRotation', m.rotationDegrees, '°');
  setSliderVal('sbMinimapZoom', 'valMinimapZoom', Math.round(m.radarZoom * 100), '%');
  setSliderVal('sbHeroSize', 'valHeroSize', m.heroIconSize, '');

  const c = state.config.camera;
  setSliderVal('sbTopCdBarY', 'valTopCdBarY', c.topCdBarPosY, '');
  setSliderVal('sbTopCdBarScale', 'valTopCdBarScale', Math.round(c.topCdBarScale * 100), '%');
  setOffsetVal('sbCamOffsetX', 'valCamOffsetX', c.camOffsetX);
  setOffsetVal('sbCamOffsetY', 'valCamOffsetY', c.camOffsetY);
  setSliderVal('sbHudLift', 'valHudLift', c.hudOffsetY, '');
  setSliderVal('sbHpScale', 'valHpScale', Math.round(c.hpBarScale * 100), '%');

  document.getElementById('switchInvertY').checked = m.invertY;
  document.getElementById('switchAutoCampFlip').checked = m.autoCampFlip;
  document.getElementById('switchTopCdBar').checked = c.showTopCdBar;
}

function setSliderVal(id, lblId, val, unit) {
  const el = document.getElementById(id);
  const lbl = document.getElementById(lblId);
  if (el) el.value = val;
  if (lbl) lbl.textContent = `${val}${unit}`;
}

function setOffsetVal(id, lblId, offset) {
  const el = document.getElementById(id);
  const lbl = document.getElementById(lblId);
  if (el) el.value = offset + 200;
  if (lbl) lbl.textContent = offset.toString();
}

function toggleStealthMode() {
  state.isStealth = !state.isStealth;
  if (dom.modMenu) dom.modMenu.style.opacity = state.isStealth ? '0.08' : '1.0';
  if (dom.puck) dom.puck.style.opacity = state.isStealth ? '0.08' : '1.0';
  showToast(state.isStealth ? '👻 Stealth Ghost Mode (8% Opacity)' : '⚡ Restored Normal Opacity');
}

function setViewMode(mode) {
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  const vpGame = document.getElementById('viewportGame');
  const vpDash = document.getElementById('viewportDashboard');

  if (mode === 'dual') {
    document.getElementById('btnViewDual')?.classList.add('active');
    vpGame.style.display = 'flex';
    vpDash.style.display = 'flex';
  } else if (mode === 'overlay') {
    document.getElementById('btnViewOverlay')?.classList.add('active');
    vpGame.style.display = 'flex';
    vpDash.style.display = 'none';
  } else if (mode === 'floating') {
    document.getElementById('btnViewFloating')?.classList.add('active');
    vpGame.style.display = 'flex';
    vpDash.style.display = 'none';
    if (dom.modMenu) dom.modMenu.style.display = 'flex';
  } else if (mode === 'dashboard') {
    document.getElementById('btnViewDashboard')?.classList.add('active');
    vpGame.style.display = 'none';
    vpDash.style.display = 'flex';
  }
}

function showToast(msg) {
  const t = dom.toast;
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}

// Start
window.addEventListener('DOMContentLoaded', init);
