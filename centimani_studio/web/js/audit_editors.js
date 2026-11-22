// AI-Guided Smart INI Notepad (Build v0.5.6)
// Combines Ideas 1 + 2 + 3 + AI Intent Recommendation:
// 1. Top Bar: AI Intent Quick Pills ("我想改 SFIS / iPLAS", "我想改 COM Port", "我想改 IP 網段", "我想切量產/調試") + Natural Language Command Box ("改 COM18", "開 SFIS").
// 2. Center: Clean Notepad-style line-by-line editor (only shows the relevant 5~8 lines for your task; modified lines immediately highlight inline: [原本: COM4] ➔ [COM18]).
// 3. Bottom: AI Plain-Language Summary & Advice + Single Green Button to Save & Pop Up the modified INI in Notepad.

let AUDIT_GLOBAL_TAB = 'ini_diff';
let INI_AI_INTENT = 'core'; // 'core' | 'sfis' | 'com' | 'ip' | 'all'
let INI_AI_LAST_MSG = '';

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
  INI_AI_INTENT = 'core';
  INI_AI_LAST_MSG = '';
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
    SFIS_Enable: 'SFIS 產線過站總開關 (0=關, 1=開)',
    SFIS_LinkIPLAS: 'SFIS 連動上傳 iPLAS (0=關, 1=開)',
    SFIS_TSP: 'SFIS 站別與路由代碼',
    SFIS_WebLink: 'SFIS WebService 網址',
    iPLAS_Enable: 'iPLAS 數據上傳開關 (0=關, 1=開)',
    iPLAS_Site: 'iPLAS 廠區代碼 (如 DC / WQ)',
    iPLAS_ProjectName: 'iPLAS 專案名稱',
    DebugMode: '除錯模式 (1=免簽章調試, 0=正式量產)',
    RetryCount: '測項失敗自動重測次數',
    CSVReport_Enable: '自動產出 CSV 報表 (0=關, 1=開)',
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
    return nv === '1'
      ? `🟢 <b>開啟 SFIS 過站</b>（站別碼 <code>${_escAttr(sys.SFIS_TSP || 'PEGA,2')}</code>，開測前將連線 SFIS 檢查路由）`
      : `⚪ <b>關閉 SFIS 過站</b>（切為單機離線測試，不檢查 SFIS 路由）`;
  }
  if (k === 'SFIS_LinkIPLAS') {
    return nv === '1' ? `🔗 <b>開啟 SFIS 連動 iPLAS</b>` : `⚪ <b>關閉 SFIS 連動 iPLAS</b>`;
  }
  if (k === 'iPLAS_Enable') {
    return nv === '1'
      ? `☁️ <b>開啟 iPLAS 數據上傳</b>（目標廠區 <code>${_escAttr(sys.iPLAS_Site || 'DC')}</code>）`
      : `⚪ <b>關閉 iPLAS 數據上傳</b>`;
  }
  if (k === 'DebugMode') {
    return nv === '0'
      ? `🔒 <b>切換為量產模式 (DebugMode=0)</b>（⚠️ 啟動時強制檢驗 Checksum，存檔時系統將自動重算簽章）`
      : `🛠️ <b>切換為工程除錯模式 (DebugMode=1)</b>（免驗 Checksum 簽章）`;
  }
  if (/^DUT_UR/i.test(k)) {
    return `🔌 <b>待測物序列埠 (${_escAttr(k)})</b> 由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>`;
  }
  if (/^(DUTIP_|PCIP_|GoldenIP)/i.test(k)) {
    return `🌐 <b>${_escAttr(e.desc)} (${_escAttr(k)})</b> 由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>`;
  }
  return `✏️ <b>${_escAttr(e.desc)} (${_escAttr(k)})</b> 由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>`;
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

function selectIniAiIntent(intent) {
  INI_AI_INTENT = intent;
  INI_AI_LAST_MSG = '';
  renderGlobalEditorPanel();
}

