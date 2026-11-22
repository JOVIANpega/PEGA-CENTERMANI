// One-Page Checkbox & Dropdown INI Common Settings Panel (Build v0.5.9)
// Designed around real production VALO360 / ZEBRA / KANGAROO INI usage:
// - Removes AI chat complexity in favor of direct Checkboxes & Dropdowns for the 9 settings engineers actually touch.
// - Instantly highlights any modified field inline ("原本: xxx") and lists a clean "📝 本次變更確認" summary at the bottom.
// - One-click "💾 存檔並直接彈出剛剛改的 INI 記事本" with locked countdown timer overlay.

let AUDIT_GLOBAL_TAB = 'ini_diff';

const SFIS_FACTORY_PRESETS = [
  {
    id: 'PXD_DEFAULT',
    label: '🇹🇼 台灣 / PXD 通用域名 (pxd-sftsp-n3.sfis.pegatroncorp.com)',
    weblink: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx',
    site: 'DC'
  },
  {
    id: 'PTB_BATAM',
    label: '🇮🇩 巴淡廠 PTB (10.176.33.13/...,2,ErrorMapping.el)',
    weblink: 'http://10.176.33.13/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el',
    alt_weblink: 'http://10.176.33.13/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PTB'
  },
  {
    id: 'PCQ_CHONGQING',
    label: '🇨🇳 重慶廠 PCQ (172.18.125.49/...,2,ErrorMapping.el)',
    weblink: 'http://172.18.125.49/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el',
    alt_weblink: 'http://172.18.125.49/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PCQ'
  },
  {
    id: 'PSZ_SUZHOU_1',
    label: '🇨🇳 蘇州廠-1 PSZ (172.24.248.17/...,2,ErrorMapping.el)',
    weblink: 'http://172.24.248.17/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el',
    alt_weblink: 'http://172.24.248.17/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PSZ'
  },
  {
    id: 'PSZ_SUZHOU_2',
    label: '🇨🇳 蘇州廠-2 PSZ (172.24.255.113/...,2,ErrorMapping.el)',
    weblink: 'http://172.24.255.113/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el',
    alt_weblink: 'http://172.24.255.113/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PSZ'
  },
  {
    id: 'PSZ_SUZHOU_LOT5',
    label: '🇨🇳 蘇州廠 Lot5 PSZ (172.24.248.15/...,2,ErrorMapping.el)',
    weblink: 'http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el',
    alt_weblink: 'http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PSZ'
  }
];

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
  STATE.lastIsnLen = null;
  STATE.lastIsnPat = null;
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
    SFIS_WebLink: 'SFIS 廠區伺服器網址',
    iPLAS_Enable: 'iPLAS 數據上傳開關',
    iPLAS_Site: 'iPLAS 廠區代碼',
    iPLAS_ProjectName: 'iPLAS 專案名稱',
    DebugMode: '除錯模式 (1=免簽章調試, 0=正式量產)',
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
  if (/^DAQ_|^NI6008/i.test(k)) return 'NI-6008/6009 電壓卡代號';
  if (/^LED_AZ/i.test(k)) return 'FeasaLED 分析儀 COM Port';
  if (/^LED_Light/i.test(k)) return 'FeasaLED 光纖通道號';
  if (/^DUT_Login/i.test(k)) return 'SSH / Console 登入帳號';
  if (/^LOAD_/i.test(k)) return '多槽位啟用開關 (true/false)';
  if (/^DEVID_/i.test(k)) return 'SFIS 機台設備編號';
  if (/^FW_VERSION|^MFG_WIFI/i.test(k)) return '目標韌體版本號';
  if (/^sfisSKU|^Product_SKU/i.test(k)) return '機種 SKU 料號';
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
  if (k === 'SFIS_WebLink') {
    const matched = SFIS_FACTORY_PRESETS.find(p => p.weblink === nv || p.alt_weblink === nv);
    return `${_escAttr(e.desc)}：由 <code>${_escAttr(ov)}</code> ➔ 改為 <b>${matched ? matched.label : _escAttr(nv)}</b>`;
  }
  return `${_escAttr(e.desc)} (<code>${_escAttr(k)}</code>)：原本 <span style="color:#B91C1C;text-decoration:line-through;">${_escAttr(ov)}</span> ➔ 改為 <b style="color:#15803D;">${_escAttr(nv)}</b>`;
}

