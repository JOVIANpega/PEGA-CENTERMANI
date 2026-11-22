// Two-Stage INI Editor & AI Change Advisor (Build v0.5.5)
// Stage 1 (Edit Mode): Clean, focused control panel for System.ini switches & active Global.ini variables (no cluttered raw INI preview while editing).
// Stage 2 (Review & Confirm Mode): When user clicks "預覽左右差異與 AI 修改報告", opens a synchronized row-by-row Side-by-Side Highlight Diff + AI Plain-Language Change Summary, with final button to write & pop up the modified INI file(s).

let AUDIT_GLOBAL_TAB = 'ini_diff';
let INI_STAGE_MODE = 'edit'; // 'edit' (第一階段：專心修改) | 'review' (第二階段：反白確認左右差異 + AI 報告 + 寫入彈出 INI)
let INI_REVIEW_SHOW_ALL_LINES = false; // false = 聚焦顯示有修改的區段與行 (預設), true = 展開完整 INI 全文左右對照

const DEFAULT_SYSTEM_INI_TEMPLATE = {
  SFIS_Enable: '0',
  SFIS_LinkIPLAS: '0',
  SFIS_TSP: 'PEGA,2',
  SFIS_WebLink: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx',
  iPLAS_Enable: '0',
  iPLAS_Site: 'DC',
  iPLAS_ProjectName: 'PEGA_PROJECT',
  DebugMode: '1',
  RetryCount: '3',
  CSVReport_Enable: '1',
  IpFinder_Enable: '0'
};

function _normalizeSystemIni(ws) {
  if (!ws) return {};
  ws.system_ini = ws.system_ini || {};
  const proj = ws.project_name || 'PEGA_PROJECT';
  const defaults = Object.assign({}, DEFAULT_SYSTEM_INI_TEMPLATE, {
    SFIS_TSP: (proj.slice(0, 6) || 'PEGA') + ',2',
    iPLAS_ProjectName: proj
  });
  Object.keys(defaults).forEach(k => {
    if (ws.system_ini[k] === undefined || ws.system_ini[k] === null) {
      ws.system_ini[k] = defaults[k];
    } else {
      ws.system_ini[k] = String(ws.system_ini[k]);
    }
  });
  return ws.system_ini;
}

function snapshotOriginalInis(ws) {
  if (!ws) return;
  _normalizeSystemIni(ws);
  STATE.origGlobalIni = JSON.parse(JSON.stringify(ws.global_ini || { Settings: {}, Scripts: {} }));
  STATE.origSystemIni = JSON.parse(JSON.stringify(ws.system_ini || {}));
  INI_STAGE_MODE = 'edit';
}

function _ensureIniSnapshots(ws) {
  if (!ws) return;
  _normalizeSystemIni(ws);
  if (!STATE.origGlobalIni) {
    STATE.origGlobalIni = JSON.parse(JSON.stringify(ws.global_ini || { Settings: {}, Scripts: {} }));
  }
  if (!STATE.origSystemIni) {
    STATE.origSystemIni = JSON.parse(JSON.stringify(ws.system_ini || {}));
  }
}

function _getSystemIniSection(key) {
  if (/^SFIS_/i.test(key)) return 'SFIS';
  if (/^iPLAS_/i.test(key)) return 'iPLAS';
  if (/^CSVReport_/i.test(key)) return 'CSVReport';
  if (/^IpFinder_/i.test(key)) return 'IpFinder';
  return 'System';
}

function _describeSystemKey(k) {
  const map = {
    SFIS_Enable: 'SFIS 產線過站總開關',
    SFIS_LinkIPLAS: 'SFIS 連動上傳 iPLAS',
    SFIS_TSP: 'SFIS 站別與路由代碼',
    SFIS_WebLink: 'SFIS WebService 網址',
    iPLAS_Enable: 'iPLAS 數據上傳開關',
    iPLAS_Site: 'iPLAS 廠區代碼',
    iPLAS_ProjectName: 'iPLAS 專案名稱',
    DebugMode: '除錯模式 (1=免簽章, 0=量產)',
    RetryCount: '測項失敗自動重測次數',
    CSVReport_Enable: '自動產出 CSV 報表',
    IpFinder_Enable: 'IpFinder 自動搜尋開關',
    TestItemCodeFile: '官方測項代碼表檔名'
  };
  return map[k] || 'System.ini 系統參數';
}

function _describeGlobalVar(k) {
  if (/^PCIP_/i.test(k)) return '電腦端網卡 IP';
  if (/^DUTIP_/i.test(k)) return '待測物 DUT 連線 IP';
  if (/^GoldenIP/i.test(k)) return 'Golden 伺服器 IP';
  if (/^DUT_UR/i.test(k)) return '待測物 UART COM Port';
  if (/^PCUART_fixture/i.test(k)) return '氣動治具控制 COM Port';
  if (/^PCUART/i.test(k)) return '電腦端序列埠 COM Port';
  if (/^DAQ_/i.test(k)) return 'NI-6008/6009 裝置代號';
  if (/^LED_AZ/i.test(k)) return 'FeasaLED 分析儀 COM Port';
  if (/^LED_Light/i.test(k)) return 'FeasaLED 光纖通道號';
  if (/^DUT_Login/i.test(k)) return 'SSH / Console 登入帳號';
  if (/^LOAD_/i.test(k)) return '多槽位啟用開關 (true/false)';
  if (/^DEVID_/i.test(k)) return 'SFIS 機台設備編號';
  if (/^FW_VERSION/i.test(k)) return '目標韌體版本號';
  if (/^Boot_Delay/i.test(k)) return '開機等待延遲 (ms)';
  return '腳本自訂變數';
}

function _collectIniDiffEntries(origObj, currObj, fileLabel) {
  const entries = [];
  if (fileLabel === 'System.ini') {
    const oFlat = origObj || {};
    const cFlat = currObj || {};
    const keys = Array.from(new Set([...Object.keys(oFlat), ...Object.keys(cFlat)]));
    keys.forEach(k => {
      if (typeof cFlat[k] === 'object' && cFlat[k] !== null) return;
      const oldVal = oFlat[k] !== undefined ? String(oFlat[k]) : null;
      const newVal = cFlat[k] !== undefined ? String(cFlat[k]) : null;
      const isAdded = (oldVal === null && newVal !== null);
      const isModified = (oldVal !== null && newVal !== null && oldVal !== newVal);
      const isChanged = isAdded || isModified;
      entries.push({
        file: 'System.ini',
        section: _getSystemIniSection(k),
        key: k,
        desc: _describeSystemKey(k),
        oldVal: oldVal === null ? '(新增)' : oldVal,
        newVal: newVal === null ? '' : newVal,
        isAdded,
        isModified,
        isChanged
      });
    });
  } else {
    const sections = Array.from(new Set([
      ...Object.keys(origObj || {}),
      ...Object.keys(currObj || {})
    ]));
    sections.forEach(sec => {
      const oSec = (origObj && origObj[sec]) || {};
      const cSec = (currObj && currObj[sec]) || {};
      if (typeof oSec !== 'object' || typeof cSec !== 'object') return;
      const keys = Array.from(new Set([...Object.keys(oSec), ...Object.keys(cSec)]));
      keys.forEach(k => {
        const oldVal = oSec[k] !== undefined ? String(oSec[k]) : null;
        const newVal = cSec[k] !== undefined ? String(cSec[k]) : null;
        const isAdded = (oldVal === null && newVal !== null);
        const isModified = (oldVal !== null && newVal !== null && oldVal !== newVal);
        const isChanged = isAdded || isModified;
        entries.push({
          file: 'Global.ini',
          section: sec,
          key: k,
          desc: _describeGlobalVar(k),
          oldVal: oldVal === null ? '(新增)' : oldVal,
          newVal: newVal === null ? '' : newVal,
          isAdded,
          isModified,
          isChanged
        });
      });
    });
  }
  return entries;
}