function applyAiPresetBundle(presetType) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  const sys = STATE.workspace.system_ini;
  const gSet = (STATE.workspace.global_ini && STATE.workspace.global_ini.Settings) || {};

  if (presetType === 'mp_sfis_on') {
    sys.SFIS_Enable = '1';
    sys.SFIS_LinkIPLAS = '1';
    sys.iPLAS_Enable = '1';
    sys.DebugMode = '0';
    INI_AI_LAST_MSG = '🤖 AI 已套用「量產過站標準組合」：開啟 SFIS_Enable=1、SFIS_LinkIPLAS=1、iPLAS_Enable=1，並切換為量產驗簽章模式 DebugMode=0。';
  } else if (presetType === 'eng_offline') {
    sys.SFIS_Enable = '0';
    sys.SFIS_LinkIPLAS = '0';
    sys.iPLAS_Enable = '0';
    sys.DebugMode = '1';
    INI_AI_LAST_MSG = '🤖 AI 已套用「工程離線調試組合」：關閉 SFIS 與 iPLAS 連線檢查，並開啟 DebugMode=1 免簽章調試模式。';
  } else if (presetType === 'sync_pc_ip') {
    const dutIp = String(gSet.DUTIP_1 || '').trim();
    const m = dutIp.match(/^(\d+\.\d+\.\d+)\.(\d+)$/);
    if (m) {
      const newPcIp = `${m[1]}.${m[2] === '100' ? '101' : '100'}`;
      gSet.PCIP_1 = newPcIp;
      INI_AI_LAST_MSG = `🤖 AI 已自動根據待測物 IP (${dutIp})，將電腦端網卡 PCIP_1 同步設為同網段之 ${newPcIp}！`;
    }
  }
  _recordPendingIniNotice(INI_AI_LAST_MSG || 'AI 推薦設定套用');
  renderGlobalEditorPanel();
}

function runIniNaturalLanguageCommand() {
  if (!STATE.workspace) return;
  const inp = document.getElementById('iniAiNlInput');
  const raw = (inp ? inp.value : '').trim();
  if (!raw) return;
  _ensureIniSnapshots(STATE.workspace);
  const txt = raw.toLowerCase();
  const sys = STATE.workspace.system_ini;
  const gSet = (STATE.workspace.global_ini && STATE.workspace.global_ini.Settings) || {};
  const actions = [];

  // 1. 偵測 COM Port (如 "改COM18", "COM8", "治具COM5")
  const comMatch = raw.match(/com\s*(\d+)/i);
  if (comMatch) {
    const comVal = 'COM' + comMatch[1];
    if (txt.includes('治具') || txt.includes('fixture')) {
      gSet.PCUART_fixture_1 = comVal;
      actions.push(`氣動治具 PCUART_fixture_1 設為 ${comVal}`);
    } else if (txt.includes('led') || txt.includes('燈')) {
      gSet.LED_AZ1 = comVal;
      actions.push(`FeasaLED LED_AZ1 設為 ${comVal}`);
    } else {
      gSet.DUT_UR1 = comVal;
      actions.push(`待測物序列埠 DUT_UR1 設為 ${comVal}`);
    }
    INI_AI_INTENT = 'com';
  } else if (txt.includes('com') || txt.includes('序列埠')) {
    INI_AI_INTENT = 'com';
    actions.push('已為您篩選出本腳本所有 COM Port 設定行');
  }

  // 2. 偵測 IP 位址 (如 "改IP 192.168.1.50")
  const ipMatch = raw.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/);
  if (ipMatch) {
    const ipVal = ipMatch[1];
    if (txt.includes('電腦') || txt.includes('pc')) {
      gSet.PCIP_1 = ipVal;
      actions.push(`電腦網卡 PCIP_1 設為 ${ipVal}`);
    } else {
      gSet.DUTIP_1 = ipVal;
      actions.push(`待測物連線 DUTIP_1 設為 ${ipVal}`);
    }
    INI_AI_INTENT = 'ip';
  } else if (txt.includes('ip') || txt.includes('網段') || txt.includes('網路')) {
    INI_AI_INTENT = 'ip';
    actions.push('已為您篩選出本腳本所有 IP 網路設定行');
  }

  // 3. 偵測 SFIS / iPLAS / 量產 / 調試
  if (txt.includes('sfis')) {
    INI_AI_INTENT = 'sfis';
    if (txt.includes('關') || txt.includes('off') || txt.includes('0')) {
      sys.SFIS_Enable = '0';
      actions.push('已關閉 SFIS_Enable=0');
    } else if (txt.includes('開') || txt.includes('on') || txt.includes('1')) {
      sys.SFIS_Enable = '1';
      actions.push('已開啟 SFIS_Enable=1');
    } else {
      actions.push('已為您篩選出 SFIS 與 iPLAS 相關設定行');
    }
  }
  if (txt.includes('iplas')) {
    INI_AI_INTENT = 'sfis';
    if (txt.includes('關') || txt.includes('off') || txt.includes('0')) {
      sys.iPLAS_Enable = '0';
      actions.push('已關閉 iPLAS_Enable=0');
    } else {
      sys.iPLAS_Enable = '1';
      actions.push('已開啟 iPLAS_Enable=1');
    }
  }
  if (txt.includes('量產')) {
    INI_AI_INTENT = 'sfis';
    applyAiPresetBundle('mp_sfis_on');
    return;
  }
  if (txt.includes('調試') || txt.includes('除錯') || txt.includes('離線') || txt.includes('debug')) {
    INI_AI_INTENT = 'sfis';
    applyAiPresetBundle('eng_offline');
    return;
  }

  if (actions.length > 0) {
    INI_AI_LAST_MSG = `🤖 AI 已根據您的指令「${raw}」執行：${actions.join('、')}！`;
    _recordPendingIniNotice(INI_AI_LAST_MSG);
  } else {
    INI_AI_LAST_MSG = `🤖 AI 提示：您可以輸入「改 COM18」、「開 SFIS」、「關 SFIS」、「改 IP 192.168.1.50」或「切量產模式」，或直接點上方分類按鈕。`;
  }
  renderGlobalEditorPanel();
}

