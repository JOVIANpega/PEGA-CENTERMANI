// Centimani Studio - Ultra-Simple 1-Page Guided Multi-SKU Wizard
// Shared by BOTH '01 / EDIT' (Existing TestFlow) and '02 / CREATE' (0 -> 1 Blank Mother)

(function () {
  'use strict';

  const TSW = {
    targetMode: 'create', // 'create' | 'edit'
    reason: 'derivative', // 'derivative' | 'version' | 'country' | 'custom'
    expandedLimitRows: new Set(),
    previewOpen: false,
    previewRes: null,
    customGuardInput: '',
    sku: {
      enabled: true,
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
      param_to_ini: true,
      toggle_var: '',
      dut_conn: 'UART',
      end_prompt: '/#',
      dut_query_cmd: 'mfg wifi get-country-code',
      dut_prefix_kw: 'countrycodeis',
      post_merge_cmds: '',
      sku_branches: [
        { code: 'FULL', label: '整機全配', iplas_model: 'MODEL_FULL', expected_hw: '', dut_write_cmd: '', limit_var: 'gCurr', limit_type: '%f', dl: '', ul: '', limit_cmd: '' },
        { code: 'NO_BAT', label: '整機無電池', iplas_model: 'MODEL_NBAT', expected_hw: '', dut_write_cmd: '', limit_var: 'gCurr', limit_type: '%f', dl: '', ul: '', limit_cmd: '' },
        { code: 'NO_WIFI', label: '整機無WiFi模組', iplas_model: 'MODEL_NOWF', expected_hw: '', dut_write_cmd: '', limit_var: 'gCurr', limit_type: '%f', dl: '', ul: '', limit_cmd: '' },
      ],
      section_guards: [], // [{ section_title, allowed_skus: [...] }]
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

  function _ensureModalDom() {
    if (!document.getElementById('tswStyles')) {
      const st = document.createElement('style');
      st.id = 'tswStyles';
      st.textContent = `
        .tsw-reason-btn { cursor:pointer; padding:8px 13px; border-radius:8px; border:1.5px solid #CBD5E1; background:#F8FAFC; color:#1E293B; font-weight:800; font-size:0.86rem; transition:all 0.15s; text-align:left; }
        .tsw-reason-btn:hover { background:#E0F2FE; border-color:#38BDF8; color:#0369A1; }
        .tsw-reason-btn.active { background:#EEF2FF; border-color:#4F46E5; color:#312E81; box-shadow:0 2px 6px rgba(79,70,229,0.18); }
        .tsw-btn-soft { cursor:pointer; padding:5px 11px; border-radius:6px; border:1px solid #CBD5E1; background:#F8FAFC; color:#1E293B; font-weight:700; font-size:0.82rem; transition:all 0.15s; }
        .tsw-btn-soft:hover { background:#E0F2FE; border-color:#38BDF8; color:#0369A1; }
        .tsw-card { background:#FFFFFF; border:1.5px solid #CBD5E1; border-radius:10px; padding:12px 15px; margin-bottom:12px; }
        .tsw-tag { display:inline-block; padding:2px 8px; border-radius:999px; font-size:0.76rem; font-weight:800; }
      `;
      document.head.appendChild(st);
    }
    if (!document.getElementById('templateSkuModal')) {
      const m = document.createElement('div');
      m.id = 'templateSkuModal';
      m.className = 'modal-backdrop';
      m.onclick = function (e) { if (e.target === m) closeTemplateSkuWizard(); };
      m.innerHTML = `
        <div class="modal-panel" style="max-width:960px; width:96vw; max-height:92vh; display:flex; flex-direction:column; background:#F8FAFC; border:2px solid #4F46E5; padding:0; overflow:hidden;">
          <div style="background:#FFFFFF; padding:12px 18px; border-bottom:1.5px solid #CBD5E1; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
              <span style="font-size:1.12rem; font-weight:900; color:#1E1B4B;">🎯 多 SKU 分流設定精靈</span>
              <span id="tswTargetBadge" class="tsw-tag" style="background:#E0F2FE; color:#0369A1; font-size:0.82rem;"></span>
            </div>
            <button type="button" onclick="closeTemplateSkuWizard()" class="btn btn-modal-close" style="padding:4px 12px;">✕ 關閉</button>
          </div>
          <div id="tswBody" style="flex:1; overflow-y:auto; padding:14px 18px;"></div>
          <div style="background:#FFFFFF; padding:10px 18px; border-top:1.5px solid #CBD5E1; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
              <span id="tswFooterStatus" style="font-size:0.84rem; color:#475569; font-weight:700;"></span>
              <button type="button" class="tsw-btn-soft" onclick="tswTogglePreview()">👁️ 預覽產出步驟</button>
            </div>
            <button type="button" class="btn btn-primary-green" onclick="tswApplyToTarget()" style="padding:8px 22px; font-weight:900; font-size:0.94rem;">✅ 套用並準備產出 Excel</button>
          </div>
        </div>
      `;
      document.body.appendChild(m);
    }
  }

  window.TSW_STATE = TSW;

  window.openTemplateSkuWizard = function (mode) {
    _ensureModalDom();
    if (mode === 'edit' && (!window.STATE || !window.STATE.workspace || !window.STATE.workspace.stations)) {
      alert('請先載入一份要編修的 TestFlow.xlsx（或點左側「產生首次使用空範本」從零建立）。');
      return;
    }
    TSW.targetMode = (mode === 'edit') ? 'edit' : 'create';
    TSW.previewOpen = false;
    TSW.previewRes = null;

    if (TSW.targetMode === 'create' && window.STATE && window.STATE.createSkuConfig) {
      TSW.sku = JSON.parse(JSON.stringify(window.STATE.createSkuConfig));
    }
    TSW.sku.enabled = true;

    const badge = document.getElementById('tswTargetBadge');
    if (badge) {
      badge.textContent = TSW.targetMode === 'edit'
        ? `✏️ 既有編修：${_getTargetStationName()}`
        : `🌱 新案建置 (0 → 1)：${_getTargetStationName()}`;
    }

    document.getElementById('templateSkuModal').classList.add('open');
    _renderSinglePage();
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

  function _collectTargetSections() {
    const items = [];
    const seen = new Set();
    if (TSW.targetMode === 'edit' && window.STATE && window.STATE.workspace) {
      const stName = _getTargetStationName();
      const rows = (window.STATE.workspace.stations && window.STATE.workspace.stations[stName]) || [];
      rows.forEach((r) => {
        const t = String(r.Title || '').trim();
        if (!t || /^1,End/i.test(t) || /CheckRoute|SFIS SKU/i.test(t)) return;
        const lbl = t.includes(',') ? t.split(',').slice(1).join(',').trim() : t;
        if (lbl && !seen.has(lbl.toLowerCase())) {
          seen.add(lbl.toLowerCase());
          items.push({ section_title: lbl, badge: '目前測項' });
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
          items.push({ section_title: lbl, badge: '已選積木' });
        }
      });
      (window.STATE.genCustomInsts || []).forEach((ci) => {
        if (ci.title_name && !seen.has(ci.title_name.toLowerCase())) {
          seen.add(ci.title_name.toLowerCase());
          items.push({ section_title: ci.title_name, badge: '儀器測項' });
        }
      });
      (window.STATE.genNi6009Blocks || []).forEach((nb) => {
        const nm = nb.title_name || 'Measure Voltage Test';
        if (!seen.has(nm.toLowerCase())) {
          seen.add(nm.toLowerCase());
          items.push({ section_title: nm, badge: 'DAQ 電壓' });
        }
      });
      (window.STATE.genRfBlocks || []).forEach((rb) => {
        const nm = rb.title_name || 'WIFI RF Test';
        if (!seen.has(nm.toLowerCase())) {
          seen.add(nm.toLowerCase());
          items.push({ section_title: nm, badge: 'RF 測項' });
        }
      });
    }
    (TSW.sku.section_guards || []).forEach((gd) => {
      if (gd.section_title && !seen.has(gd.section_title.toLowerCase())) {
        seen.add(gd.section_title.toLowerCase());
        items.push({ section_title: gd.section_title, badge: '自訂區塊' });
      }
    });
    return items;
  }

  window.tswSelectReason = function (reasonKey) {
    TSW.reason = reasonKey;
    const sk = TSW.sku;
    sk.enabled = true;
    if (reasonKey === 'derivative') {
      sk.title_name = 'SFIS SKU Dynamic Routing';
      sk.source_mode = 'CUSTITEM';
      sk.result_var = 'sfSKUCode';
      sk.compare_mode = 'BRANCH_RULES';
      sk.offline_default_sku = 'FULL';
      sk.sku_branches = [
        { code: 'FULL', label: '整機全配', iplas_model: 'MODEL_FULL', expected_hw: '', dut_write_cmd: '', limit_var: 'gCurr', limit_type: '%f', dl: '', ul: '', limit_cmd: '' },
        { code: 'NO_BAT', label: '整機無電池', iplas_model: 'MODEL_NBAT', expected_hw: '', dut_write_cmd: '', limit_var: 'gCurr', limit_type: '%f', dl: '', ul: '', limit_cmd: '' },
        { code: 'NO_WIFI', label: '整機無WiFi模組', iplas_model: 'MODEL_NOWF', expected_hw: '', dut_write_cmd: '', limit_var: 'gCurr', limit_type: '%f', dl: '', ul: '', limit_cmd: '' },
      ];
    } else if (reasonKey === 'version') {
      sk.title_name = 'SFIS Version / MO Routing';
      sk.source_mode = 'ISN_ITEMINFO';
      sk.result_var = 'sfMO';
      sk.compare_mode = 'BRANCH_RULES';
      sk.offline_default_sku = 'REV_A';
      sk.sku_branches = [
        { code: 'REV_A', label: '新硬體版 (HW11)', iplas_model: '', expected_hw: '11', dut_write_cmd: '', limit_var: 'gSpec', limit_type: '%s', dl: '', ul: '', limit_cmd: '' },
        { code: 'REV_B', label: '舊硬體版 (HW10)', iplas_model: '', expected_hw: '10', dut_write_cmd: '', limit_var: 'gSpec', limit_type: '%s', dl: '', ul: '', limit_cmd: '' },
      ];
    } else if (reasonKey === 'country') {
      sk.title_name = 'Compare Country Code';
      sk.source_mode = 'ISN_BASEINFO';
      sk.cust_field = 'SNE';
      sk.result_var = 'sfCC';
      sk.compare_mode = 'DUT_COMPARE';
      sk.offline_default_sku = 'US';
      sk.dut_conn = 'UART';
      sk.dut_query_cmd = 'mfg wifi get-country-code';
      sk.dut_prefix_kw = 'countrycodeis';
    } else if (reasonKey === 'custom') {
      sk.compare_mode = 'BRANCH_RULES';
    }
    TSW.previewRes = null;
    _renderSinglePage();
  };

  window.tswToggleRowLimit = function (idx) {
    if (TSW.expandedLimitRows.has(idx)) TSW.expandedLimitRows.delete(idx);
    else TSW.expandedLimitRows.add(idx);
    _renderSinglePage();
  };

  window.tswToggleSectionGuardSku = function (sectionTitle, skuCode, checked) {
    const allCodes = (TSW.sku.sku_branches || []).map((b) => b.code).filter(Boolean);
    let idx = (TSW.sku.section_guards || []).findIndex((g) => g.section_title.toLowerCase() === sectionTitle.toLowerCase());
    if (idx < 0) {
      TSW.sku.section_guards.push({ section_title: sectionTitle, target_block_key: '', allowed_skus: [...allCodes] });
      idx = TSW.sku.section_guards.length - 1;
    }
    const gd = TSW.sku.section_guards[idx];
    const set = new Set(gd.allowed_skus || []);
    if (checked) set.add(skuCode);
    else set.delete(skuCode);
    gd.allowed_skus = Array.from(set);
    if (gd.allowed_skus.length >= allCodes.length) {
      TSW.sku.section_guards.splice(idx, 1);
    }
    TSW.previewRes = null;
    _renderSinglePage();
  };

  window.tswAddCustomGuardSection = function () {
    const inp = document.getElementById('tswCustomSecInput');
    const title = (inp && inp.value.trim()) || '';
    if (!title) return;
    const allCodes = (TSW.sku.sku_branches || []).map((b) => b.code).filter(Boolean);
    const exists = (TSW.sku.section_guards || []).some((g) => g.section_title.toLowerCase() === title.toLowerCase());
    if (!exists) {
      TSW.sku.section_guards.push({ section_title: title, target_block_key: '', allowed_skus: allCodes.slice(0, Math.max(1, allCodes.length - 1)) });
    }
    TSW.previewRes = null;
    _renderSinglePage();
  };

  function _renderSinglePage() {
    const sk = TSW.sku;
    const skuCodes = (sk.sku_branches || []).map((b) => b.code).filter(Boolean);
    const guardsCount = (sk.section_guards || []).length;
    const statusEl = document.getElementById('tswFooterStatus');
    if (statusEl) {
      statusEl.textContent = sk.compare_mode === 'DUT_COMPARE'
        ? `國別 / 一對一比對 (${sk.source_mode} ${sk.cust_field || ''})`
        : `已設定 ${skuCodes.length} 支 SKU · ${guardsCount} 處測項閘門`;
    }

    const branchesRowsHtml = (sk.sku_branches || []).map((br, idx) => {
      const limOpen = TSW.expandedLimitRows.has(idx) || br.dl !== '' || br.ul !== '';
      return `
        <tr style="border-bottom:${limOpen ? 'none' : '1px solid #E2E8F0'};">
          <td style="padding:5px;"><input type="text" value="${_esc(br.code)}" class="mono" placeholder="例 FULL" style="width:100%; padding:5px 7px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box; font-weight:700;" onchange="TSW_STATE.sku.sku_branches[${idx}].code=this.value.trim(); TSW_STATE.previewRes=null; window.tswRerender();"></td>
          <td style="padding:5px;"><input type="text" value="${_esc(br.label || '')}" placeholder="例 整機全配" style="width:100%; padding:5px 7px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;" onchange="TSW_STATE.sku.sku_branches[${idx}].label=this.value"></td>
          <td style="padding:5px;"><input type="text" value="${_esc(br.iplas_model || '')}" class="mono" placeholder="切換機種名 (選填)" style="width:100%; padding:5px 7px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;" onchange="TSW_STATE.sku.sku_branches[${idx}].iplas_model=this.value.trim()"></td>
          <td style="padding:5px;"><input type="text" value="${_esc(br.expected_hw || '')}" class="mono" placeholder="預期版號 (選填)" style="width:100%; padding:5px 7px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;" onchange="TSW_STATE.sku.sku_branches[${idx}].expected_hw=this.value.trim()"></td>
          <td style="padding:5px; white-space:nowrap; text-align:right;">
            <button type="button" class="tsw-btn-soft" onclick="tswToggleRowLimit(${idx})" style="${limOpen ? 'background:#E0F2FE;border-color:#38BDF8;color:#0369A1;' : ''}">${limOpen ? '▾ DL/UL' : '+ DL/UL'}</button>
            <button type="button" class="tsw-btn-soft" style="color:#B91C1C; border-color:#FCA5A5; margin-left:4px;" onclick="TSW_STATE.sku.sku_branches.splice(${idx},1); window.tswRerender();">✕</button>
          </td>
        </tr>
        ${limOpen ? `
          <tr style="background:#F0F9FF; border-bottom:1px solid #BAE6FD;">
            <td colspan="5" style="padding:6px 8px;">
              <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; font-size:0.8rem;">
                <label style="font-weight:700;">量測指令：
                  <input type="text" value="${_esc(br.limit_cmd || '')}" class="mono" placeholder="例 mfg get-curr (空白則取既有變數)" style="width:185px; padding:3px 6px; border:1px solid #94A3B8; border-radius:4px;" onchange="TSW_STATE.sku.sku_branches[${idx}].limit_cmd=this.value.trim()">
                </label>
                <label style="font-weight:700;">變數：
                  <input type="text" value="${_esc(br.limit_var || 'gCurr')}" class="mono" style="width:80px; padding:3px 6px; border:1px solid #94A3B8; border-radius:4px;" onchange="TSW_STATE.sku.sku_branches[${idx}].limit_var=this.value.trim()">
                </label>
                <label style="font-weight:700;">下限 DL：
                  <input type="text" value="${_esc(br.dl || '')}" class="mono" placeholder="例 100" style="width:72px; padding:3px 6px; border:1px solid #94A3B8; border-radius:4px;" onchange="TSW_STATE.sku.sku_branches[${idx}].dl=this.value.trim()">
                </label>
                <label style="font-weight:700;">上限 UL：
                  <input type="text" value="${_esc(br.ul || '')}" class="mono" placeholder="例 300" style="width:72px; padding:3px 6px; border:1px solid #94A3B8; border-radius:4px;" onchange="TSW_STATE.sku.sku_branches[${idx}].ul=this.value.trim()">
                </label>
              </div>
            </td>
          </tr>
        ` : ''}
      `;
    }).join('');

    const availSections = _collectTargetSections();
    const matrixHtml = availSections.map((sec) => {
      const gd = (sk.section_guards || []).find((g) => g.section_title.toLowerCase() === sec.section_title.toLowerCase());
      const isGated = !!gd;
      const skippedSkus = isGated ? skuCodes.filter((c) => !(gd.allowed_skus || []).includes(c)) : [];
      return `
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; padding:7px 10px; background:${isGated ? '#EEF2FF' : '#F8FAFC'}; border:1px solid ${isGated ? '#818CF8' : '#E2E8F0'}; border-radius:7px;">
          <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <span class="tsw-tag" style="background:#E2E8F0; color:#334155;">${_esc(sec.badge)}</span>
            <span style="font-weight:800; font-size:0.86rem; color:#0F172A;">${_esc(sec.section_title)}</span>
          </div>
          <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            ${skuCodes.map((code) => {
              const checked = isGated ? (gd.allowed_skus || []).includes(code) : true;
              return `<label style="display:inline-flex; align-items:center; gap:4px; font-size:0.82rem; font-weight:700; cursor:pointer;">
                <input type="checkbox" ${checked ? 'checked' : ''} style="width:15px; height:15px; cursor:pointer;" onchange="tswToggleSectionGuardSku('${_esc(sec.section_title)}','${_esc(code)}',this.checked)">
                <span class="mono">${_esc(code)}</span>
              </label>`;
            }).join('')}
            <span style="font-size:0.77rem; font-weight:700; color:${isGated ? '#4338CA' : '#64748B'}; min-width:140px; text-align:right;">
              ${isGated ? `🔒 ExecMode 4:1,end（略過 ${skippedSkus.map(_esc).join(', ')}）` : '全部 SKU 皆執行'}
            </span>
          </div>
        </div>
      `;
    }).join('');

    const previewBoxHtml = TSW.previewOpen ? _renderPreviewBoxHtml() : '';

    document.getElementById('tswBody').innerHTML = `
      <!-- 區段 1：分 SKU 原因快選列 ＋ 收合式進階 SFIS 來源 -->
      <div class="tsw-card">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
          <span style="font-weight:900; color:#0F172A; font-size:0.95rem;">1. 這次為何要分 SKU？（點一個最接近的，欄位會自動整理）</span>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(195px, 1fr)); gap:8px;">
          <button type="button" class="tsw-reason-btn ${TSW.reason === 'derivative' ? 'active' : ''}" onclick="tswSelectReason('derivative')">
            <div>🧩 硬體模組增減</div>
            <div style="font-size:0.76rem; font-weight:600; color:#64748B;">整機 / 無電池 / 無 WiFi</div>
          </button>
          <button type="button" class="tsw-reason-btn ${TSW.reason === 'version' ? 'active' : ''}" onclick="tswSelectReason('version')">
            <div>⚙️ 版號 / 料號差異</div>
            <div style="font-size:0.76rem; font-weight:600; color:#64748B;">HW Rev / FW / 工單名單</div>
          </button>
          <button type="button" class="tsw-reason-btn ${TSW.reason === 'country' ? 'active' : ''}" onclick="tswSelectReason('country')">
            <div>🌐 區域 / 國別碼不同</div>
            <div style="font-size:0.76rem; font-weight:600; color:#64748B;">SFIS CountryCode vs DUT</div>
          </button>
          <button type="button" class="tsw-reason-btn ${TSW.reason === 'custom' ? 'active' : ''}" onclick="tswSelectReason('custom')">
            <div>✏️ 自由設定</div>
            <div style="font-size:0.76rem; font-weight:600; color:#64748B;">自訂 SFIS 欄位與分支</div>
          </button>
        </div>

        <details style="margin-top:10px; background:#F8FAFC; border:1px dashed #94A3B8; border-radius:7px; padding:7px 10px;" ${TSW.reason === 'custom' ? 'open' : ''}>
          <summary style="cursor:pointer; font-size:0.82rem; font-weight:700; color:#475569;">⚙️ SFIS 進階來源設定（目前：<code>${_esc(sk.source_mode)}</code> ➔ <code>$${_esc(sk.result_var)}</code>，無網路自動退回 <code>${_esc(sk.offline_default_sku)}</code>）</summary>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:8px; margin-top:8px;">
            <label style="font-size:0.8rem; font-weight:700;">SFIS 查詢表：
              <select onchange="TSW_STATE.sku.source_mode=this.value; window.tswRerender();" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px;">
                <option value="CUSTITEM" ${sk.source_mode === 'CUSTITEM' ? 'selected' : ''}>CUSTITEM (SKU 代碼)</option>
                <option value="ISN_ITEMINFO" ${sk.source_mode === 'ISN_ITEMINFO' ? 'selected' : ''}>ISN_ITEMINFO (工單/料號)</option>
                <option value="ITEM_CUSTINFO_N" ${sk.source_mode === 'ITEM_CUSTINFO_N' ? 'selected' : ''}>ITEM_CUSTINFO_N (客製欄位)</option>
                <option value="ISN_BASEINFO" ${sk.source_mode === 'ISN_BASEINFO' ? 'selected' : ''}>ISN_BASEINFO (基本欄位 SNE 等)</option>
                <option value="MANUAL_ONLY" ${sk.source_mode === 'MANUAL_ONLY' ? 'selected' : ''}>不連 SFIS (僅用 Global.ini 預設)</option>
              </select>
            </label>
            ${(sk.source_mode === 'ITEM_CUSTINFO_N' || sk.source_mode === 'ISN_BASEINFO') ? `
              <label style="font-size:0.8rem; font-weight:700;">欄位名稱：
                <input type="text" value="${_esc(sk.cust_field)}" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.cust_field=this.value.trim()">
              </label>
            ` : ''}
            <label style="font-size:0.8rem; font-weight:700;">比對模式：
              <select onchange="TSW_STATE.sku.compare_mode=this.value; window.tswRerender();" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px;">
                <option value="BRANCH_RULES" ${sk.compare_mode === 'BRANCH_RULES' ? 'selected' : ''}>多 SKU 規格分支</option>
                <option value="EXTERNAL_TXT" ${sk.compare_mode === 'EXTERNAL_TXT' ? 'selected' : ''}>外部 .txt 名單檔比對</option>
                <option value="DUT_COMPARE" ${sk.compare_mode === 'DUT_COMPARE' ? 'selected' : ''}>一對一比對 DUT 指令</option>
              </select>
            </label>
            <label style="font-size:0.8rem; font-weight:700;">離線預設 SKU：
              <input type="text" value="${_esc(sk.offline_default_sku)}" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.offline_default_sku=this.value.trim()">
            </label>
            <label style="font-size:0.8rem; font-weight:700;">DUT 通訊別名：
              <input type="text" value="${_esc(sk.dut_conn)}" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.dut_conn=this.value.trim()||'UART'">
            </label>
          </div>
          <div style="display:flex; gap:14px; flex-wrap:wrap; margin-top:8px; font-size:0.8rem; font-weight:700;">
            <label style="display:inline-flex; align-items:center; gap:5px; cursor:pointer;" title="開啟後，SKU 代碼、版號、iPLAS 名與 DL/UL 會以 *$(...) 寫進 Global.ini [Scripts]，日後免改 Excel 即可微調">
              <input type="checkbox" ${sk.param_to_ini !== false ? 'checked' : ''} onchange="TSW_STATE.sku.param_to_ini=this.checked; TSW_STATE.previewRes=null; window.tswRerender();">
              <span>數值同步抽出至 Global.ini [Scripts]（免改 Excel 即可微調門檻）</span>
            </label>
            <label style="display:inline-flex; align-items:center; gap:5px; cursor:pointer;">
              <input type="checkbox" ${sk.offline_wrap ? 'checked' : ''} onchange="TSW_STATE.sku.offline_wrap=this.checked">
              <span>自動包一層 :SfEnabled（無網路時不紅字）</span>
            </label>
            <label style="display:inline-flex; align-items:center; gap:5px;">未匹配時：
              <select onchange="TSW_STATE.sku.no_match_policy=this.value" style="padding:2px 6px; border:1px solid #94A3B8; border-radius:4px;">
                <option value="FAIL" ${sk.no_match_policy === 'FAIL' ? 'selected' : ''}>強制判 FAIL 防呆</option>
                <option value="DEFAULT" ${sk.no_match_policy === 'DEFAULT' ? 'selected' : ''}>繼續往下執行</option>
              </select>
            </label>
          </div>
        </details>
      </div>

      <!-- 區段 2：極簡 SKU 清單 -->
      <div class="tsw-card">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
          <span style="font-weight:900; color:#0F172A; font-size:0.95rem;">2. SKU 清單與各自規則</span>
          ${sk.compare_mode !== 'DUT_COMPARE' ? `<button type="button" class="tsw-btn-soft" onclick="TSW_STATE.sku.sku_branches.push({code:'SKU_NEW',label:'新規格',iplas_model:'',expected_hw:'',dut_write_cmd:'',limit_var:'gCurr',limit_type:'%f',dl:'',ul:'',limit_cmd:''}); window.tswRerender();">➕ 新增 SKU</button>` : ''}
        </div>
        ${sk.compare_mode === 'DUT_COMPARE' ? `
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <label style="font-size:0.82rem; font-weight:700;">DUT 讀取指令：
              <input type="text" value="${_esc(sk.dut_query_cmd)}" class="mono" style="width:100%; margin-top:3px; padding:5px 7px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;" onchange="TSW_STATE.sku.dut_query_cmd=this.value">
            </label>
            <label style="font-size:0.82rem; font-weight:700;">回傳擷取關鍵字：
              <input type="text" value="${_esc(sk.dut_prefix_kw)}" class="mono" style="width:100%; margin-top:3px; padding:5px 7px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;" onchange="TSW_STATE.sku.dut_prefix_kw=this.value">
            </label>
          </div>
        ` : `
          ${sk.compare_mode === 'EXTERNAL_TXT' ? `
            <div style="display:grid; grid-template-columns:180px 1fr; gap:8px; margin-bottom:8px; background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #CBD5E1;">
              <label style="font-size:0.8rem; font-weight:700;">名單檔名：
                <input type="text" value="${_esc(sk.txt_filename)}" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.txt_filename=this.value.trim()">
              </label>
              <label style="font-size:0.8rem; font-weight:700;">名單內容：
                <textarea rows="2" class="mono" style="width:100%; margin-top:2px; padding:4px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;" onchange="TSW_STATE.sku.txt_content=this.value">${_esc(sk.txt_content)}</textarea>
              </label>
            </div>
          ` : ''}
          <table style="width:100%; border-collapse:collapse; font-size:0.83rem;">
            <thead>
              <tr style="background:#F1F5F9; color:#334155;">
                <th style="padding:6px; text-align:left;">SKU 代碼</th>
                <th style="padding:6px; text-align:left;">說明</th>
                <th style="padding:6px; text-align:left;">iPLAS 機種名 (選填)</th>
                <th style="padding:6px; text-align:left;">預期版號 (選填)</th>
                <th style="padding:6px; text-align:right; width:130px;">上下限 / 刪除</th>
              </tr>
            </thead>
            <tbody>${branchesRowsHtml}</tbody>
          </table>
        `}
        <details style="margin-top:8px; background:#F8FAFC; border:1px dashed #94A3B8; border-radius:7px; padding:6px 10px;" ${sk.post_merge_cmds ? 'open' : ''}>
          <summary style="cursor:pointer; font-size:0.82rem; font-weight:700; color:#475569;">▸ 進階：各 SKU 分流結束「匯合後」接著執行的共用指令（置於匯合點之後，保證不破壞前方跳轉編號）</summary>
          <textarea rows="2" class="mono" placeholder="每行一條指令（例：mfg sync-sku 或 :Delay,&quot;300&quot;），留空即可"
            style="width:100%; margin-top:6px; padding:5px 8px; font-size:0.82rem; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;"
            onchange="TSW_STATE.sku.post_merge_cmds=this.value">${_esc(sk.post_merge_cmds || '')}</textarea>
        </details>
      </div>

      <!-- 區段 3：哪個測項誰不測（視覺化 ExecMode 4:1,end） -->
      ${sk.compare_mode !== 'DUT_COMPARE' && skuCodes.length > 0 ? `
        <div class="tsw-card">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
            <div>
              <span style="font-weight:900; color:#0F172A; font-size:0.95rem;">3. 哪個測項「特定 SKU 不測」？直接取消勾選</span>
              <span style="font-size:0.78rem; color:#64748B; margin-left:6px;">（取消勾選即自動在該段開頭補上 ExecMode 4:1,end 安全略過，不會判 FAIL）</span>
            </div>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px; margin-bottom:8px;">
            ${matrixHtml || '<div style="font-size:0.82rem; color:#64748B;">目前尚未勾選或載入其他測項（可於下方輸入要控管的測項名稱，或在 Step 2 先勾選測項再進來勾誰要跳過）。</div>'}
          </div>
          <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
            <input id="tswCustomSecInput" type="text" placeholder="或直接輸入要依 SKU 跳過的測項名稱（例：CHECK BATTERY）" style="flex:1; min-width:240px; padding:5px 8px; font-size:0.82rem; border:1px solid #94A3B8; border-radius:5px;">
            <button type="button" class="tsw-btn-soft" onclick="tswAddCustomGuardSection()">➕ 加入條件測項列</button>
          </div>
        </div>
      ` : ''}

      ${previewBoxHtml}
    `;
  }

  window.tswRerender = _renderSinglePage;

  function _renderPreviewBoxHtml() {
    const pr = TSW.previewRes;
    if (!pr || pr.loading) {
      return '<div class="tsw-card" style="text-align:center; color:#1E40AF; font-weight:800;">⏳ 正在計算 ExecMode 跳轉編號並預演...</div>';
    }
    if (pr.status !== 'ok') {
      return `<div class="tsw-card" style="background:#FEF2F2; border-color:#EF4444; color:#991B1B;">預覽失敗：${_esc(pr.message || '')}</div>`;
    }
    const rep = pr.report || { errors: [], manual_warnings: [] };
    const errs = rep.errors || [];
    const warns = rep.manual_warnings !== undefined ? rep.manual_warnings : (rep.warnings || []);
    const stSteps = ((pr.workspace && pr.workspace.stations && pr.workspace.stations[pr.station_name]) || []).slice(0, 60);
    const visList = pr.row_visuals || [];
    return `
      <div class="tsw-card" style="background:${errs.length === 0 && warns.length === 0 ? '#F0FDF4' : '#FFFBEB'}; border-color:${errs.length === 0 ? '#22C55E' : '#F59E0B'};">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">
          <span style="font-weight:900; font-size:0.9rem;">
            ${errs.length === 0 && warns.length === 0 ? '🟢 Script Doctor 預檢通過：0 Error / 0 Warning' : `⚠️ 檢出 ${errs.length} 錯誤 / ${warns.length} 警告`}
          </span>
          <span style="font-size:0.75rem; color:#475569; font-weight:700;">
            🎨 與匯出 Excel 同步配色：多分支粉彩輪替 ｜ 條件略過柔青 ｜ <span style="color:#BE185D;">SFIS 粉紅字</span> ｜ <span style="background:#FFF2CC;padding:0 4px;">P97金</span>/<span style="background:#DCFCE7;color:#15803D;padding:0 4px;">P98綠</span>/<span style="background:#FFE4E6;color:#9F1239;padding:0 4px;">P99紅</span>
          </span>
        </div>
        <div style="max-height:280px; overflow:auto; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
          <table style="width:100%; border-collapse:collapse; font-size:0.78rem;">
            <thead><tr style="background:#D9E1F2; text-align:left;"><th style="padding:3px 6px;">列</th><th style="padding:3px 6px;" title="Title 內 0 起算步號（對齊 ExecMode 4:P,F）">步號</th><th style="padding:3px 6px;">Phase</th><th style="padding:3px 6px;">Title</th><th style="padding:3px 6px;">Send</th><th style="padding:3px 6px;">Reply</th><th style="padding:3px 6px;">Validation</th><th style="padding:3px 6px;">ExecMode</th><th style="padding:3px 6px;">分流角色</th></tr></thead>
            <tbody>
              ${stSteps.map((r, i) => {
                const v = visList[i] || {};
                const bg = v.fill_hex ? ('#' + v.fill_hex) : '#FFFFFF';
                const fg = v.font_hex ? ('#' + v.font_hex) : '#0F172A';
                const fw = v.font_bold ? '700' : '400';
                return `
                  <tr style="border-bottom:1px solid #E2E8F0; background:${bg}; color:${fg}; font-weight:${fw};">
                    <td class="mono" style="padding:2px 6px; color:#64748B;">${i}</td>
                    <td class="mono" style="padding:2px 6px; font-weight:800; color:#1E40AF;">${v.local_idx !== undefined ? v.local_idx : i}</td>
                    <td class="mono" style="padding:2px 6px; font-weight:700;">${_esc(r.Phase || '')}</td>
                    <td style="padding:2px 6px; font-weight:700;">${_esc(r.Title || '')}</td>
                    <td class="mono" style="padding:2px 6px;">${_esc(r.Send || '')}</td>
                    <td class="mono" style="padding:2px 6px;">${_esc(r.Reply || '')}</td>
                    <td class="mono" style="padding:2px 6px;">${_esc(r.Validation || '')}</td>
                    <td class="mono" style="padding:2px 6px; color:#6D28D9; font-weight:800;">${_esc(r.ExecMode || '')}</td>
                    <td style="padding:2px 6px; font-size:0.73rem;">${_esc(v.role_label || '')}</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  function _buildRequestPayload(previewFlag) {
    const body = {
      target_mode: TSW.targetMode,
      project_name: _getTargetProjectName(),
      station_name: _getTargetStationName(),
      bundle_spec: {},
      sku_spec: JSON.parse(JSON.stringify(TSW.sku)),
      preview: !!previewFlag,
    };
    if (TSW.targetMode === 'edit' && window.STATE && window.STATE.workspace) {
      body.workspace = window.STATE.workspace;
    }
    return body;
  }

  window.tswTogglePreview = async function () {
    TSW.previewOpen = !TSW.previewOpen;
    if (!TSW.previewOpen) {
      _renderSinglePage();
      return;
    }
    TSW.previewRes = { loading: true };
    _renderSinglePage();
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
    _renderSinglePage();
  };

  window.tswApplyToTarget = async function () {
    const reqBody = _buildRequestPayload(false);
    if (TSW.targetMode === 'create') {
      if (!window.STATE) window.STATE = {};
      window.STATE.createTemplateBundle = null;
      window.STATE.createSkuConfig = reqBody.sku_spec;
      _renderCreateModeBanner();
      closeTemplateSkuWizard();
      return;
    }

    const res = await fetch('/api/template_bundle/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody),
    });
    const appliedData = await res.json();
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
      inst: '多 SKU 分流精靈',
      summary: `SKU ${sm.sku_steps_added || 0} 步${(sm.guarded_sections || []).length ? ` · 測項閘門 ${sm.guarded_sections.length} 處` : ''}`,
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
    const sk = window.STATE.createSkuConfig || {};
    if (!sk.enabled) {
      banner.style.display = 'none';
      banner.innerHTML = '';
      return;
    }
    const guardsLen = (sk.section_guards || []).length;
    banner.style.display = 'block';
    banner.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:0.86rem; color:#312E81;">
          <b>🎯 已掛載「多 SKU 分流精靈」：</b>
          <code>${_esc(sk.source_mode)}</code> ｜ <b>${(sk.sku_branches || []).length}</b> 支 SKU
          ${guardsLen ? ` ｜ 衍生品閘門 <b>${guardsLen}</b> 處` : ''}
          ${sk.post_merge_cmds ? ' ｜ 含匯合後共用指令' : ''}
        </div>
        <div style="display:flex; gap:6px;">
          <button type="button" class="tsw-btn-soft" onclick="openTemplateSkuWizard('create')">✏️ 修改設定</button>
          <button type="button" class="tsw-btn-soft" style="color:#B91C1C; border-color:#FCA5A5;" onclick="window.STATE.createSkuConfig=null; document.getElementById('wizTemplateSkuBanner').style.display='none';">🧹 清除</button>
        </div>
      </div>
    `;
  }

  window.tswGetCreatePayloadExtras = function () {
    const out = {};
    if (window.STATE && window.STATE.createSkuConfig && window.STATE.createSkuConfig.enabled) {
      out.sku_wizard = window.STATE.createSkuConfig;
    }
    return out;
  };
})();
