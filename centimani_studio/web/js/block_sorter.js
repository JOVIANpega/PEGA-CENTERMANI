// =========================================================================
// Centimani Studio - 極簡抽卡牌桌工作台 (Minimalist Poker Deck Sorter)
// 支援：左右雙欄工作台 (支援一鍵折疊右欄展開全螢幕大牌桌)、
//      極簡撲克小卡牌 (僅顯示 Phase X、Title、幾步)、
//      滑鼠碰觸微浮起抽卡感 (放大 1.15 倍)、
//      自適應卡片密度縮放 (自動支援 20 ~ 50+ Phase)、
//      流暢網格抓取插牌、右欄即時 Command │ Send 指令終端、
//      一鍵 Phase 1, 2, 3... 連續順編、全盤自動修復並呼叫 Excel 檢視。
// =========================================================================

const BS_STATE = {
  sheetName: '',
  origBlocks: [],
  currentBlocks: [],
  selectedIdx: 0,
  dragFromIdx: -1,
  dropTargetIdx: -1,
  dropPos: 'before', // 'before' | 'after'
  dragMode: 'swap',  // 'swap' (碰牌直接對調) | 'insert' (插牌移位)
  searchQuery: '',
  zoomMode: 'auto',  // 'auto' | 'small' | 'norm'
  isRightCollapsed: false,
  swappedAIdx: -1,
  swappedBIdx: -1,
};

function bsEscapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function bsSetDragMode(mode) {
  BS_STATE.dragMode = mode;
  const btnSwap = document.getElementById('bsDragModeSwap');
  const btnInsert = document.getElementById('bsDragModeInsert');
  if (btnSwap && btnInsert) {
    if (mode === 'swap') {
      btnSwap.style.background = '#2563EB';
      btnSwap.style.color = '#FFFFFF';
      btnSwap.style.border = 'none';
      btnInsert.style.background = '#FFFFFF';
      btnInsert.style.color = '#334155';
      btnInsert.style.border = '1px solid #CBD5E1';
    } else {
      btnInsert.style.background = '#2563EB';
      btnInsert.style.color = '#FFFFFF';
      btnInsert.style.border = 'none';
      btnSwap.style.background = '#FFFFFF';
      btnSwap.style.color = '#334155';
      btnSwap.style.border = '1px solid #CBD5E1';
    }
  }
}

function bsSetCardZoom(mode) {
  BS_STATE.zoomMode = mode;
  ['bsZoomAuto', 'bsZoomSmall', 'bsZoomNorm'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const isAct = (id === 'bsZoomAuto' && mode === 'auto') ||
                  (id === 'bsZoomSmall' && mode === 'small') ||
                  (id === 'bsZoomNorm' && mode === 'norm');
    el.style.background = isAct ? '#16A34A' : '#FFFFFF';
    el.style.color = isAct ? '#FFFFFF' : '#334155';
    el.style.border = isAct ? 'none' : '1px solid #CBD5E1';
  });
  bsApplyCardDimensions();
}

function bsApplyCardDimensions() {
  const listEl = document.getElementById('bsBlockList');
  if (!listEl) return;
  const count = BS_STATE.currentBlocks.length;
  let cardW = 105;
  let cardH = 110;

  if (BS_STATE.zoomMode === 'small') {
    cardW = 82;
    cardH = 88;
  } else if (BS_STATE.zoomMode === 'norm') {
    cardW = 110;
    cardH = 115;
  } else {
    // auto mode
    if (count > 28) {
      cardW = 80;
      cardH = 86;
    } else if (count > 14) {
      cardW = 94;
      cardH = 100;
    } else {
      cardW = 108;
      cardH = 112;
    }
  }

  const rootFontPx = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--app-font-size')) || 15;
  const fontScale = Math.max(1, rootFontPx / 15);
  cardW = Math.round(cardW * fontScale);
  cardH = Math.round(cardH * fontScale);

  listEl.style.setProperty('--bs-card-w', `${cardW}px`);
  listEl.style.setProperty('--bs-card-h', `${cardH}px`);
}

function bsToggleRightPane() {
  BS_STATE.isRightCollapsed = !BS_STATE.isRightCollapsed;
  const rightPane = document.getElementById('bsRightDetailPane');
  const leftPane = document.getElementById('bsDeckPane');
  const btn = document.getElementById('bsBtnCollapseRight');

  if (BS_STATE.isRightCollapsed) {
    if (rightPane) rightPane.style.display = 'none';
    if (leftPane) leftPane.style.flex = '1 1 100%';
    if (btn) {
      btn.innerHTML = '◀ 恢復雙欄';
      btn.style.background = '#16A34A';
    }
  } else {
    if (rightPane) rightPane.style.display = 'flex';
    if (leftPane) leftPane.style.flex = '1 1 50%';
    if (btn) {
      btn.innerHTML = '⛶ 全螢幕大牌桌';
      btn.style.background = '#0F172A';
    }
  }
  bsApplyCardDimensions();
}

