// Interactive Drag-and-Drop Phase / Title Block Sorter with Live Variable Dependency & Order Inspection
const BS_STATE = {
  sheetName: '',
  origBlocks: [],
  currentBlocks: [],
  dragFromIdx: -1
};

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

  document.getElementById('modalBlockSorter').style.display = 'flex';
  await bsLoadSheetBlocks();
}

function closeBlockSorterModal() {
  document.getElementById('modalBlockSorter').style.display = 'none';
}

async function bsLoadSheetBlocks() {
  const sheet = document.getElementById('bsSheetSel').value;
  BS_STATE.sheetName = sheet;
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
  BS_STATE.origBlocks = (data.blocks || []).map(b => Object.assign({}, b));
  BS_STATE.currentBlocks = (data.blocks || []).map(b => Object.assign({}, b));
  bsRenderBlocks();
}

function bsResetOrder() {
  BS_STATE.currentBlocks = BS_STATE.origBlocks.map(b => Object.assign({}, b));
  bsRenderBlocks();
}

function bsMoveBlock(idx, delta) {
  const target = idx + delta;
  if (target < 0 || target >= BS_STATE.currentBlocks.length) return;
  const arr = BS_STATE.currentBlocks;
  const tmp = arr[idx];
  arr[idx] = arr[target];
  arr[target] = tmp;
  bsRenderBlocks();
}

function bsOnDragStart(e, idx) {
  BS_STATE.dragFromIdx = idx;
  e.dataTransfer.effectAllowed = 'move';
  try { e.dataTransfer.setData('text/plain', String(idx)); } catch (_) {}
}

function bsOnDragOver(e, idx) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const card = document.getElementById('bsCard_' + idx);
  if (card) card.style.borderColor = '#2563EB';
}

function bsOnDragLeave(e, idx) {
  const card = document.getElementById('bsCard_' + idx);
  if (card) card.style.borderColor = '#CBD5E1';
}

function bsOnDrop(e, dropIdx) {
  e.preventDefault();
  const fromIdx = BS_STATE.dragFromIdx;
  BS_STATE.dragFromIdx = -1;
  if (fromIdx < 0 || fromIdx === dropIdx || fromIdx >= BS_STATE.currentBlocks.length) {
    bsRenderBlocks();
    return;
  }
  const item = BS_STATE.currentBlocks.splice(fromIdx, 1)[0];
  BS_STATE.currentBlocks.splice(dropIdx, 0, item);
  bsRenderBlocks();
}

function bsAutoSortByPhase() {
  // Group each empty-phase block with its nearest preceding numeric-phase block so sub-blocks stay together
  const groups = [];
  let curGroup = null;
  BS_STATE.currentBlocks.forEach((b, idx) => {
    if (b.phase_num !== null && b.phase_num !== undefined) {
      if (curGroup) groups.push(curGroup);
      curGroup = {
        sortKey: b.is_teardown ? 999900 + b.phase_num : b.phase_num,
        origPos: idx,
        items: [b]
      };
    } else {
      if (!curGroup) {
        curGroup = { sortKey: -1, origPos: idx, items: [b] };
      } else {
        curGroup.items.push(b);
      }
    }
  });
  if (curGroup) groups.push(curGroup);

  groups.sort((a, b) => (a.sortKey !== b.sortKey) ? (a.sortKey - b.sortKey) : (a.origPos - b.origPos));
  const flattened = [];
  groups.forEach(g => g.items.forEach(it => flattened.push(it)));
  BS_STATE.currentBlocks = flattened;
  bsRenderBlocks();
}

