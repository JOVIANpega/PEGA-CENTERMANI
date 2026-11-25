// Centimani Studio - Shared Template Block Transplant & Guided SKU Wizard UI
// Shared by BOTH '01 / EDIT' (Existing TestFlow) and '02 / CREATE' (0 -> 1 Blank Mother)

(function () {
  'use strict';

  const TSW = {
    targetMode: 'create', // 'create' | 'edit'
    step: 1,              // 1: Source & Blocks | 2: Tweaks & 5-Q SKU Wizard | 3: Preview & Apply
    catalog: [],
    catalogLoaded: false,
    inspected: null,      // Response from /api/template_bundle/inspect
    selectedSheet: '',
    selectedKeys: new Set(),
    pausedKeys: new Set(),
    instRemap: {},        // srcName -> targetName or '__PAUSE__'
    connRemap: {},        // srcAlias -> targetAlias
    iniSettingsOv: {},
    iniScriptsOv: {},
    compOv: {},
    insertPosition: 'before_teardown',
    marcoConflict: 'skip',
    previewRes: null,
    sku: {
      enabled: false,
      title_name: 'SFIS SKU Dynamic Routing',
      source_mode: 'CUSTITEM',
      isn_var: '*(ISN)',
      cust_field: 'CUSTINFO06',
      result_var: 'sfSKUCode',
      compare_mode: 'BRANCH_RULES',
      txt_filename: '69MO.txt',
      txt_content: 'A=24386522\nB=1B412008',
      offline_wrap: true,
      offline_default_sku: 'FULL',
      no_match_policy: 'FAIL',
      toggle_var: '',
      dut_conn: 'UART',
      end_prompt: '/#',
      dut_query_cmd: 'mfg wifi get-country-code',
      dut_prefix_kw: 'countrycodeis',
      sku_branches: [
        { code: 'FULL', label: '整機全配', iplas_model: 'MODEL_FULL', expected_hw: '11', dut_write_cmd: '' },
        { code: 'NO_BAT', label: '整機無電池', iplas_model: 'MODEL_NBAT', expected_hw: '11', dut_write_cmd: '' },
        { code: 'NO_WIFI', label: '整機無WiFi模組', iplas_model: 'MODEL_NOWF', expected_hw: '10', dut_write_cmd: '' },
      ],
      section_guards: [], // [{ section_title, allowed_skus: [...], target_block_key }]
    },
  };

  function _esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _ensureStylesAndModal() {
    if (!document.getElementById('tswStyles')) {
      const st = document.createElement('style');
      st.id = 'tswStyles';
      st.textContent = `
        .tsw-pill { cursor:pointer; padding:6px 14px; border-radius:999px; border:1.5px solid #CBD5E1; background:#F8FAFC; color:#334155; font-weight:800; font-size:0.86rem; transition:all 0.15s; }
        .tsw-pill:hover { background:#E0F2FE; border-color:#38BDF8; color:#0369A1; }
        .tsw-pill.active { background:#2563EB; border-color:#1D4ED8; color:#FFFFFF; }
        .tsw-btn-soft { cursor:pointer; padding:6px 12px; border-radius:6px; border:1px solid #CBD5E1; background:#F8FAFC; color:#1E293B; font-weight:700; font-size:0.84rem; transition:all 0.15s; }
        .tsw-btn-soft:hover { background:#E0F2FE; border-color:#38BDF8; color:#0369A1; }
        .tsw-blk-card { border:1.5px solid #CBD5E1; border-radius:8px; padding:9px 12px; background:#FFFFFF; cursor:pointer; transition:all 0.15s; }
        .tsw-blk-card:hover { background:#F0F9FF; border-color:#38BDF8; }
        .tsw-blk-card.selected { background:#EEF2FF; border-color:#4F46E5; }
        .tsw-sec-card { background:#FFFFFF; border:1.5px solid #CBD5E1; border-radius:10px; padding:12px 14px; margin-bottom:12px; }
        .tsw-tag { display:inline-block; padding:1px 7px; border-radius:999px; font-size:0.75rem; font-weight:700; margin-right:4px; }
      `;
      document.head.appendChild(st);
    }
    if (!document.getElementById('templateSkuModal')) {
      const m = document.createElement('div');
      m.id = 'templateSkuModal';
      m.className = 'modal-backdrop';
      m.onclick = function (e) { if (e.target === m) closeTemplateSkuWizard(); };
      m.innerHTML = `
        <div class="modal-panel" style="max-width:1060px; width:96vw; max-height:92vh; display:flex; flex-direction:column; background:#F8FAFC; border:2px solid #4F46E5; padding:0; overflow:hidden;">
          <div style="background:#FFFFFF; padding:12px 18px; border-bottom:1.5px solid #CBD5E1; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
              <span style="font-size:1.1rem; font-weight:900; color:#1E1B4B;">🧩 範本測項移植與引導式 SKU 精靈</span>
              <span id="tswTargetBadge" class="tsw-tag" style="background:#E0F2FE; color:#0369A1; font-size:0.82rem; padding:3px 10px;"></span>
            </div>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <button type="button" id="tswNav1" class="tsw-pill active" onclick="tswGoStep(1)">① 挑範本與測項</button>
              <span style="color:#94A3B8;">➔</span>
              <button type="button" id="tswNav2" class="tsw-pill" onclick="tswGoStep(2)">② 微調與 5 題 SKU 設定</button>
              <span style="color:#94A3B8;">➔</span>
              <button type="button" id="tswNav3" class="tsw-pill" onclick="tswGoStep(3)">③ 預覽與套用</button>
              <button type="button" onclick="closeTemplateSkuWizard()" class="btn btn-modal-close" style="margin-left:8px; padding:4px 12px;">✕ 關閉</button>
            </div>
          </div>
          <div id="tswBody" style="flex:1; overflow-y:auto; padding:14px 18px;"></div>
          <div style="background:#FFFFFF; padding:10px 18px; border-top:1.5px solid #CBD5E1; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div id="tswFooterStatus" style="font-size:0.84rem; color:#475569; font-weight:700;"></div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button type="button" id="tswBtnPrev" class="tsw-btn-soft" onclick="tswGoStep(TSW_STATE.step - 1)" style="display:none;">◀ 上一步</button>
              <button type="button" id="tswBtnNext" class="btn btn-primary-blue" onclick="tswGoStep(TSW_STATE.step + 1)" style="padding:7px 18px; font-weight:800;">下一步 ▶</button>
              <button type="button" id="tswBtnApply" class="btn btn-primary-green" onclick="tswApplyToTarget()" style="display:none; padding:7px 20px; font-weight:900;">✅ 確認套用至目標腳本</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(m);
    }
  }

  window.TSW_STATE = TSW;

  window.openTemplateSkuWizard = async function (mode) {
    _ensureStylesAndModal();
    if (mode === 'edit' && (!window.STATE || !window.STATE.workspace || !window.STATE.workspace.stations)) {
      alert('請先載入一份要編修的 TestFlow.xlsx，或切換至「產生首次使用空範本 (0 → 1)」入口開啟此精靈。');
      return;
    }
    TSW.targetMode = (mode === 'edit') ? 'edit' : 'create';
    TSW.step = 1;
    TSW.previewRes = null;

    // Seed saved create config if re-opening in create mode
    if (TSW.targetMode === 'create' && window.STATE && window.STATE.createSkuConfig) {
      TSW.sku = JSON.parse(JSON.stringify(window.STATE.createSkuConfig));
    }

    const stLabel = TSW.targetMode === 'edit'
      ? `✏️ 既有編修：${_getTargetStationName()}`
      : `🌱 新案建置 (0 → 1)：${_getTargetStationName()}`;
    const badge = document.getElementById('tswTargetBadge');
    if (badge) badge.textContent = stLabel;

    document.getElementById('templateSkuModal').classList.add('open');
    _renderCurrentStep();

    if (!TSW.catalogLoaded) {
      await _loadCatalog();
    }
  };

  window.closeTemplateSkuWizard = function () {
    const m = document.getElementById('templateSkuModal');
    if (m) m.classList.remove('open');
  };

  function _getTargetStationName() {
    if (TSW.targetMode === 'edit' && window.STATE && window.STATE.workspace) {
      const sel = document.getElementById('editorSheetSel');
      if (sel && sel.value) return sel.value;
      const keys = Object.keys(window.STATE.workspace.stations || {});
      return keys[0] || window.STATE.workspace.station_name || 'MB';
    }
    const gSt = document.getElementById('genStation');
    return (gSt && gSt.value.trim()) ? gSt.value.trim() : 'MB';
  }

  function _getTargetProjectName() {
    if (TSW.targetMode === 'edit' && window.STATE && window.STATE.workspace) {
      return window.STATE.workspace.project_name || 'Centimani';
    }
    const gP = document.getElementById('genProj');
    return (gP && gP.value.trim()) ? gP.value.trim() : 'PEGA_NEW';
  }

  async function _loadCatalog() {
    try {
      const res = await fetch('/api/template_bundle/catalog');
      const data = await res.json();
      if (data.status === 'ok') {
        TSW.catalog = data.templates || [];
        TSW.catalogLoaded = true;
        if (TSW.step === 1) _renderCurrentStep();
      }
    } catch (err) {
      console.warn('Template catalog load failed:', err);
    }
  }

  window.tswInspectTemplatePath = async function (xlsxPath) {
    if (!xlsxPath) return;
    const body = document.getElementById('tswBody');
    const prevFooter = document.getElementById('tswFooterStatus').textContent;
    document.getElementById('tswFooterStatus').textContent = '⏳ 正在深度解析來源範本、Global.ini 與 5 層相依性...';
    try {
      const res = await fetch('/api/template_bundle/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ excel_path: xlsxPath }),
      });
      const data = await res.json();
      if (data.status !== 'ok') {
        alert('解析來源範本失敗：' + (data.message || ''));
        return;
      }
      TSW.inspected = data;
      TSW.selectedSheet = (data.station_names && data.station_names[0]) || '';
      TSW.selectedKeys = new Set();
      TSW.pausedKeys = new Set();
      TSW.instRemap = {};
      TSW.connRemap = {};
      TSW.iniSettingsOv = {};
      TSW.iniScriptsOv = {};
      TSW.compOv = {};
      TSW.previewRes = null;
      _renderCurrentStep();
    } catch (err) {
      alert('解析失敗：' + err);
    } finally {
      if (document.getElementById('tswFooterStatus').textContent.startsWith('⏳')) {
        document.getElementById('tswFooterStatus').textContent = prevFooter;
      }
    }
  };

  window.tswPickCustomExcel = async function () {
    const res = await fetch('/api/pick_file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path_only: true, title: '選擇來源範本 TestFlow.xlsx' }),
    });
    const data = await res.json();
    if (data.status === 'ok' && data.file_path) {
      await window.tswInspectTemplatePath(data.file_path);
    }
  };

  window.tswGoStep = async function (nextStep) {
    const s = Math.max(1, Math.min(3, nextStep));
    TSW.step = s;
    _renderCurrentStep();
    if (s === 3) {
      await window.tswRunPreview();
    }
  };

  window.tswToggleBlock = function (blockKey) {
    if (TSW.selectedKeys.has(blockKey)) {
      TSW.selectedKeys.delete(blockKey);
      TSW.pausedKeys.delete(blockKey);
    } else {
      TSW.selectedKeys.add(blockKey);
    }
    _renderCurrentStep();
  };

  window.tswAddUpstreamKeys = function (keys) {
    (keys || []).forEach((k) => TSW.selectedKeys.add(k));
    _renderCurrentStep();
  };

  window.tswSelectStationBlocksBatch = function (mode) {
    const blks = _getInspectedSheetBlocks();
    if (mode === 'all_non_td') {
      blks.forEach((b) => { if (!b.is_teardown) TSW.selectedKeys.add(b.block_key); });
    } else if (mode === 'none') {
      blks.forEach((b) => TSW.selectedKeys.delete(b.block_key));
    }
    _renderCurrentStep();
  };

  function _getInspectedSheetBlocks() {
    if (!TSW.inspected || !TSW.selectedSheet) return [];
    return (TSW.inspected.stations && TSW.inspected.stations[TSW.selectedSheet]) || [];
  }

  function _getSelectedBlocks() {
    if (!TSW.inspected || !TSW.inspected.stations) return [];
    const out = [];
    Object.values(TSW.inspected.stations).forEach((arr) => {
      (arr || []).forEach((b) => {
        if (TSW.selectedKeys.has(b.block_key)) out.push(b);
      });
    });
    return out;
  }

  function _collectAvailableSectionsForGuard() {
    // Combine selected transplanted blocks + current workspace/wizard blocks so user can gate ANY of them!
    const items = [];
    const seen = new Set();
    _getSelectedBlocks().forEach((b) => {
      seen.add(b.title_label.toLowerCase());
      items.push({ section_title: b.title_label, target_block_key: b.block_key, badge: '移植測項' });
    });
    if (TSW.targetMode === 'edit' && window.STATE && window.STATE.workspace) {
      const stName = _getTargetStationName();
      const rows = (window.STATE.workspace.stations && window.STATE.workspace.stations[stName]) || [];
      rows.forEach((r) => {
        const t = String(r.Title || '').trim();
        if (!t || /^1,End/i.test(t) || /CheckRoute|SFIS SKU/i.test(t)) return;
        const lbl = t.includes(',') ? t.split(',').slice(1).join(',').trim() : t;
        if (lbl && !seen.has(lbl.toLowerCase())) {
          seen.add(lbl.toLowerCase());
          items.push({ section_title: lbl, target_block_key: '', badge: '目標既有' });
        }
      });
    } else if (window.STATE) {
      const blkMap = {};
      (window.STATE.blocks || []).forEach((b) => { blkMap[b.block_id] = b; });
      (window.STATE.selectedBlockIds || []).forEach((bid) => {
        if (bid === 'BLK_PRETEST_ROUTE' || bid === 'BLK_PHASE97_TEARDOWN' || bid === 'BLK_PHASE98_99_BRANCH_TEARDOWN') return;
        const b = blkMap[bid];
        if (!b || !b.steps || !b.steps.length) return;
        const t = String(b.steps[0].Title || b.name || '').trim();
        const lbl = t.includes(',') ? t.split(',').slice(1).join(',').trim() : t;
        if (lbl && !seen.has(lbl.toLowerCase())) {
          seen.add(lbl.toLowerCase());
          items.push({ section_title: lbl, target_block_key: '', badge: 'Step 2 積木' });
        }
      });
      (window.STATE.genCustomInsts || []).forEach((ci) => {
        if (ci.title_name && !seen.has(ci.title_name.toLowerCase())) {
          seen.add(ci.title_name.toLowerCase());
          items.push({ section_title: ci.title_name, target_block_key: '', badge: '自訂儀器' });
        }
      });
      (window.STATE.genRfBlocks || []).forEach((rb) => {
        const nm = rb.title_name || 'WIFI RF Test';
        if (!seen.has(nm.toLowerCase())) {
          seen.add(nm.toLowerCase());
          items.push({ section_title: nm, target_block_key: '', badge: 'RF 積木' });
        }
      });
    }
    // Always also include any user-already-configured section_guards not in the list above
    (TSW.sku.section_guards || []).forEach((gd) => {
      if (gd.section_title && !seen.has(gd.section_title.toLowerCase())) {
        seen.add(gd.section_title.toLowerCase());
        items.push({ section_title: gd.section_title, target_block_key: gd.target_block_key || '', badge: '自訂區塊' });
      }
    });
    return items;
  }

  function _renderCurrentStep() {
    [1, 2, 3].forEach((n) => {
      const nav = document.getElementById('tswNav' + n);
      if (nav) nav.classList.toggle('active', TSW.step === n);
    });
    const prevBtn = document.getElementById('tswBtnPrev');
    const nextBtn = document.getElementById('tswBtnNext');
    const applyBtn = document.getElementById('tswBtnApply');
    if (prevBtn) prevBtn.style.display = TSW.step > 1 ? 'inline-block' : 'none';
    if (nextBtn) nextBtn.style.display = TSW.step < 3 ? 'inline-block' : 'none';
    if (applyBtn) applyBtn.style.display = TSW.step === 3 ? 'inline-block' : 'none';

    const selCount = TSW.selectedKeys.size;
    const skuMsg = TSW.sku.enabled ? `已啟用 SKU 精靈 (${TSW.sku.sku_branches.length} 支)` : '未啟用 SKU 精靈';
    document.getElementById('tswFooterStatus').textContent = `已挑範本測項：${selCount} 塊 ｜ ${skuMsg}`;

    const body = document.getElementById('tswBody');
    if (!body) return;
    if (TSW.step === 1) {
      body.innerHTML = _renderStep1Html();
    } else if (TSW.step === 2) {
      body.innerHTML = _renderStep2Html();
    } else {
      body.innerHTML = _renderStep3Html();
    }
  }

  function _renderStep1Html() {
    const primaryTpls = (TSW.catalog || []).filter((t) => t.is_primary);
    const otherTpls = (TSW.catalog || []).filter((t) => !t.is_primary);
    const curPath = (TSW.inspected && TSW.inspected.source_path) || '';

    let tplOptions = '<option value="">-- 請選擇 perter_SCRIPT_11102026 站別範本 --</option>';
    if (primaryTpls.length) {
      tplOptions += '<optgroup label="⭐ 主力標準站別範本 (perter_SCRIPT_11102026)">';
      primaryTpls.forEach((t) => {
        const sel = (t.path === curPath) ? 'selected' : '';
        tplOptions += `<option value="${_esc(t.path)}" ${sel}>[${_esc(t.station_folder)}] ${_esc(t.name)} (${t.station_sheets.join('/')})</option>`;
      });
      tplOptions += '</optgroup>';
    }
    if (otherTpls.length) {
      tplOptions += '<optgroup label="📁 備份 / 歷史版本">';
      otherTpls.forEach((t) => {
        const sel = (t.path === curPath) ? 'selected' : '';
        tplOptions += `<option value="${_esc(t.path)}" ${sel}>[${_esc(t.rel_folder)}] ${_esc(t.name)}</option>`;
      });
      tplOptions += '</optgroup>';
    }

    let blocksHtml = '';
    if (!TSW.inspected) {
      blocksHtml = `
        <div style="background:#EFF6FF; border:1.5px dashed #60A5FA; border-radius:8px; padding:18px; text-align:center; color:#1E3A8A;">
          <div style="font-weight:800; font-size:0.98rem; margin-bottom:6px;">請先從上方挑選一份 <code>perter_SCRIPT_11102026</code> 範本（或瀏覽本機 Excel）</div>
          <div style="font-size:0.86rem; color:#475569;">若本次只需要產生「引導式 SKU 分流積木」而無需從舊檔搬測項，也可直接點擊右下角 <b>「下一步 ▶」</b> 進入 5 題 SKU 精靈。</div>
        </div>
      `;
    } else {
      const hints = TSW.inspected.sku_hints || {};
      const sheetOpts = (TSW.inspected.station_names || []).map((sn) =>
        `<option value="${_esc(sn)}" ${sn === TSW.selectedSheet ? 'selected' : ''}>${_esc(sn)} (${(TSW.inspected.stations[sn] || []).length} 個測項區塊)</option>`
      ).join('');
      const blks = _getInspectedSheetBlocks();

      const hintTags = [];
      if (hints.has_custitem) hintTags.push('<span class="tsw-tag" style="background:#DCFCE7;color:#166534;">SFIS CUSTITEM (SKU)</span>');
      if (hints.has_iteminfo_mo) hintTags.push('<span class="tsw-tag" style="background:#DBEAFE;color:#1E40AF;">ISN_ITEMINFO (工單/MO)</span>');
      if (hints.has_custinfo) hintTags.push('<span class="tsw-tag" style="background:#FEF3C7;color:#92400E;">ITEM_CUSTINFO_N</span>');
      if (hints.has_country_code) hintTags.push('<span class="tsw-tag" style="background:#F3E8FF;color:#6B21A8;">CountryCode 比對</span>');
      if ((hints.txt_files || []).length) hintTags.push(`<span class="tsw-tag" style="background:#E2E8F0;color:#0F172A;">📄 附檔: ${_esc(hints.txt_files.join(', '))}</span>`);

      // Compute missing upstream producers
      const missingUpstream = new Set();
      blks.forEach((b) => {
        if (TSW.selectedKeys.has(b.block_key)) {
          (b.upstream_block_keys || []).forEach((uk) => {
            if (!TSW.selectedKeys.has(uk)) missingUpstream.add(uk);
          });
        }
      });

      blocksHtml = `
        <div class="tsw-sec-card" style="background:#F0FDF4; border-color:#86EFAC;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
              <span style="font-weight:800; color:#166534;">📄 已解析：${_esc(TSW.inspected.file_name)}</span>
              <div style="margin-top:4px;">${hintTags.join('') || '<span style="font-size:0.8rem;color:#475569;">標準 Centimani 流程範本</span>'}</div>
            </div>
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <label style="font-size:0.84rem; font-weight:700;">來源分頁：
                <select onchange="TSW_STATE.selectedSheet=this.value; TSW_STATE.step=1; window.tswGoStep(1);" style="padding:4px 8px; border:1px solid #94A3B8; border-radius:5px;">${sheetOpts}</select>
              </label>
              <button type="button" class="tsw-btn-soft" onclick="tswSelectStationBlocksBatch('all_non_td')">☑ 全選測試段</button>
              <button type="button" class="tsw-btn-soft" onclick="tswSelectStationBlocksBatch('none')">☐ 清空</button>
            </div>
          </div>
          ${missingUpstream.size > 0 ? `
            <div style="margin-top:8px; background:#FEF3C7; border:1px solid #F59E0B; border-radius:6px; padding:6px 10px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
              <span style="font-size:0.83rem; color:#92400E; font-weight:700;">⚠️ 偵測到部分已勾測項讀取前方步驟產生的 $Var（共有 ${missingUpstream.size} 個前置區塊尚未勾選）</span>
              <button type="button" class="tsw-btn-soft" style="background:#FFFFFF; border-color:#D97706; color:#92400E;" onclick="tswAddUpstreamKeys(${_esc(JSON.stringify(Array.from(missingUpstream)))})">⚡ 一鍵補勾前置來源區塊</button>
            </div>
          ` : ''}
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr)); gap:8px;">
          ${blks.map((b) => {
            const sel = TSW.selectedKeys.has(b.block_key);
            const badges = [];
            badges.push(`<span class="tsw-tag" style="background:#E2E8F0;color:#1E293B;">P${_esc(b.effective_phase || '?')} · ${b.step_count} 步</span>`);
            if (b.marcos && b.marcos.length) badges.push(`<span class="tsw-tag" style="background:#F3E8FF;color:#6B21A8;">📐 Marco:${_esc(b.marcos.join(','))}</span>`);
            if (b.instruments && b.instruments.length) badges.push(`<span class="tsw-tag" style="background:#DBEAFE;color:#1E40AF;">🔬 ${_esc(b.instruments.map(i => i.name).join(','))}</span>`);
            if (b.sfis_calls && b.sfis_calls.length) badges.push(`<span class="tsw-tag" style="background:#FEF3C7;color:#92400E;">🛡️ SFIS×${b.sfis_calls.length}</span>`);
            if (b.companion_files && b.companion_files.length) badges.push(`<span class="tsw-tag" style="background:#DCFCE7;color:#166534;">📄 ${_esc(b.companion_files.join(','))}</span>`);
            const previewLine = (b.preview_steps || []).map((ps) => _esc(ps.Send || ps.Description)).slice(0, 2).join(' ➔ ');
            return `
              <div class="tsw-blk-card ${sel ? 'selected' : ''}" onclick="tswToggleBlock('${_esc(b.block_key)}')">
                <div style="display:flex; align-items:flex-start; gap:8px;">
                  <input type="checkbox" ${sel ? 'checked' : ''} style="margin-top:3px; width:16px; height:16px; pointer-events:none;">
                  <div style="flex:1; min-width:0;">
                    <div style="font-weight:800; font-size:0.9rem; color:#0F172A; word-break:break-word;">${_esc(b.title_label)}</div>
                    <div style="margin:4px 0;">${badges.join('')}</div>
                    <div class="mono" style="font-size:0.75rem; color:#64748B; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${previewLine}</div>
                  </div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    return `
      <div class="tsw-sec-card">
        <div style="font-weight:800; color:#0F172A; margin-bottom:8px;">步驟 ①：挑選來源範本（預設帶出 <code>perter_SCRIPT_11102026</code> 各站完整寫法）</div>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <select id="tswCatalogSel" onchange="if(this.value) tswInspectTemplatePath(this.value)" style="flex:1; min-width:280px; padding:6px 10px; border:1.5px solid #94A3B8; border-radius:6px; font-weight:700;">
            ${tplOptions}
          </select>
          <button type="button" class="tsw-btn-soft" onclick="tswPickCustomExcel()">📂 瀏覽本機其他 Excel...</button>
        </div>
      </div>
      ${blocksHtml}
    `;
  }

  function _renderStep2Html() {
    const selBlocks = _getSelectedBlocks();
    let transplantHtml = '';

    if (selBlocks.length > 0) {
      // Aggregate unique instruments, connections, ini vars, companion files across selected blocks
      const instMap = {};
      const connMap = {};
      const settVars = {};
      const scrVars = {};
      const compFiles = {};
      const allSrcComp = (TSW.inspected && TSW.inspected.companion_files) || {};

      selBlocks.forEach((b) => {
        (b.instruments || []).forEach((ins) => { instMap[ins.name] = ins; });
        Object.entries(b.connections || {}).forEach(([k, v]) => { connMap[k] = v; });
        Object.entries((b.ini_vars && b.ini_vars.Settings) || {}).forEach(([k, v]) => { settVars[k] = v; });
        Object.entries((b.ini_vars && b.ini_vars.Scripts) || {}).forEach(([k, v]) => { scrVars[k] = v; });
        (b.companion_files || []).forEach((cf) => {
          if (allSrcComp[cf]) compFiles[cf] = allSrcComp[cf].content || '';
        });
      });

      const targetInsts = (window.STATE && window.STATE.workspace && window.STATE.workspace.instruments)
        ? window.STATE.workspace.instruments.map((i) => i.Name).filter(Boolean)
        : ['NI6008', 'Agilent34401A', 'PPH1503', 'IPOWER2401', 'FeasaLED', 'DevUart', 'vnxRFSW'];

      const instRowsHtml = Object.values(instMap).map((ins) => {
        const curVal = TSW.instRemap[ins.name] !== undefined ? TSW.instRemap[ins.name] : ins.name;
        const opts = [
          `<option value="${_esc(ins.name)}" ${curVal === ins.name ? 'selected' : ''}>沿用來源儀器 (${_esc(ins.name)})</option>`,
          ...targetInsts.filter((tn) => tn !== ins.name).map((tn) =>
            `<option value="${_esc(tn)}" ${curVal === tn ? 'selected' : ''}>替換為 ➔ ${_esc(tn)}</option>`
          ),
          `<option value="__PAUSE__" ${curVal === '__PAUSE__' ? 'selected' : ''}>⏸️ 暫無此儀器 (設 Phase=-1)</option>`,
        ].join('');
        return `
          <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding:5px 0; border-bottom:1px dashed #E2E8F0;">
            <div>
              <span class="mono" style="font-weight:800; color:#1E40AF;">${_esc(ins.name)}</span>
              <span style="font-size:0.78rem; color:#64748B;">(${_esc(ins.func || ins.dll)}${ins.sub === '1' ? ' · Sub=1' : ''})</span>
            </div>
            <select onchange="TSW_STATE.instRemap['${_esc(ins.name)}']=this.value" style="padding:4px 8px; border:1px solid #94A3B8; border-radius:5px; font-size:0.83rem;">
              ${opts}
            </select>
          </div>
        `;
      }).join('');

      const connRowsHtml = Object.keys(connMap).map((al) => {
        const curVal = TSW.connRemap[al] !== undefined ? TSW.connRemap[al] : al;
        return `
          <label style="display:flex; align-items:center; gap:6px; font-size:0.83rem; font-weight:700;">
            <span>連線 <code style="color:#0369A1;">${_esc(al)}</code> ➔</span>
            <input type="text" value="${_esc(curVal)}" onchange="TSW_STATE.connRemap['${_esc(al)}']=this.value.trim()||'${_esc(al)}'" style="width:120px; padding:3px 7px; border:1px solid #94A3B8; border-radius:4px;" class="mono">
          </label>
        `;
      }).join('');

      const allIniEntries = [
        ...Object.entries(settVars).map(([k, v]) => ({ sec: 'Settings', k, v })),
        ...Object.entries(scrVars).map(([k, v]) => ({ sec: 'Scripts', k, v })),
      ];

      transplantHtml = `
        <div class="tsw-sec-card" style="border-color:#93C5FD; background:#F0F9FF;">
          <div style="font-weight:900; color:#1E3A8A; margin-bottom:8px;">🔧 Card A：已挑範本測項的微調清單（共 ${selBlocks.length} 個區塊）</div>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:12px;">
            <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
              <div style="font-weight:800; font-size:0.86rem; color:#0F172A; margin-bottom:6px;">🔬 儀器 / Sub=1 對應設定</div>
              ${instRowsHtml || '<div style="font-size:0.82rem;color:#64748B;">所選測項無外部儀器依賴。</div>'}
              ${connRowsHtml ? `<div style="margin-top:8px; padding-top:8px; border-top:1px solid #E2E8F0; display:flex; flex-wrap:wrap; gap:10px;">${connRowsHtml}</div>` : ''}
            </div>
            <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
              <div style="font-weight:800; font-size:0.86rem; color:#0F172A; margin-bottom:6px;">📍 插入位置與 Marco 衝突處理</div>
              <div style="display:flex; flex-direction:column; gap:7px; font-size:0.83rem;">
                <label>插入至目標流程位置：
                  <select onchange="TSW_STATE.insertPosition=this.value" style="margin-left:4px; padding:4px 6px; border:1px solid #94A3B8; border-radius:5px;">
                    <option value="before_teardown" ${TSW.insertPosition === 'before_teardown' ? 'selected' : ''}>接在主測試尾端（Phase 97 之前）</option>
                    <option value="after_pretest" ${TSW.insertPosition === 'after_pretest' ? 'selected' : ''}>接在 Phase 0 CheckRoute 之後</option>
                  </select>
                </label>
                <label>若目標已有同名 Marco：
                  <select onchange="TSW_STATE.marcoConflict=this.value" style="margin-left:4px; padding:4px 6px; border:1px solid #94A3B8; border-radius:5px;">
                    <option value="skip" ${TSW.marcoConflict === 'skip' ? 'selected' : ''}>沿用目標既有（不覆蓋）</option>
                    <option value="overwrite" ${TSW.marcoConflict === 'overwrite' ? 'selected' : ''}>以來源範本覆蓋</option>
                    <option value="rename" ${TSW.marcoConflict === 'rename' ? 'selected' : ''}>另存新名保留兩者</option>
                  </select>
                </label>
              </div>
              ${allIniEntries.length ? `
                <div style="margin-top:8px; padding-top:8px; border-top:1px solid #E2E8F0;">
                  <div style="font-weight:800; font-size:0.83rem; margin-bottom:4px;">⚙️ 連帶搬移的 Global.ini 參數（${allIniEntries.length} 項，可直接改預設值）</div>
                  <div style="max-height:130px; overflow-y:auto; display:grid; grid-template-columns:1fr; gap:4px;">
                    ${allIniEntries.slice(0, 14).map((e) => {
                      const storeVal = e.sec === 'Settings'
                        ? (TSW.iniSettingsOv[e.k] !== undefined ? TSW.iniSettingsOv[e.k] : e.v)
                        : (TSW.iniScriptsOv[e.k] !== undefined ? TSW.iniScriptsOv[e.k] : e.v);
                      return `<div style="display:flex; align-items:center; gap:6px; font-size:0.8rem;">
                        <span class="mono" style="min-width:130px; color:#334155; font-weight:700;">[${e.sec}] ${_esc(e.k)}</span>
                        <input type="text" value="${_esc(storeVal)}" class="mono" style="flex:1; padding:2px 6px; border:1px solid #CBD5E1; border-radius:4px;"
                          onchange="TSW_STATE['${e.sec === 'Settings' ? 'iniSettingsOv' : 'iniScriptsOv'}']['${_esc(e.k)}']=this.value">
                      </div>`;
                    }).join('')}
                  </div>
                </div>
              ` : ''}
            </div>
          </div>
          ${Object.keys(compFiles).length ? `
            <div style="margin-top:8px; background:#FFFFFF; border:1px solid #86EFAC; border-radius:6px; padding:8px 10px;">
              <div style="font-weight:800; font-size:0.84rem; color:#166534;">📄 隨包複製附屬清單檔（匯出時同步寫入 System 資料夾）</div>
              ${Object.entries(compFiles).map(([cf, txt]) => `
                <div style="margin-top:6px;">
                  <div class="mono" style="font-weight:700; font-size:0.8rem;">${_esc(cf)}</div>
                  <textarea rows="2" class="mono" style="width:100%; font-size:0.79rem; padding:4px 6px; border:1px solid #CBD5E1; border-radius:4px; box-sizing:border-box;"
                    onchange="TSW_STATE.compOv['${_esc(cf)}']=this.value">${_esc(TSW.compOv[cf] !== undefined ? TSW.compOv[cf] : txt)}</textarea>
                </div>
              `).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }

    return transplantHtml + _renderSku5QuestionHtml();
  }

  function _renderSku5QuestionHtml() {
    const sk = TSW.sku;
    const availSections = _collectAvailableSectionsForGuard();

    const branchesHtml = (sk.sku_branches || []).map((br, idx) => `
      <tr>
        <td style="padding:4px;"><input type="text" value="${_esc(br.code)}" class="mono" style="width:100%; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.sku_branches[${idx}].code=this.value.trim(); window.tswRefreshStep2();"></td>
        <td style="padding:4px;"><input type="text" value="${_esc(br.label || '')}" style="width:100%; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.sku_branches[${idx}].label=this.value"></td>
        <td style="padding:4px;"><input type="text" value="${_esc(br.iplas_model || '')}" class="mono" placeholder="選填" style="width:100%; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.sku_branches[${idx}].iplas_model=this.value.trim()"></td>
        <td style="padding:4px;"><input type="text" value="${_esc(br.expected_hw || '')}" class="mono" placeholder="例: 11" style="width:100%; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.sku_branches[${idx}].expected_hw=this.value.trim()"></td>
        <td style="padding:4px;"><input type="text" value="${_esc(br.dut_write_cmd || '')}" class="mono" placeholder="選填指令" style="width:100%; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.sku_branches[${idx}].dut_write_cmd=this.value.trim()"></td>
        <td style="padding:4px; text-align:center;"><button type="button" class="tsw-btn-soft" style="color:#B91C1C; border-color:#FCA5A5;" onclick="TSW_STATE.sku.sku_branches.splice(${idx},1); window.tswRefreshStep2();">✕</button></td>
      </tr>
    `).join('');

    const skuCodes = (sk.sku_branches || []).map((b) => b.code).filter(Boolean);
    const guardRowsHtml = availSections.map((sec) => {
      const existingIdx = (sk.section_guards || []).findIndex((g) => g.section_title.toLowerCase() === sec.section_title.toLowerCase());
      const gd = existingIdx >= 0 ? sk.section_guards[existingIdx] : null;
      const isActive = !!gd;
      const checksHtml = skuCodes.map((code) => {
        const checked = isActive ? (gd.allowed_skus || []).includes(code) : true;
        return `<label style="display:inline-flex; align-items:center; gap:3px; margin-right:8px; font-size:0.8rem; font-weight:700; cursor:pointer;">
          <input type="checkbox" ${checked ? 'checked' : ''} onchange="tswToggleSectionGuardSku('${_esc(sec.section_title)}','${_esc(sec.target_block_key)}','${_esc(code)}',this.checked)">
          <span>${_esc(code)}</span>
        </label>`;
      }).join('');
      return `
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; padding:6px 8px; background:${isActive ? '#EEF2FF' : '#F8FAFC'}; border:1px solid ${isActive ? '#818CF8' : '#E2E8F0'}; border-radius:6px;">
          <div style="font-size:0.83rem; font-weight:800; color:#0F172A;">
            <span class="tsw-tag" style="background:#E2E8F0; color:#334155;">${_esc(sec.badge)}</span>
            ${_esc(sec.section_title)}
            ${isActive ? '<span class="tsw-tag" style="background:#C7D2FE;color:#3730A3;margin-left:4px;">已套用 4:1,end 閘門</span>' : ''}
          </div>
          <div style="display:flex; align-items:center; flex-wrap:wrap; gap:4px;">
            <span style="font-size:0.78rem; color:#475569; margin-right:4px;">允許執行的 SKU：</span>
            ${checksHtml}
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="tsw-sec-card" style="border-color:#818CF8;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
          <label style="display:flex; align-items:center; gap:8px; font-weight:900; font-size:0.98rem; color:#312E81; cursor:pointer;">
            <input type="checkbox" ${sk.enabled ? 'checked' : ''} style="width:18px; height:18px; cursor:pointer;" onchange="TSW_STATE.sku.enabled=this.checked; window.tswRefreshStep2();">
            <span>🎯 Card B：引導式 5 題「SFIS 動態取 SKU ＋ 衍生品分流」精靈</span>
          </label>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button type="button" class="tsw-btn-soft" onclick="tswApplySkuPreset('derivative_3')">🧩 範例 1：整機 / 無電池 / 無WiFi (3 SKU)</button>
            <button type="button" class="tsw-btn-soft" onclick="tswApplySkuPreset('fwdl_69mo')">📋 範例 2：FWDL 69MO.txt 工單名單分流</button>
            <button type="button" class="tsw-btn-soft" onclick="tswApplySkuPreset('lock_cc')">🌐 範例 3：LOCK 國別碼 SNE vs DUT 比對</button>
          </div>
        </div>

        <div style="${sk.enabled ? '' : 'opacity:0.55; pointer-events:none;'} display:flex; flex-direction:column; gap:12px;">
          <!-- Q1 -->
          <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
            <div style="font-weight:800; color:#0F172A; margin-bottom:6px;">第 1 題｜SKU / 機種資訊要從 SFIS 哪一個欄位抓？</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px;">
              <label style="font-size:0.82rem; font-weight:700;">SFIS 查詢類型：
                <select onchange="TSW_STATE.sku.source_mode=this.value; window.tswRefreshStep2();" style="width:100%; margin-top:3px; padding:5px; border:1px solid #94A3B8; border-radius:5px;">
                  <option value="CUSTITEM" ${sk.source_mode === 'CUSTITEM' ? 'selected' : ''}>CUSTITEM (SFIS SKU Code · 如 LOCK R34)</option>
                  <option value="ISN_ITEMINFO" ${sk.source_mode === 'ISN_ITEMINFO' ? 'selected' : ''}>ISN_ITEMINFO (工單 69MO / 90MO · 如 FWDL)</option>
                  <option value="ITEM_CUSTINFO_N" ${sk.source_mode === 'ITEM_CUSTINFO_N' ? 'selected' : ''}>ITEM_CUSTINFO_N (CUSTINFO01..06)</option>
                  <option value="ISN_BASEINFO" ${sk.source_mode === 'ISN_BASEINFO' ? 'selected' : ''}>ISN_BASEINFO (基本欄位如 SNE 國別碼)</option>
                  <option value="MANUAL_ONLY" ${sk.source_mode === 'MANUAL_ONLY' ? 'selected' : ''}>不連 SFIS（純讀 Global.ini 預設值）</option>
                </select>
              </label>
              ${(sk.source_mode === 'ITEM_CUSTINFO_N' || sk.source_mode === 'ISN_BASEINFO') ? `
                <label style="font-size:0.82rem; font-weight:700;">欄位名稱：
                  <input type="text" value="${_esc(sk.cust_field)}" class="mono" style="width:100%; margin-top:3px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;" onchange="TSW_STATE.sku.cust_field=this.value.trim()">
                </label>
              ` : ''}
              <label style="font-size:0.82rem; font-weight:700;">查詢條碼變數：
                <input type="text" value="${_esc(sk.isn_var)}" class="mono" style="width:100%; margin-top:3px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;" onchange="TSW_STATE.sku.isn_var=this.value.trim()">
              </label>
              <label style="font-size:0.82rem; font-weight:700;">存入暫存變數 ($Var)：
                <input type="text" value="${_esc(sk.result_var)}" class="mono" style="width:100%; margin-top:3px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;" onchange="TSW_STATE.sku.result_var=this.value.trim()">
              </label>
            </div>
          </div>

          <!-- Q2 -->
          <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
            <div style="font-weight:800; color:#0F172A; margin-bottom:6px;">第 2 題｜判斷邏輯屬於哪一種「SKU 比對模式」？</div>
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
              <label style="display:flex; align-items:center; gap:5px; font-size:0.84rem; font-weight:700; cursor:pointer;">
                <input type="radio" name="tswCmpMode" ${sk.compare_mode === 'BRANCH_RULES' ? 'checked' : ''} onchange="TSW_STATE.sku.compare_mode='BRANCH_RULES'; window.tswRefreshStep2();">
                <span>🔀 多 SKU 規則分流 (2~N 種衍生機種)</span>
              </label>
              <label style="display:flex; align-items:center; gap:5px; font-size:0.84rem; font-weight:700; cursor:pointer;">
                <input type="radio" name="tswCmpMode" ${sk.compare_mode === 'EXTERNAL_TXT' ? 'checked' : ''} onchange="TSW_STATE.sku.compare_mode='EXTERNAL_TXT'; window.tswRefreshStep2();">
                <span>📄 外部名單檔比對 (.txt · 如 69MO.txt / 90MO.txt)</span>
              </label>
              <label style="display:flex; align-items:center; gap:5px; font-size:0.84rem; font-weight:700; cursor:pointer;">
                <input type="radio" name="tswCmpMode" ${sk.compare_mode === 'DUT_COMPARE' ? 'checked' : ''} onchange="TSW_STATE.sku.compare_mode='DUT_COMPARE'; window.tswRefreshStep2();">
                <span>🔌 一對一比對 DUT 指令回傳 (如國別碼 / SKU 回讀)</span>
              </label>
            </div>
          </div>

          <!-- Q3 -->
          <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">
              <span style="font-weight:800; color:#0F172A;">第 3 題｜每個 SKU / 分支的規格動作 ＋ 整段測項篩選</span>
              <button type="button" class="tsw-btn-soft" onclick="TSW_STATE.sku.sku_branches.push({code:'SKU_NEW',label:'新分支',iplas_model:'',expected_hw:'',dut_write_cmd:''}); window.tswRefreshStep2();">➕ 新增 SKU 分支</button>
            </div>
            ${sk.compare_mode === 'EXTERNAL_TXT' ? `
              <div style="display:grid; grid-template-columns:180px 1fr; gap:8px; margin-bottom:8px;">
                <label style="font-size:0.82rem; font-weight:700;">名單檔名：
                  <input type="text" value="${_esc(sk.txt_filename)}" class="mono" style="width:100%; margin-top:3px; padding:5px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.txt_filename=this.value.trim()">
                </label>
                <label style="font-size:0.82rem; font-weight:700;">名單內容（寫入 .\\System\\${_esc(sk.txt_filename)}）：
                  <textarea rows="2" class="mono" style="width:100%; margin-top:3px; padding:5px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.txt_content=this.value">${_esc(sk.txt_content)}</textarea>
                </label>
              </div>
            ` : ''}
            ${sk.compare_mode === 'DUT_COMPARE' ? `
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
                <label style="font-size:0.82rem; font-weight:700;">DUT 查詢指令（不含連線前綴）：
                  <input type="text" value="${_esc(sk.dut_query_cmd)}" class="mono" style="width:100%; margin-top:3px; padding:5px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.dut_query_cmd=this.value">
                </label>
                <label style="font-size:0.82rem; font-weight:700;">回傳字串擷取前標（至 \\n 為止）：
                  <input type="text" value="${_esc(sk.dut_prefix_kw)}" class="mono" style="width:100%; margin-top:3px; padding:5px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.dut_prefix_kw=this.value">
                </label>
              </div>
            ` : ''}
            ${sk.compare_mode !== 'DUT_COMPARE' ? `
              <table style="width:100%; border-collapse:collapse; font-size:0.82rem; background:#FFFFFF; border:1px solid #CBD5E1;">
                <thead>
                  <tr style="background:#E2E8F0; color:#0F172A;">
                    <th style="padding:5px; text-align:left;">匹配值 / SKU 代碼</th>
                    <th style="padding:5px; text-align:left;">中文說明</th>
                    <th style="padding:5px; text-align:left;">切換 iPLAS Model (:SetModelName)</th>
                    <th style="padding:5px; text-align:left;">驗證版號/HW</th>
                    <th style="padding:5px; text-align:left;">寫入 DUT 指令</th>
                    <th style="padding:5px; width:42px;">刪除</th>
                  </tr>
                </thead>
                <tbody>${branchesHtml}</tbody>
              </table>
            ` : ''}
            ${availSections.length > 0 && skuCodes.length > 0 ? `
              <div style="margin-top:10px; padding-top:8px; border-top:1px dashed #CBD5E1;">
                <div style="font-weight:800; font-size:0.83rem; color:#312E81; margin-bottom:6px;">✂️ 衍生品整段測項篩選（取消勾選某 SKU 即自動為該區塊加入 <code>4:1,end</code> 略過保護）：</div>
                <div style="display:flex; flex-direction:column; gap:6px;">${guardRowsHtml}</div>
              </div>
            ` : ''}
          </div>

          <!-- Q4 & Q5 -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:10px;">
            <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
              <div style="font-weight:800; color:#0F172A; margin-bottom:6px;">第 4 題｜離線退路與例外防呆</div>
              <label style="display:flex; align-items:center; gap:6px; font-size:0.83rem; font-weight:700; margin-bottom:6px; cursor:pointer;">
                <input type="checkbox" ${sk.offline_wrap ? 'checked' : ''} onchange="TSW_STATE.sku.offline_wrap=this.checked">
                <span>自動包一層 <code>:SfEnabled</code> 離線雙用旁路</span>
              </label>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                <label style="font-size:0.81rem; font-weight:700;">離線預設 SKU (寫入 Global.ini)：
                  <input type="text" value="${_esc(sk.offline_default_sku)}" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.offline_default_sku=this.value.trim()">
                </label>
                <label style="font-size:0.81rem; font-weight:700;">所有 SKU 皆未匹配時：
                  <select onchange="TSW_STATE.sku.no_match_policy=this.value" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px;">
                    <option value="FAIL" ${sk.no_match_policy === 'FAIL' ? 'selected' : ''}>強制判 FAIL (:Delay,"000" 停損)</option>
                    <option value="DEFAULT" ${sk.no_match_policy === 'DEFAULT' ? 'selected' : ''}>繼續往下執行</option>
                  </select>
                </label>
              </div>
            </div>

            <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
              <div style="font-weight:800; color:#0F172A; margin-bottom:6px;">第 5 題｜目標站別、通訊通道與總開關</div>
              <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;">
                <label style="font-size:0.81rem; font-weight:700;">DUT 通訊別名：
                  <input type="text" value="${_esc(sk.dut_conn)}" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.dut_conn=this.value.trim()||'UART'">
                </label>
                <label style="font-size:0.81rem; font-weight:700;">EndPrompt：
                  <input type="text" value="${_esc(sk.end_prompt)}" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.end_prompt=this.value">
                </label>
                <label style="font-size:0.81rem; font-weight:700;">INI 總開關名 (選填)：
                  <input type="text" value="${_esc(sk.toggle_var)}" placeholder="例 CHECK_SKU" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.toggle_var=this.value.trim()">
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  window.tswRefreshStep2 = function () {
    if (TSW.step === 2) _renderCurrentStep();
  };

  window.tswToggleSectionGuardSku = function (sectionTitle, blockKey, skuCode, checked) {
    const allCodes = (TSW.sku.sku_branches || []).map((b) => b.code).filter(Boolean);
    let idx = (TSW.sku.section_guards || []).findIndex((g) => g.section_title.toLowerCase() === sectionTitle.toLowerCase());
    if (idx < 0) {
      TSW.sku.section_guards.push({
        section_title: sectionTitle,
        target_block_key: blockKey || '',
        allowed_skus: [...allCodes],
      });
      idx = TSW.sku.section_guards.length - 1;
    }
    const gd = TSW.sku.section_guards[idx];
    const set = new Set(gd.allowed_skus || []);
    if (checked) set.add(skuCode);
    else set.delete(skuCode);
    gd.allowed_skus = Array.from(set);
    // If all SKUs are allowed, guard is unnecessary -> remove cleanly
    if (gd.allowed_skus.length >= allCodes.length) {
      TSW.sku.section_guards.splice(idx, 1);
    }
    _renderCurrentStep();
  };

  window.tswApplySkuPreset = function (presetKey) {
    TSW.sku.enabled = true;
    if (presetKey === 'derivative_3') {
      TSW.sku.title_name = 'SFIS SKU Dynamic Routing';
      TSW.sku.source_mode = 'CUSTITEM';
      TSW.sku.isn_var = '*(ISN)';
      TSW.sku.result_var = 'sfSKUCode';
      TSW.sku.compare_mode = 'BRANCH_RULES';
      TSW.sku.offline_wrap = true;
      TSW.sku.offline_default_sku = 'FULL';
      TSW.sku.no_match_policy = 'FAIL';
      TSW.sku.dut_conn = 'UART';
      TSW.sku.sku_branches = [
        { code: 'FULL', label: '整機全配', iplas_model: 'OLYMPUS_FULL', expected_hw: '11', dut_write_cmd: '' },
        { code: 'NO_BAT', label: '整機無電池', iplas_model: 'OLYMPUS_NBAT', expected_hw: '11', dut_write_cmd: '' },
        { code: 'NO_WIFI', label: '整機無WiFi模組', iplas_model: 'OLYMPUS_NOWF', expected_hw: '10', dut_write_cmd: '' },
      ];
    } else if (presetKey === 'fwdl_69mo') {
      TSW.sku.title_name = 'SFIS 69MO Hardware Check';
      TSW.sku.source_mode = 'ISN_ITEMINFO';
      TSW.sku.isn_var = '*(ISN)';
      TSW.sku.result_var = 'sf69MO';
      TSW.sku.compare_mode = 'EXTERNAL_TXT';
      TSW.sku.txt_filename = '69MO.txt';
      TSW.sku.txt_content = 'A=24386522\nB=1B412008\nC=24386530';
      TSW.sku.offline_wrap = true;
      TSW.sku.offline_default_sku = '24386522';
      TSW.sku.dut_conn = 'UART';
      TSW.sku.dut_query_cmd = 'mfg get-hw-version';
      TSW.sku.dut_prefix_kw = 'HardwareVersion:';
      TSW.sku.sku_branches = [
        { code: 'A', label: '清單命中版 HW11', expected_hw: '11', iplas_model: '', dut_write_cmd: '' },
        { code: 'B', label: '預設版 HW10', expected_hw: '10', iplas_model: '', dut_write_cmd: '' },
      ];
    } else if (presetKey === 'lock_cc') {
      TSW.sku.title_name = 'Compare Country Code';
      TSW.sku.source_mode = 'ISN_BASEINFO';
      TSW.sku.cust_field = 'SNE';
      TSW.sku.isn_var = '*(ISN)';
      TSW.sku.result_var = 'sfCC';
      TSW.sku.compare_mode = 'DUT_COMPARE';
      TSW.sku.offline_wrap = true;
      TSW.sku.offline_default_sku = 'US';
      TSW.sku.dut_conn = 'LinuxUART';
      TSW.sku.dut_query_cmd = 'mfg wifi get-country-code';
      TSW.sku.dut_prefix_kw = 'countrycodeis';
    }
    _renderCurrentStep();
  };

  function _buildRequestPayload(previewFlag) {
    const bundleSpec = {
      source_xlsx: (TSW.inspected && TSW.inspected.source_path) || '',
      selected_block_keys: Array.from(TSW.selectedKeys),
      paused_block_keys: Array.from(TSW.pausedKeys),
      inst_remap: TSW.instRemap,
      conn_remap: TSW.connRemap,
      ini_overrides: { Settings: TSW.iniSettingsOv, Scripts: TSW.iniScriptsOv },
      companion_overrides: TSW.compOv,
      insert_position: TSW.insertPosition,
      marco_conflict: TSW.marcoConflict,
    };
    const body = {
      target_mode: TSW.targetMode,
      project_name: _getTargetProjectName(),
      station_name: _getTargetStationName(),
      bundle_spec: bundleSpec,
      sku_spec: JSON.parse(JSON.stringify(TSW.sku)),
      preview: !!previewFlag,
    };
    if (TSW.targetMode === 'edit' && window.STATE && window.STATE.workspace) {
      body.workspace = window.STATE.workspace;
    }
    return body;
  }

  window.tswRunPreview = async function () {
    TSW.previewRes = { loading: true };
    if (TSW.step === 3) _renderCurrentStep();
    try {
      const res = await fetch('/api/template_bundle/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(_buildRequestPayload(true)),
      });
      TSW.previewRes = await res.json();
    } catch (err) {
      TSW.previewRes = { status: 'error', message: String(err) };
    }
    if (TSW.step === 3) _renderCurrentStep();
  };

  function _renderStep3Html() {
    const pr = TSW.previewRes;
    if (!pr || pr.loading) {
      return '<div style="padding:24px; text-align:center; font-weight:800; color:#1E40AF;">⏳ 正在預演合併並執行 Script Doctor 健檢...</div>';
    }
    if (pr.status !== 'ok') {
      return `<div style="padding:16px; background:#FEF2F2; border:1px solid #EF4444; border-radius:8px; color:#991B1B;">預覽失敗：${_esc(pr.message || '')}</div>`;
    }
    const sm = pr.summary || {};
    const rep = pr.report || { errors: [], manual_warnings: [] };
    const errs = rep.errors || [];
    const warns = rep.manual_warnings !== undefined ? rep.manual_warnings : (rep.warnings || []);

    const stSteps = ((pr.workspace && pr.workspace.stations && pr.workspace.stations[pr.station_name]) || []).slice(0, 40);
    const rowsHtml = stSteps.map((r, i) => `
      <tr style="border-bottom:1px solid #E2E8F0; background:${r.Title ? '#F8FAFC' : '#FFFFFF'};">
        <td class="mono" style="padding:3px 6px;">${i}</td>
        <td class="mono" style="padding:3px 6px; font-weight:700;">${_esc(r.Phase || '')}</td>
        <td style="padding:3px 6px; font-weight:700; color:#1E3A8A;">${_esc(r.Title || '')}</td>
        <td class="mono" style="padding:3px 6px;">${_esc(r.Send || '')}</td>
        <td class="mono" style="padding:3px 6px;">${_esc(r.Reply || '')}</td>
        <td class="mono" style="padding:3px 6px;">${_esc(r.Ref || '')}</td>
        <td class="mono" style="padding:3px 6px; color:#7C3AED; font-weight:700;">${_esc(r.ExecMode || '')}</td>
      </tr>
    `).join('');

    return `
      <div class="tsw-sec-card" style="background:${errs.length === 0 && warns.length === 0 ? '#F0FDF4' : '#FFFBEB'}; border-color:${errs.length === 0 ? '#22C55E' : '#F59E0B'};">
        <div style="font-weight:900; font-size:0.98rem; color:#0F172A; margin-bottom:6px;">
          ${errs.length === 0 && warns.length === 0 ? '🟢 Script Doctor 預檢通過：0 Error / 0 Warning' : `⚠️ 檢出 ${errs.length} 錯誤 / ${warns.length} 警告`}
        </div>
        <div style="font-size:0.85rem; line-height:1.65; color:#1E293B;">
          <div>📌 <b>目標站別：</b><code>${_esc(sm.target_station)}</code></div>
          <div>🧩 <b>移植測項 (${(sm.transplanted_blocks || []).length})：</b>${(sm.transplanted_blocks || []).map(_esc).join('、') || '無（僅建立 SKU 規則）'}</div>
          <div>🎯 <b>SKU 積木：</b>新增 <b>${sm.sku_steps_added || 0}</b> 列 ${(sm.sku_summary || []).map((x) => `｜ ${_esc(x)}`).join('')}</div>
          ${(sm.guarded_sections || []).length ? `<div>✂️ <b>已掛載衍生品閘門：</b>${sm.guarded_sections.map((g) => `<code>${_esc(g)}</code>`).join('、')}</div>` : ''}
          <div>⚙️ <b>相依補齊：</b>Marco (${(sm.marcos_added || []).length}) ｜ 儀器 (${(sm.instruments_added || []).length}) ｜ DUT 連線 (${(sm.connections_added || []).length}) ｜ INI 參數 (${(sm.ini_vars_added || []).length}) ｜ 附屬檔 (${(sm.companion_files || []).join(', ') || '無'})</div>
        </div>
      </div>
      <div class="tsw-sec-card">
        <div style="font-weight:800; font-size:0.88rem; margin-bottom:6px;">📋 合併後流程預覽（顯示前 ${stSteps.length} 列）</div>
        <div style="max-height:300px; overflow:auto; border:1px solid #CBD5E1; border-radius:6px;">
          <table style="width:100%; border-collapse:collapse; font-size:0.79rem;">
            <thead><tr style="background:#E2E8F0; text-align:left;"><th style="padding:4px 6px;">#</th><th style="padding:4px 6px;">Phase</th><th style="padding:4px 6px;">Title</th><th style="padding:4px 6px;">Send</th><th style="padding:4px 6px;">Reply</th><th style="padding:4px 6px;">Ref</th><th style="padding:4px 6px;">ExecMode</th></tr></thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  window.tswApplyToTarget = async function () {
    const reqBody = _buildRequestPayload(false);
    if (TSW.targetMode === 'create') {
      // Save bundle_spec & sku_spec into STATE for Step 4 /api/generate_new_standalone
      if (!window.STATE) window.STATE = {};
      window.STATE.createTemplateBundle = reqBody.bundle_spec;
      window.STATE.createSkuConfig = reqBody.sku_spec;
      window.STATE.createTemplatePreviewSummary = (TSW.previewRes && TSW.previewRes.summary) || null;
      _renderCreateModeBanner();
      closeTemplateSkuWizard();
      return;
    }

    // Mode 01: EDIT — merge right into STATE.workspace and refresh editor
    const pr = TSW.previewRes;
    let appliedData = pr;
    if (!appliedData || appliedData.status !== 'ok') {
      const res = await fetch('/api/template_bundle/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody),
      });
      appliedData = await res.json();
    }
    if (!appliedData || appliedData.status !== 'ok') {
      alert('套用失敗：' + ((appliedData && appliedData.message) || ''));
      return;
    }
    window.STATE.workspace = appliedData.workspace;
    window.STATE.report = appliedData.report;
    if (!window.STATE.pendingInserts) window.STATE.pendingInserts = [];
    const sm = appliedData.summary || {};
    window.STATE.pendingInserts.push({
      sheet: sm.target_station || _getTargetStationName(),
      inst: '範本移植 + SKU 精靈',
      summary: `移植 ${(sm.transplanted_blocks || []).length} 區塊 · SKU ${sm.sku_steps_added || 0} 步${(sm.guarded_sections || []).length ? ` · 閘門 ${sm.guarded_sections.length} 處` : ''}`,
    });
    closeTemplateSkuWizard();
    if (typeof window.renderAuditResults === 'function') window.renderAuditResults();
    if (typeof window.bsLoadBlocks === 'function') {
      try { await window.bsLoadBlocks(true); } catch (_e) {}
    }
  };

  function _renderCreateModeBanner() {
    const banner = document.getElementById('wizTemplateSkuBanner');
    if (!banner || !window.STATE) return;
    const tb = window.STATE.createTemplateBundle || {};
    const sk = window.STATE.createSkuConfig || {};
    const sm = window.STATE.createTemplatePreviewSummary || {};
    const hasBlk = (tb.selected_block_keys || []).length > 0;
    const hasSku = !!sk.enabled;
    if (!hasBlk && !hasSku) {
      banner.style.display = 'none';
      banner.innerHTML = '';
      return;
    }
    banner.style.display = 'block';
    banner.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:0.86rem; color:#312E81;">
          <b>🧩 已掛載「範本移植 ＋ 引導式 SKU」組件：</b>
          ${hasBlk ? `移植 <b>${tb.selected_block_keys.length}</b> 個範本測項` : ''}
          ${hasBlk && hasSku ? ' ＋ ' : ''}
          ${hasSku ? `SKU 精靈 (<b>${(sk.sku_branches || []).length}</b> 分支 / <code>${_esc(sk.source_mode)}</code>)` : ''}
          ${(sm.guarded_sections || []).length ? ` ｜ 衍生品閘門 <b>${sm.guarded_sections.length}</b> 處` : ''}
        </div>
        <div style="display:flex; gap:6px;">
          <button type="button" class="tsw-btn-soft" onclick="openTemplateSkuWizard('create')">✏️ 修改設定</button>
          <button type="button" class="tsw-btn-soft" style="color:#B91C1C; border-color:#FCA5A5;" onclick="window.STATE.createTemplateBundle=null; window.STATE.createSkuConfig=null; window.STATE.createTemplatePreviewSummary=null; document.getElementById('wizTemplateSkuBanner').style.display='none';">🧹 清除</button>
        </div>
      </div>
    `;
  }

  window.tswGetCreatePayloadExtras = function () {
    const out = {};
    if (window.STATE && window.STATE.createTemplateBundle) {
      out.template_bundle = window.STATE.createTemplateBundle;
    }
    if (window.STATE && window.STATE.createSkuConfig && window.STATE.createSkuConfig.enabled) {
      out.sku_wizard = window.STATE.createSkuConfig;
    }
    return out;
  };
})();