async function openBlockSorterModal(preferredSheet = '') {
  if (!STATE.workspace || !STATE.workspace.stations) {
    alert('請先載入一份 TestFlow.xlsx 檔案後再開啟積木排序器。');
    return;
  }
  const stNames = Object.keys(STATE.workspace.stations || {});
  if (stNames.length === 0) {
    alert('此檔案沒有可排序的測試站工作表。');
    return;
  }
  const sel = document.getElementById('bsSheetSel');
  sel.innerHTML = stNames.map(n => `<option value="${n}">${n}</option>`).join('');

  const edSel = document.getElementById('editorSheetSel');
  if (preferredSheet && stNames.includes(preferredSheet)) {
    sel.value = preferredSheet;
  } else if (edSel && edSel.value && stNames.includes(edSel.value)) {
    sel.value = edSel.value;
  } else if (STATE.activeSheetFilter && STATE.activeSheetFilter !== 'ALL' && stNames.includes(STATE.activeSheetFilter)) {
    sel.value = STATE.activeSheetFilter;
  } else {
    sel.value = stNames[0];
  }

  const sInput = document.getElementById('bsSearchInput');
  if (sInput) sInput.value = '';
  BS_STATE.searchQuery = '';
  BS_STATE.selectedIdx = 0;

  const container = document.getElementById('modalBlockSorter');
  if (container) {
    container.style.display = 'flex';
    container.classList.add('open');
  }
  await bsLoadSheetBlocks();
}

function closeBlockSorterModal() {
  const container = document.getElementById('modalBlockSorter');
  if (container) {
    container.style.display = 'none';
    container.classList.remove('open');
  }
}

async function bsLoadSheetBlocks() {
  const sheet = document.getElementById('bsSheetSel').value;
  BS_STATE.sheetName = sheet;
  BS_STATE.selectedIdx = 0;
  try {
    const res = await fetch('/api/get_station_blocks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace: STATE.workspace, sheet_name: sheet })
    });
    const data = await res.json();
    if (data.status !== 'ok') {
      alert(data.message || '讀取積木區塊失敗');
      return;
    }
    BS_STATE.origBlocks = (data.blocks || []).map(b => JSON.parse(JSON.stringify(b)));
    BS_STATE.currentBlocks = (data.blocks || []).map(b => JSON.parse(JSON.stringify(b)));
    bsRenderBlocks();
  } catch (err) {
    console.error('bsLoadSheetBlocks error:', err);
    alert('讀取站位積木時發生錯誤：' + (err && err.message ? err.message : err));
  }
}

function bsResetOrder() {
  BS_STATE.currentBlocks = BS_STATE.origBlocks.map(b => JSON.parse(JSON.stringify(b)));
  BS_STATE.selectedIdx = 0;
  bsRenderBlocks();
}

function bsAutoSortByPhase() {
  const normalBlocks = [];
  const teardownBlocks = [];
  BS_STATE.currentBlocks.forEach(b => {
    if (b.is_teardown) {
      teardownBlocks.push(b);
    } else {
      normalBlocks.push(b);
    }
  });

  normalBlocks.sort((a, b) => {
    const pa = a.phase_num !== null && a.phase_num !== undefined ? a.phase_num : a.orig_idx;
    const pb = b.phase_num !== null && b.phase_num !== undefined ? b.phase_num : b.orig_idx;
    return pa - pb;
  });

  teardownBlocks.sort((a, b) => {
    const pa = a.phase_num !== null && a.phase_num !== undefined ? a.phase_num : a.orig_idx;
    const pb = b.phase_num !== null && b.phase_num !== undefined ? b.phase_num : b.orig_idx;
    return pa - pb;
  });

  BS_STATE.currentBlocks = [...normalBlocks, ...teardownBlocks];
  BS_STATE.selectedIdx = 0;
  bsRenderBlocks();
}

function bsFilterCards() {
  const sInput = document.getElementById('bsSearchInput');
  BS_STATE.searchQuery = (sInput ? sInput.value : '').trim().toLowerCase();
  bsRenderBlocks();
}

function bsMoveBlock(idx, delta) {
  const current = BS_STATE.currentBlocks[idx];
  if (current && (current.is_teardown || (current.phase_num !== null && current.phase_num >= 95))) return;
  const targetIdx = idx + delta;
  if (targetIdx < 0 || targetIdx >= BS_STATE.currentBlocks.length) return;
  const target = BS_STATE.currentBlocks[targetIdx];
  if (target && (target.is_teardown || (target.phase_num !== null && target.phase_num >= 95))) return;

  const item = BS_STATE.currentBlocks.splice(idx, 1)[0];
  BS_STATE.currentBlocks.splice(targetIdx, 0, item);
  BS_STATE.selectedIdx = targetIdx;
  bsTriggerSwapHighlight(idx, targetIdx);
  bsRenderBlocks();
}