function _explainChangeByAi(e, ws) {
  const k = e.key;
  const nv = String(e.newVal).trim();
  const ov = String(e.oldVal).trim();
  const sys = (ws && ws.system_ini) || {};

  if (k === 'SFIS_Enable') {
    if (nv === '1') {
      return `🟢 <b>已開啟 SFIS 產線過站管控</b>（路由站別碼：<code>${_escAttr(sys.SFIS_TSP || 'PEGA,2')}</code>）。開測前系統將自動連線 SFIS 檢查待測物 ISN 路由，測試後自動過站；請確認機台已連通工廠 SFIS 內網。`;
    }
    return `⚪ <b>已關閉 SFIS 產線過站管控</b>（切換為單機離線測試模式）。測試時不再向 SFIS 伺服器查詢路由或上傳過站結果，適合工程調試使用。`;
  }
  if (k === 'SFIS_LinkIPLAS') {
    if (nv === '1') {
      return `🔗 <b>已開啟 SFIS 連動 iPLAS 功能</b>。當 SFIS 過站啟用時，將同步觸發 iPLAS 測試紀錄連動。`;
    }
    return `⚪ <b>已關閉 SFIS 連動 iPLAS 功能</b>。`;
  }
  if (k === 'iPLAS_Enable') {
    if (nv === '1') {
      return `☁️ <b>已開啟 iPLAS 數據自動上傳</b>（目標廠區：<code>${_escAttr(sys.iPLAS_Site || 'DC')}</code>，專案：<code>${_escAttr(sys.iPLAS_ProjectName || '')}</code>）。測試完成後將自動打包 Log 與報表上傳。`;
    }
    return `⚪ <b>已關閉 iPLAS 數據上傳</b>，測試 Log 僅保留於本機硬碟。`;
  }
  if (k === 'DebugMode') {
    if (nv === '0') {
      return `🔒 <b>⚠️ 重要提醒：已切換為「正式量產模式 (DebugMode=0)」</b>！在此模式下 Centimani 啟動時會強制驗證 Excel 與 <code>System.ini</code> 的 64 碼 Checksum 簽章（本工具寫入時將自動為您重算最新簽章）。`;
    }
    return `🛠️ <b>已切換為「工程除錯模式 (DebugMode=1)」</b>，免除 Checksum 簽章強制攔截，方便現場快速修改調試。`;
  }
  if (k === 'SFIS_TSP') {
    return `🏷️ <b>已更新 SFIS 站別路由代碼</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>，請確認與產線 SFIS 系統配置的站別名稱一致。`;
  }
  if (k === 'iPLAS_Site') {
    return `🏭 <b>已切換 iPLAS 目標廠區代碼</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>。`;
  }
  if (/^DUT_UR/i.test(k)) {
    return `🔌 <b>已變更待測物 (DUT) UART 通訊序列埠</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>。請確認 Windows 裝置管理員中的 USB-to-UART 埠號與此設定一致。`;
  }
  if (/^PCUART_fixture/i.test(k)) {
    return `🔧 <b>已變更氣動治具控制 COM Port</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>。請確認治具下壓與 Phase 97 結束抬起可正常收發指令。`;
  }
  if (/^(DUTIP_|PCIP_|GoldenIP)/i.test(k)) {
    return `🌐 <b>已變更測試網路 IP 位址 (${_escAttr(e.desc)})</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>。請確認電腦網卡與待測物處於相同網段且可 Ping 通。`;
  }
  if (/^DAQ_/i.test(k)) {
    return `📊 <b>已變更 NI-6008/6009 DAQ 裝置代號</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>，請確認與 NI MAX 內的裝置編號相符。`;
  }
  if (/^LED_/i.test(k)) {
    return `💡 <b>已變更 FeasaLED 分析儀設定 (${_escAttr(e.desc)})</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>。`;
  }
  if (/^LOAD_/i.test(k)) {
    return `🗂️ <b>已變更槽位載入開關 (${_escAttr(k)})</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>。`;
  }
  if (/^FW_VERSION/i.test(k)) {
    return `📦 <b>已更新目標韌體版本號基準</b>：由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>。`;
  }
  return `✏️ <b>已修改 ${_escAttr(e.desc)} (<code>${_escAttr(k)}</code>)</b>：由原本的 <code>${_escAttr(ov)}</code> 更新為 <code>${_escAttr(nv)}</code>。`;
}

function _recordPendingIniNotice(summaryText) {
  STATE.pendingInserts = STATE.pendingInserts || [];
  const existing = STATE.pendingInserts.find(p => p.inst === 'INI 設定微調');
  if (existing) {
    existing.summary = summaryText;
  } else {
    STATE.pendingInserts.push({
      sheet: 'Global.ini / System.ini',
      inst: 'INI 設定微調',
      summary: summaryText
    });
  }
  if (typeof updatePendingBar === 'function') updatePendingBar();
}

function setSystemIniValueLive(key, val, rerender = true) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.system_ini[key] = String(val);
  _recordPendingIniNotice(`System.ini: ${key}=${val}`);
  if (rerender) renderGlobalEditorPanel();
  else _updateEditStageBadgesOnly();
}

function setGlobalIniValueLive(sec, key, val, rerender = true) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.global_ini = STATE.workspace.global_ini || { Settings: {}, Scripts: {} };
  STATE.workspace.global_ini[sec] = STATE.workspace.global_ini[sec] || {};
  STATE.workspace.global_ini[sec][key] = String(val);
  _recordPendingIniNotice(`Global.ini [${sec}] ${key}=${val}`);
  if (rerender) renderGlobalEditorPanel();
  else _updateEditStageBadgesOnly();
}

function _updateEditStageBadgesOnly() {
  if (!STATE.workspace) return;
  const total = [
    ..._collectIniDiffEntries(STATE.origGlobalIni, STATE.workspace.global_ini, 'Global.ini'),
    ..._collectIniDiffEntries(STATE.origSystemIni, STATE.workspace.system_ini, 'System.ini')
  ].filter(e => e.isChanged).length;
  const b1 = document.getElementById('iniTabDiffCountBadge');
  if (b1) b1.textContent = `(${total})`;
  const b2 = document.getElementById('btnEnterReviewCount');
  if (b2) b2.textContent = total;
}

function revertSingleIniKey(fileLabel, sec, key) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  if (fileLabel === 'System.ini') {
    if (STATE.origSystemIni && STATE.origSystemIni[key] !== undefined) {
      STATE.workspace.system_ini[key] = STATE.origSystemIni[key];
    }
  } else {
    if (STATE.origGlobalIni && STATE.origGlobalIni[sec] && STATE.origGlobalIni[sec][key] !== undefined) {
      STATE.workspace.global_ini[sec][key] = STATE.origGlobalIni[sec][key];
    } else if (STATE.workspace.global_ini && STATE.workspace.global_ini[sec]) {
      delete STATE.workspace.global_ini[sec][key];
    }
  }
  renderGlobalEditorPanel();
}

function revertAllIniChanges() {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.global_ini = JSON.parse(JSON.stringify(STATE.origGlobalIni));
  STATE.workspace.system_ini = JSON.parse(JSON.stringify(STATE.origSystemIni));
  INI_STAGE_MODE = 'edit';
  renderGlobalEditorPanel();
}