function bsComputeLiveInspection() {
  const blocks = BS_STATE.currentBlocks;
  const autoRenumber = document.getElementById('chkBsAutoRenumber') ? document.getElementById('chkBsAutoRenumber').checked : true;

  // 1. Check variable dependencies
  const allProduced = new Set();
  blocks.forEach(b => (b.produced_vars || []).forEach(v => allProduced.add(v)));
  const seenProduced = new Set();
  const depWarnings = [];
  blocks.forEach((b, pos) => {
    (b.used_vars || []).forEach(v => {
      if (allProduced.has(v) && !seenProduced.has(v)) {
        const prodBlk = blocks.slice(pos + 1).find(x => (x.produced_vars || []).includes(v));
        if (prodBlk) {
          depWarnings.push(`變數 $${v} 在 [${b.title}] 被使用，但產出它的積木 [${prodBlk.title}] 目前排在後面！`);
        }
      }
    });
    (b.produced_vars || []).forEach(v => seenProduced.add(v));
  });

  // 2. Compute preview Phase numbers & check Phase order
  const normalNums = blocks.filter(b => b.phase_num !== null && !b.is_teardown).map(b => b.phase_num);
  let nextPhase = normalNums.length > 0 ? Math.min(...normalNums) : 1;
  if (nextPhase > 1) nextPhase = 1;

  let prevPhase = null;
  let seenTeardown = false;
  const orderWarnings = [];
  const rowStates = blocks.map(b => {
    let previewPhase = b.phase;
    let pnum = b.phase_num;
    if (autoRenumber && pnum !== null && !b.is_teardown) {
      previewPhase = String(nextPhase);
      pnum = nextPhase;
      nextPhase += 1;
    }
    let badOrder = false;
    let reason = '';
    if (pnum !== null) {
      if (seenTeardown && !b.is_teardown) {
        badOrder = true;
        reason = `位於收尾區 Phase 97 之後`;
        orderWarnings.push(`積木 [${b.title}] 位於收尾區 Phase 97 之後，建議移至 Phase 97 之前。`);
      } else if (!b.is_teardown && prevPhase !== null && pnum < prevPhase) {
        badOrder = true;
        reason = `Phase ${pnum} 倒退小於前方 Phase ${prevPhase}`;
        orderWarnings.push(`積木 [${b.title}] 的 Phase (${pnum}) 小於前方 Phase (${prevPhase})。`);
      }
      if (b.is_teardown) seenTeardown = true;
      else prevPhase = pnum;
    } else if (seenTeardown) {
      badOrder = true;
      reason = `位於收尾區 Phase 97 之後`;
      orderWarnings.push(`積木 [${b.title}] 位於收尾區 Phase 97 之後，建議移至 Phase 97 之前。`);
    }
    return { previewPhase, badOrder, reason };
  });

  return { depWarnings, orderWarnings, rowStates };
}