function bsDirectJumpPhase(currentIdx, newOrderInput) {
  const current = BS_STATE.currentBlocks[currentIdx];
  if (current && (current.is_teardown || (current.phase_num !== null && current.phase_num >= 95))) return;
  const val = parseInt(newOrderInput, 10);
  if (isNaN(val)) return;

  // 计算允许的最大顺序 (排除 Phase >= 95 的固定尾端卡片)
  let maxOrder = 0;
  for (let i = 0; i < BS_STATE.currentBlocks.length; i++) {
    const b = BS_STATE.currentBlocks[i];
    if (b.is_teardown || (b.phase_num !== null && b.phase_num >= 95)) break;
    maxOrder++;
  }
  if (maxOrder <= 0) maxOrder = BS_STATE.currentBlocks.length;

  let targetIdx = Math.max(0, Math.min(val - 1, maxOrder - 1));
  if (targetIdx === currentIdx) return;
  const item = BS_STATE.currentBlocks.splice(currentIdx, 1)[0];
  BS_STATE.currentBlocks.splice(targetIdx, 0, item);
  BS_STATE.selectedIdx = targetIdx;
  bsTriggerSwapHighlight(currentIdx, targetIdx);
  bsRenderBlocks();
}

let _bsSwapTimer = null;
function bsTriggerSwapHighlight(idxA, idxB = -1) {
  if (_bsSwapTimer) clearTimeout(_bsSwapTimer);
  BS_STATE.swappedAIdx = idxA;
  BS_STATE.swappedBIdx = idxB;
  _bsSwapTimer = setTimeout(() => {
    BS_STATE.swappedAIdx = -1;
    BS_STATE.swappedBIdx = -1;
    document.querySelectorAll('.bs-poker-mini-card').forEach(el => {
      el.classList.remove('just-swapped-a', 'just-swapped-b');
    });
  }, 1700);
}

function bsSelectCard(idx) {
  if (idx < 0 || idx >= BS_STATE.currentBlocks.length) return;
  BS_STATE.selectedIdx = idx;
  bsRenderRightInspector();
  bsHighlightSelectedCard();
}

function bsHighlightSelectedCard() {
  document.querySelectorAll('.bs-poker-mini-card').forEach((el, i) => {
    const isCur = (i === BS_STATE.selectedIdx);
    if (isCur) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  });
}

// ----------------- 流暢拖曳與碰牌對調 / 插牌落點指示 -----------------
function bsOnDragStart(e, idx) {
  const b = BS_STATE.currentBlocks[idx];
  if (b && (b.is_teardown || (b.phase_num !== null && b.phase_num >= 95))) {
    e.preventDefault();
    return false;
  }
  BS_STATE.dragFromIdx = idx;
  e.dataTransfer.effectAllowed = 'move';
  try { e.dataTransfer.setData('text/plain', String(idx)); } catch (_) {}
  const card = document.getElementById('bsCard_' + idx);
  if (card) {
    card.classList.add('is-dragging');
  }
}

function bsOnDragOver(e, targetIdx) {
  e.preventDefault();
  const target = BS_STATE.currentBlocks[targetIdx];
  if (target && (target.is_teardown || (target.phase_num !== null && target.phase_num >= 95))) {
    e.dataTransfer.dropEffect = 'none';
    return;
  }
  e.dataTransfer.dropEffect = 'move';

  if (BS_STATE.dragFromIdx < 0 || BS_STATE.dragFromIdx === targetIdx) return;

  const listEl = document.getElementById('bsBlockList');
  if (listEl) {
    const rect = listEl.getBoundingClientRect();
    if (e.clientY < rect.top + 60) listEl.scrollTop -= 18;
    else if (e.clientY > rect.bottom - 60) listEl.scrollTop += 18;
  }

  const card = document.getElementById('bsCard_' + targetIdx);
  if (!card) return;

  document.querySelectorAll('.bs-poker-mini-card').forEach(c => {
    c.classList.remove('drop-target-swap', 'drop-target-before', 'drop-target-after');
  });

  if (BS_STATE.dragMode === 'swap') {
    card.classList.add('drop-target-swap');
    BS_STATE.dropTargetIdx = targetIdx;
  } else {
    const r = card.getBoundingClientRect();
    const isBefore = (e.clientX - r.left) < (r.width / 2);
    BS_STATE.dropTargetIdx = targetIdx;
    BS_STATE.dropPos = isBefore ? 'before' : 'after';
    if (isBefore) {
      card.classList.add('drop-target-before');
    } else {
      card.classList.add('drop-target-after');
    }
  }
}