function switchIniStageMode(stage) {
  INI_STAGE_MODE = stage;
  renderGlobalEditorPanel();
}

function toggleIniReviewShowAllLines(showAll) {
  INI_REVIEW_SHOW_ALL_LINES = Boolean(showAll);
  renderGlobalEditorPanel();
}

async function saveAndOpenModifiedIni(targetMode) {
  if (!STATE.workspace) {
    alert('請先載入腳本！');
    return;
  }
  _ensureIniSnapshots(STATE.workspace);
  const gEntries = _collectIniDiffEntries(STATE.origGlobalIni, STATE.workspace.global_ini, 'Global.ini');
  const sEntries = _collectIniDiffEntries(STATE.origSystemIni, STATE.workspace.system_ini, 'System.ini');
  const gChanged = gEntries.filter(e => e.isChanged).length;
  const sChanged = sEntries.filter(e => e.isChanged).length;

  let openTarget = targetMode || 'auto';
  if (openTarget === 'auto') {
    if (gChanged > 0 && sChanged > 0) openTarget = 'both';
    else if (sChanged > 0 && gChanged === 0) openTarget = 'system';
    else openTarget = 'global';
  }

  const res = await fetch('/api/save_and_open_ini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      file_path: STATE.selectedPath || '',
      workspace: STATE.workspace,
      open_target: openTarget
    })
  });
  const data = await res.json();
  if (data.status !== 'ok') {
    alert(data.message || '儲存 INI 失敗');
    return;
  }
  const banner = document.getElementById('iniSaveResultBanner');
  if (banner) {
    banner.style.display = 'block';
    banner.innerHTML = `
      <div style="font-weight:800; color:#14532D; font-size:13.5px;">🎉 已成功將修改寫入硬碟，並直接以記事本 (Notepad) 置頂彈出剛剛修改的 INI 檔案！</div>
      <div class="mono" style="font-size:12px; color:#166534; margin-top:4px; word-break:break-all;">
        • Global.ini：${_escAttr(data.global_ini_path)}<br>
        • System.ini：${_escAttr(data.system_ini_path)}
      </div>
    `;
  }
}

function toggleGlobalEditorPanel(forceTab, forceStage) {
  const box = document.getElementById('auditGlobalEditor');
  if (!box || !STATE.workspace) return;
  if (forceTab) {
    AUDIT_GLOBAL_TAB = forceTab;
    if (forceStage) INI_STAGE_MODE = forceStage;
    box.style.display = 'block';
    renderGlobalEditorPanel();
    return;
  }
  const willShow = (box.style.display === 'none' || !box.style.display);
  box.style.display = willShow ? 'block' : 'none';
  if (willShow) renderGlobalEditorPanel();
}

function switchGlobalEditorTab(tab) {
  AUDIT_GLOBAL_TAB = tab;
  renderGlobalEditorPanel();
}

function _findKeyByPrefix(obj, prefix, fallback) {
  if (!obj) return fallback;
  const k = Object.keys(obj).find(x => x.toLowerCase().startsWith(prefix.toLowerCase()));
  return k || fallback;
}

function _escAttr(v) {
  return String(v == null ? '' : v)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function _collectUsedVarsAndInstruments(ws) {
  const usedVars = new Set();
  const usedInstRefs = new Set();
  const reVar = /\*\$\(([^)]+)\)/g;

  const scanText = (txt) => {
    if (!txt) return;
    let m;
    while ((m = reVar.exec(String(txt))) !== null) {
      usedVars.add(m[1].trim());
    }
  };

  (ws.duts || []).forEach(d => Object.values(d).forEach(scanText));
  (ws.instruments || []).forEach(inst => Object.values(inst).forEach(scanText));
  Object.values(ws.stations || {}).forEach(steps => {
    steps.forEach(s => {
      Object.values(s).forEach(scanText);
      const instCol = String(s.Instrument || '').trim();
      if (instCol) usedInstRefs.add(instCol.toLowerCase());
    });
  });
  return { usedVars, usedInstRefs };
}

function _parseScanBarcode(raw) {
  const s = String(raw || '').trim();
  if (!s) return { simple: true, name: 'ISN', len: '15', pat: '[0-9]' };
  if (s.includes(';')) return { simple: false, raw: s };
  const m = s.match(/^\{\s*([^,]+)\s*,\s*(\d+)\s*,\s*([^}]+?)\s*\}$/);
  if (!m) return { simple: false, raw: s };
  return { simple: true, name: m[1].trim(), len: m[2].trim(), pat: m[3].trim() };
}

function _updateScanBarcodeField(dutIdx, scanKey, field, val) {
  const d = STATE.workspace.duts[dutIdx];
  const parsed = _parseScanBarcode(d[scanKey]);
  if (!parsed.simple) return;
  parsed[field] = val;
  d[scanKey] = `{ ${parsed.name},${parsed.len},${parsed.pat} }`;
}

function _parseConn1(raw) {
  const s = String(raw || '').trim();
  const m = s.match(/^"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]*)"$/);
  if (!m) return { structured: false, raw: s };
  const parts = m[3].split(',');
  if (m[1].toUpperCase() === 'UDP' && parts.length >= 3) {
    return { structured: true, proto: m[1], cname: m[2], pcIp: parts[0], dutIp: parts[1], port: parts[2], rest: parts.slice(3) };
  }
  return { structured: false, raw: s };
}

function _updateConn1Field(dutIdx, connKey, field, val) {
  const d = STATE.workspace.duts[dutIdx];
  const p = _parseConn1(d[connKey]);
  if (!p.structured) return;
  p[field] = val;
  const connStr = [p.pcIp, p.dutIp, p.port, ...p.rest].join(',');
  d[connKey] = `"${p.proto}","${p.cname}","${connStr}"`;
}