function _validateIniCorrectness(ws, allChanged) {
  const issues = [];
  const sys = (ws && ws.system_ini) || {};
  const gSet = (ws && ws.global_ini && ws.global_ini.Settings) || {};

  // 1. 廠區網址與 iPLAS_Site 配對檢查
  const curWebLink = String(sys.SFIS_WebLink || '').trim();
  const curSite = String(sys.iPLAS_Site || '').trim().toUpperCase();
  const matchedFactory = SFIS_FACTORY_PRESETS.find(p => p.weblink === curWebLink || p.alt_weblink === curWebLink);
  if (matchedFactory && matchedFactory.site !== curSite) {
    issues.push({
      level: 'warn',
      msg: `廠區代號提醒：SFIS 網址已選為 <b>${matchedFactory.label}</b>，建議將 <code>iPLAS_Site</code> 同步設為 <code>${matchedFactory.site}</code>（目前為 <code>${_escAttr(curSite)}</code>）。`,
      fixJs: `setSystemIniValueLive('iPLAS_Site', '${matchedFactory.site}', true)`,
      fixLabel: `🔧 同步設為 ${matchedFactory.site}`
    });
  }

  // 2. 改了 SFIS 網址但 SFIS_Enable 為 0
  const sfisUrlChanged = allChanged.some(e => e.key === 'SFIS_WebLink' || e.key === 'SFIS_TSP');
  if (sfisUrlChanged && String(sys.SFIS_Enable).trim() === '0') {
    issues.push({
      level: 'warn',
      msg: `您修改了 SFIS 廠區網址或站別碼，但 <code>SFIS_Enable</code> 目前未打勾（關閉中），若要正式過站請勾選開啟。`,
      fixJs: `setSystemIniValueLive('SFIS_Enable', '1', true)`,
      fixLabel: `🔧 勾選開啟 SFIS_Enable`
    });
  }

  // 3. 待測物與電腦網卡 IP 網段檢查
  const dutIp = String(gSet.DUTIP_1 || '').trim();
  const pcIp = String(gSet.PCIP_1 || '').trim();
  const mDut = dutIp.match(/^(\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,3})$/);
  const mPc = pcIp.match(/^(\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,3})$/);
  if (mDut && mPc && mDut[1] !== mPc[1]) {
    const fixHost = mDut[2] === '100' ? '101' : '100';
    issues.push({
      level: 'warn',
      msg: `網段不同提醒：待測物 <code>DUTIP_1 (${_escAttr(dutIp)})</code> 與電腦 <code>PCIP_1 (${_escAttr(pcIp)})</code> 前三碼不同網段。`,
      fixJs: `setGlobalIniValueLive('Settings', 'PCIP_1', '${mDut[1]}.${fixHost}', true)`,
      fixLabel: `🔧 同步電腦 IP 為 ${mDut[1]}.${fixHost}`
    });
  }
  return issues;
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

function applySfisFactoryPreset(presetId) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  const p = SFIS_FACTORY_PRESETS.find(x => x.id === presetId);
  if (!p) return;
  const sys = STATE.workspace.system_ini;
  sys.SFIS_WebLink = p.weblink;
  sys.iPLAS_Site = p.site;
  _recordPendingIniNotice(`切換廠區為 ${p.label}`);
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
  } else if (presetType === 'eng_offline') {
    sys.SFIS_Enable = '0';
    sys.SFIS_LinkIPLAS = '0';
    sys.iPLAS_Enable = '0';
    sys.DebugMode = '1';
  } else if (presetType === 'sync_pc_ip') {
    const dutIp = String(gSet.DUTIP_1 || '').trim();
    const m = dutIp.match(/^(\d+\.\d+\.\d+)\.(\d+)$/);
    if (m) {
      gSet.PCIP_1 = `${m[1]}.${m[2] === '100' ? '101' : '100'}`;
    }
  }
  _recordPendingIniNotice('套用模式快捷設定');
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
  renderGlobalEditorPanel();
}

// Keep compatibility functions for automated verification suite
function _renderIniStage1EditHtml(ws, usedVars) {
  return _renderOnePageIniPanelHtml(ws, usedVars);
}
function _renderIniStage2ReviewHtml(ws) {
  const { usedVars } = _collectUsedVarsAndInstruments(ws);
  return _renderOnePageIniPanelHtml(ws, usedVars);
}