function bsOnDragLeave(e, targetIdx) {
  const card = document.getElementById('bsCard_' + targetIdx);
  if (card) {
    card.classList.remove('drop-target-swap', 'drop-target-before', 'drop-target-after');
  }
}

function bsOnDrop(e, targetIdx) {
  e.preventDefault();
  const fromIdx = BS_STATE.dragFromIdx;
  BS_STATE.dragFromIdx = -1;
  BS_STATE.dropTargetIdx = -1;

  document.querySelectorAll('.bs-poker-mini-card').forEach(c => {
    c.classList.remove('is-dragging', 'drop-target-swap', 'drop-target-before', 'drop-target-after');
  });

  if (fromIdx < 0 || fromIdx >= BS_STATE.currentBlocks.length || fromIdx === targetIdx) {
    bsRenderBlocks();
    return;
  }

  const target = BS_STATE.currentBlocks[targetIdx];
  const from = BS_STATE.currentBlocks[fromIdx];
  if (target && (target.is_teardown || (target.phase_num !== null && target.phase_num >= 95))) {
    bsRenderBlocks();
    return;
  }
  if (from && (from.is_teardown || (from.phase_num !== null && from.phase_num >= 95))) {
    bsRenderBlocks();
    return;
  }

  if (BS_STATE.dragMode === 'swap') {
    // 🔀 碰牌直接對調：兩張卡牌互換位置 (完全無死角、絕不失誤)
    const tmp = BS_STATE.currentBlocks[fromIdx];
    BS_STATE.currentBlocks[fromIdx] = BS_STATE.currentBlocks[targetIdx];
    BS_STATE.currentBlocks[targetIdx] = tmp;
    BS_STATE.selectedIdx = targetIdx;
    bsTriggerSwapHighlight(fromIdx, targetIdx);
  } else {
    // 📌 插牌移位：插入目標卡片的前方或後方
    const isBefore = (BS_STATE.dropPos === 'before');
    const item = BS_STATE.currentBlocks.splice(fromIdx, 1)[0];
    let insertIdx = targetIdx;
    if (fromIdx < targetIdx) {
      insertIdx = isBefore ? targetIdx - 1 : targetIdx;
    } else {
      insertIdx = isBefore ? targetIdx : targetIdx + 1;
    }
    if (insertIdx < 0) insertIdx = 0;
    if (insertIdx > BS_STATE.currentBlocks.length) insertIdx = BS_STATE.currentBlocks.length;

    BS_STATE.currentBlocks.splice(insertIdx, 0, item);
    BS_STATE.selectedIdx = insertIdx;
    bsTriggerSwapHighlight(fromIdx, insertIdx);
  }

  bsRenderBlocks();
}

function bsOnDragEnd() {
  BS_STATE.dragFromIdx = -1;
  BS_STATE.dropTargetIdx = -1;
  document.querySelectorAll('.bs-poker-mini-card').forEach(c => {
    c.classList.remove('is-dragging', 'drop-target-swap', 'drop-target-before', 'drop-target-after');
  });
  bsRenderBlocks();
}

// ----------------- 即時相依性計算 -----------------
function bsComputeLiveInspection() {
  const blocks = BS_STATE.currentBlocks;
  const autoRenumber = document.getElementById('chkBsAutoRenumber') ? document.getElementById('chkBsAutoRenumber').checked : true;

  // 1. 檢查變數相依性
  const allProduced = new Set();
  blocks.forEach(b => (b.produced_vars || []).forEach(v => allProduced.add(v)));
  const seenProduced = new Set();
  const depWarnings = [];
  const conflictIndices = new Set();

  blocks.forEach((b, pos) => {
    (b.used_vars || []).forEach(v => {
      if (allProduced.has(v) && !seenProduced.has(v)) {
        const prodBlk = blocks.slice(pos + 1).find(x => (x.produced_vars || []).includes(v));
        if (prodBlk) {
          depWarnings.push(`變數 $${v} 在 [${b.title}] 被引用，但產出該變數的積木 [${prodBlk.title}] 目前排在後方！`);
          conflictIndices.add(pos);
        }
      }
    });
    (b.produced_vars || []).forEach(v => seenProduced.add(v));
  });

  // 2. 計算動態順編 Phase (1, 2, 3...)
  let nextPhase = 1;
  let seenTeardown = false;
  const orderWarnings = [];

  const rowStates = blocks.map((b, idx) => {
    let previewPhase = b.phase;
    const isFixed = b.is_teardown || (b.phase_num !== null && b.phase_num >= 95);
    if (autoRenumber && !isFixed && b.phase_num !== -1) {
      previewPhase = String(nextPhase);
      nextPhase += 1;
    }

    let hasTeardownViolation = false;
    if (isFixed) {
      seenTeardown = true;
    } else if (seenTeardown) {
      hasTeardownViolation = true;
      orderWarnings.push(`積木 [${b.title}] 位於固定收尾區 (Phase >= 95) 之後，建議移至其前方。`);
    }

    const hasConflict = conflictIndices.has(idx) || hasTeardownViolation;
    return {
      previewPhase,
      hasConflict,
      hasTeardownViolation
    };
  });

  return { depWarnings, orderWarnings, rowStates };
}