function _renderIniStage1EditHtml(ws, usedVars, allChangedCount) {
  const sysIni = ws.system_ini || {};

  const mkSysToggle = (key, label, onText = '🟢 開啟 (1)', offText = '⚪ 關閉 (0)') => {
    const curVal = String(sysIni[key] !== undefined ? sysIni[key] : '0').trim();
    const origVal = String((STATE.origSystemIni || {})[key] !== undefined ? STATE.origSystemIni[key] : curVal).trim();
    const isOn = curVal === '1' || curVal.toLowerCase() === 'true';
    const isMod = curVal !== origVal;
    return `
      <div style="background:${isMod ? '#FEF9C3' : '#F8FAFC'}; border:1.5px solid ${isMod ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <div>
          <div style="font-weight:800; font-size:13px; color:#0F172A;">
            ${label}
            ${isMod ? `<span style="background:#FEF08A; color:#854D0E; border:1px solid #FACC15; padding:1px 6px; border-radius:4px; font-size:11px; margin-left:4px;">✏️ 已改 (${_escAttr(origVal)} ➔ ${_escAttr(curVal)})</span>` : ''}
          </div>
          <div class="mono" style="font-size:11.5px; color:#64748B;">[System.ini] ${key}</div>
        </div>
        <div style="display:flex; gap:5px;">
          <button onclick="setSystemIniValueLive('${key}','1')" class="btn" style="padding:4px 11px; font-size:12px; ${isOn ? 'background:#16A34A;color:#FFF;font-weight:800;border-color:#15803D;' : 'background:#FFF;color:#64748B;'}">${onText}</button>
          <button onclick="setSystemIniValueLive('${key}','0')" class="btn" style="padding:4px 11px; font-size:12px; ${!isOn ? 'background:#334155;color:#FFF;font-weight:800;border-color:#1E293B;' : 'background:#FFF;color:#64748B;'}">${offText}</button>
        </div>
      </div>
    `;
  };

  const mkSysInput = (key, label, widthPx = 140) => {
    const curVal = String(sysIni[key] !== undefined ? sysIni[key] : '');
    const origVal = String((STATE.origSystemIni || {})[key] !== undefined ? STATE.origSystemIni[key] : curVal);
    const isMod = curVal !== origVal;
    return `
      <div style="background:${isMod ? '#FEF9C3' : '#F8FAFC'}; border:1.5px solid ${isMod ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <div>
          <div style="font-weight:800; font-size:12.5px; color:#0F172A;">
            ${label}
            ${isMod ? `<span style="background:#FEF08A; color:#854D0E; padding:1px 5px; border-radius:4px; font-size:11px;">原本: ${_escAttr(origVal)}</span>` : ''}
          </div>
          <div class="mono" style="font-size:11.5px; color:#64748B;">[System.ini] ${key}</div>
        </div>
        <input value="${_escAttr(curVal)}" oninput="setSystemIniValueLive('${key}',this.value,false)" onchange="setSystemIniValueLive('${key}',this.value,true)" class="mono"
          style="width:${widthPx}px; padding:5px 8px; font-size:12.5px; border:1.5px solid ${isMod ? '#CA8A04' : '#94A3B8'}; background:${isMod ? '#FEF08A' : '#FFF'}; border-radius:5px; font-weight:${isMod ? '800' : '500'};">
      </div>
    `;
  };

  const gEntries = _collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini');
  const activeGlobalEntries = [];
  const idleGlobalEntries = [];
  gEntries.forEach(e => {
    const isCore = usedVars.has(e.key) || /^(DUT_UR1|DUTIP_1|PCIP_1|DAQ_1|LED_AZ1|LED_Light1|LOAD_1|DEVID_1|FW_VERSION)$/i.test(e.key);
    if (e.isChanged || isCore) activeGlobalEntries.push(e);
    else idleGlobalEntries.push(e);
  });

  const mkGlobalCard = (e) => `
    <div style="background:${e.isChanged ? '#FEF9C3' : '#FFFFFF'}; border:1.5px solid ${e.isChanged ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:7px 11px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
      <div style="min-width:0; flex:1;">
        <div style="font-weight:800; font-size:12.5px; color:#0F172A; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
          <span>${_escAttr(e.desc)}</span>
          ${e.isChanged ? `<span style="background:#FEF08A; color:#854D0E; border:1px solid #FACC15; padding:0px 5px; border-radius:4px; font-size:11px;">原本: ${_escAttr(e.oldVal)}</span>` : ''}
        </div>
        <div class="mono" style="font-size:11.5px; color:#1E40AF;">[${_escAttr(e.section)}] ${_escAttr(e.key)}</div>
      </div>
      <div style="display:flex; align-items:center; gap:4px;">
        <input value="${_escAttr(e.newVal)}"
          oninput="setGlobalIniValueLive('${_escAttr(e.section)}','${_escAttr(e.key)}',this.value,false)"
          onchange="setGlobalIniValueLive('${_escAttr(e.section)}','${_escAttr(e.key)}',this.value,true)"
          class="mono"
          style="width:165px; padding:5px 8px; font-size:12.5px; border:1.5px solid ${e.isChanged ? '#CA8A04' : '#94A3B8'}; background:${e.isChanged ? '#FEF08A' : '#FFFFFF'}; font-weight:${e.isChanged ? '800' : '500'}; border-radius:5px;">
        ${e.isChanged ? `<button onclick="revertSingleIniKey('Global.ini','${_escAttr(e.section)}','${_escAttr(e.key)}')" class="btn" style="padding:3px 7px; font-size:11px; background:#FFF; color:#64748B;" title="還原此項">↩</button>` : ''}
      </div>
    </div>
  `;

  return `
    <div style="display:flex; flex-direction:column; gap:12px;">
      <!-- 步驟導引列 -->
      <div style="background:#EFF6FF; border:1.5px solid #60A5FA; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
          <span style="background:#2563EB; color:#FFF; font-weight:800; font-size:12px; padding:2px 8px; border-radius:999px;">步驟 1 / 2：修改設定</span>
          <span style="font-weight:800; font-size:13.5px; color:#1E3A8A; margin-left:6px;">請先在下方調整 SFIS / iPLAS 開關或 COM / IP（有修改的欄位會自動反白標示）</span>
          <div style="font-size:12px; color:#475569; margin-top:3px;">全部調整完畢後，請點擊右側「<b>🔍 下一步：反白確認左右差異與 AI 修改報告</b>」，確認無誤再寫入並彈出 INI！</div>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          ${allChangedCount > 0 ? `<button onclick="revertAllIniChanges()" class="btn" style="padding:6px 12px; font-size:12.5px; background:#FFFFFF; color:#B91C1C; border:1px solid #FCA5A5; font-weight:700;">↩ 全部重設 (${allChangedCount})</button>` : ''}
          <button onclick="switchIniStageMode('review')" class="btn btn-primary-blue" style="padding:8px 18px; font-size:13.5px; font-weight:800; box-shadow:0 2px 8px rgba(37,99,235,0.28);">
            🔍 下一步：反白確認左右差異與 AI 修改報告 (<span id="btnEnterReviewCount">${allChangedCount}</span> 項修改) ▶
          </button>
        </div>
      </div>

      <!-- 區塊 1: System.ini 開關 -->
      <div style="border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px; background:#FFFFFF;">
        <div style="font-weight:800; font-size:13px; color:#1E293B; margin-bottom:8px;">
          🌐 1. System.ini 產線過站、iPLAS 上傳與除錯開關
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(310px, 1fr)); gap:8px;">
          ${mkSysToggle('SFIS_Enable', 'SFIS 產線過站總開關')}
          ${mkSysToggle('SFIS_LinkIPLAS', 'SFIS 連動 iPLAS')}
          ${mkSysToggle('iPLAS_Enable', 'iPLAS 測試數據上傳')}
          ${mkSysToggle('DebugMode', '除錯模式 (免 Checksum 簽章)', '🟢 調試 (1)', '🔒 量產 (0)')}
          ${mkSysInput('SFIS_TSP', 'SFIS 站別路由代碼', 135)}
          ${mkSysInput('iPLAS_Site', 'iPLAS 廠區代碼', 100)}
        </div>
      </div>

      <!-- 區塊 2: Global.ini 本腳本實際使用之變數 -->
      <div style="border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px; background:#FFFFFF;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <span style="font-weight:800; font-size:13px; color:#1E293B;">🔌 2. Global.ini 本腳本實際使用之 COM Port / IP / 硬體變數（共 ${activeGlobalEntries.length} 項）</span>
          <button onclick="addGlobalIniVar()" class="btn" style="padding:3px 10px; font-size:12px; background:#EFF6FF; color:#1E40AF; border:1px solid #93C5FD; font-weight:700;">+ 新增 Global.ini 變數</button>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:8px;">
          ${activeGlobalEntries.map(mkGlobalCard).join('')}
        </div>
        ${idleGlobalEntries.length > 0 ? `
          <details style="margin-top:10px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:6px 10px;">
            <summary style="cursor:pointer; font-weight:700; font-size:12px; color:#64748B;">📦 展開其餘未引用的備用 Global.ini 變數（共 ${idleGlobalEntries.length} 項，預設收合保持畫面乾淨）</summary>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:8px; margin-top:8px;">
              ${idleGlobalEntries.map(mkGlobalCard).join('')}
            </div>
          </details>
        ` : ''}
      </div>

      <!-- 底部下一步確認列 -->
      <div style="display:flex; justify-content:flex-end;">
        <button onclick="switchIniStageMode('review')" class="btn btn-primary-blue" style="padding:8px 22px; font-size:14px; font-weight:800;">
          🔍 全部改好了！點此反白確認左右差異與 AI 修改報告 ▶
        </button>
      </div>
    </div>
  `;
}