function bsRenderBlocks() {
  const listEl = document.getElementById('bsBlockList');
  const statusEl = document.getElementById('bsLiveStatusBox');
  if (!listEl || !statusEl) return;

  const { depWarnings, orderWarnings, rowStates } = bsComputeLiveInspection();
  const allWarns = [...depWarnings, ...orderWarnings];

  if (allWarns.length === 0) {
    statusEl.style.background = '#F0FDF4';
    statusEl.style.borderColor = '#22C55E';
    statusEl.style.color = '#14532D';
    statusEl.innerHTML = `✅ <b>即時檢查通過：</b>目前積木順序、Phase 遞增邏輯與 <code>$變數</code> 先後相依關係均正常。`;
  } else {
    statusEl.style.background = '#FEF2F2';
    statusEl.style.borderColor = '#EF4444';
    statusEl.style.color = '#7F1D1D';
    statusEl.innerHTML = `
      <div style="font-weight:800; margin-bottom:4px;">⚠️ 偵測到 ${allWarns.length} 項順序或變數相依問題（請拖拉調整或點「🔢 依 Phase 號碼自動排序」）：</div>
      <ul style="margin:0 0 0 18px; padding:0; font-size:12.5px; line-height:1.5;">
        ${allWarns.map(w => `<li>${w}</li>`).join('')}
      </ul>
    `;
  }

  listEl.innerHTML = BS_STATE.currentBlocks.map((b, idx) => {
    const st = rowStates[idx];
    const phaseChanged = String(st.previewPhase || '') !== String(b.phase || '');
    let phaseBadge = '';
    if (b.is_teardown) {
      phaseBadge = `<span style="background:#1E293B; color:#FFFFFF; font-weight:800; font-size:12px; padding:2px 8px; border-radius:5px;">🔒 Phase ${b.phase} (收尾)</span>`;
    } else if (st.badOrder) {
      phaseBadge = `<span style="background:#FEE2E2; color:#991B1B; border:1px solid #EF4444; font-weight:800; font-size:12px; padding:2px 8px; border-radius:5px;">⚠️ Phase ${st.previewPhase || '-'} (${st.reason})</span>`;
    } else if (st.previewPhase) {
      phaseBadge = `<span style="background:#FACC15; color:#0F172A; border:1px solid #CA8A04; font-weight:800; font-size:12px; padding:2px 8px; border-radius:5px;">Phase ${st.previewPhase}${phaseChanged ? ` <span style="font-weight:600;opacity:0.75;">(原 ${b.phase})</span>` : ''}</span>`;
    } else {
      phaseBadge = `<span style="background:#E2E8F0; color:#475569; font-weight:700; font-size:12px; padding:2px 8px; border-radius:5px;">無獨立 Phase（接續前段）</span>`;
    }

    const prodChips = (b.produced_vars || []).map(v => `<span class="mono" style="background:#DCFCE7; color:#166534; border:1px solid #86EFAC; font-size:11px; padding:1px 6px; border-radius:4px;">產出 $${v}</span>`).join(' ');
    const usedChips = (b.used_vars || []).map(v => `<span class="mono" style="background:#DBEAFE; color:#1E40AF; border:1px solid #93C5FD; font-size:11px; padding:1px 6px; border-radius:4px;">引用 $${v}</span>`).join(' ');

    return `
      <div id="bsCard_${idx}"
           draggable="true"
           ondragstart="bsOnDragStart(event, ${idx})"
           ondragover="bsOnDragOver(event, ${idx})"
           ondragleave="bsOnDragLeave(event, ${idx})"
           ondrop="bsOnDrop(event, ${idx})"
           style="display:flex; align-items:center; justify-content:space-between; gap:10px; background:${st.badOrder ? '#FFF1F2' : '#FFFFFF'}; border:1.5px solid ${st.badOrder ? '#F43F5E' : '#CBD5E1'}; border-left:5px solid ${b.is_teardown ? '#1E293B' : (st.badOrder ? '#E11D48' : '#2563EB')}; border-radius:8px; padding:8px 12px; cursor:grab; user-select:none;">
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
          <span style="font-size:16px; color:#64748B; cursor:grab;" title="按住滑鼠上下拖拉">☰</span>
          <span class="mono" style="font-size:12px; font-weight:800; color:#64748B; min-width:26px;">#${idx + 1}</span>
          ${phaseBadge}
          <span style="font-weight:800; font-size:14px; color:#0F172A;">${b.title}</span>
          <span style="font-size:12px; color:#64748B;">（共 ${b.row_count} 列 · 原第 ${b.start_row} 列）</span>
          ${prodChips}
          ${usedChips}
        </div>
        <div style="display:flex; gap:4px; align-items:center; flex-shrink:0;">
          <button type="button" class="btn" style="padding:3px 8px; font-size:12px;" onclick="bsMoveBlock(${idx}, -1)" ${idx === 0 ? 'disabled' : ''} title="上移">▲</button>
          <button type="button" class="btn" style="padding:3px 8px; font-size:12px;" onclick="bsMoveBlock(${idx}, 1)" ${idx === BS_STATE.currentBlocks.length - 1 ? 'disabled' : ''} title="下移">▼</button>
        </div>
      </div>
    `;
  }).join('');
}

async function bsApplyReorder() {
  const { depWarnings } = bsComputeLiveInspection();
  if (depWarnings.length > 0) {
    const ok = confirm(`⚠️ 偵測到變數先後相依警告：\n• ${depWarnings.join('\n• ')}\n\n確定仍要套用此順序嗎？`);
    if (!ok) return;
  }

  const newOrder = BS_STATE.currentBlocks.map(b => b.orig_idx);
  const autoRenum = document.getElementById('chkBsAutoRenumber') ? document.getElementById('chkBsAutoRenumber').checked : true;

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
    summary: `共 ${BS_STATE.currentBlocks.length} 個區塊已重排${autoRenum ? '並自動順編 Phase' : ''}`
  });
  closeBlockSorterModal();
  renderAuditResults();
}