function setSystemIniValueLive(key, val, rerender = true) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.system_ini[key] = String(val);
  _recordPendingIniNotice(`System.ini: ${key}=${val}`);
  if (rerender) renderGlobalEditorPanel();
}

function setGlobalIniValueLive(sec, key, val, rerender = true) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.global_ini = STATE.workspace.global_ini || { Settings: {}, Scripts: {} };
  STATE.workspace.global_ini[sec] = STATE.workspace.global_ini[sec] || {};
  STATE.workspace.global_ini[sec][key] = String(val);
  _recordPendingIniNotice(`Global.ini [${sec}] ${key}=${val}`);
  if (rerender) renderGlobalEditorPanel();
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
  INI_AI_LAST_MSG = '🤖 已將所有 INI 設定還原為原始值。';
  renderGlobalEditorPanel();
}

// Keep compatibility functions for tests & callers
function _renderIniStage1EditHtml(ws, usedVars, allChangedCount) {
  return _renderSmartIniNotepadHtml(ws, usedVars);
}
function _renderIniStage2ReviewHtml(ws) {
  const { usedVars } = _collectUsedVarsAndInstruments(ws);
  return _renderSmartIniNotepadHtml(ws, usedVars);
}

function _renderSmartIniNotepadHtml(ws, usedVars) {
  const gEntries = _collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini');
  const sEntries = _collectIniDiffEntries(STATE.origSystemIni, ws.system_ini, 'System.ini');
  const allEntries = [...sEntries, ...gEntries];
  const allChanged = allEntries.filter(e => e.isChanged);

  // 根據使用者選擇的 AI 意圖，自動篩選出最精準的那幾行（再也不把 50 行塞在一起！）
  const isComKey = (e) => e.file === 'Global.ini' && (/^(DUT_UR|PCUART|LED_AZ|WLAN_COM)/i.test(e.key) || /^COM\d+/i.test(e.newVal) || /^COM\d+/i.test(e.oldVal));
  const isIpKey = (e) => (e.file === 'Global.ini' && /IP/i.test(e.key)) || e.key === 'IpFinder_Enable';
  const isSfisKey = (e) => e.file === 'System.ini' && /^(SFIS_|iPLAS_|DebugMode|RetryCount|CSVReport_)/i.test(e.key);
  const isCoreKey = (e) => e.isChanged
    || (e.file === 'System.ini' && /^(SFIS_Enable|SFIS_LinkIPLAS|iPLAS_Enable|DebugMode|SFIS_TSP|iPLAS_Site)$/i.test(e.key))
    || (e.file === 'Global.ini' && (usedVars.has(e.key) || /^(DUT_UR1|DUTIP_1|PCIP_1|DAQ_1|LED_AZ1|FW_VERSION)$/i.test(e.key)));

  let filteredEntries = [];
  let aiRecommendationBanner = '';

  if (INI_AI_INTENT === 'sfis') {
    filteredEntries = allEntries.filter(e => isSfisKey(e) || /^DEVID_/i.test(e.key));
    aiRecommendationBanner = `
      <div style="background:#F0F9FF; border:1.5px solid #38BDF8; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:12.5px; color:#0C4A6E;">
          🤖 <b>AI 自動推薦（改 SFIS / iPLAS）：</b>已為您只篩出過站與上傳相關的 <b>${filteredEntries.length} 行</b>設定。正式上線建議同時開啟 <code>SFIS_Enable=1</code>、<code>iPLAS_Enable=1</code> 並設為 <code>DebugMode=0</code>；工程調試則建議全關。
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <button onclick="applyAiPresetBundle('mp_sfis_on')" class="btn" style="padding:4px 10px; font-size:12px; background:#0284C7; color:#FFF; border:none; font-weight:700;">✨ AI 一鍵套用：正式量產過站組合</button>
          <button onclick="applyAiPresetBundle('eng_offline')" class="btn" style="padding:4px 10px; font-size:12px; background:#FFFFFF; color:#0369A1; border:1px solid #38BDF8; font-weight:700;">🛠️ AI 一鍵套用：工程離線調試組合</button>
        </div>
      </div>
    `;
  } else if (INI_AI_INTENT === 'com') {
    filteredEntries = allEntries.filter(isComKey);
    const usedComList = filteredEntries.filter(e => usedVars.has(e.key)).map(e => `${e.key} (${e.desc})`).join('、');
    aiRecommendationBanner = `
      <div style="background:#F0F9FF; border:1.5px solid #38BDF8; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:12.5px; color:#0C4A6E;">
          🤖 <b>AI 自動推薦（改 COM Port）：</b>AI 掃描本腳本 Excel 發現實際引用了 <b>${usedComList || 'DUT_UR1 (待測物序列埠)'}</b>。您只需在下方直接把舊 COM 改成新 COM（例如 <code>COM18</code>），改完那一行會直接反白對照！
        </div>
        <button onclick="openCommModal()" class="btn" style="padding:4px 10px; font-size:12px; background:#FFFFFF; color:#0369A1; border:1px solid #38BDF8; font-weight:700;">🔄 需要把測站 UART@ 批次轉成 SSH@ 點此</button>
      </div>
    `;
  } else if (INI_AI_INTENT === 'ip') {
    filteredEntries = allEntries.filter(isIpKey);
    aiRecommendationBanner = `
      <div style="background:#F0F9FF; border:1.5px solid #38BDF8; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:12.5px; color:#0C4A6E;">
          🤖 <b>AI 自動推薦（改 IP 網段）：</b>修改待測物 <code>DUTIP_1</code> 時，請確保電腦網卡 <code>PCIP_1</code> 前三碼處於同一網段（例如 <code>192.168.11.x</code>），否則 Ping 與 Telnet/SSH 會連線逾時。
        </div>
        <button onclick="applyAiPresetBundle('sync_pc_ip')" class="btn" style="padding:4px 10px; font-size:12px; background:#0284C7; color:#FFF; border:none; font-weight:700;">✨ AI 一鍵將電腦 PCIP_1 同步為待測物同網段</button>
      </div>
    `;
  } else if (INI_AI_INTENT === 'all') {
    filteredEntries = allEntries;
  } else {
    // 'core' (預設：只列出本腳本真正用到的核心行 + 已修改行)
    filteredEntries = allEntries.filter(isCoreKey);
    aiRecommendationBanner = `
      <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:8px 12px; font-size:12.5px; color:#334155;">
        💡 <b>智慧精簡記事本：</b>已自動隱藏本腳本沒用到的 ${Math.max(0, allEntries.length - filteredEntries.length)} 行無關變數，只把<b>這份 Excel 真正有用到的 ${filteredEntries.length} 行</b>排在下方。想改特定項目可直接點上方<b>「我想改 SFIS」</b>、<b>「我想改 COM」</b>、<b>「我想改 IP」</b>！
      </div>
    `;
  }

  // 把已修改的行或本腳本實際引用的行排在前面
  filteredEntries.sort((a, b) => {
    if (a.file !== b.file) return a.file === 'System.ini' ? -1 : 1;
    const scoreA = (a.isChanged ? 10 : 0) + (usedVars.has(a.key) ? 5 : 0);
    const scoreB = (b.isChanged ? 10 : 0) + (usedVars.has(b.key) ? 5 : 0);
    return scoreB - scoreA;
  });

  // 渲染像記事本一樣一行行直接改的列表（改過的那一行直接左紅舊值 ➔ 右綠新值反白！）
  const renderNotepadLine = (e, idx) => {
    const isBoolSwitch = e.file === 'System.ini' && /^(SFIS_Enable|SFIS_LinkIPLAS|iPLAS_Enable|DebugMode|CSVReport_Enable|IpFinder_Enable)$/i.test(e.key);
    const isUsedInExcel = usedVars.has(e.key);
    const rowBg = e.isChanged ? '#FEF9C3' : (idx % 2 === 0 ? '#FFFFFF' : '#F8FAFC');
    const rowBorder = e.isChanged ? '2px solid #EAB308' : '1px solid #E2E8F0';

    let editorControl = '';
    if (isBoolSwitch) {
      const isOn = String(e.newVal).trim() === '1';
      const onLbl = e.key === 'DebugMode' ? '1 (免簽章調試)' : '1 (開啟 ON)';
      const offLbl = e.key === 'DebugMode' ? '0 (正式量產)' : '0 (關閉 OFF)';
      editorControl = `
        <select onchange="setSystemIniValueLive('${_escAttr(e.key)}', this.value, true)" class="mono"
          style="width:170px; padding:5px 8px; font-size:13px; font-weight:800; border-radius:5px; border:1.5px solid ${e.isChanged ? '#16A34A' : '#94A3B8'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; color:${isOn ? '#15803D' : '#334155'};">
          <option value="1" ${isOn ? 'selected' : ''}>${onLbl}</option>
          <option value="0" ${!isOn ? 'selected' : ''}>${offLbl}</option>
        </select>
      `;
    } else if (e.file === 'System.ini') {
      editorControl = `
        <input value="${_escAttr(e.newVal)}"
          onchange="setSystemIniValueLive('${_escAttr(e.key)}', this.value, true)"
          class="mono"
          style="width:170px; padding:5px 8px; font-size:13px; font-weight:${e.isChanged ? '800' : '600'}; border-radius:5px; border:1.5px solid ${e.isChanged ? '#16A34A' : '#94A3B8'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A;">
      `;
    } else {
      editorControl = `
        <input value="${_escAttr(e.newVal)}"
          onchange="setGlobalIniValueLive('${_escAttr(e.section)}', '${_escAttr(e.key)}', this.value, true)"
          class="mono"
          style="width:170px; padding:5px 8px; font-size:13px; font-weight:${e.isChanged ? '800' : '600'}; border-radius:5px; border:1.5px solid ${e.isChanged ? '#16A34A' : '#94A3B8'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A;">
      `;
    }

    return `
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; padding:7px 12px; background:${rowBg}; border:${rowBorder}; border-radius:6px;">
        <!-- 左側：INI 檔案標籤 + 變數名 = -->
        <div style="display:flex; align-items:center; gap:8px; min-width:250px;">
          <span class="mono" style="font-size:11px; font-weight:800; padding:2px 6px; border-radius:4px; background:${e.file === 'System.ini' ? '#EDE9FE' : '#DBEAFE'}; color:${e.file === 'System.ini' ? '#5B21B6' : '#1E40AF'};">
            ${_escAttr(e.file)}
          </span>
          <span class="mono" style="font-weight:800; font-size:13.5px; color:#0F172A;">${_escAttr(e.key)}</span>
          <span class="mono" style="font-weight:800; color:#64748B;">=</span>
        </div>

        <!-- 中間：[原本舊值 ➔] 可直接修改的輸入框 -->
        <div style="display:flex; align-items:center; gap:8px;">
          ${e.isChanged ? `
            <span class="mono" style="background:#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5; padding:3px 8px; border-radius:4px; font-size:12.5px; font-weight:800; text-decoration:line-through;" title="修改前原始值">
              原本: ${_escAttr(e.oldVal)}
            </span>
            <span style="font-weight:900; color:#16A34A; font-size:15px;">➔</span>
          ` : ''}
          ${editorControl}
          ${e.isChanged ? `
            <button onclick="revertSingleIniKey('${_escAttr(e.file)}','${_escAttr(e.section)}','${_escAttr(e.key)}')" class="btn" style="padding:3px 8px; font-size:11.5px; background:#FFFFFF; color:#475569; border:1px solid #94A3B8;" title="還原回原始值">↩ 還原</button>
          ` : ''}
        </div>

        <!-- 右側：// 中文白話註解 -->
        <div style="flex:1; min-width:200px; font-size:12.5px; color:${e.isChanged ? '#854D0E' : '#64748B'}; font-weight:${e.isChanged ? '700' : '400'};">
          <span class="mono" style="color:#94A3B8;">//</span> ${_escAttr(e.desc)}
          ${isUsedInExcel ? `<span style="background:#E0F2FE; color:#0369A1; font-size:11px; font-weight:700; padding:1px 6px; border-radius:4px; margin-left:4px;">📌 本腳本使用中</span>` : ''}
        </div>
      </div>
    `;
  };

  const intentBtn = (id, label) => {
    const active = INI_AI_INTENT === id;
    return `<button onclick="selectIniAiIntent('${id}')" class="btn" style="padding:6px 13px; font-size:13px; border-radius:999px; ${active ? 'background:#0284C7;color:#FFFFFF;border-color:#0369A1;font-weight:800;box-shadow:0 2px 5px rgba(2,132,199,0.25);' : 'background:#FFFFFF;color:#334155;border-color:#CBD5E1;font-weight:700;'}">${label}</button>`;
  };

  // 底部 AI 白話確認報告（只要有改任何一行，AI 自動用白話文列出你改了什麼）
  let aiFooterSummaryHtml = '';
  if (allChanged.length > 0) {
    const itemsHtml = allChanged.map((e, i) => `
      <div style="margin-top:3px;">
        <b>${i + 1}.</b> ${_explainChangeByAi(e, ws)}
      </div>
    `).join('');
    aiFooterSummaryHtml = `
      <div style="background:#FEF9C3; border:1.5px solid #EAB308; border-radius:8px; padding:10px 14px; font-size:13px; color:#713F12;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:800; font-size:13.5px; color:#854D0E;">🤖 AI 為您確認本次共修改了 ${allChanged.length} 行 INI 設定（已於上方反白標示）：</span>
          <button onclick="revertAllIniChanges()" class="btn" style="padding:2px 10px; font-size:12px; background:#FFFFFF; color:#B91C1C; border:1px solid #FCA5A5; font-weight:700;">↩ 全部取消還原</button>
        </div>
        ${itemsHtml}
      </div>
    `;
  } else {
    aiFooterSummaryHtml = `
      <div style="background:#F8FAFC; border:1px dashed #CBD5E1; border-radius:8px; padding:8px 14px; font-size:12.5px; color:#64748B;">
        🤖 <b>AI 狀態：</b>目前尚未修改任何設定。您可直接在上方像記事本一樣改數值，改過的那一行會自動反白顯示「<code>原本舊值 ➔ 新值</code>」。
      </div>
    `;
  }

  return `
    <div style="display:flex; flex-direction:column; gap:10px;">
      <!-- 1. 頂部：🤖 AI 意圖快選列 + 白話文指令框 -->
      <div style="background:#F0F9FF; border:1.5px solid #7DD3FC; border-radius:8px; padding:10px 14px; display:flex; flex-direction:column; gap:8px;">
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <span style="font-weight:900; font-size:13.5px; color:#0C4A6E;">🤖 你想改什麼？點一下 AI 自動幫你篩選並推薦：</span>
            ${intentBtn('core', '🔥 常用核心設定')}
            ${intentBtn('sfis', '🌐 我想改 SFIS / iPLAS')}
            ${intentBtn('com', '🔌 我想改 COM Port')}
            ${intentBtn('ip', '🌍 我想改 IP 網段')}
            ${intentBtn('all', `📄 全部 INI (${allEntries.length} 行)`)}
          </div>
        </div>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <input id="iniAiNlInput" type="text"
            placeholder="💬 或直接打白話文告訴 AI（例如輸入：改 COM18、開 SFIS、關 SFIS、改 IP 192.168.1.50、切量產模式）..."
            onkeydown="if(event.key==='Enter') runIniNaturalLanguageCommand()"
            style="flex:1; min-width:260px; padding:6px 12px; font-size:13px; border:1.5px solid #38BDF8; border-radius:6px; background:#FFFFFF;">
          <button onclick="runIniNaturalLanguageCommand()" class="btn btn-primary-blue" style="padding:6px 14px; font-size:13px; font-weight:800;">
            🤖 AI 自動幫我改
          </button>
        </div>
        ${INI_AI_LAST_MSG ? `<div style="background:#DCFCE7; border:1px solid #4ADE80; color:#14532D; font-weight:700; font-size:12.5px; padding:6px 10px; border-radius:6px;">${_escAttr(INI_AI_LAST_MSG)}</div>` : ''}
      </div>

      <!-- 2. AI 針對當前意圖的自動推薦橫幅 -->
      ${aiRecommendationBanner}

      <!-- 3. 中間：極簡智慧記事本（一行行直接改，改過的那一行原地反白顯示「原本 ➔ 新值」） -->
      <div style="display:flex; flex-direction:column; gap:5px; max-height:380px; overflow:auto; padding:2px;">
        ${filteredEntries.map(renderNotepadLine).join('')}
      </div>

      <!-- 4. 底部：🤖 AI 白話修改確認報告 + 唯一一顆存檔並彈出 INI 大綠鈕 -->
      ${aiFooterSummaryHtml}

      <div id="iniSaveResultBanner" style="display:none; background:#DCFCE7; border:1.5px solid #22C55E; border-radius:6px; padding:10px 14px;"></div>

      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-top:4px;">
        <div style="display:flex; gap:6px; align-items:center;">
          <button onclick="addGlobalIniVar()" class="btn" style="padding:5px 11px; font-size:12px; background:#F8FAFC; color:#334155; border:1px solid #CBD5E1;">+ 新增自訂變數</button>
          <button onclick="saveAndOpenModifiedIni('global')" class="btn" style="padding:5px 11px; font-size:12px; background:#F8FAFC; color:#1E40AF; border:1px solid #93C5FD;">📄 存檔並開 Global.ini</button>
          <button onclick="saveAndOpenModifiedIni('system')" class="btn" style="padding:5px 11px; font-size:12px; background:#F8FAFC; color:#5B21B6; border:1px solid #C4B5FD;">⚙️ 存檔並開 System.ini</button>
        </div>
        <button onclick="saveAndOpenModifiedIni('auto')" class="btn btn-primary-green" style="padding:9px 24px; font-size:14.5px; font-weight:900; box-shadow:0 3px 10px rgba(22,163,74,0.3);">
          💾 存檔並直接彈出剛剛改的 INI 記事本
        </button>
      </div>
    </div>
  `;
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

function toggleGlobalEditorPanel(forceTab, forceIntent) {
  const box = document.getElementById('auditGlobalEditor');
  if (!box || !STATE.workspace) return;
  if (forceTab) {
    AUDIT_GLOBAL_TAB = forceTab;
    if (forceIntent && ['core', 'sfis', 'com', 'ip', 'all'].includes(forceIntent)) {
      INI_AI_INTENT = forceIntent;
    }
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
    bodyHtml = _renderSmartIniNotepadHtml(ws, usedVars);
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
          <span style="font-weight:700; font-size:14.5px; color:#0F172A;">⚙️ INI 智慧記事本與全域設定</span>
          ${tabBtn('ini_diff', `📄 INI 智慧記事本 <span id="iniTabDiffCountBadge">(${totalIniChanges})</span>`)}
          ${tabBtn('station_isn', `📋 Excel 站別與 ISN 條碼 (${duts.length})`)}
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
  const labelMap = { station_isn: '站別開關與 ISN', net_ip: '網路 IP / Ping / Port', inst_com: '儀器掛載與 COM Port', ini_diff: 'INI 智慧記事本' };
  STATE.pendingInserts.push({
    sheet: labelMap[AUDIT_GLOBAL_TAB] || '全域設定',
    inst: 'Excel 全域微調',
    summary: '已套用 Excel 全域微調並完成即時覆檢（請點擊底部「💾 寫入並匯出 Excel (*_FIXED.xlsx)」）'
  });
  renderGlobalEditorPanel();
  renderAuditResults();
}
