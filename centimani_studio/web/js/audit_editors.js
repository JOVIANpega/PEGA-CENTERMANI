// AI-Guided Smart INI Notepad with Factory Presets, Isolated Change Summary & Correctness Checker (Build v0.5.7)
// Solves the 3 core user questions when editing INI:
// 1. "改了哪裡 / 改了什麼？" -> Top isolated "🎯 本次已修改項目對照卡" (separates changed lines from untouched lines, marks "🤖 AI 剛剛修改").
// 2. "是否改對？" -> Real-time "🩺 AI 設定正確性驗證 (Correctness Validator)" checking SFIS/iPLAS pairing, Factory URL vs Site match, COM format, and PC/DUT IP subnet match.
// 3. "自然語言與廠區支援" -> Understands "巴淡 / PTB", "蘇州 / PSZ", "重慶 / PCQ", "台灣 / DC", COM ports, IP addresses, and never fakes "已執行" if no value was changed.

let AUDIT_GLOBAL_TAB = 'ini_diff';
let INI_AI_INTENT = 'core'; // 'core' | 'sfis' | 'com' | 'ip' | 'all'
let INI_AI_LAST_MSG = '';
let INI_AI_LAST_MSG_TYPE = 'info'; // 'success' | 'warn' | 'info'
let INI_AI_RECENT_KEYS = new Set(); // Tracks keys just modified by AI command so we can badge them "🤖 AI 剛改"

const SFIS_FACTORY_PRESETS = [
  {
    id: 'PTB_BATAM',
    label: '🇮🇩 巴淡廠 PTB (10.176.33.13)',
    keywords: ['巴淡', 'batam', 'ptb', '10.176.33.13'],
    weblink: 'http://10.176.33.13/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PTB'
  },
  {
    id: 'PSZ_SUZHOU_1',
    label: '🇨🇳 蘇州廠 PSZ-1 (172.24.248.17)',
    keywords: ['蘇州', '苏州', 'suzhou', 'psz', '172.24.248.17'],
    weblink: 'http://172.24.248.17/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PSZ'
  },
  {
    id: 'PSZ_SUZHOU_LOT5',
    label: '🇨🇳 蘇州廠 PSZ Lot5 (172.24.248.15)',
    keywords: ['lot5', '172.24.248.15'],
    weblink: 'http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PSZ'
  },
  {
    id: 'PCQ_CHONGQING',
    label: '🇨🇳 重慶廠 PCQ (172.18.125.49)',
    keywords: ['重慶', '重庆', 'chongqing', 'pcq', '172.18.125.49'],
    weblink: 'http://172.18.125.49/SFISWebService/SFISTSPWebService.asmx,2',
    site: 'PCQ'
  },
  {
    id: 'PXD_DEFAULT',
    label: '🇹🇼 台灣 / PXD 通用域名 (pxd-sftsp-n3)',
    keywords: ['台灣', '臺灣', '新店', '桃科', '關渡', 'pxd', 'dc'],
    weblink: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx',
    site: 'DC'
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
  INI_AI_INTENT = 'core';
  INI_AI_LAST_MSG = '';
  INI_AI_RECENT_KEYS.clear();
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
    SFIS_WebLink: 'SFIS 廠區伺服器網址 (WebLink)',
    iPLAS_Enable: 'iPLAS 數據上傳開關 (0=關, 1=開)',
    iPLAS_Site: 'iPLAS 廠區代碼 (如 PTB / PSZ / PCQ / DC)',
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
      ? `🟢 <b>開啟 SFIS 過站總開關</b>（站別碼 <code>${_escAttr(sys.SFIS_TSP || 'PEGA,2')}</code>）`
      : `⚪ <b>關閉 SFIS 過站總開關</b>（切為單機離線測試）`;
  }
  if (k === 'SFIS_WebLink') {
    const matchedPreset = SFIS_FACTORY_PRESETS.find(p => p.weblink === nv);
    const factoryTag = matchedPreset ? `（對應廠區：<b>${matchedPreset.label}</b>）` : '';
    return `🏭 <b>切換 SFIS 廠區伺服器網址</b> 為 <code>${_escAttr(nv)}</code> ${factoryTag}`;
  }
  if (k === 'iPLAS_Site') {
    return `🏭 <b>切換 iPLAS 廠區代碼</b> 由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>`;
  }
  if (k === 'SFIS_LinkIPLAS') {
    return nv === '1' ? `🔗 <b>開啟 SFIS 連動 iPLAS</b>` : `⚪ <b>關閉 SFIS 連動 iPLAS</b>`;
  }
  if (k === 'iPLAS_Enable') {
    return nv === '1'
      ? `☁️ <b>開啟 iPLAS 數據上傳</b>（廠區 <code>${_escAttr(sys.iPLAS_Site || 'DC')}</code>）`
      : `⚪ <b>關閉 iPLAS 數據上傳</b>`;
  }
  if (k === 'DebugMode') {
    return nv === '0'
      ? `🔒 <b>切換為量產驗簽章模式 (DebugMode=0)</b>（存檔時將自動重算 64 碼 Checksum）`
      : `🛠️ <b>切換為工程除錯模式 (DebugMode=1)</b>（免驗 Checksum）`;
  }
  if (/^DUT_UR/i.test(k)) {
    return `🔌 <b>待測物序列埠 (${_escAttr(k)})</b> 由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>`;
  }
  if (/^(DUTIP_|PCIP_|GoldenIP)/i.test(k)) {
    return `🌐 <b>${_escAttr(e.desc)} (${_escAttr(k)})</b> 由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>`;
  }
  return `✏️ <b>${_escAttr(e.desc)} (${_escAttr(k)})</b> 由 <code>${_escAttr(ov)}</code> 改為 <code>${_escAttr(nv)}</code>`;
}