function _renderOnePageIniPanelHtml(ws, usedVars) {
  const sys = ws.system_ini || {};
  const gSet = (ws.global_ini && ws.global_ini.Settings) || {};
  const gScr = (ws.global_ini && ws.global_ini.Scripts) || {};
  const origSys = STATE.origSystemIni || {};
  const origSet = (STATE.origGlobalIni && STATE.origGlobalIni.Settings) || {};
  const origScr = (STATE.origGlobalIni && STATE.origGlobalIni.Scripts) || {};

  const gEntries = _collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini');
  const sEntries = _collectIniDiffEntries(STATE.origSystemIni, ws.system_ini, 'System.ini');
  const allChanged = [...sEntries, ...gEntries].filter(e => e.isChanged);
  const validationIssues = _validateIniCorrectness(ws, allChanged);

  // Helper 1: System.ini Checkbox 卡片
  const mkSysCheckbox = (key, title, subHint, onVal = '1', offVal = '0') => {
    const cur = String(sys[key] !== undefined ? sys[key] : offVal).trim();
    const orig = String(origSys[key] !== undefined ? origSys[key] : cur).trim();
    const checked = (cur === onVal);
    const isMod = (cur !== orig);
    return `
      <label style="cursor:pointer; display:flex; align-items:flex-start; gap:8px; padding:8px 11px; border-radius:7px; border:1.5px solid ${isMod ? '#EAB308' : (checked ? '#86EFAC' : '#CBD5E1')}; background:${isMod ? '#FEF9C3' : (checked ? '#F0FDF4' : '#F8FAFC')}; user-select:none;">
        <input type="checkbox" ${checked ? 'checked' : ''}
          onchange="setSystemIniValueLive('${key}', this.checked ? '${onVal}' : '${offVal}', true)"
          style="width:17px; height:17px; margin-top:2px; cursor:pointer; accent-color:#16A34A;">
        <div style="flex:1; min-width:0;">
          <div style="font-weight:800; font-size:13px; color:#0F172A; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <span>${title}</span>
            <span class="mono" style="font-size:11.5px; color:${checked ? '#15803D' : '#64748B'};">(${key}=${cur})</span>
            ${isMod ? `<span style="background:#FEF08A; color:#854D0E; border:1px solid #FACC15; font-size:11px; padding:0 5px; border-radius:4px;">原本: ${_escAttr(orig)}</span>` : ''}
          </div>
          <div style="font-size:11.5px; color:#475569; margin-top:2px;">${subHint}</div>
        </div>
      </label>
    `;
  };

  // Helper 2: Global.ini 槽位 LOAD_1..4 Checkbox
  const mkLoadSlotCheckbox = (slotIdx) => {
    const key = `LOAD_${slotIdx}`;
    const cur = String(gSet[key] !== undefined ? gSet[key] : (slotIdx === 1 ? 'true' : 'false')).trim().toLowerCase();
    const orig = String(origSet[key] !== undefined ? origSet[key] : cur).trim().toLowerCase();
    const checked = (cur === 'true' || cur === '1');
    const isMod = (cur !== orig);
    return `
      <label style="cursor:pointer; display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:6px; border:1.5px solid ${isMod ? '#EAB308' : (checked ? '#60A5FA' : '#CBD5E1')}; background:${isMod ? '#FEF9C3' : (checked ? '#EFF6FF' : '#F8FAFC')}; font-weight:800; font-size:12.5px; color:#0F172A; user-select:none;">
        <input type="checkbox" ${checked ? 'checked' : ''}
          onchange="setGlobalIniValueLive('Settings', '${key}', this.checked ? 'true' : 'false', true)"
          style="width:16px; height:16px; cursor:pointer; accent-color:#2563EB;">
        <span>${slotIdx} 號槽 (${key}=${checked ? 'true' : 'false'})</span>
        ${isMod ? `<span style="background:#FEF08A; color:#854D0E; font-size:10.5px; padding:0 4px; border-radius:3px;">原本:${orig}</span>` : ''}
      </label>
    `;
  };

  // Helper 3: COM Port 下拉選單 (COM1 ~ COM30 + 自訂)
  const mkComSelectField = (key, label) => {
    // 支援 PCUART_fixture 或 PCUART_fixture_1 自動對應既有 key
    let actualKey = key;
    if (key === 'PCUART_fixture_1' && gSet['PCUART_fixture'] !== undefined && gSet['PCUART_fixture_1'] === undefined) {
      actualKey = 'PCUART_fixture';
    }
    const cur = String(gSet[actualKey] !== undefined ? gSet[actualKey] : 'COM1').trim();
    const orig = String(origSet[actualKey] !== undefined ? origSet[actualKey] : cur).trim();
    const isMod = (cur !== orig);
    const comList = [];
    for (let c = 1; c <= 30; c++) comList.push(`COM${c}`);
    if (cur && !comList.includes(cur.toUpperCase())) comList.unshift(cur);

    const opts = comList.map(c => `<option value="${_escAttr(c)}" ${c.toUpperCase() === cur.toUpperCase() ? 'selected' : ''}>${_escAttr(c)}</option>`).join('');
    return `
      <div style="background:${isMod ? '#FEF9C3' : '#F8FAFC'}; border:1.5px solid ${isMod ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:7px 10px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <div>
          <div style="font-weight:800; font-size:12.5px; color:#0F172A;">
            ${label}
            ${isMod ? `<span style="background:#FEE2E2; color:#B91C1C; font-size:11px; padding:1px 5px; border-radius:4px; text-decoration:line-through; margin-left:4px;">原本: ${_escAttr(orig)}</span>` : ''}
          </div>
          <div class="mono" style="font-size:11px; color:#1E40AF;">[Settings] ${actualKey}</div>
        </div>
        <select onchange="setGlobalIniValueLive('Settings', '${actualKey}', this.value, true)" class="mono"
          style="width:110px; padding:5px 8px; font-size:13px; font-weight:800; border-radius:5px; border:1.5px solid ${isMod ? '#16A34A' : '#94A3B8'}; background:${isMod ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A; cursor:pointer;">
          ${opts}
        </select>
      </div>
    `;
  };

  // Helper 4: DAQ Dev1~Dev4 下拉選單
  const mkDaqSelectField = (key, label) => {
    const cur = String(gSet[key] !== undefined ? gSet[key] : 'Dev1').trim();
    const orig = String(origSet[key] !== undefined ? origSet[key] : cur).trim();
    const isMod = (cur !== orig);
    const devs = ['Dev1', 'Dev2', 'Dev3', 'Dev4'];
    if (cur && !devs.includes(cur)) devs.unshift(cur);
    const opts = devs.map(d => `<option value="${_escAttr(d)}" ${d === cur ? 'selected' : ''}>${_escAttr(d)}</option>`).join('');
    return `
      <div style="background:${isMod ? '#FEF9C3' : '#F8FAFC'}; border:1.5px solid ${isMod ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:7px 10px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <div>
          <div style="font-weight:800; font-size:12.5px; color:#0F172A;">
            ${label}
            ${isMod ? `<span style="background:#FEE2E2; color:#B91C1C; font-size:11px; padding:1px 5px; border-radius:4px; text-decoration:line-through; margin-left:4px;">原本: ${_escAttr(orig)}</span>` : ''}
          </div>
          <div class="mono" style="font-size:11px; color:#1E40AF;">[Settings] ${key}</div>
        </div>
        <select onchange="setGlobalIniValueLive('Settings', '${key}', this.value, true)" class="mono"
          style="width:110px; padding:5px 8px; font-size:13px; font-weight:800; border-radius:5px; border:1.5px solid ${isMod ? '#16A34A' : '#94A3B8'}; background:${isMod ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A; cursor:pointer;">
          ${opts}
        </select>
      </div>
    `;
  };

  // Helper 5: 一般文字輸入欄位 (IP / 機台號 / 版號)
  const mkTextField = (file, sec, key, label, widthPx = 155) => {
    const curObj = file === 'System.ini' ? sys : (sec === 'Scripts' ? gScr : gSet);
    const origObj = file === 'System.ini' ? origSys : (sec === 'Scripts' ? origScr : origSet);
    const cur = String(curObj[key] !== undefined ? curObj[key] : '').trim();
    const orig = String(origObj[key] !== undefined ? origObj[key] : cur).trim();
    const isMod = (cur !== orig);
    const onChangeJs = file === 'System.ini'
      ? `setSystemIniValueLive('${_escAttr(key)}', this.value, true)`
      : `setGlobalIniValueLive('${_escAttr(sec)}', '${_escAttr(key)}', this.value, true)`;

    return `
      <div style="background:${isMod ? '#FEF9C3' : '#F8FAFC'}; border:1.5px solid ${isMod ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:7px 10px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <div style="min-width:0; flex:1;">
          <div style="font-weight:800; font-size:12.5px; color:#0F172A; display:flex; align-items:center; gap:5px; flex-wrap:wrap;">
            <span>${label}</span>
            ${isMod ? `<span style="background:#FEE2E2; color:#B91C1C; font-size:11px; padding:0 5px; border-radius:4px; text-decoration:line-through;">原本: ${_escAttr(orig)}</span>` : ''}
          </div>
          <div class="mono" style="font-size:11px; color:${file === 'System.ini' ? '#5B21B6' : '#1E40AF'};">[${sec}] ${key}</div>
        </div>
        <input value="${_escAttr(cur)}" onchange="${onChangeJs}" class="mono"
          style="width:${widthPx}px; padding:5px 8px; font-size:13px; font-weight:${isMod ? '800' : '600'}; border-radius:5px; border:1.5px solid ${isMod ? '#16A34A' : '#94A3B8'}; background:${isMod ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A;">
      </div>
    `;
  };

  // System.ini 廠區下拉選單 + RetryCount 下拉選單
  const curWebLink = String(sys.SFIS_WebLink || '').trim();
  const origWebLink = String(origSys.SFIS_WebLink !== undefined ? origSys.SFIS_WebLink : curWebLink).trim();
  const webLinkMod = (curWebLink !== origWebLink);
  const matchedFactory = SFIS_FACTORY_PRESETS.find(fp => fp.weblink === curWebLink || fp.alt_weblink === curWebLink);

  const curRetry = String(sys.RetryCount !== undefined ? sys.RetryCount : '3').trim();
  const origRetry = String(origSys.RetryCount !== undefined ? origSys.RetryCount : curRetry).trim();
  const retryMod = (curRetry !== origRetry);

  const curSite = String(sys.iPLAS_Site !== undefined ? sys.iPLAS_Site : 'DC').trim();
  const origSite = String(origSys.iPLAS_Site !== undefined ? origSys.iPLAS_Site : curSite).trim();
  const siteMod = (curSite !== origSite);
  const siteOptions = ['DC', 'PTB', 'PSZ', 'PCQ', 'PVN', 'PMX'];
  if (curSite && !siteOptions.includes(curSite)) siteOptions.unshift(curSite);

  // 找出 [Scripts] 中常用會改的版號/SKU欄位 (FW_VERSION, MFG_WIFI_MB, sfisSKU, Product_SKU, Boot_Delay)
  const scriptCoreKeys = Object.keys(gScr).filter(k =>
    usedVars.has(k) || /^(FW_VERSION|MFG_WIFI|sfisSKU|Product_SKU|Boot_Delay)/i.test(k)
  ).slice(0, 6);

  // 其餘少用的 Global.ini 參數收合在底部
  const shownSettingsKeys = new Set([
    'LOAD_1', 'LOAD_2', 'LOAD_3', 'LOAD_4',
    'DUT_UR1', 'PCUART_fixture', 'PCUART_fixture_1', 'LED_AZ1', 'DAQ_1',
    'PCIP_1', 'DUTIP_1', 'DEVID_1', 'DUT_Login'
  ]);
  const extraEntries = gEntries.filter(e =>
    !(e.section === 'Settings' && shownSettingsKeys.has(e.key)) &&
    !(e.section === 'Scripts' && scriptCoreKeys.includes(e.key))
  );

  // 📝 底部「本次變更確認清單」（只有被動到的項目才列出來！）
  let changeSummaryHtml = '';
  if (allChanged.length > 0) {
    const listHtml = allChanged.map((e, idx) => `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; padding:5px 10px; background:#FFFFFF; border:1px solid #FDE047; border-radius:5px;">
        <div style="font-size:12.5px; color:#0F172A;">
          <b style="color:#854D0E;">#${idx + 1} [${_escAttr(e.file)}]</b> ${_explainChangeByAi(e, ws)}
        </div>
        <button onclick="revertSingleIniKey('${_escAttr(e.file)}','${_escAttr(e.section)}','${_escAttr(e.key)}')" class="btn" style="padding:2px 8px; font-size:11.5px; background:#F8FAFC; color:#B91C1C; border:1px solid #FCA5A5; font-weight:700;">↩ 還原此項</button>
      </div>
    `).join('');

    const issueHtml = validationIssues.map(iss => `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; padding:6px 10px; background:#FFFBEB; border:1.5px solid #F59E0B; border-radius:6px; margin-top:4px;">
        <span style="font-size:12.5px; color:#92400E; font-weight:700;">⚠️ ${iss.msg}</span>
        ${iss.fixJs ? `<button onclick="${iss.fixJs}" class="btn" style="padding:3px 10px; font-size:12px; background:#16A34A; color:#FFF; border:none; font-weight:800;">${iss.fixLabel}</button>` : ''}
      </div>
    `).join('');

    changeSummaryHtml = `
      <div style="background:#FEF9C3; border:2px solid #EAB308; border-radius:8px; padding:10px 14px; display:flex; flex-direction:column; gap:6px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <span style="font-weight:900; font-size:13.5px; color:#713F12;">📝 本次已修改項目確認（共 ${allChanged.length} 處變更，確認無誤請點右下角存檔彈出 INI）：</span>
          <button onclick="revertAllIniChanges()" class="btn" style="padding:3px 10px; font-size:12px; background:#FFFFFF; color:#B91C1C; border:1px solid #FCA5A5; font-weight:800;">↩ 全部取消還原</button>
        </div>
        ${listHtml}
        ${issueHtml}
      </div>
    `;
  } else {
    changeSummaryHtml = `
      <div style="background:#F8FAFC; border:1px dashed #CBD5E1; border-radius:8px; padding:8px 14px; font-size:12.5px; color:#64748B;">
        📝 <b>本次變更確認：</b>目前尚未修改任何設定（0 項變更）。直接在上方打勾或下拉選取後，有變動的項目會自動列在此處供您最後確認。
      </div>
    `;
  }

  return `
    <div style="display:flex; flex-direction:column; gap:12px;">
      <!-- ==================== 區塊 1：System.ini 過站與廠區設定 ==================== -->
      <div style="border:1.5px solid #C4B5FD; border-radius:8px; background:#FFFFFF; overflow:hidden;">
        <div style="background:#F5F3FF; padding:8px 14px; border-bottom:1px solid #C4B5FD; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <span style="font-weight:900; font-size:13.5px; color:#4C1D95;">
            🌐 1. System.ini 過站開關與出廠廠區設定（打勾或下拉選好即可，設一次即固定）
          </span>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button onclick="applyAiPresetBundle('eng_offline')" class="btn" style="padding:3px 10px; font-size:12px; background:#FFFFFF; color:#4C1D95; border:1px solid #A78BFA; font-weight:700;">🛠️ 一鍵設為：工程離線調試 (Debug=1, SFIS關)</button>
            <button onclick="applyAiPresetBundle('mp_sfis_on')" class="btn" style="padding:3px 10px; font-size:12px; background:#6D28D9; color:#FFFFFF; border:none; font-weight:700;">🏭 一鍵設為：正式量產過站 (Debug=0, SFIS開)</button>
          </div>
        </div>

        <div style="padding:10px 14px; display:flex; flex-direction:column; gap:10px;">
          <!-- 4 個核心 Checkbox -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:8px;">
            ${mkSysCheckbox('DebugMode', '工程除錯模式 (DebugMode)', '勾選=1 (免驗 Checksum)；取消=0 (量產驗簽章)')}
            ${mkSysCheckbox('SFIS_Enable', 'SFIS 產線過站 (SFIS_Enable)', '勾選=1 (開啟 SFIS 路由檢查與過站)')}
            ${mkSysCheckbox('iPLAS_Enable', 'iPLAS 數據上傳 (iPLAS_Enable)', '勾選=1 (測試後自動打包上傳 Log)')}
            ${mkSysCheckbox('SFIS_LinkIPLAS', 'SFIS 連動 iPLAS (SFIS_LinkIPLAS)', '勾選=1 (SFIS 過站時同步連動 iPLAS)')}
          </div>

          <!-- 廠區 SFIS_WebLink 下拉選單 (真實 System.ini 5 大廠區網址) -->
          <div style="background:${webLinkMod ? '#FEF9C3' : '#F8FAFC'}; border:1.5px solid ${webLinkMod ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:8px 12px; display:flex; flex-direction:column; gap:6px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
              <div style="font-weight:800; font-size:12.5px; color:#0F172A;">
                🏭 出廠廠區伺服器網址 (<span class="mono" style="color:#5B21B6;">[SFIS] SFIS_WebLink</span>)
                ${webLinkMod ? `<span style="background:#FEE2E2; color:#B91C1C; font-size:11px; padding:1px 6px; border-radius:4px; text-decoration:line-through; margin-left:6px;">原本: ${_escAttr(origWebLink)}</span>` : ''}
              </div>
              <span style="font-size:11.5px; color:#64748B;">選擇廠區後會自動帶入該廠標準網址並同步切換 iPLAS_Site</span>
            </div>
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
              <select onchange="if(this.value) applySfisFactoryPreset(this.value)" style="padding:6px 10px; font-size:13px; font-weight:800; border-radius:5px; border:1.5px solid #6D28D9; background:#F5F3FF; color:#4C1D95; cursor:pointer; min-width:310px;">
                <option value="" ${!matchedFactory ? 'selected' : ''}>✏️ 自訂廠區網址...</option>
                ${SFIS_FACTORY_PRESETS.map(fp => `<option value="${fp.id}" ${(matchedFactory && matchedFactory.id === fp.id) ? 'selected' : ''}>${_escAttr(fp.label)}</option>`).join('')}
              </select>
              <input value="${_escAttr(curWebLink)}" onchange="setSystemIniValueLive('SFIS_WebLink', this.value, true)" class="mono"
                style="flex:1; min-width:260px; padding:6px 10px; font-size:12.5px; font-weight:${webLinkMod ? '800' : '500'}; border-radius:5px; border:1.5px solid ${webLinkMod ? '#16A34A' : '#94A3B8'}; background:${webLinkMod ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A;">
            </div>
          </div>

          <!-- 站別路由碼、專案名、廠區代號、重測次數 -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:8px;">
            ${mkTextField('System.ini', 'SFIS', 'SFIS_TSP', 'SFIS 站別路由碼', 110)}
            ${mkTextField('System.ini', 'iPLAS', 'iPLAS_ProjectName', '專案名稱 (Project)', 120)}
            <div style="background:${siteMod ? '#FEF9C3' : '#F8FAFC'}; border:1.5px solid ${siteMod ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:7px 10px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
              <div>
                <div style="font-weight:800; font-size:12.5px; color:#0F172A;">iPLAS 廠區代碼 ${siteMod ? `<span style="background:#FEE2E2;color:#B91C1C;font-size:11px;padding:0 4px;border-radius:3px;text-decoration:line-through;">原本:${_escAttr(origSite)}</span>` : ''}</div>
                <div class="mono" style="font-size:11px; color:#5B21B6;">[iPLAS] iPLAS_Site</div>
              </div>
              <select onchange="setSystemIniValueLive('iPLAS_Site', this.value, true)" class="mono"
                style="width:95px; padding:5px 8px; font-size:13px; font-weight:800; border-radius:5px; border:1.5px solid ${siteMod ? '#16A34A' : '#94A3B8'}; background:${siteMod ? '#DCFCE7' : '#FFFFFF'}; cursor:pointer;">
                ${siteOptions.map(s => `<option value="${_escAttr(s)}" ${s === curSite ? 'selected' : ''}>${_escAttr(s)}</option>`).join('')}
              </select>
            </div>
            <div style="background:${retryMod ? '#FEF9C3' : '#F8FAFC'}; border:1.5px solid ${retryMod ? '#EAB308' : '#CBD5E1'}; border-radius:7px; padding:7px 10px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
              <div>
                <div style="font-weight:800; font-size:12.5px; color:#0F172A;">失敗重測次數 ${retryMod ? `<span style="background:#FEE2E2;color:#B91C1C;font-size:11px;padding:0 4px;border-radius:3px;text-decoration:line-through;">原本:${_escAttr(origRetry)}</span>` : ''}</div>
                <div class="mono" style="font-size:11px; color:#5B21B6;">[System] RetryCount</div>
              </div>
              <select onchange="setSystemIniValueLive('RetryCount', this.value, true)" class="mono"
                style="width:95px; padding:5px 8px; font-size:13px; font-weight:800; border-radius:5px; border:1.5px solid ${retryMod ? '#16A34A' : '#94A3B8'}; background:${retryMod ? '#DCFCE7' : '#FFFFFF'}; cursor:pointer;">
                ${['0', '1', '2', '3', '4', '5'].map(r => `<option value="${r}" ${r === curRetry ? 'selected' : ''}>${r} 次</option>`).join('')}
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 區塊 2：Global.ini 治具通訊、槽位與版號設定 ==================== -->
      <div style="border:1.5px solid #93C5FD; border-radius:8px; background:#FFFFFF; overflow:hidden;">
        <div style="background:#EFF6FF; padding:8px 14px; border-bottom:1px solid #93C5FD; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <span style="font-weight:900; font-size:13.5px; color:#1E3A8A;">
            🔌 2. Global.ini 治具 COM Port、網卡 IP、槽位開關與韌體版號（架站或韌體進版時改一次）
          </span>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button onclick="applyAiPresetBundle('sync_pc_ip')" class="btn" style="padding:3px 10px; font-size:12px; background:#FFFFFF; color:#1E40AF; border:1px solid #60A5FA; font-weight:700;">🔗 同步電腦 PCIP_1 與待測物同網段</button>
            <button onclick="openCommModal()" class="btn" style="padding:3px 10px; font-size:12px; background:#FFFFFF; color:#0369A1; border:1px solid #38BDF8; font-weight:700;">🔄 測站 UART@ 批次轉 SSH@</button>
          </div>
        </div>

        <div style="padding:10px 14px; display:flex; flex-direction:column; gap:10px;">
          <!-- 一拖四槽位開關 LOAD_1 ~ LOAD_4 Checkboxes -->
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span style="font-weight:800; font-size:12.5px; color:#334155;">🗂️ 測試槽位啟用開關：</span>
            ${mkLoadSlotCheckbox(1)}
            ${mkLoadSlotCheckbox(2)}
            ${mkLoadSlotCheckbox(3)}
            ${mkLoadSlotCheckbox(4)}
          </div>

          <!-- COM Port 與 DAQ 下拉選單 -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:8px;">
            ${mkComSelectField('DUT_UR1', '待測物序列埠 (DUT)')}
            ${mkComSelectField('PCUART_fixture_1', '氣動治具控制埠')}
            ${mkComSelectField('LED_AZ1', 'FeasaLED 分析儀埠')}
            ${mkDaqSelectField('DAQ_1', 'NI-6008/6009 電壓卡')}
          </div>

          <!-- 網路 IP、機台號與 [Scripts] 常用版號 -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:8px;">
            ${mkTextField('Global.ini', 'Settings', 'DUTIP_1', '待測物連線 IP', 135)}
            ${mkTextField('Global.ini', 'Settings', 'PCIP_1', '電腦端網卡 IP', 135)}
            ${mkTextField('Global.ini', 'Settings', 'DEVID_1', 'SFIS 機台編號', 120)}
            ${scriptCoreKeys.map(k => mkTextField('Global.ini', 'Scripts', k, _describeGlobalVar(k), 145)).join('')}
          </div>

          <!-- 其餘少用的 INI 參數收合匣 -->
          ${extraEntries.length > 0 ? `
            <details style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:6px 10px;">
              <summary style="cursor:pointer; font-weight:700; font-size:12px; color:#64748B;">
                📦 展開檢視 / 微調其餘少用的 Global.ini 參數（共 ${extraEntries.length} 項，平時無須更動）
              </summary>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:8px; margin-top:8px;">
                ${extraEntries.map(e => mkTextField('Global.ini', e.section, e.key, e.desc, 130)).join('')}
              </div>
            </details>
          ` : ''}
        </div>
      </div>

      <!-- ==================== 區塊 3：本次變更確認與存檔彈出 INI ==================== -->
      ${changeSummaryHtml}

      <div id="iniSaveResultBanner" style="display:none; background:#DCFCE7; border:1.5px solid #22C55E; border-radius:6px; padding:10px 14px;"></div>

      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
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

  const runSaveIni = async () => {
    const res = await fetch('/api/save_and_open_ini', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: STATE.selectedPath || '',
        workspace: STATE.workspace,
        open_target: openTarget
      })
    });
    return await res.json();
  };

  const data = (typeof withLoadingTimer === 'function')
    ? await withLoadingTimer(
        '正在寫入 INI 設定檔並喚醒開啟記事本視窗',
        runSaveIni,
        1100,
        '正在同步更新 Global.ini 與 System.ini 並將記事本 (Notepad) 拉至桌面最上層...'
      )
    : await runSaveIni();

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

function toggleGlobalEditorPanel(forceTab) {
  const box = document.getElementById('auditGlobalEditor');
  if (!box || !STATE.workspace) return;
  if (forceTab) {
    AUDIT_GLOBAL_TAB = forceTab;
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
  const defLen = (STATE && STATE.lastIsnLen) ? String(STATE.lastIsnLen) : '15';
  const defPat = (STATE && STATE.lastIsnPat) ? String(STATE.lastIsnPat) : '[0-9]';
  if (!s) return { simple: true, name: 'ISN', len: defLen, pat: defPat };
  if (s.includes(';')) return { simple: false, raw: s };
  const m = s.match(/^\{\s*([^,]+)\s*,\s*(\d+)\s*,\s*([^}]+?)\s*\}$/);
  if (!m) return { simple: false, raw: s };
  return { simple: true, name: m[1].trim(), len: m[2].trim(), pat: m[3].trim() };
}

function _updateScanBarcodeField(dutIdx, scanKey, field, val, rerender = false) {
  const d = STATE.workspace.duts[dutIdx];
  if (!d) return;
  const parsed = _parseScanBarcode(d[scanKey]);
  if (!parsed.simple) return;
  parsed[field] = String(val).trim();
  d[scanKey] = `{ ${parsed.name},${parsed.len},${parsed.pat} }`;
  if (field === 'len') {
    STATE.lastIsnLen = parsed.len;
    const topLenEl = document.getElementById('geIsnLen');
    if (topLenEl && topLenEl.value !== parsed.len) topLenEl.value = parsed.len;
  } else if (field === 'pat') {
    STATE.lastIsnPat = parsed.pat;
    const topPatEl = document.getElementById('geIsnPat');
    if (topPatEl && topPatEl.value !== parsed.pat) topPatEl.value = parsed.pat;
  }
  _recordPendingIniNotice(`Excel DUTs 條碼規則已改為: ${d[scanKey]}`);
  if (rerender) renderGlobalEditorPanel();
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
    bodyHtml = _renderOnePageIniPanelHtml(ws, usedVars);
  } else if (AUDIT_GLOBAL_TAB === 'station_isn') {
    let topIsnLen = STATE.lastIsnLen || '15';
    let topIsnPat = STATE.lastIsnPat || '[0-9]';
    if (duts.length > 0) {
      const k0 = _findKeyByPrefix(duts[0], 'ScanBarcode', 'ScanBarcode( {Name,Lengh,Pattern} )');
      const sb0 = _parseScanBarcode(duts[0][k0]);
      if (sb0.simple) {
        topIsnLen = sb0.len;
        topIsnPat = sb0.pat;
        STATE.lastIsnLen = topIsnLen;
        STATE.lastIsnPat = topIsnPat;
      }
    }

    const rowsHtml = duts.map((d, i) => {
      const scanKey = _findKeyByPrefix(d, 'ScanBarcode', 'ScanBarcode( {Name,Lengh,Pattern} )');
      const loadVal = String(d['Load'] || '').trim();
      const isEnabled = loadVal !== '' && loadVal.toLowerCase() !== 'false' && loadVal !== '0';
      const sb = _parseScanBarcode(d[scanKey]);
      if (!String(d[scanKey] || '').trim() && sb.simple) {
        d[scanKey] = `{ ${sb.name},${sb.len},${sb.pat} }`;
      }
      const patPresets = ['[0-9]', '[0-9A-Z]', '[0-9A-Za-z]'];
      const sbHtml = sb.simple ? `
        <div style="display:flex; gap:5px; align-items:center; flex-wrap:wrap;">
          <input value="${_escAttr(sb.name)}" oninput="_updateScanBarcodeField(${i},'${_escAttr(scanKey)}','name',this.value,false)" onchange="_updateScanBarcodeField(${i},'${_escAttr(scanKey)}','name',this.value,true)" class="mono" style="width:58px;padding:4px;font-size:12px;" title="條碼名稱">
          <input type="number" min="1" max="64" value="${_escAttr(sb.len)}" oninput="_updateScanBarcodeField(${i},'${_escAttr(scanKey)}','len',this.value,false)" onchange="_updateScanBarcodeField(${i},'${_escAttr(scanKey)}','len',this.value,true)" class="mono" style="width:56px;padding:4px;font-size:12.5px;font-weight:800;color:#1E3A8A;background:#FEF9C3;border:1.5px solid #EAB308;border-radius:4px;" title="直接輸入條碼位數即刻生效"> 碼
          <select onchange="if(this.value!=='__CUSTOM__'){_updateScanBarcodeField(${i},'${_escAttr(scanKey)}','pat',this.value,true);}" class="mono" style="padding:4px;font-size:12px;">
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
          <span style="font-weight:700; color:#1E3A8A;">🔢 快速批量設定 ISN 條碼（目前為 <span style="color:#DC2626;font-size:14px;">${_escAttr(topIsnLen)}</span> 碼）：</span>
          <label>位數 <input id="geIsnLen" type="number" min="1" max="64" value="${_escAttr(topIsnLen)}" oninput="batchApplyDutIsn(false)" onchange="batchApplyDutIsn(true)" class="mono" style="width:58px;padding:3px 6px;font-weight:800;color:#1E3A8A;"></label>
          <label>規則 <select id="geIsnPat" onchange="batchApplyDutIsn(true)" class="mono" style="padding:3px 5px;">
            <option value="[0-9]" ${topIsnPat==='[0-9]'?'selected':''}>[0-9]（純數字）</option>
            <option value="[0-9A-Z]" ${topIsnPat==='[0-9A-Z]'?'selected':''}>[0-9A-Z]（大寫英數字）</option>
            <option value="[0-9A-Za-z]" ${topIsnPat==='[0-9A-Za-z]'?'selected':''}>[0-9A-Za-z]（大小寫英數字）</option>
          </select></label>
          <button onclick="batchApplyDutIsn(true)" class="btn btn-primary-blue" style="padding:3px 10px; font-size:12px;">套用至所有站別</button>
          <button onclick="setQuickDutIsn(3, '[0-9A-Z]')" class="btn" style="padding:3px 9px; font-size:11.5px; background:#FEF9C3; color:#854D0E; border:1px solid #EAB308; font-weight:800;">⚡ 一鍵設 3 碼 (調試)</button>
          <button onclick="setQuickDutIsn(15, '[0-9A-Z]')" class="btn" style="padding:3px 9px; font-size:11.5px; background:#FFFFFF; color:#334155; border:1px solid #CBD5E1; font-weight:700;">⚡ 一鍵設 15 碼 (量產)</button>
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
          <span style="font-weight:700; font-size:14.5px; color:#0F172A;">⚙️ INI 常用設定面板與 Excel 全域微調</span>
          ${tabBtn('ini_diff', `🎛️ INI 常用設定 (打勾/下拉) <span id="iniTabDiffCountBadge">(${totalIniChanges})</span>`)}
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

function setQuickDutIsn(len, pat) {
  STATE.lastIsnLen = String(len);
  STATE.lastIsnPat = String(pat || '[0-9A-Z]');
  const rule = `{ ISN,${STATE.lastIsnLen},${STATE.lastIsnPat} }`;
  (STATE.workspace.duts || []).forEach(d => {
    const scanKey = _findKeyByPrefix(d, 'ScanBarcode', 'ScanBarcode( {Name,Lengh,Pattern} )');
    d[scanKey] = rule;
  });
  _recordPendingIniNotice(`已將所有站別 ISN 條碼設為 ${STATE.lastIsnLen} 碼 (${rule})`);
  renderGlobalEditorPanel();
}

function batchApplyDutIsn(rerender = true) {
  const lenEl = document.getElementById('geIsnLen');
  const patEl = document.getElementById('geIsnPat');
  const rawLen = lenEl ? lenEl.value.trim() : '';
  if (!rawLen) return;
  const len = Math.max(1, parseInt(rawLen, 10) || 15);
  const pat = (patEl && patEl.value) || STATE.lastIsnPat || '[0-9]';
  STATE.lastIsnLen = String(len);
  STATE.lastIsnPat = pat;
  const rule = `{ ISN,${len},${pat} }`;
  (STATE.workspace.duts || []).forEach(d => {
    const scanKey = _findKeyByPrefix(d, 'ScanBarcode', 'ScanBarcode( {Name,Lengh,Pattern} )');
    d[scanKey] = rule;
  });
  _recordPendingIniNotice(`已將所有站別 ISN 條碼設為 ${len} 碼 (${rule})`);
  if (rerender) renderGlobalEditorPanel();
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
  if (AUDIT_GLOBAL_TAB === 'station_isn') {
    batchApplyDutIsn(false);
  }
  const runReaudit = async () => {
    const res = await fetch('/api/re_audit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ workspace: STATE.workspace })
    });
    return await res.json();
  };
  const data = (typeof withLoadingTimer === 'function')
    ? await withLoadingTimer('正在套用 Excel 站別 / ISN 條碼設定並重新體檢', runReaudit, 700)
    : await runReaudit();
  if (data.status !== 'ok') {
    alert(data.message || '覆檢失敗');
    return;
  }
  STATE.report = data.report;
  if (data.isn_info) STATE.isnInfo = data.isn_info;
  STATE.pendingInserts = STATE.pendingInserts || [];
  const labelMap = { station_isn: '站別開關與 ISN', net_ip: '網路 IP / Ping / Port', inst_com: '儀器掛載與 COM Port', ini_diff: 'INI 常用設定面板' };
  STATE.pendingInserts.push({
    sheet: labelMap[AUDIT_GLOBAL_TAB] || '全域設定',
    inst: 'Excel 全域微調',
    summary: `已套用 Excel 全域微調（ISN 條碼：${STATE.lastIsnLen || 15} 碼；請點擊底部「💾 寫入並匯出 Excel (*_FIXED.xlsx)」寫入檔案）`
  });
  renderGlobalEditorPanel();
  renderAuditResults();
}