function _renderIniStage2ReviewHtml(ws) {
  const gEntries = _collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini');
  const sEntries = _collectIniDiffEntries(STATE.origSystemIni, ws.system_ini, 'System.ini');
  const sChanged = sEntries.filter(e => e.isChanged);
  const gChanged = gEntries.filter(e => e.isChanged);
  const allChanged = [...sChanged, ...gChanged];

  // 1. 🤖 AI 白話修改診斷報告 (AI Change Advisor)
  let aiReportHtml = '';
  if (allChanged.length === 0) {
    aiReportHtml = `
      <div style="background:#FFFBEB; border:1.5px solid #F59E0B; border-radius:8px; padding:12px 16px; color:#92400E; font-size:13px;">
        🤖 <b>AI 檢查報告：</b>您目前尚未修改任何 INI 設定值（所有參數均與原始檔案相同）。您可以點擊左上角「<b>⬅ 返回修改設定</b>」調整參數，或直接點擊右下角存檔並彈出 INI 檢視。
      </div>
    `;
  } else {
    const bulletItems = allChanged.map((e, idx) => `
      <div style="padding:6px 10px; background:#FFFFFF; border:1px solid #BAE6FD; border-radius:6px; font-size:12.5px; color:#0F172A; line-height:1.55;">
        <span style="background:#0284C7; color:#FFF; font-weight:800; font-size:11.5px; padding:1px 7px; border-radius:999px; margin-right:6px;">修改 #${idx + 1}</span>
        <span class="mono" style="font-weight:800; color:#1E3A8A;">[${_escAttr(e.file)}]</span>
        ${_explainChangeByAi(e, ws)}
      </div>
    `).join('');

    aiReportHtml = `
      <div style="background:linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%); border:1.5px solid #38BDF8; border-radius:8px; padding:12px 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
          <div style="font-weight:800; font-size:14px; color:#0C4A6E;">
            🤖 AI 智慧修改總結報告（已為您核對本次修改的 ${allChanged.length} 項設定與產線影響）：
          </div>
          <span style="font-size:12px; color:#0369A1; font-weight:700;">請核對下方反白差異，確認無誤後點擊右下角綠色按鈕寫入並彈出 INI</span>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px;">
          ${bulletItems}
        </div>
      </div>
    `;
  }

  // 2. 🆚 同行水平嚴格對齊、反白高亮左右差異表 (Synchronized Row-by-Row Side-by-Side Diff)
  const buildFileDiffRows = (fileLabel, entries) => {
    const shown = INI_REVIEW_SHOW_ALL_LINES ? entries : entries.filter(e => e.isChanged);
    if (shown.length === 0) return '';
    let html = `
      <tr style="background:#1E293B; color:#F8FAFC;">
        <td colspan="4" class="mono" style="padding:6px 12px; font-weight:800; font-size:12.5px;">
          📄 ${_escAttr(fileLabel)} （本次修改 ${entries.filter(e => e.isChanged).length} 項 / 共 ${entries.length} 項）
        </td>
      </tr>
    `;
    let lastSec = null;
    shown.forEach(e => {
      if (e.section !== lastSec) {
        lastSec = e.section;
        html += `
          <tr style="background:#F1F5F9; border-bottom:1px solid #CBD5E1;">
            <td style="padding:4px 10px; font-size:11.5px; color:#64748B; font-weight:700;">區段</td>
            <td class="mono" style="padding:4px 10px; font-weight:800; color:#0369A1;">[${_escAttr(e.section)}]</td>
            <td class="mono" style="padding:4px 10px; font-weight:800; color:#0369A1;">[${_escAttr(e.section)}]</td>
            <td style="padding:4px 10px;"></td>
          </tr>
        `;
      }
      if (e.isChanged) {
        html += `
          <tr style="border-bottom:1.5px solid #FDE047;">
            <td style="padding:7px 10px; background:#FEF9C3; font-size:12px; font-weight:800; color:#854D0E;">
              ${_escAttr(e.desc)}
            </td>
            <td class="mono" style="padding:7px 10px; background:#FEE2E2; color:#991B1B; font-size:12.5px;">
              <span>${_escAttr(e.key)}=</span><span style="background:#FECACA; color:#7F1D1D; font-weight:900; padding:2px 6px; border-radius:4px; text-decoration:line-through;">${_escAttr(e.oldVal)}</span>
            </td>
            <td class="mono" style="padding:7px 10px; background:#FEF08A; color:#14532D; font-size:12.5px;">
              <span style="font-weight:800;">${_escAttr(e.key)}=</span><span style="background:#22C55E; color:#FFFFFF; font-weight:900; padding:2px 8px; border-radius:4px; box-shadow:0 1px 3px rgba(0,0,0,0.15);">${_escAttr(e.newVal)}</span>
            </td>
            <td style="padding:7px 10px; background:#FEF9C3; text-align:right; white-space:nowrap;">
              <span style="background:#16A34A; color:#FFF; font-size:11px; font-weight:800; padding:2px 6px; border-radius:4px;">✨ 已修改</span>
              <button onclick="revertSingleIniKey('${_escAttr(e.file)}','${_escAttr(e.section)}','${_escAttr(e.key)}')" class="btn" style="padding:2px 7px; font-size:11px; margin-left:4px; background:#FFF; color:#475569;" title="取消此項修改">↩ 還原</button>
            </td>
          </tr>
        `;
      } else {
        html += `
          <tr style="border-bottom:1px solid #F1F5F9; color:#64748B;">
            <td style="padding:4px 10px; font-size:11.5px;">${_escAttr(e.desc)}</td>
            <td class="mono" style="padding:4px 10px; font-size:12px;">${_escAttr(e.key)}=${_escAttr(e.oldVal)}</td>
            <td class="mono" style="padding:4px 10px; font-size:12px;">${_escAttr(e.key)}=${_escAttr(e.newVal)}</td>
            <td style="padding:4px 10px; font-size:11px; text-align:right; color:#94A3B8;">未變更</td>
          </tr>
        `;
      }
    });
    return html;
  };

  const diffTableRows = buildFileDiffRows('System.ini', sEntries) + buildFileDiffRows('Global.ini', gEntries);

  return `
    <div style="display:flex; flex-direction:column; gap:12px;">
      <!-- 頂部導覽與切換列 -->
      <div style="background:#F0FDF4; border:1.5px solid #22C55E; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
          <button onclick="switchIniStageMode('edit')" class="btn" style="padding:6px 14px; font-size:13px; background:#FFFFFF; color:#1E293B; border:1.5px solid #94A3B8; font-weight:800;">
            ⬅ 返回修改設定
          </button>
          <span style="background:#16A34A; color:#FFF; font-weight:800; font-size:12px; padding:2px 8px; border-radius:999px;">步驟 2 / 2：反白確認左右差異與寫入 INI</span>
          <span style="font-weight:800; font-size:13.5px; color:#14532D;">請確認下方反白差異與 AI 報告，點擊右下角即可寫入並彈出 INI！</span>
        </div>
        <div style="display:flex; gap:6px;">
          <button onclick="toggleIniReviewShowAllLines(false)" class="btn" style="padding:4px 11px; font-size:12px; ${!INI_REVIEW_SHOW_ALL_LINES ? 'background:#16A34A;color:#FFF;font-weight:800;' : 'background:#FFF;color:#334155;'}">
            🎯 只看本次反白修改行 (${allChanged.length})
          </button>
          <button onclick="toggleIniReviewShowAllLines(true)" class="btn" style="padding:4px 11px; font-size:12px; ${INI_REVIEW_SHOW_ALL_LINES ? 'background:#2563EB;color:#FFF;font-weight:800;' : 'background:#FFF;color:#334155;'}">
            📄 展開完整 INI 全文對照 (${sEntries.length + gEntries.length})
          </button>
        </div>
      </div>

      <!-- 🤖 AI 白話修改總結報告 -->
      ${aiReportHtml}

      <!-- 🆚 左右同行嚴格對齊反白差異表 -->
      <div style="border:1.5px solid #94A3B8; border-radius:8px; overflow:hidden; background:#FFFFFF;">
        <div style="max-height:340px; overflow:auto;">
          <table style="width:100%; border-collapse:collapse;">
            <thead>
              <tr style="background:#E2E8F0; color:#0F172A; font-size:12.5px; border-bottom:1.5px solid #94A3B8;">
                <th style="padding:8px 10px; text-align:left; width:20%;">參數中文用途</th>
                <th style="padding:8px 10px; text-align:left; width:34%; background:#FEE2E2; color:#991B1B;">⬅️ 修改前（原始 INI 設定值）</th>
                <th style="padding:8px 10px; text-align:left; width:34%; background:#FEF08A; color:#14532D;">➡️ 修改後（反白高亮新設定值）</th>
                <th style="padding:8px 10px; text-align:right; width:12%;">狀態 / 還原</th>
              </tr>
            </thead>
            <tbody>
              ${diffTableRows || `<tr><td colspan="4" style="padding:24px; text-align:center; color:#64748B; font-size:13px;">目前尚無修改行（可點右上角「📄 展開完整 INI 全文對照」檢視全部原始設定，或點「⬅ 返回修改設定」進行調整）</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 存檔成功通知橫幅 -->
      <div id="iniSaveResultBanner" style="display:none; background:#DCFCE7; border:1.5px solid #22C55E; border-radius:6px; padding:10px 14px;"></div>

      <!-- 最終確認寫入並彈出 INI 行動列 -->
      <div style="background:#F0FDF4; border:2px solid #22C55E; border-radius:8px; padding:12px 16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <button onclick="switchIniStageMode('edit')" class="btn" style="padding:6px 14px; font-size:12.5px; background:#FFFFFF; color:#334155; border:1px solid #94A3B8; font-weight:700;">⬅ 返回繼續修改</button>
          <button onclick="saveAndOpenModifiedIni('global')" class="btn" style="padding:6px 12px; font-size:12px; background:#FFFFFF; color:#1E40AF; border:1px solid #93C5FD; font-weight:700;">📄 寫入並只彈出 Global.ini</button>
          <button onclick="saveAndOpenModifiedIni('system')" class="btn" style="padding:6px 12px; font-size:12px; background:#FFFFFF; color:#5B21B6; border:1px solid #C4B5FD; font-weight:700;">⚙️ 寫入並只彈出 System.ini</button>
        </div>
        <button onclick="saveAndOpenModifiedIni('auto')" class="btn btn-primary-green" style="padding:9px 24px; font-size:14.5px; font-weight:900; box-shadow:0 3px 10px rgba(22,163,74,0.3);">
          💾 確認差異無誤！寫入硬碟並立即彈出剛剛改的 INI
        </button>
      </div>
    </div>
  `;
}

function renderGlobalEditorPanel() {
  const box = document.getElementById('auditGlobalEditor');
  if (!box || !STATE.workspace) return;
  const ws = STATE.workspace;
  _ensureIniSnapshots(ws);
  const duts = ws.duts || [];
  const insts = ws.instruments || [];
  const gSettings = (ws.global_ini && ws.global_ini.Settings) || {};
  const stationNames = Object.keys(ws.stations || {});
  const { usedVars, usedInstRefs } = _collectUsedVarsAndInstruments(ws);

  const totalIniChanges = [
    ..._collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini'),
    ..._collectIniDiffEntries(STATE.origSystemIni, ws.system_ini, 'System.ini')
  ].filter(e => e.isChanged).length;

  const tabBtn = (id, labelHtml) => {
    const active = AUDIT_GLOBAL_TAB === id;
    return `<button onclick="switchGlobalEditorTab('${id}')" class="btn" style="padding:5px 12px; font-size:13px; ${active ? 'background:#2563EB;color:#FFFFFF;border-color:#1D4ED8;font-weight:700;' : 'background:#FFFFFF;color:#334155;border-color:#CBD5E1;'}">${labelHtml}</button>`;
  };

  let bodyHtml = '';
  if (AUDIT_GLOBAL_TAB === 'ini_diff') {
    bodyHtml = (INI_STAGE_MODE === 'review')
      ? _renderIniStage2ReviewHtml(ws)
      : _renderIniStage1EditHtml(ws, usedVars, totalIniChanges);
  } else if (AUDIT_GLOBAL_TAB === 'station_isn') {
    const rowsHtml = duts.map((d, i) => {
      const scanKey = _findKeyByPrefix(d, 'ScanBarcode', 'ScanBarcode({Name,Length,Pattern})');
      const loadVal = String(d['Load'] || '').trim();
      const isEnabled = loadVal !== '' && loadVal.toLowerCase() !== 'false' && loadVal !== '0';
      const sb = _parseScanBarcode(d[scanKey]);
      const patPresets = ['[0-9]', '[0-9A-Z]', '[0-9A-Za-z]'];
      const sbHtml = sb.simple ? `
        <div style="display:flex; gap:5px; align-items:center; flex-wrap:wrap;">
          <input value="${_escAttr(sb.name)}" onchange="_updateScanBarcodeField(${i},'${_escAttr(scanKey)}','name',this.value)" class="mono" style="width:58px;padding:4px;font-size:12px;" title="條碼名稱">
          <input type="number" min="1" max="64" value="${_escAttr(sb.len)}" onchange="_updateScanBarcodeField(${i},'${_escAttr(scanKey)}','len',this.value)" class="mono" style="width:52px;padding:4px;font-size:12px;" title="位數"> 碼
          <select onchange="if(this.value!=='__CUSTOM__'){_updateScanBarcodeField(${i},'${_escAttr(scanKey)}','pat',this.value);renderGlobalEditorPanel();}" class="mono" style="padding:4px;font-size:12px;">
            <option value="[0-9]" ${sb.pat==='[0-9]'?'selected':''}>純數字 [0-9]</option>
            <option value="[0-9A-Z]" ${sb.pat==='[0-9A-Z]'?'selected':''}>大寫英數 [0-9A-Z]</option>
            <option value="[0-9A-Za-z]" ${sb.pat==='[0-9A-Za-z]'?'selected':''}>大小寫 [0-9A-Za-z]</option>
            ${!patPresets.includes(sb.pat) ? `<option value="__CUSTOM__" selected>自訂 (${_escAttr(sb.pat)})</option>` : ''}
          </select>
        </div>
      ` : `<input value="${_escAttr(sb.raw)}" onchange="STATE.workspace.duts[${i}]['${_escAttr(scanKey)}']=this.value" class="mono" style="width:100%;padding:4px;font-size:12px;box-sizing:border-box;">`;

      return `
        <tr>
          <td style="text-align:center;">
            <button onclick="toggleDutLoadState(${i})" class="btn" style="padding:3px 10px; font-size:12px; font-weight:700; ${isEnabled ? 'background:#DCFCE7;color:#166534;border-color:#4ADE80;' : 'background:#F1F5F9;color:#64748B;border-color:#CBD5E1;'}">
              ${isEnabled ? '🟢 啟用' : '⚪ 停用'}
            </button>
          </td>
          <td><input value="${_escAttr(d['Station']||'')}" onchange="STATE.workspace.duts[${i}]['Station']=this.value" class="mono" style="width:130px;padding:4px;font-size:12px;"></td>
          <td><input value="${_escAttr(d['DUT Name']||'')}" onchange="STATE.workspace.duts[${i}]['DUT Name']=this.value" class="mono" style="width:155px;padding:4px;font-size:12px;"></td>
          <td>${sbHtml}</td>
          <td><input value="${_escAttr(d['SFIS_DeviceID']||'')}" onchange="STATE.workspace.duts[${i}]['SFIS_DeviceID']=this.value" class="mono" style="width:95px;padding:4px;font-size:12px;"></td>
          <td><button class="btn" style="padding:2px 7px;font-size:12px;" onclick="STATE.workspace.duts.splice(${i},1);renderGlobalEditorPanel();">✕</button></td>
        </tr>
      `;
    }).join('');

    bodyHtml = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px; background:#EFF6FF; border:1px solid #93C5FD; border-radius:6px; padding:8px 10px;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; font-size:12.5px;">
          <span style="font-weight:700; color:#1E3A8A;">🔢 快速批量設定 ISN 條碼：</span>
          <label>位數 <input id="geIsnLen" type="number" min="1" max="64" value="15" class="mono" style="width:54px;padding:3px 5px;"></label>
          <label>規則 <select id="geIsnPat" class="mono" style="padding:3px 5px;">
            <option value="[0-9]">[0-9]（純數字）</option>
            <option value="[0-9A-Z]">[0-9A-Z]（大寫英數字）</option>
            <option value="[0-9A-Za-z]">[0-9A-Za-z]（大小寫英數字）</option>
          </select></label>
          <button onclick="batchApplyDutIsn()" class="btn btn-primary-blue" style="padding:3px 10px; font-size:12px;">套用至所有站別</button>
        </div>
        <button onclick="addNewDutRow()" class="btn btn-primary-green" style="padding:4px 10px; font-size:12.5px;">+ 新增站別列</button>
      </div>
      <div style="overflow:auto; max-height:360px;">
        <table class="meas-table">
          <thead><tr><th>測試開關</th><th>站別 (Station)</th><th>DUT 名稱</th><th>條碼規則 (名稱 / 位數 / 格式)</th><th>SFIS 機台碼</th><th>刪</th></tr></thead>
          <tbody>${rowsHtml || '<tr><td colspan="6" style="text-align:center;color:#64748B;">此工作簿沒有 DUTs 資料</td></tr>'}</tbody>
        </table>
      </div>
    `;
  } else if (AUDIT_GLOBAL_TAB === 'net_ip') {
    const ipKeys = Object.keys(gSettings).filter(k => /IP/i.test(k) && (usedVars.has(k) || /^(PCIP_1|DUTIP_1|GoldenIP)$/i.test(k)));
    const ipRows = ipKeys.map(k => `
      <tr>
        <td style="font-size:12.5px; color:#334155;">${_describeGlobalVar(k)}</td>
        <td class="mono" style="font-weight:700; color:#1E3A8A;">${_escAttr(k)}</td>
        <td><input value="${_escAttr(gSettings[k])}" onchange="setGlobalIniValueLive('Settings','${_escAttr(k)}',this.value)" class="mono" style="width:100%;padding:4px;font-size:12.5px;box-sizing:border-box;"></td>
      </tr>
    `).join('');

    const dutConnRows = duts.map((d, i) => {
      const connKey = _findKeyByPrefix(d, 'Connection1', 'Connection1(Type,Name,ConnectString)');
      const c = _parseConn1(d[connKey]);
      if (c.structured) {
        return `
          <tr>
            <td class="mono" style="font-weight:700;">${_escAttr(d['Station'] || d['DUT Name'])}</td>
            <td style="font-size:12px; color:#475569;">DUTs 連線 (${_escAttr(c.proto)})</td>
            <td>
              <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
                <span style="font-size:12px;">DUT IP:</span>
                <input value="${_escAttr(c.dutIp)}" onchange="_updateConn1Field(${i},'${_escAttr(connKey)}','dutIp',this.value)" class="mono" style="width:130px;padding:4px;font-size:12px;">
                <span style="font-size:12px;">Port:</span>
                <input value="${_escAttr(c.port)}" onchange="_updateConn1Field(${i},'${_escAttr(connKey)}','port',this.value)" class="mono" style="width:65px;padding:4px;font-size:12px;">
              </div>
            </td>
          </tr>
        `;
      }
      return '';
    }).join('');

    const pingRows = [];
    stationNames.forEach(sn => {
      (ws.stations[sn] || []).forEach((st, idx) => {
        const sendStr = String(st.Send || '');
        if (/Utility\.Ping|PING@/i.test(sendStr)) {
          pingRows.push(`
            <tr>
              <td class="mono" style="font-weight:700;">${_escAttr(sn)}</td>
              <td class="mono">第 ${idx + 2} 列 (:Utility.Ping)</td>
              <td><input value="${_escAttr(sendStr)}" onchange="updatePingStepSend('${_escAttr(sn)}', ${idx}, this.value)" class="mono" style="width:100%;padding:4px;font-size:12px;box-sizing:border-box;"></td>
            </tr>
          `);
        }
      });
    });

    bodyHtml = `
      <div style="font-size:12.5px; color:#475569; margin-bottom:8px;">僅列出本腳本實際使用的 <b>PC / DUT 網路 IP</b>、<b>站別連線 Port</b> 與 <b>Ping 目標 IP</b>。</div>
      <div style="overflow:auto; max-height:360px;">
        <table class="meas-table">
          <thead><tr><th>用途 / 站別</th><th>欄位 / 變數</th><th>IP / Port 設定值</th></tr></thead>
          <tbody>
            ${ipRows}
            ${dutConnRows}
            ${pingRows.join('')}
          </tbody>
        </table>
      </div>
    `;
  } else if (AUDIT_GLOBAL_TAB === 'inst_com') {
    const isInstUsed = (inst) => {
      const m = String(inst['Mount'] || '').trim();
      const nm = String(inst['Name'] || '').trim().toLowerCase();
      const fns = String(inst['Functions'] || '').split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
      return Boolean(m) || usedInstRefs.has(nm) || fns.some(f => usedInstRefs.has(f));
    };
    const activeInsts = [];
    const idleInsts = [];
    insts.forEach((inst, i) => {
      if (isInstUsed(inst)) activeInsts.push({ inst, i });
      else idleInsts.push({ inst, i });
    });

    const renderInstRow = ({ inst, i }) => `
      <tr>
        <td>
          <div style="display:flex; gap:4px; align-items:center;">
            <input value="${_escAttr(inst['Mount']||'')}" onchange="STATE.workspace.instruments[${i}]['Mount']=this.value" class="mono" style="width:125px;padding:4px;font-size:12px;" placeholder="站名">
            <select onchange="appendMountStation(${i}, this.value); this.value='';" style="padding:3px;font-size:11.5px;max-width:80px;">
              <option value="">+站別</option>
              ${stationNames.map(sn => `<option value="${_escAttr(sn)}">${sn}</option>`).join('')}
            </select>
          </div>
        </td>
        <td class="mono" style="font-weight:700;">${_escAttr(inst['Name']||'')}</td>
        <td><input value="${_escAttr(inst['Settings']||'')}" onchange="STATE.workspace.instruments[${i}]['Settings']=this.value" class="mono" style="width:230px;padding:4px;font-size:12px;"></td>
        <td class="mono" style="font-size:12px;">${_escAttr(inst['Functions']||'')}</td>
        <td><input value="${_escAttr(inst['Version']||'')}" onchange="STATE.workspace.instruments[${i}]['Version']=this.value" class="mono" style="width:70px;padding:4px;font-size:12px;"></td>
      </tr>
    `;

    bodyHtml = `
      <div style="font-size:12.5px; color:#475569; margin-bottom:8px;">顯示本腳本 Excel <b>Instrument 工作表</b>實際掛載使用中的儀器（${activeInsts.length} 台）。</div>
      <div style="overflow:auto; max-height:360px; display:flex; flex-direction:column; gap:10px;">
        <table class="meas-table">
          <thead><tr><th>Mount (掛載站別)</th><th>儀器名稱</th><th>Settings (IP / COM / GPIB)</th><th>Functions</th><th>Version</th></tr></thead>
          <tbody>${activeInsts.map(renderInstRow).join('') || '<tr><td colspan="5" style="text-align:center;color:#64748B;">目前測站尚無掛載使用中之儀器</td></tr>'}</tbody>
        </table>
        ${idleInsts.length > 0 ? `
          <details style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:6px 10px;">
            <summary style="cursor:pointer; font-weight:700; font-size:12.5px; color:#475569;">📦 展開其餘未掛載的型錄儀器（共 ${idleInsts.length} 台）</summary>
            <table class="meas-table" style="margin-top:6px;">
              <thead><tr><th>Mount</th><th>儀器名稱</th><th>Settings</th><th>Functions</th><th>Version</th></tr></thead>
              <tbody>${idleInsts.map(renderInstRow).join('')}</tbody>
            </table>
          </details>
        ` : ''}
      </div>
    `;
  }

  box.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid #3B82F6; border-radius:8px; padding:12px 14px; margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid #E2E8F0;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="font-weight:700; font-size:14.5px; color:#0F172A;">⚙️ 全域與 INI 設定工作台</span>
          ${tabBtn('ini_diff', `🎛️ INI 設定與 AI 差異確認 <span id="iniTabDiffCountBadge">(${totalIniChanges})</span>`)}
          ${tabBtn('station_isn', `📋 Excel 站別與 ISN 條碼 (${duts.length})`)}
          ${tabBtn('net_ip', '🌐 Excel 網路 IP / Ping')}
          ${tabBtn('inst_com', '🔌 Excel 儀器掛載表')}
        </div>
        <div style="display:flex; gap:8px;">
          ${AUDIT_GLOBAL_TAB !== 'ini_diff' ? `<button onclick="applyGlobalEditorAndReaudit()" class="btn btn-primary-blue" style="padding:5px 14px; font-size:13px;">✔ 套用 Excel 表格微調</button>` : ''}
          <button onclick="toggleGlobalEditorPanel()" class="btn" style="padding:5px 10px; font-size:13px; background:#E2E8F0; color:#334155;">收合 ▲</button>
        </div>
      </div>
      ${bodyHtml}
    </div>
  `;
}

function toggleDutLoadState(idx) {
  const d = STATE.workspace.duts[idx];
  const cur = String(d['Load'] || '').trim();
  const isEnabled = cur !== '' && cur.toLowerCase() !== 'false' && cur !== '0';
  d['Load'] = isEnabled ? 'false' : '*(Load_1)';
  renderGlobalEditorPanel();
}

function addNewDutRow() {
  const duts = STATE.workspace.duts = STATE.workspace.duts || [];
  const sample = duts[0] || {};
  const scanKey = _findKeyByPrefix(sample, 'ScanBarcode', 'ScanBarcode({Name,Length,Pattern})');
  const connKey = _findKeyByPrefix(sample, 'Connection1', 'Connection1(Type,Name,ConnectString)');
  const newRow = {
    'Load': '*(Load_1)',
    'DUT Name': 'PROJ$MB',
    'Station': `MB,${duts.length + 1}`,
    'Parameter': '*(PCIP_1),1',
    'SFIS_DeviceID': '*(DEVID_1)'
  };
  newRow[scanKey] = '{ ISN,15,[0-9] }';
  newRow[connKey] = '"UDP","LAN","*(PCIP_1),192.168.100.10,2345,0,10000"';
  duts.push(newRow);
  renderGlobalEditorPanel();
}

function appendMountStation(instIdx, stName) {
  if (!stName) return;
  const inst = STATE.workspace.instruments[instIdx];
  const cur = String(inst['Mount'] || '').split(',').map(x => x.trim()).filter(Boolean);
  if (!cur.includes(stName)) cur.push(stName);
  inst['Mount'] = cur.join(',');
  renderGlobalEditorPanel();
}

function addGlobalIniVar() {
  const sec = prompt('請輸入區段名稱（Settings 或 Scripts）：', 'Settings');
  if (!sec || !['Settings', 'Scripts'].includes(sec.trim())) return;
  const k = prompt('請輸入變數名稱（例如 DUT_UR1 或 FW_VERSION）：', '');
  if (!k || !k.trim()) return;
  const v = prompt(`請輸入 ${k.trim()} 的設定值：`, '');
  if (v === null) return;
  setGlobalIniValueLive(sec.trim(), k.trim(), v, true);
}

function batchApplyDutIsn() {
  const len = Math.max(1, parseInt(document.getElementById('geIsnLen').value || '15', 10));
  const pat = document.getElementById('geIsnPat').value || '[0-9]';
  const rule = `{ ISN,${len},${pat} }`;
  (STATE.workspace.duts || []).forEach(d => {
    const scanKey = _findKeyByPrefix(d, 'ScanBarcode', 'ScanBarcode({Name,Length,Pattern})');
    d[scanKey] = rule;
  });
  renderGlobalEditorPanel();
}

function updatePingStepSend(sheetName, idx, newVal) {
  const step = STATE.workspace.stations[sheetName][idx];
  if (!step) return;
  const oldVal = step.Send || '';
  step.Send = newVal;
  STATE.workspace._modified_cells = STATE.workspace._modified_cells || [];
  STATE.workspace._modified_cells.push({
    sheet: sheetName, row: idx + 2, col_name: 'Send',
    old: oldVal, new: newVal, note: '透過全域微調區修改 Ping IP'
  });
}

async function applyGlobalEditorAndReaudit() {
  if (!STATE.workspace) return;
  const res = await fetch('/api/re_audit', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ workspace: STATE.workspace })
  });
  const data = await res.json();
  if (data.status !== 'ok') {
    alert(data.message || '覆檢失敗');
    return;
  }
  STATE.report = data.report;
  if (data.isn_info) STATE.isnInfo = data.isn_info;
  STATE.pendingInserts = STATE.pendingInserts || [];
  const labelMap = { station_isn: '站別開關與 ISN', net_ip: '網路 IP / Ping / Port', inst_com: '儀器掛載與 COM Port', ini_diff: 'INI 左右對照微調' };
  STATE.pendingInserts.push({
    sheet: labelMap[AUDIT_GLOBAL_TAB] || '全域設定',
    inst: 'Excel 全域微調',
    summary: '已套用 Excel 全域微調並完成即時覆檢（請點擊底部「💾 寫入並匯出 Excel (*_FIXED.xlsx)」）'
  });
  renderGlobalEditorPanel();
  renderAuditResults();
}