// 🩺 AI 設定正確性自動診斷器 (告訴使用者「是否改對！」並提供一鍵修復)
function _validateIniCorrectness(ws, allChanged) {
  const issues = []; // { level: 'error'|'warn', msg: '...', fixJs: '...', fixLabel: '...' }
  const sys = (ws && ws.system_ini) || {};
  const gSet = (ws && ws.global_ini && ws.global_ini.Settings) || {};

  // 1. 檢查廠區網址 SFIS_WebLink 與 iPLAS_Site 是否互相匹配
  const curWebLink = String(sys.SFIS_WebLink || '').trim();
  const curSite = String(sys.iPLAS_Site || '').trim().toUpperCase();
  const matchedFactory = SFIS_FACTORY_PRESETS.find(p => p.weblink === curWebLink);
  if (matchedFactory && matchedFactory.site !== curSite) {
    issues.push({
      level: 'warn',
      msg: `廠區代號不一致：您的 <code>SFIS_WebLink</code> 已選為 <b>${matchedFactory.label}</b>，但 <code>iPLAS_Site</code> 目前卻是 <code>${_escAttr(curSite)}</code>（應為 <code>${matchedFactory.site}</code>）。`,
      fixJs: `setSystemIniValueLive('iPLAS_Site', '${matchedFactory.site}', true)`,
      fixLabel: `🔧 一鍵修正 iPLAS_Site 為 ${matchedFactory.site}`
    });
  }

  // 2. 檢查改了 SFIS 網址或站別，但 SFIS_Enable 卻還是 0 (關閉)
  const sfisUrlChanged = allChanged.some(e => e.key === 'SFIS_WebLink' || e.key === 'SFIS_TSP');
  if (sfisUrlChanged && String(sys.SFIS_Enable).trim() === '0') {
    issues.push({
      level: 'warn',
      msg: `您剛剛修改了 SFIS 廠區網址或站別碼，但 <b>SFIS 過站總開關 (<code>SFIS_Enable</code>) 目前仍是 0 (關閉)</b>，這樣產線測試時不會連線過站！`,
      fixJs: `setSystemIniValueLive('SFIS_Enable', '1', true)`,
      fixLabel: `🔧 一鍵開啟 SFIS_Enable = 1`
    });
  }

  // 3. 檢查開啟了 SFIS_LinkIPLAS=1，但 SFIS_Enable 或 iPLAS_Enable 卻是 0
  if (String(sys.SFIS_LinkIPLAS).trim() === '1' && (String(sys.SFIS_Enable).trim() === '0' || String(sys.iPLAS_Enable).trim() === '0')) {
    issues.push({
      level: 'warn',
      msg: `您開啟了 <code>SFIS_LinkIPLAS=1</code>，但 <code>SFIS_Enable</code> 或 <code>iPLAS_Enable</code> 尚未同步開啟，連動不會生效。`,
      fixJs: `setSystemIniValueLive('SFIS_Enable', '1', false); setSystemIniValueLive('iPLAS_Enable', '1', true);`,
      fixLabel: `🔧 一鍵同步開啟 SFIS 與 iPLAS`
    });
  }

  // 4. 檢查 COM Port 格式是否正確 (例如使用者把 COM18 誤打成 18 或 COM 18)
  Object.keys(gSet).forEach(k => {
    if (/^(DUT_UR|PCUART|LED_AZ)/i.test(k)) {
      const v = String(gSet[k] || '').trim();
      if (/^\d+$/.test(v)) {
        issues.push({
          level: 'error',
          msg: `序列埠格式錯誤：<code>${_escAttr(k)}</code> 目前填寫為純數字 <code>${_escAttr(v)}</code>，Centimani 規定必須加上 COM 前綴（應為 <code>COM${_escAttr(v)}</code>）！`,
          fixJs: `setGlobalIniValueLive('Settings', '${_escAttr(k)}', 'COM${_escAttr(v)}', true)`,
          fixLabel: `🔧 一鍵修正為 COM${_escAttr(v)}`
        });
      } else if (v && !/^COM\d+$/i.test(v)) {
        issues.push({
          level: 'error',
          msg: `序列埠格式異常：<code>${_escAttr(k)} = ${_escAttr(v)}</code> 不是標準的 <code>COMx</code> 格式（例如 <code>COM4</code>、<code>COM18</code>）。`,
          fixJs: '',
          fixLabel: ''
        });
      }
    }
  });

  // 5. 檢查待測物 DUTIP_1 與電腦網卡 PCIP_1 是否在同一個網段、或是否 IP 撞號
  const dutIp = String(gSet.DUTIP_1 || '').trim();
  const pcIp = String(gSet.PCIP_1 || '').trim();
  const mDut = dutIp.match(/^(\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,3})$/);
  const mPc = pcIp.match(/^(\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,3})$/);
  if (dutIp && !mDut) {
    issues.push({
      level: 'error',
      msg: `IP 格式錯誤：待測物 <code>DUTIP_1 = ${_escAttr(dutIp)}</code> 不是有效的 IPv4 位址（應為 4 段數字如 <code>192.168.11.143</code>）。`,
      fixJs: '',
      fixLabel: ''
    });
  } else if (mDut && mPc) {
    if (dutIp === pcIp) {
      const fixHost = mDut[2] === '100' ? '101' : '100';
      issues.push({
        level: 'error',
        msg: `IP 撞號衝突：待測物 <code>DUTIP_1</code> 與電腦網卡 <code>PCIP_1</code> 被設成一模一樣的 <code>${_escAttr(dutIp)}</code>！兩者末碼必須不同。`,
        fixJs: `setGlobalIniValueLive('Settings', 'PCIP_1', '${mDut[1]}.${fixHost}', true)`,
        fixLabel: `🔧 將電腦 PCIP_1 改為 ${mDut[1]}.${fixHost}`
      });
    } else if (mDut[1] !== mPc[1]) {
      const fixHost = mDut[2] === '100' ? '101' : '100';
      issues.push({
        level: 'warn',
        msg: `網段不一致提醒：待測物 <code>DUTIP_1 (${_escAttr(dutIp)})</code> 與電腦網卡 <code>PCIP_1 (${_escAttr(pcIp)})</code> 前三碼不同網段，可能導致 Ping 或連線失敗！`,
        fixJs: `setGlobalIniValueLive('Settings', 'PCIP_1', '${mDut[1]}.${fixHost}', true)`,
        fixLabel: `🔧 一鍵將電腦 PCIP_1 同步為同網段 ${mDut[1]}.${fixHost}`
      });
    }
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

function selectIniAiIntent(intent) {
  INI_AI_INTENT = intent;
  INI_AI_LAST_MSG = '';
  renderGlobalEditorPanel();
}

function applySfisFactoryPreset(presetId) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  const p = SFIS_FACTORY_PRESETS.find(x => x.id === presetId);
  if (!p) return;
  const sys = STATE.workspace.system_ini;
  sys.SFIS_Enable = '1';
  sys.SFIS_WebLink = p.weblink;
  sys.iPLAS_Enable = '1';
  sys.iPLAS_Site = p.site;
  INI_AI_RECENT_KEYS = new Set(['SFIS_Enable', 'SFIS_WebLink', 'iPLAS_Enable', 'iPLAS_Site']);
  INI_AI_INTENT = 'sfis';
  INI_AI_LAST_MSG_TYPE = 'success';
  INI_AI_LAST_MSG = `✅ AI 已為您套用【${p.label}】標準設定：已將 SFIS_WebLink 設為該廠網址、iPLAS_Site 設為 ${p.site}，並同步開啟 SFIS_Enable=1 與 iPLAS_Enable=1！（請見下方「🎯 本次修改明細對照卡」）`;
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
    INI_AI_RECENT_KEYS = new Set(['SFIS_Enable', 'SFIS_LinkIPLAS', 'iPLAS_Enable', 'DebugMode']);
    INI_AI_LAST_MSG_TYPE = 'success';
    INI_AI_LAST_MSG = '✅ AI 已套用「正式量產過站組合」：已開啟 SFIS_Enable=1、SFIS_LinkIPLAS=1、iPLAS_Enable=1，並設為量產驗簽章模式 DebugMode=0。';
  } else if (presetType === 'eng_offline') {
    sys.SFIS_Enable = '0';
    sys.SFIS_LinkIPLAS = '0';
    sys.iPLAS_Enable = '0';
    sys.DebugMode = '1';
    INI_AI_RECENT_KEYS = new Set(['SFIS_Enable', 'SFIS_LinkIPLAS', 'iPLAS_Enable', 'DebugMode']);
    INI_AI_LAST_MSG_TYPE = 'success';
    INI_AI_LAST_MSG = '✅ AI 已套用「工程離線調試組合」：已關閉 SFIS_Enable=0、iPLAS_Enable=0，並開啟 DebugMode=1 免簽章調試模式。';
  } else if (presetType === 'sync_pc_ip') {
    const dutIp = String(gSet.DUTIP_1 || '').trim();
    const m = dutIp.match(/^(\d+\.\d+\.\d+)\.(\d+)$/);
    if (m) {
      const newPcIp = `${m[1]}.${m[2] === '100' ? '101' : '100'}`;
      gSet.PCIP_1 = newPcIp;
      INI_AI_RECENT_KEYS = new Set(['PCIP_1']);
      INI_AI_LAST_MSG_TYPE = 'success';
      INI_AI_LAST_MSG = `✅ AI 已根據待測物 IP (${dutIp})，將電腦端網卡 PCIP_1 自動同步為同網段之 ${newPcIp}！`;
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
  const changedFields = [];
  INI_AI_RECENT_KEYS.clear();

  // 0. 優先檢查是否提到廠區名稱（如「巴淡 / PTB」、「蘇州 / PSZ」、「重慶 / PCQ」、「台灣 / 新店 / 桃科 / PXD」）
  for (const fp of SFIS_FACTORY_PRESETS) {
    if (fp.keywords.some(kw => txt.includes(kw))) {
      applySfisFactoryPreset(fp.id);
      return;
    }
  }

  // 1. 偵測 COM Port (如 "改COM18", "COM8", "治具COM5", "待測物改18")
  const comMatch = raw.match(/com\s*(\d+)/i);
  if (comMatch) {
    const comVal = 'COM' + comMatch[1];
    if (txt.includes('治具') || txt.includes('fixture')) {
      const oldV = gSet.PCUART_fixture_1;
      gSet.PCUART_fixture_1 = comVal;
      INI_AI_RECENT_KEYS.add('PCUART_fixture_1');
      changedFields.push(`[Global.ini] 氣動治具 PCUART_fixture_1：由 ${oldV || '無'} ➔ 改為 ${comVal}`);
    } else if (txt.includes('led') || txt.includes('燈')) {
      const oldV = gSet.LED_AZ1;
      gSet.LED_AZ1 = comVal;
      INI_AI_RECENT_KEYS.add('LED_AZ1');
      changedFields.push(`[Global.ini] FeasaLED LED_AZ1：由 ${oldV || '無'} ➔ 改為 ${comVal}`);
    } else {
      const oldV = gSet.DUT_UR1;
      gSet.DUT_UR1 = comVal;
      INI_AI_RECENT_KEYS.add('DUT_UR1');
      changedFields.push(`[Global.ini] 待測物序列埠 DUT_UR1：由 ${oldV || '無'} ➔ 改為 ${comVal}`);
    }
    INI_AI_INTENT = 'com';
  }

  // 2. 偵測 IP 位址 (如 "改IP 192.168.1.50")
  const ipMatch = raw.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/);
  if (ipMatch) {
    const ipVal = ipMatch[1];
    if (txt.includes('電腦') || txt.includes('pc')) {
      const oldV = gSet.PCIP_1;
      gSet.PCIP_1 = ipVal;
      INI_AI_RECENT_KEYS.add('PCIP_1');
      changedFields.push(`[Global.ini] 電腦網卡 PCIP_1：由 ${oldV || '無'} ➔ 改為 ${ipVal}`);
    } else {
      const oldV = gSet.DUTIP_1;
      gSet.DUTIP_1 = ipVal;
      INI_AI_RECENT_KEYS.add('DUTIP_1');
      changedFields.push(`[Global.ini] 待測物連線 DUTIP_1：由 ${oldV || '無'} ➔ 改為 ${ipVal}`);
    }
    INI_AI_INTENT = 'ip';
  }

  // 3. 偵測明確的 SFIS / iPLAS 開關指令
  if (txt.includes('sfis')) {
    INI_AI_INTENT = 'sfis';
    if (txt.includes('關') || txt.includes('off') || txt.includes('0') || txt.includes('不要')) {
      const oldV = sys.SFIS_Enable;
      sys.SFIS_Enable = '0';
      INI_AI_RECENT_KEYS.add('SFIS_Enable');
      changedFields.push(`[System.ini] SFIS_Enable：由 ${oldV} ➔ 改為 0 (關閉)`);
    } else if (txt.includes('開') || txt.includes('on') || txt.includes('1') || txt.includes('啟用')) {
      const oldV = sys.SFIS_Enable;
      sys.SFIS_Enable = '1';
      INI_AI_RECENT_KEYS.add('SFIS_Enable');
      changedFields.push(`[System.ini] SFIS_Enable：由 ${oldV} ➔ 改為 1 (開啟)`);
    }
  }
  if (txt.includes('iplas')) {
    INI_AI_INTENT = 'sfis';
    if (txt.includes('關') || txt.includes('off') || txt.includes('0') || txt.includes('不要')) {
      const oldV = sys.iPLAS_Enable;
      sys.iPLAS_Enable = '0';
      INI_AI_RECENT_KEYS.add('iPLAS_Enable');
      changedFields.push(`[System.ini] iPLAS_Enable：由 ${oldV} ➔ 改為 0 (關閉)`);
    } else if (txt.includes('開') || txt.includes('on') || txt.includes('1') || txt.includes('啟用')) {
      const oldV = sys.iPLAS_Enable;
      sys.iPLAS_Enable = '1';
      INI_AI_RECENT_KEYS.add('iPLAS_Enable');
      changedFields.push(`[System.ini] iPLAS_Enable：由 ${oldV} ➔ 改為 1 (開啟)`);
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

  // 如果真的有改到數值，清楚列出「改了哪幾個欄位」；如果沒認出具體新值，老實告知使用者並引導點按鈕！
  if (changedFields.length > 0) {
    INI_AI_LAST_MSG_TYPE = 'success';
    INI_AI_LAST_MSG = `✅ AI 已根據您的指令「${raw}」實際修改了 ${changedFields.length} 處設定：${changedFields.join(' ｜ ')}（請見下方「🎯 本次已修改項目對照卡」確認）`;
    _recordPendingIniNotice(INI_AI_LAST_MSG);
  } else {
    if (txt.includes('com') || txt.includes('序列埠')) INI_AI_INTENT = 'com';
    else if (txt.includes('ip') || txt.includes('網段')) INI_AI_INTENT = 'ip';
    else if (txt.includes('sfis') || txt.includes('iplas')) INI_AI_INTENT = 'sfis';

    INI_AI_LAST_MSG_TYPE = 'warn';
    INI_AI_LAST_MSG = `🤔 AI 收到您的「${raw}」，但尚未從句子裡抓到要改成的目標數值（所以目前尚未自動變動任何欄位）！您可以直接點擊下方廠區按鈕（如：🇮🇩 巴淡廠 PTB / 🇨🇳 蘇州廠 PSZ / 🇨🇳 重慶廠 PCQ），或輸入明確數值如「改 COM18」、「SFIS 巴淡廠」、「開 SFIS」。`;
  }
  renderGlobalEditorPanel();
}

function setSystemIniValueLive(key, val, rerender = true) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.system_ini[key] = String(val);
  INI_AI_RECENT_KEYS.add(key);
  _recordPendingIniNotice(`System.ini: ${key}=${val}`);
  if (rerender) renderGlobalEditorPanel();
}

function setGlobalIniValueLive(sec, key, val, rerender = true) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.global_ini = STATE.workspace.global_ini || { Settings: {}, Scripts: {} };
  STATE.workspace.global_ini[sec] = STATE.workspace.global_ini[sec] || {};
  STATE.workspace.global_ini[sec][key] = String(val);
  INI_AI_RECENT_KEYS.add(key);
  _recordPendingIniNotice(`Global.ini [${sec}] ${key}=${val}`);
  if (rerender) renderGlobalEditorPanel();
}