// ----------------- 渲染極簡撲克牌桌 (網格排開) -----------------
function bsRenderBlocks() {
  const listEl = document.getElementById('bsBlockList');
  const badgeEl = document.getElementById('bsCardCountBadge');
  if (!listEl) return;

  const { depWarnings, orderWarnings, rowStates } = bsComputeLiveInspection();
  const allWarns = [...depWarnings, ...orderWarnings];

  if (badgeEl) {
    badgeEl.textContent = `共 ${BS_STATE.currentBlocks.length} 個 Phase`;
  }

  bsApplyCardDimensions();

  if (BS_STATE.selectedIdx >= BS_STATE.currentBlocks.length) {
    BS_STATE.selectedIdx = Math.max(0, BS_STATE.currentBlocks.length - 1);
  }

  const query = BS_STATE.searchQuery;
  let html = '';

  BS_STATE.currentBlocks.forEach((b, idx) => {
    const st = rowStates[idx];
    const isSelected = (idx === BS_STATE.selectedIdx);

    let isMatched = true;
    if (query) {
      const titleMatch = (b.title || '').toLowerCase().includes(query);
      const phaseMatch = String(st.previewPhase || '').toLowerCase().includes(query) || String(b.phase || '').toLowerCase().includes(query);
      const stepMatch = (b.steps || []).some(s => (s.Command || '').toLowerCase().includes(query) || (s.Send || '').toLowerCase().includes(query));
      isMatched = titleMatch || phaseMatch || stepMatch;
    }
    if (!isMatched) return;

    const isTeardown = b.is_teardown || (b.phase_num !== null && b.phase_num >= 95);
    const currentOrderNum = idx + 1;
    const totalCount = BS_STATE.currentBlocks.length;
    const isSwappedA = (BS_STATE.swappedAIdx === idx);
    const isSwappedB = (BS_STATE.swappedBIdx === idx);

    // 檢查卡牌是否有被調整過順序 (與原始載入順序 orig_idx 比對)
    const isOrderChanged = (b.orig_idx !== undefined && b.orig_idx !== idx);

    html += `
      <div id="bsCard_${idx}"
           class="bs-poker-mini-card ${isSelected ? 'active' : ''} ${st.hasConflict ? 'conflict' : ''} ${isTeardown ? 'teardown' : ''} ${isOrderChanged && !isTeardown ? 'order-modified' : ''} ${isSwappedA ? 'just-swapped-a' : ''} ${isSwappedB ? 'just-swapped-b' : ''}"
           ${isTeardown ? '' : 'draggable="true"'}
           ondragstart="bsOnDragStart(event, ${idx})"
           ondragover="bsOnDragOver(event, ${idx})"
           ondragleave="bsOnDragLeave(event, ${idx})"
           ondrop="bsOnDrop(event, ${idx})"
           ondragend="bsOnDragEnd()"
           onclick="bsSelectCard(${idx})"
           title="${bsEscapeHtml(b.title)} (${b.row_count} 行) · 原第 ${b.start_row} 列${isOrderChanged ? ' · 順序已調整' : ''}">
        
        <!-- Phase 標籤（支援點擊序號直接手動指派順序） -->
        <div class="bs-card-phase-badge" onclick="event.stopPropagation();">
          ${isTeardown ? `🔒 Phase ${b.phase || '95+'}` : `
            Phase 
            <input type="number" 
                   min="1" 
                   max="${totalCount}" 
                   value="${st.previewPhase || currentOrderNum}" 
                   class="bs-phase-direct-input" 
                   title="直接輸入欲排順序 (1~${totalCount})，按 Enter 自動跳位插隊" 
                   onfocus="this.select()" 
                   onchange="bsDirectJumpPhase(${idx}, this.value)" 
                   onkeydown="if(event.key==='Enter'){this.blur();}">
          `}
        </div>

        <!-- Title 名稱 -->
        <div class="bs-card-title-label">
          ${bsEscapeHtml(b.title)}
        </div>

        <!-- 步數 (改成 行) 膠囊標籤與異動標籤 -->
        <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap; justify-content:center;">
          <div class="bs-card-steps-pill">
            ${b.row_count} 行
          </div>
          ${isOrderChanged && !isTeardown ? `
            <span class="bs-card-moved-tag" title="此積木順序已經過調動 (原序號 #${b.orig_idx + 1})">
              已調動
            </span>
          ` : ''}
        </div>

        <!-- 底座隱形懸停條：固定區不顯示微調按鈕 -->
        ${isTeardown ? '' : `
        <div class="bs-card-hover-drawer" onclick="event.stopPropagation();">
          <button type="button" class="bs-card-hover-btn" onclick="bsMoveBlock(${idx}, -1)" ${idx === 0 ? 'disabled' : ''} title="往前挪一位 (◀)">
            ◀
          </button>
          <span style="font-size:10px; color:#64748B; font-weight:700;">#${currentOrderNum}</span>
          <button type="button" class="bs-card-hover-btn" onclick="bsMoveBlock(${idx}, 1)" ${idx === totalCount - 1 ? 'disabled' : ''} title="往後挪一位 (▶)">
            ▶
          </button>
        </div>
        `}
      </div>
    `;
  });

  listEl.innerHTML = html;
  bsRenderRightInspector();
}

// ----------------- 右欄指令終端檢視器與錯誤診斷 (Command │ Send) -----------------
function bsRenderRightInspector() {
  const issuesEl = document.getElementById('bsRightIssuesBox');
  const headerEl = document.getElementById('bsDetailHeader');
  const tableEl = document.getElementById('bsDetailTableWrap');
  if (!headerEl || !tableEl) return;

  const { depWarnings, orderWarnings, rowStates } = bsComputeLiveInspection();
  const allWarns = [...depWarnings, ...orderWarnings];

  // 1. 錯誤顯示在右邊視窗 (依使用者要求)
  if (issuesEl) {
    if (allWarns.length === 0) {
      issuesEl.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px; color:#4ADE80; font-weight:700;">
          <span style="font-size:15px;">✅</span>
          <span>即時檢查通過：全流程 Phase 順編與變數相依皆正確無誤</span>
        </div>
      `;
    } else {
      issuesEl.innerHTML = `
        <div style="background:#450A0A; border:1px solid #DC2626; border-radius:6px; padding:7px 10px; color:#FECACA;">
          <div style="font-weight:800; font-size:12px; color:#FCA5A5; margin-bottom:3px; display:flex; justify-content:space-between; align-items:center;">
            <span>⚠️ 偵測到 ${allWarns.length} 項問題（請調整卡牌前後順序）：</span>
          </div>
          <ul style="margin:0 0 0 16px; padding:0; font-size:11.5px; line-height:1.45;">
            ${allWarns.map(w => `<li>${w}</li>`).join('')}
          </ul>
        </div>
      `;
    }
  }

  const b = BS_STATE.currentBlocks[BS_STATE.selectedIdx];
  if (!b) {
    headerEl.innerHTML = `<span style="color:#94A3B8; font-size:13px;">請從左側點選任一張卡牌以檢視內部指令</span>`;
    tableEl.innerHTML = '';
    return;
  }

  const st = rowStates[BS_STATE.selectedIdx] || {};

  const prodChips = (b.produced_vars || []).map(v => `<span class="mono" style="background:#14532D; color:#86EFAC; border:1px solid #166534; font-size:11px; padding:1px 6px; border-radius:4px; font-weight:700;">🏷️ 產出變數: $${v}</span>`).join(' ');
  const usedChips = (b.used_vars || []).map(v => `<span class="mono" style="background:#1E3A8A; color:#93C5FD; border:1px solid #1D4ED8; font-size:11px; padding:1px 6px; border-radius:4px; font-weight:700;">📥 引用變數: $${v}</span>`).join(' ');

  // 當前選取卡牌若有警告，顯示專屬提示與「⚡ 一鍵前置產出積木」按鈕
  let conflictAlertHtml = '';
  if (st.hasConflict && st.reason) {
    conflictAlertHtml = `
      <div style="width:100%; background:#7F1D1D; border:1px solid #EF4444; border-radius:6px; padding:5px 10px; margin-top:5px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px;">
        <span style="color:#FEE2E2; font-size:11.5px; font-weight:700;">⚠️ ${st.reason}</span>
        <button type="button" class="btn" onclick="bsResolveCardConflict(${BS_STATE.selectedIdx})" style="padding:2px 8px; font-size:11px; background:#F59E0B; color:#0F172A; font-weight:800; border:none; border-radius:3px; cursor:pointer;" title="一鍵將產出該變數的積木移至本卡牌前方">
          ⚡ 一鍵前置產出積木
        </button>
      </div>
    `;
  }

  headerEl.innerHTML = `
    <div style="width:100%; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:16px;">📌</span>
        <span style="font-weight:800; font-size:14px; color:#F8FAFC;">
          [ Phase ${st.previewPhase || b.phase} ] ${bsEscapeHtml(b.title)}
        </span>
        <span style="background:#334155; color:#E2E8F0; font-size:11.5px; font-weight:700; padding:2px 7px; border-radius:4px;">
          共 ${b.row_count} 列指令 · 原第 ${b.start_row} 列
        </span>
      </div>
      <div style="font-size:12px; color:#94A3B8;">
        序號：#${BS_STATE.selectedIdx + 1} / ${BS_STATE.currentBlocks.length}
      </div>
    </div>
    ${conflictAlertHtml}
    ${(b.produced_vars && b.produced_vars.length > 0) || (b.used_vars && b.used_vars.length > 0) ? `
      <div style="width:100%; display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:4px;">
        ${prodChips}
        ${usedChips}
      </div>
    ` : ''}
  `;

  const steps = b.steps || [];
  tableEl.innerHTML = `
    <div style="height:100%; display:flex; flex-direction:column;">
      <div style="background:#1E293B; color:#94A3B8; font-size:12px; font-weight:800; padding:6px 14px; display:grid; grid-template-columns:220px 1fr; border-bottom:1px solid #334155; font-family:Consolas, monospace; letter-spacing:0.4px;">
        <span>Command (執行命令)</span>
        <span>Send (發送字串/參數規格)</span>
      </div>
      <div style="flex:1; overflow-y:auto; font-family:Consolas, monospace; font-size:12.5px;">
        ${steps.length === 0 ? `
          <div style="padding:20px; color:#64748B; text-align:center;">此 Phase 區塊無內部子指令</div>
        ` : steps.map((s, sIdx) => `
          <div style="display:grid; grid-template-columns:220px 1fr; padding:5px 14px; border-bottom:1px solid #1E293B; background:${sIdx % 2 === 0 ? '#0F172A' : '#141E33'}; line-height:1.45;">
            <span style="color:#38BDF8; font-weight:700; word-break:break-all;">${bsEscapeHtml(s.Command || '-')}</span>
            <span style="color:#FCD34D; word-break:break-all;">${bsEscapeHtml(s.Send || '-')}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

// 快速解決變數相依衝突：將產出該變數的積木直接移至當前卡牌前方
function bsResolveCardConflict(cardIdx) {
  const b = BS_STATE.currentBlocks[cardIdx];
  if (!b) return;
  const seenProduced = new Set();
  for (let i = 0; i < cardIdx; i++) {
    (BS_STATE.currentBlocks[i].produced_vars || []).forEach(v => seenProduced.add(v));
  }
  const missingVars = (b.used_vars || []).filter(v => !seenProduced.has(v));
  if (missingVars.length === 0) return;

  let foundIdx = -1;
  for (let j = cardIdx + 1; j < BS_STATE.currentBlocks.length; j++) {
    const pVars = BS_STATE.currentBlocks[j].produced_vars || [];
    if (missingVars.some(v => pVars.includes(v))) {
      foundIdx = j;
      break;
    }
  }

  if (foundIdx > cardIdx) {
    const item = BS_STATE.currentBlocks.splice(foundIdx, 1)[0];
    BS_STATE.currentBlocks.splice(cardIdx, 0, item);
    BS_STATE.selectedIdx = cardIdx + 1;
    bsRenderBlocks();
  }
}

// ----------------- 套用變更回後端 -----------------
async function bsApplyReorder() {
  const { depWarnings, orderWarnings } = bsComputeLiveInspection();
  const allWarns = [...depWarnings, ...orderWarnings];
  if (allWarns.length > 0) {
    const ok = confirm(`⚠️ 偵測到以下順序或變數相依警示：\n\n• ${allWarns.join('\n• ')}\n\n確定仍要套用此順序嗎？`);
    if (!ok) return;
  }

  const newOrder = BS_STATE.currentBlocks.map(b => b.orig_idx);
  const autoRenum = document.getElementById('chkBsAutoRenumber') ? document.getElementById('chkBsAutoRenumber').checked : true;

  try {
    const res = await fetch('/api/reorder_station_blocks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace: STATE.workspace,
        sheet_name: BS_STATE.sheetName,
        new_order_indices: newOrder,
        auto_renumber_phase: autoRenum
      })
    });
    const data = await res.json();
    if (data.status !== 'ok') {
      alert(data.message || '套用積木順序失敗');
      return;
    }
    STATE.workspace = data.workspace;
    STATE.report = data.report;
    STATE.pendingInserts = STATE.pendingInserts || [];
    STATE.pendingInserts.push({
      sheet: BS_STATE.sheetName,
      inst: '積木順序重排',
      summary: `共 ${BS_STATE.currentBlocks.length} 個 Phase 區塊已重排${autoRenum ? '並自動順編 Phase' : ''}`
    });
    closeBlockSorterModal();
    renderAuditResults();
  } catch (err) {
    console.error('bsApplyReorder error:', err);
    alert('套用積木順序時發生錯誤：' + (err && err.message ? err.message : err));
  }
}

// ----------------- 一鍵套用排序、自動修復並開啟 Excel 檢視 -----------------
async function bsApplyAndOpenExcel() {
  const { depWarnings, orderWarnings } = bsComputeLiveInspection();
  const allWarns = [...depWarnings, ...orderWarnings];
  if (allWarns.length > 0) {
    const ok = confirm(`⚠️ 偵測到以下順序或變數相依警示：\n\n• ${allWarns.join('\n• ')}\n\n確定仍要套用此順序並自動健檢修復匯出嗎？`);
    if (!ok) return;
  }

  const newOrder = BS_STATE.currentBlocks.map(b => b.orig_idx);
  const autoRenum = document.getElementById('chkBsAutoRenumber') ? document.getElementById('chkBsAutoRenumber').checked : true;

  const btnBottom = document.getElementById('btnBsApplyAndOpen');
  const btnTop = document.getElementById('btnBsApplyAndOpenTop');
  const origTextBottom = btnBottom ? btnBottom.innerHTML : '';
  const origTextTop = btnTop ? btnTop.innerHTML : '';

  const setBusy = (busy) => {
    if (btnBottom) {
      btnBottom.disabled = busy;
      btnBottom.innerHTML = busy ? '⏳ 正在套用、自動修復並啟動 Excel...' : origTextBottom;
    }
    if (btnTop) {
      btnTop.disabled = busy;
      btnTop.innerHTML = busy ? '⏳ 處理中...' : origTextTop;
    }
  };

  setBusy(true);

  try {
    const runExportFlow = async () => {
      // 步驟 1：套用 Phase 順序重排與自動順編
      const resReorder = await fetch('/api/reorder_station_blocks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace: STATE.workspace,
          sheet_name: BS_STATE.sheetName,
          new_order_indices: newOrder,
          auto_renumber_phase: autoRenum
        })
      });
      const dataReorder = await resReorder.json();
      if (dataReorder.status !== 'ok') {
        throw new Error(dataReorder.message || '套用積木順序失敗');
      }
      STATE.workspace = dataReorder.workspace;

      // 步驟 2：執行全盤自動健檢修復，並輸出至原目錄 *_FIXED.xlsx，自動鎖定當前 sheet 並啟動 Excel 程式
      const resFix = await fetch('/api/fix_and_export_in_place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace: STATE.workspace,
          user_choices: STATE.userChoices || {},
          dry_run: false,
          active_sheet: BS_STATE.sheetName,
          open_excel: false
        })
      });
      return await resFix.json();
    };

    const dataFix = (typeof withLoadingTimer === 'function')
      ? await withLoadingTimer(
          `正在套用 [${BS_STATE.sheetName}] Phase 排序、標記淡藍底色並開啟輸出目錄`,
          runExportFlow,
          1200,
          '正在重排 Phase 積木順序、標記柔和淡藍底色 (#E8F4FD)、重算 Checksum 並開啟輸出目錄...'
        )
      : await runExportFlow();

    if (dataFix.status !== 'ok') {
      alert(dataFix.message || '自動修復與匯出 Excel 失敗');
      setBusy(false);
      return;
    }

    STATE.workspace = dataFix.workspace;
    STATE.report = dataFix.report;
    renderAuditResults();
    closeBlockSorterModal();

    const fixedCount = (dataFix.fixed_logs || []).length;
    if (typeof showExportCompleteModal === 'function') {
      showExportCompleteModal({
        title: `🎉 [${BS_STATE.sheetName}] 順序套用與修復匯出完成（已開啟輸出資料夾）`,
        excelPath: dataFix.excel_path,
        outputDir: dataFix.output_dir,
        centimaniDir: dataFix.centimani_dir,
        centimaniDirExists: dataFix.centimani_dir_exists,
        missingDlls: dataFix.missing_dlls,
        summaryHtml: `<div>• <b>Phase 積木：</b>${BS_STATE.currentBlocks.length} 個區塊${autoRenum ? '（已順編並標註淡藍底色 #E8F4FD）' : ''}，自動修復 ${fixedCount} 處</div>`
      });
    } else {
      alert(
        `🎉 順序套用與腳本修復成功！\n\n` +
        `1. Phase 積木重排完成：共 ${BS_STATE.currentBlocks.length} 個區塊已更新${autoRenum ? '，已依序順編 Phase 號碼' : ''}。\n` +
        `2. 腳本邏輯自動修復完成：共修正 ${fixedCount} 處潛在問題。\n` +
        `3. 已生成標準檔案並開啟目錄：\n   ${dataFix.excel_path}`
      );
    }

  } catch (err) {
    console.error('bsApplyAndOpenExcel error:', err);
    alert('套用排序並開啟 Excel 失敗：' + (err && err.message ? err.message : err));
  } finally {
    setBusy(false);
  }
}