function revertSingleIniKey(fileLabel, sec, key) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  INI_AI_RECENT_KEYS.delete(key);
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
  INI_AI_RECENT_KEYS.clear();
  INI_AI_LAST_MSG_TYPE = 'info';
  INI_AI_LAST_MSG = '↩ 已將所有 INI 設定全部還原為原始檔案狀態（目前 0 項修改）。';
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
  const validationIssues = _validateIniCorrectness(ws, allChanged);

  // 根據使用者選擇的 AI 意圖篩選
  const isComKey = (e) => e.file === 'Global.ini' && (/^(DUT_UR|PCUART|LED_AZ|WLAN_COM)/i.test(e.key) || /^COM\d+/i.test(e.newVal) || /^COM\d+/i.test(e.oldVal));
  const isIpKey = (e) => (e.file === 'Global.ini' && /IP/i.test(e.key)) || e.key === 'IpFinder_Enable';
  const isSfisKey = (e) => e.file === 'System.ini' && /^(SFIS_|iPLAS_|DebugMode|RetryCount|CSVReport_)/i.test(e.key);
  const isCoreKey = (e) => e.isChanged
    || (e.file === 'System.ini' && /^(SFIS_Enable|SFIS_WebLink|SFIS_LinkIPLAS|iPLAS_Enable|iPLAS_Site|DebugMode|SFIS_TSP)$/i.test(e.key))
    || (e.file === 'Global.ini' && (usedVars.has(e.key) || /^(DUT_UR1|DUTIP_1|PCIP_1|DAQ_1|LED_AZ1|FW_VERSION)$/i.test(e.key)));

  let filteredEntries = [];
  let aiRecommendationBanner = '';

  if (INI_AI_INTENT === 'sfis') {
    filteredEntries = allEntries.filter(e => isSfisKey(e) || /^DEVID_/i.test(e.key));
    const factoryBtns = SFIS_FACTORY_PRESETS.map(fp => {
      const isCur = String((ws.system_ini || {}).SFIS_WebLink || '').trim() === fp.weblink;
      return `<button onclick="applySfisFactoryPreset('${fp.id}')" class="btn" style="padding:5px 11px; font-size:12px; font-weight:800; ${isCur ? 'background:#16A34A;color:#FFF;border-color:#15803D;' : 'background:#FFFFFF;color:#0F172A;border:1.5px solid #38BDF8;'}">${isCur ? '✔ ' : ''}${fp.label}</button>`;
    }).join('');

    aiRecommendationBanner = `
      <div style="background:#F0F9FF; border:1.5px solid #38BDF8; border-radius:8px; padding:10px 14px; display:flex; flex-direction:column; gap:8px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <span style="font-size:13px; color:#0C4A6E; font-weight:800;">🏭 1. 一鍵選擇 SFIS / iPLAS 廠區（點一下自動改好該廠網址、Site 代碼並開啟過站）：</span>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button onclick="applyAiPresetBundle('mp_sfis_on')" class="btn" style="padding:4px 10px; font-size:12px; background:#0284C7; color:#FFF; border:none; font-weight:700;">✨ 全開：量產過站模式</button>
            <button onclick="applyAiPresetBundle('eng_offline')" class="btn" style="padding:4px 10px; font-size:12px; background:#FFFFFF; color:#475569; border:1px solid #94A3B8; font-weight:700;">🛠️ 全關：工程離線調試</button>
          </div>
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          ${factoryBtns}
        </div>
      </div>
    `;
  } else if (INI_AI_INTENT === 'com') {
    filteredEntries = allEntries.filter(isComKey);
    const usedComList = filteredEntries.filter(e => usedVars.has(e.key)).map(e => `${e.key} (${e.desc})`).join('、');
    aiRecommendationBanner = `
      <div style="background:#F0F9FF; border:1.5px solid #38BDF8; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:12.5px; color:#0C4A6E;">
          🤖 <b>AI 序列埠掃描：</b>本腳本 Excel 實際引用了 <b>${usedComList || 'DUT_UR1 (待測物序列埠)'}</b>。直接修改下方 COM 編號，系統會自動檢查格式是否正確！
        </div>
        <button onclick="openCommModal()" class="btn" style="padding:4px 10px; font-size:12px; background:#FFFFFF; color:#0369A1; border:1px solid #38BDF8; font-weight:700;">🔄 需要把測站 UART@ 批次轉成 SSH@ 點此</button>
      </div>
    `;
  } else if (INI_AI_INTENT === 'ip') {
    filteredEntries = allEntries.filter(isIpKey);
    aiRecommendationBanner = `
      <div style="background:#F0F9FF; border:1.5px solid #38BDF8; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:12.5px; color:#0C4A6E;">
          🤖 <b>AI 網段同步助手：</b>修改待測物 <code>DUTIP_1</code> 時，電腦網卡 <code>PCIP_1</code> 前三碼必須同網段（系統會自動為您檢查網段是否相符）。
        </div>
        <button onclick="applyAiPresetBundle('sync_pc_ip')" class="btn" style="padding:4px 10px; font-size:12px; background:#0284C7; color:#FFF; border:none; font-weight:700;">✨ 一鍵將電腦 PCIP_1 同步為待測物同網段</button>
      </div>
    `;
  } else if (INI_AI_INTENT === 'all') {
    filteredEntries = allEntries;
  } else {
    filteredEntries = allEntries.filter(isCoreKey);
  }

  // =========================================================================
  // 🎯 解答「改了哪裡、改了什麼、是否改對」：置頂獨立的【本次修改明細 ＋ AI 正確性驗證卡】
  // =========================================================================
  let isolatedChangesAndValidationHtml = '';
  if (allChanged.length > 0) {
    const changedRowsHtml = allChanged.map((e, i) => {
      const isAiRecent = INI_AI_RECENT_KEYS.has(e.key);
      return `
        <tr style="border-bottom:1px solid #FDE047; background:${isAiRecent ? '#FEF08A' : '#FEF9C3'};">
          <td style="padding:7px 10px; white-space:nowrap;">
            <span style="font-weight:900; color:#854D0E; margin-right:4px;">#${i + 1}</span>
            <span class="mono" style="font-size:11px; font-weight:800; padding:2px 6px; border-radius:4px; background:${e.file === 'System.ini' ? '#EDE9FE' : '#DBEAFE'}; color:${e.file === 'System.ini' ? '#5B21B6' : '#1E40AF'};">${_escAttr(e.file)}</span>
            ${isAiRecent ? `<span style="background:#0284C7; color:#FFF; font-size:11px; font-weight:800; padding:1px 6px; border-radius:4px; margin-left:4px;">🤖 AI 剛改</span>` : ''}
          </td>
          <td style="padding:7px 10px;">
            <div class="mono" style="font-weight:900; font-size:13px; color:#0F172A;">[${_escAttr(e.section)}] ${_escAttr(e.key)}</div>
            <div style="font-size:11.5px; color:#475569;">${_escAttr(e.desc)}</div>
          </td>
          <td class="mono" style="padding:7px 10px; background:#FEE2E2; color:#991B1B; font-size:12.5px; text-decoration:line-through; word-break:break-all;">
            ${_escAttr(e.oldVal)}
          </td>
          <td style="padding:7px 6px; text-align:center; font-weight:900; color:#16A34A; font-size:15px;">➔</td>
          <td class="mono" style="padding:7px 10px; background:#DCFCE7; color:#14532D; font-size:13px; font-weight:900; word-break:break-all;">
            ${_escAttr(e.newVal)}
          </td>
          <td style="padding:7px 10px; font-size:12px; color:#1E293B;">
            ${_explainChangeByAi(e, ws)}
          </td>
          <td style="padding:7px 10px; text-align:right; white-space:nowrap;">
            <button onclick="revertSingleIniKey('${_escAttr(e.file)}','${_escAttr(e.section)}','${_escAttr(e.key)}')" class="btn" style="padding:3px 8px; font-size:11.5px; background:#FFFFFF; color:#B91C1C; border:1px solid #FCA5A5; font-weight:700;">✕ 取消此項</button>
          </td>
        </tr>
      `;
    }).join('');

    let correctnessBoxHtml = '';
    if (validationIssues.length === 0) {
      correctnessBoxHtml = `
        <div style="background:#DCFCE7; border-top:1.5px solid #4ADE80; padding:9px 14px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
          <div style="font-weight:800; font-size:13px; color:#14532D;">
            ✅ <b>AI 設定正確性診斷通過（是否改對：100% 正確！）：</b>已檢查所有修改項目的格式、SFIS/iPLAS 廠區配對、過站開關與 COM/IP 網段邏輯均正確無誤！
          </div>
        </div>
      `;
    } else {
      const issueItems = validationIssues.map(iss => `
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; padding:4px 0;">
          <span style="font-size:12.5px; color:${iss.level === 'error' ? '#991B1B' : '#92400E'}; font-weight:700;">
            ${iss.level === 'error' ? '❌ [格式錯誤]' : '⚠️ [AI 防呆提醒]'} ${iss.msg}
          </span>
          ${iss.fixJs ? `<button onclick="${iss.fixJs}" class="btn" style="padding:3px 10px; font-size:12px; background:#16A34A; color:#FFFFFF; border:none; font-weight:800;">${iss.fixLabel}</button>` : ''}
        </div>
      `).join('');
      correctnessBoxHtml = `
        <div style="background:#FFFBEB; border-top:2px solid #F59E0B; padding:10px 14px; display:flex; flex-direction:column; gap:4px;">
          <div style="font-weight:900; font-size:13px; color:#B45309;">🩺 AI 設定正確性診斷（發現 ${validationIssues.length} 項需要注意或一鍵修正的地方）：</div>
          ${issueItems}
        </div>
      `;
    }

    isolatedChangesAndValidationHtml = `
      <div style="border:2px solid #EAB308; border-radius:8px; overflow:hidden; background:#FFFFFF; box-shadow:0 2px 8px rgba(234,179,8,0.18);">
        <div style="background:#FEF08A; padding:8px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; border-bottom:1.5px solid #EAB308;">
          <span style="font-weight:900; font-size:14px; color:#713F12;">
            🎯 1. 您剛剛改了哪裡、改了什麼？（目前已修改 ${allChanged.length} 處，已與下方未修改項目完全分開顯示）
          </span>
          <button onclick="revertAllIniChanges()" class="btn" style="padding:3px 10px; font-size:12px; background:#FFFFFF; color:#B91C1C; border:1px solid #FCA5A5; font-weight:800;">↩ 全部取消還原 (${allChanged.length})</button>
        </div>
        <div style="overflow-x:auto;">
          <table style="width:100%; border-collapse:collapse;">
            <thead>
              <tr style="background:#FEF9C3; color:#713F12; font-size:12px; border-bottom:1px solid #FDE047;">
                <th style="padding:6px 10px; text-align:left;">檔案</th>
                <th style="padding:6px 10px; text-align:left;">改了哪個參數</th>
                <th style="padding:6px 10px; text-align:left; background:#FEE2E2; color:#991B1B;">⬅️ 修改前 (原始值)</th>
                <th style="padding:6px 6px;"></th>
                <th style="padding:6px 10px; text-align:left; background:#DCFCE7; color:#14532D;">➡️ 修改後 (新值)</th>
                <th style="padding:6px 10px; text-align:left;">🤖 AI 白話解釋</th>
                <th style="padding:6px 10px; text-align:right;">操作</th>
              </tr>
            </thead>
            <tbody>${changedRowsHtml}</tbody>
          </table>
        </div>
        ${correctnessBoxHtml}
      </div>
    `;
  } else {
    isolatedChangesAndValidationHtml = `
      <div style="background:#F8FAFC; border:1.5px dashed #94A3B8; border-radius:8px; padding:10px 14px; font-size:13px; color:#475569;">
        🎯 <b>目前尚未修改任何設定（0 項異動）。</b>只要您在下方改了任何欄位、點了廠區按鈕或使用 AI 指令，這裡就會立刻獨立列出<b>「改了哪裡、原本是什麼 ➔ 改成什麼、以及 AI 診斷是否改對」</b>！
      </div>
    `;
  }

  // 把已修改的行排最上面
  filteredEntries.sort((a, b) => {
    const scoreA = (a.isChanged ? 20 : 0) + (INI_AI_RECENT_KEYS.has(a.key) ? 10 : 0) + (usedVars.has(a.key) ? 5 : 0);
    const scoreB = (b.isChanged ? 20 : 0) + (INI_AI_RECENT_KEYS.has(b.key) ? 10 : 0) + (usedVars.has(b.key) ? 5 : 0);
    if (scoreA !== scoreB) return scoreB - scoreA;
    if (a.file !== b.file) return a.file === 'System.ini' ? -1 : 1;
    return 0;
  });

  // 渲染每一行記事本編輯列（特別針對 SFIS_WebLink 提供廠區下拉 + 全寬網址框，不再被截斷！）
  const renderNotepadLine = (e, idx) => {
    const isBoolSwitch = e.file === 'System.ini' && /^(SFIS_Enable|SFIS_LinkIPLAS|iPLAS_Enable|DebugMode|CSVReport_Enable|IpFinder_Enable)$/i.test(e.key);
    const isWebLink = e.file === 'System.ini' && e.key === 'SFIS_WebLink';
    const isUsedInExcel = usedVars.has(e.key);
    const isAiRecent = INI_AI_RECENT_KEYS.has(e.key);
    const rowBg = e.isChanged ? '#FEF9C3' : (idx % 2 === 0 ? '#FFFFFF' : '#F8FAFC');
    const rowBorder = e.isChanged ? '2px solid #EAB308' : '1px solid #E2E8F0';

    let editorControl = '';
    if (isBoolSwitch) {
      const isOn = String(e.newVal).trim() === '1';
      const onLbl = e.key === 'DebugMode' ? '1 (免簽章調試)' : '1 (開啟 ON)';
      const offLbl = e.key === 'DebugMode' ? '0 (正式量產)' : '0 (關閉 OFF)';
      editorControl = `
        <select onchange="setSystemIniValueLive('${_escAttr(e.key)}', this.value, true)" class="mono"
          style="width:175px; padding:5px 8px; font-size:13px; font-weight:800; border-radius:5px; border:1.5px solid ${e.isChanged ? '#16A34A' : '#94A3B8'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; color:${isOn ? '#15803D' : '#334155'};">
          <option value="1" ${isOn ? 'selected' : ''}>${onLbl}</option>
          <option value="0" ${!isOn ? 'selected' : ''}>${offLbl}</option>
        </select>
      `;
    } else if (isWebLink) {
      const presetOpts = SFIS_FACTORY_PRESETS.map(fp =>
        `<option value="${_escAttr(fp.id)}" ${fp.weblink === e.newVal ? 'selected' : ''}>${_escAttr(fp.label)}</option>`
      ).join('');
      const hasPresetMatch = SFIS_FACTORY_PRESETS.some(fp => fp.weblink === e.newVal);
      editorControl = `
        <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; flex:1; min-width:340px;">
          <select onchange="if(this.value) applySfisFactoryPreset(this.value)" style="padding:5px 8px; font-size:12.5px; font-weight:800; border-radius:5px; border:1.5px solid #0284C7; background:#EFF6FF; color:#0C4A6E;">
            <option value="" ${!hasPresetMatch ? 'selected' : ''}>🏭 快速切換廠區網址...</option>
            ${presetOpts}
          </select>
          <input value="${_escAttr(e.newVal)}"
            onchange="setSystemIniValueLive('SFIS_WebLink', this.value, true)"
            class="mono"
            style="flex:1; min-width:280px; padding:5px 8px; font-size:12px; font-weight:${e.isChanged ? '800' : '600'}; border-radius:5px; border:1.5px solid ${e.isChanged ? '#16A34A' : '#94A3B8'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A;">
        </div>
      `;
    } else if (e.file === 'System.ini') {
      editorControl = `
        <input value="${_escAttr(e.newVal)}"
          onchange="setSystemIniValueLive('${_escAttr(e.key)}', this.value, true)"
          class="mono"
          style="width:175px; padding:5px 8px; font-size:13px; font-weight:${e.isChanged ? '800' : '600'}; border-radius:5px; border:1.5px solid ${e.isChanged ? '#16A34A' : '#94A3B8'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A;">
      `;
    } else {
      editorControl = `
        <input value="${_escAttr(e.newVal)}"
          onchange="setGlobalIniValueLive('${_escAttr(e.section)}', '${_escAttr(e.key)}', this.value, true)"
          class="mono"
          style="width:175px; padding:5px 8px; font-size:13px; font-weight:${e.isChanged ? '800' : '600'}; border-radius:5px; border:1.5px solid ${e.isChanged ? '#16A34A' : '#94A3B8'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; color:#0F172A;">
      `;
    }

    return `
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; padding:7px 12px; background:${rowBg}; border:${rowBorder}; border-radius:6px;">
        <!-- 左側：INI 檔案標籤 + 變數名 = -->
        <div style="display:flex; align-items:center; gap:8px; min-width:255px;">
          <span class="mono" style="font-size:11px; font-weight:800; padding:2px 6px; border-radius:4px; background:${e.file === 'System.ini' ? '#EDE9FE' : '#DBEAFE'}; color:${e.file === 'System.ini' ? '#5B21B6' : '#1E40AF'};">
            ${_escAttr(e.file)}
          </span>
          <span class="mono" style="font-weight:800; font-size:13.5px; color:#0F172A;">${_escAttr(e.key)}</span>
          <span class="mono" style="font-weight:800; color:#64748B;">=</span>
          ${isAiRecent ? `<span style="background:#0284C7; color:#FFF; font-size:11px; font-weight:800; padding:1px 6px; border-radius:4px;">🤖 AI 剛改</span>` : ''}
        </div>

        <!-- 中間：[原本舊值 ➔] 可直接修改的輸入框 -->
        <div style="display:flex; align-items:center; gap:8px; flex:${isWebLink ? '2' : '0 1 auto'}; flex-wrap:wrap;">
          ${e.isChanged ? `
            <span class="mono" style="background:#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:800; text-decoration:line-through; max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="修改前原始值: ${_escAttr(e.oldVal)}">
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
        <div style="flex:1; min-width:190px; font-size:12.5px; color:${e.isChanged ? '#854D0E' : '#64748B'}; font-weight:${e.isChanged ? '700' : '400'};">
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

  const msgStyle = INI_AI_LAST_MSG_TYPE === 'warn'
    ? 'background:#FFFBEB; border:1.5px solid #F59E0B; color:#92400E;'
    : 'background:#DCFCE7; border:1.5px solid #22C55E; color:#14532D;';

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
            placeholder="💬 直接打白話文告訴 AI（例如：SFIS 我要巴淡的、蘇州廠 SFIS、改 COM18、開 SFIS、改 IP 192.168.1.50）..."
            onkeydown="if(event.key==='Enter') runIniNaturalLanguageCommand()"
            style="flex:1; min-width:260px; padding:6px 12px; font-size:13px; border:1.5px solid #38BDF8; border-radius:6px; background:#FFFFFF;">
          <button onclick="runIniNaturalLanguageCommand()" class="btn btn-primary-blue" style="padding:6px 14px; font-size:13px; font-weight:800;">
            🤖 AI 自動幫我改
          </button>
        </div>
        ${INI_AI_LAST_MSG ? `<div style="${msgStyle} font-weight:800; font-size:12.5px; padding:8px 12px; border-radius:6px;">${_escAttr(INI_AI_LAST_MSG)}</div>` : ''}
      </div>

      <!-- 2. 🎯 獨立置頂：【改了哪裡、改了什麼、以及 AI 診斷是否改對！】（沒改的行絕不混進來） -->
      ${isolatedChangesAndValidationHtml}

      <!-- 3. AI 針對當前分類的一鍵廠區 / 推薦橫幅 -->
      ${aiRecommendationBanner}

      <!-- 4. 下方：記事本直改區 -->
      <div style="border:1px solid #CBD5E1; border-radius:8px; padding:8px 10px; background:#FFFFFF;">
        <div style="font-weight:800; font-size:12.5px; color:#475569; margin-bottom:6px;">
          📄 2. 記事本明細調整區（共顯示 ${filteredEntries.length} 行，可直接下拉或輸入修改）：
        </div>
        <div style="display:flex; flex-direction:column; gap:5px; max-height:330px; overflow:auto; padding:2px;">
          ${filteredEntries.map(renderNotepadLine).join('')}
        </div>
      </div>

      <div id="iniSaveResultBanner" style="display:none; background:#DCFCE7; border:1.5px solid #22C55E; border-radius:6px; padding:10px 14px;"></div>

      <!-- 5. 底部：唯一存檔並彈出 INI 大綠鈕 -->
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-top:2px;">
        <div style="display:flex; gap:6px; align-items:center;">
          <button onclick="addGlobalIniVar()" class="btn" style="padding:5px 11px; font-size:12px; background:#F8FAFC; color:#334155; border:1px solid #CBD5E1;">+ 新增自訂變數</button>
          <button onclick="saveAndOpenModifiedIni('global')" class="btn" style="padding:5px 11px; font-size:12px; background:#F8FAFC; color:#1E40AF; border:1px solid #93C5FD;">📄 存檔並開 Global.ini</button>
          <button onclick="saveAndOpenModifiedIni('system')" class="btn" style="padding:5px 11px; font-size:12px; background:#F8FAFC; color:#5B21B6; border:1px solid #C4B5FD;">⚙️ 存檔並開 System.ini</button>
        </div>
        <button onclick="saveAndOpenModifiedIni('auto')" class="btn btn-primary-green" style="padding:9px 24px; font-size:14.5px; font-weight:900; box-shadow:0 3px 10px rgba(22,163,74,0.3);">
          💾 確認無誤！存檔並直接彈出剛剛改的 INI 記事本
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
