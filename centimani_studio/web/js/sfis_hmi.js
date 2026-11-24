// SFIS WebService Animated Workstation HMI & Single-ISN Verification + Excel Script Builder

const SFIS_PLANT_PRESETS = [
  {
    id: 'TAIPEI',
    label: '台北 TAIPEI',
    url: 'http://172.18.202.12/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'PEGA,2',
    hint: '台北內網預設；可在上方直接改寫實際 IP（自動記住）'
  },
  {
    id: 'PTB_PROD',
    label: '重慶 PTB 正式',
    url: 'http://10.176.33.13/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2',
    hint: 'PTB 正式機 (SCRIPTS/System.ini 實測網址)'
  },
  {
    id: 'PTB_QA',
    label: '重慶 PTB 測試 (QA)',
    url: 'http://172.24.255.10/SFISWebService_BTARDB0QA/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2',
    hint: 'PTB 測試機 BTARDB0QA'
  },
  {
    id: 'PTB_F1',
    label: 'PTB F1 (可編輯)',
    url: 'http://172.24.255.113/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2',
    hint: 'PTB F1 預留範本（請依廠區實際 IP 修改上方 WebLink，系統會自動記住）'
  },
  {
    id: 'PTSN_PXD',
    label: '蘇州 PTSN (PXD)',
    url: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2',
    hint: '蘇州 PTSN / PXD 正式機'
  },
  {
    id: 'PTSN_SZ',
    label: '蘇州 SZ (.248.15)',
    url: 'http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2',
    hint: '蘇州 SFIS .248.15 伺服器'
  },
  {
    id: 'SZASCD0QA',
    label: '蘇州 QA (SZASCD0QA)',
    url: 'http://172.24.255.10/SFISWebService_SZASCD0QA/SFISTSPWebService.asmx',
    defaultDevice: '430079',
    defaultTsp: 'ATLAS,2',
    hint: '蘇州 QA 測試機'
  }
];

const SFIS_PROXY_FIELDS = [
  { key: 'SNA', label: 'SNA（代用欄位 A）' },
  { key: 'SNB', label: 'SNB（代用欄位 B / UUID）' },
  { key: 'SNC', label: 'SNC（代用欄位 C / PID）' },
  { key: 'SND', label: 'SND（代用欄位 D / SSN）' },
  { key: 'SNE', label: 'SNE（代用欄位 E）' },
  { key: 'SNF', label: 'SNF（代用欄位 F）' },
  { key: 'SNG', label: 'SNG（代用欄位 G）' },
  { key: 'MAC1', label: 'MAC1（LAN / 主網卡 MAC）' },
  { key: 'SSN', label: 'SSN（出貨序號）' },
  { key: 'ITEMINFO_60', label: 'ITEMINFO 60階（MB 序號）' },
  { key: 'ITEMINFO_80', label: 'ITEMINFO 80階（料號/主序號）' }
];

const SFIS_CATALOG_BLOCKS = [
  {
    kind: 'login',
    icon: '🔐',
    title: 'OP Login / Logout',
    subtitle: '模擬測試機台登入或登出（檢查這台 PC 跟 SFIS 通不通）',
    soap: 'WTSP_LOGINOUT',
    theme: '#0284C7',
    bg: '#F0F9FF',
    border: '#7DD3FC',
    safeNote: '不消耗 ISN'
  },
  {
    kind: 'checkroute',
    icon: '🔍',
    title: 'CheckRoute 過站檢查',
    subtitle: '檢查目前這 1 顆 ISN 在此 DeviceID 是否可刷過站',
    soap: 'WTSP_CHKROUTE',
    theme: '#2563EB',
    bg: '#EFF6FF',
    border: '#93C5FD',
    safeNote: '不推進途程'
  },
  {
    kind: 'get',
    icon: '📥',
    title: 'GET 讀欄位 (Read)',
    subtitle: '選代用欄位 (SNA~SNG / MAC1 / ITEMINFO)，無限次安全讀取',
    soap: 'WTSP_GETVERSION',
    theme: '#059669',
    bg: '#ECFDF5',
    border: '#6EE7B7',
    safeNote: '可無限次讀'
  },
  {
    kind: 'savelink',
    icon: '📤',
    title: 'WRITE 寫入欄位',
    subtitle: '選欄位並寫入測試值（送出 #SAVE:欄位=值）',
    soap: 'WTSP_RESULT (#SAVE)',
    theme: '#D97706',
    bg: '#FFFBEB',
    border: '#FCD34D',
    safeNote: '⚠️ 慎按：寫入可能消耗此顆 ISN'
  },
  {
    kind: 'rw',
    icon: '🔄',
    title: 'R/W 寫入＋回讀比對',
    subtitle: '先寫入測試值，再立刻 GET 回讀比對資料庫是否存成功',
    soap: 'RESULT + GETVERSION',
    theme: '#7C3AED',
    bg: '#F5F3FF',
    border: '#C4B5FD',
    safeNote: '⚠️ 會執行 1 次寫入＋1 次回讀'
  },
  {
    kind: 'clear',
    icon: '🧹',
    title: 'CLEAR 試寫空值清空',
    subtitle: '嘗試寫入空字串清除代用欄位並回讀（已推站鎖定時仍需 PE 清站）',
    soap: 'RESULT (#SAVE="")',
    theme: '#475569',
    bg: '#F8FAFC',
    border: '#CBD5E1',
    safeNote: '試探清除欄位值'
  }
];

function _loadCustomPlantUrls() {
  try {
    return JSON.parse(localStorage.getItem('centimani_sfis_custom_urls') || '{}') || {};
  } catch (e) {
    return {};
  }
}

function _saveCustomPlantUrl(plantId, url) {
  try {
    const map = _loadCustomPlantUrls();
    map[plantId] = String(url || '').trim();
    localStorage.setItem('centimani_sfis_custom_urls', JSON.stringify(map));
  } catch (e) {}
}

function _getEffectivePlantUrl(plantId) {
  const custom = _loadCustomPlantUrls();
  if (custom[plantId]) return custom[plantId];
  const found = SFIS_PLANT_PRESETS.find(x => x.id === plantId);
  return found ? found.url : SFIS_PLANT_PRESETS[1].url;
}

const SFIS_HMI_STATE = {
  activeSubTab: 'sfis', // 'sfis' | 'dll'
  plantId: 'PTB_PROD',
  config: {
    url: _getEffectivePlantUrl('PTB_PROD'),
    project_name: 'SFIS_VERIFY',
    station: 'MB',
    device_id: '710001',
    tsp: 'ATLAS,2',
    op: 'S09166390',
    isn: '1B5723090000004',
    skip_save_on_fail: true
  },
  isnPoolText: '1B5723090000004\n1B5723090000005\n1B5723090000006',
  showIsnPool: false,
  items: [
    { uid: 'sf_1', kind: 'login', login_status: '1', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' },
    { uid: 'sf_2', kind: 'checkroute', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' },
    { uid: 'sf_3', kind: 'get', field_key: 'SNA', custom_field: '', ref_var: 'sfSNA', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' },
    { uid: 'sf_4', kind: 'rw', field_key: 'SNB', custom_field: '', save_val: 'TEST_001', ref_var: 'sfSNB', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' }
  ],
  // Animator state
  anim: {
    phase: 'idle', // 'idle' | 'sending' | 'receiving' | 'pass' | 'fail' | 'offline'
    actionLabel: '待機就緒 — 請先按 Login 測這台電腦通不通',
    opLoggedIn: null, // null | true | false
    netConnected: null, // null | true | false
    lastFieldVal: '',
    sentPacketText: '尚未送出請求（點擊下方任一步驟之 ⚡ 實測）',
    recvRawText: '尚無回傳字串',
    recvSummary: '待機中',
    history: []
  },
  isRunning: false,
  dragSrcIdx: -1,
  dragCatalogKind: ''
};

function _escH(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function _getBlockMeta(kind) {
  return SFIS_CATALOG_BLOCKS.find(b => b.kind === kind) || SFIS_CATALOG_BLOCKS[1];
}

function _resolveCardField(it) {
  if (!it) return 'SNA';
  if (it.field_key === '__CUSTOM__') return (it.custom_field || 'SNA').trim() || 'SNA';
  return (it.field_key || it.save_key || it.chk_data || 'SNA').trim();
}

function _itemToBackendStep(it) {
  const k = it.kind;
  const f = _resolveCardField(it);
  if (k === 'get') {
    if (f === 'ITEMINFO_60') return { kind: 'getversion', ver_type: 'ITEMINFO', slot_code: '4', chk_data: '', chk_data2: '', ref_var: it.ref_var || 'sf60ISN' };
    if (f === 'ITEMINFO_80') return { kind: 'getversion', ver_type: 'ITEMINFO', slot_code: '5', chk_data: '', chk_data2: '', ref_var: it.ref_var || 'sf80ISN' };
    if (f === 'SSN') return { kind: 'getversion', ver_type: 'ISN_BASEINFO', slot_code: '3', chk_data: 'SSN', chk_data2: '', ref_var: it.ref_var || 'sfSSN' };
    return { kind: 'getversion', ver_type: 'ISN_BASEINFO', slot_code: '2', chk_data: f, chk_data2: '', ref_var: it.ref_var || ('sf_' + f.replace(/[^A-Za-z0-9_]/g, '')) };
  }
  if (k === 'savelink') {
    return { kind: 'savelink', save_key: f, save_val: it.save_val || 'TEST_VAL' };
  }
  if (k === 'rw') {
    return { kind: 'rw', save_key: f, save_val: it.save_val || 'TEST_VAL', ref_var: it.ref_var || ('sf_' + f.replace(/[^A-Za-z0-9_]/g, '')) };
  }
  if (k === 'clear') {
    return { kind: 'clear', save_key: f };
  }
  if (k === 'login') {
    return { kind: String(it.login_status || '1') === '0' ? 'logout' : 'login' };
  }
  return { kind: k };
}

function _buildCardExcelPreview(it) {
  if (!it) return '';
  const k = it.kind;
  const f = _resolveCardField(it);
  if (k === 'login') {
    return String(it.login_status || '1') === '0'
      ? 'SOAP: WTSP_LOGINOUT(status=0 登出) — Centimani 內建系統管理'
      : 'SOAP: WTSP_LOGINOUT(status=1 登入) — System.ini [SFIS] SFIS_AutoLogin=1';
  }
  if (k === 'checkroute') return ':ShowISN,"*(ISN)" ➔ :SfCheckRoute  |  ExecMode: 8';
  if (k === 'get') {
    const st = _itemToBackendStep(it);
    return `:SfGetVersion,"*(ISN)","${st.ver_type}","${st.slot_code}","${st.chk_data}",""  ➔  $${st.ref_var}  |  EM: 8`;
  }
  if (k === 'savelink') return `:SfSaveLinkData,"${f}","${it.save_val || 'TEST_VAL'}"  |  EM: 8`;
  if (k === 'rw') return `:SfSaveLinkData,"${f}","${it.save_val || 'TEST_VAL'}" ➔ :SfGetVersion(...,"${f}","")  |  EM: 8`;
  if (k === 'clear') return `:SfSaveLinkData,"${f}","" (試寫空值) + 回讀確認`;
  return '';
}

function switchToolsVerifyTab(subTab) {
  SFIS_HMI_STATE.activeSubTab = (subTab === 'dll') ? 'dll' : 'sfis';
  const sfisPane = document.getElementById('toolsSubPaneSfis');
  const dllPane = document.getElementById('toolsSubPaneDll');
  const btnSfis = document.getElementById('btnToolsTabSfis');
  const btnDll = document.getElementById('btnToolsTabDll');
  if (sfisPane) sfisPane.style.display = (SFIS_HMI_STATE.activeSubTab === 'sfis') ? 'block' : 'none';
  if (dllPane) dllPane.style.display = (SFIS_HMI_STATE.activeSubTab === 'dll') ? 'block' : 'none';
  if (btnSfis) btnSfis.className = 'source-mode-tab' + (SFIS_HMI_STATE.activeSubTab === 'sfis' ? ' active' : '');
  if (btnDll) btnDll.className = 'source-mode-tab' + (SFIS_HMI_STATE.activeSubTab === 'dll' ? ' active' : '');
  if (SFIS_HMI_STATE.activeSubTab === 'sfis') renderSfisHmiWorkspace();
}

function sfisSelectPlant(plantId) {
  const p = SFIS_PLANT_PRESETS.find(x => x.id === plantId);
  if (!p) return;
  SFIS_HMI_STATE.plantId = p.id;
  SFIS_HMI_STATE.config.url = _getEffectivePlantUrl(p.id);
  SFIS_HMI_STATE.config.device_id = p.defaultDevice;
  SFIS_HMI_STATE.config.tsp = p.defaultTsp;
  renderSfisHmiWorkspace();
}

function sfisSyncConfig(key, val) {
  if (key === 'skip_save_on_fail') {
    SFIS_HMI_STATE.config.skip_save_on_fail = !!val;
    return;
  }
  SFIS_HMI_STATE.config[key] = String(val == null ? '' : val).trim();
  if (key === 'url' && SFIS_HMI_STATE.plantId) {
    _saveCustomPlantUrl(SFIS_HMI_STATE.plantId, SFIS_HMI_STATE.config.url);
  }
  if (['isn', 'device_id', 'op'].includes(key)) {
    const pcDevEl = document.getElementById('sfisPcDevTxt');
    const pcIsnEl = document.getElementById('sfisPcIsnTxt');
    if (pcDevEl) pcDevEl.textContent = SFIS_HMI_STATE.config.device_id || '-';
    if (pcIsnEl) pcIsnEl.textContent = SFIS_HMI_STATE.config.isn || '(未填)';
  }
  sfisRenderLiveExcelPreview();
}

function sfisToggleIsnPool() {
  SFIS_HMI_STATE.showIsnPool = !SFIS_HMI_STATE.showIsnPool;
  renderSfisHmiWorkspace();
}

function sfisPickIsnFromPool(isnVal) {
  const clean = String(isnVal || '').trim();
  if (!clean) return;
  SFIS_HMI_STATE.config.isn = clean;
  renderSfisHmiWorkspace();
}

function sfisImportFromWorkspaceIni() {
  if (typeof STATE === 'undefined' || !STATE.workspace) {
    alert('目前「既有腳本編修」尚未載入任何測試腳本。請先去載入一份包含 System.ini 的專案，或直接選擇上方廠區與貼入一顆測試 ISN。');
    return;
  }
  const ws = STATE.workspace;
  const sys = ws.system_ini || {};
  const glb = (ws.global_ini && ws.global_ini.Settings) ? ws.global_ini.Settings : {};
  const rawLink = String(sys.SFIS_WebLink || '').split(',')[0].trim();
  if (rawLink) SFIS_HMI_STATE.config.url = rawLink;
  if (sys.SFIS_TSP) SFIS_HMI_STATE.config.tsp = String(sys.SFIS_TSP).trim();
  if (sys.StationName) SFIS_HMI_STATE.config.station = String(sys.StationName).trim();
  if (sys.SFIS_SkipSaveResultOnFail !== undefined) {
    SFIS_HMI_STATE.config.skip_save_on_fail = (String(sys.SFIS_SkipSaveResultOnFail).trim() === '1');
  }
  if (glb.DEVID_1) SFIS_HMI_STATE.config.device_id = String(glb.DEVID_1).trim();
  if (ws.project_name) SFIS_HMI_STATE.config.project_name = String(ws.project_name).trim();
  if (sys.SFIS_LoginID) SFIS_HMI_STATE.config.op = String(sys.SFIS_LoginID).trim();
  renderSfisHmiWorkspace();
}

async function toolsCheckSfisLink() {
  const url = String(SFIS_HMI_STATE.config.url || '').trim();
  if (!url) { alert('請先選擇廠區或輸入 SFIS_WebLink 網址'); return; }
  SFIS_HMI_STATE.anim.phase = 'sending';
  SFIS_HMI_STATE.anim.actionLabel = '正在檢查測試機台 ➔ SFIS WebLink HTTP 連通狀態...';
  SFIS_HMI_STATE.anim.sentPacketText = `HTTP GET/HEAD 連通預檢\nURL: ${url}`;
  renderSfisHmiWorkspace();
  try {
    const res = await fetch('/api/check_sfis_weblink', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const d = await res.json();
    SFIS_HMI_STATE.anim.netConnected = !!d.reachable;
    SFIS_HMI_STATE.anim.phase = d.reachable ? 'pass' : 'offline';
    SFIS_HMI_STATE.anim.actionLabel = d.reachable
      ? `✅ 機台與 SFIS Server 連通正常 (HTTP ${d.http_code})`
      : `⚠️ 機台無法連通該 SFIS IP（可能不在廠區內網）`;
    SFIS_HMI_STATE.anim.recvSummary = d.reachable ? `連通成功 (HTTP ${d.http_code})` : '離線 / 無法連線';
    SFIS_HMI_STATE.anim.recvRawText = d.message || (d.reachable ? 'HTTP 200 OK' : 'Connection failed');
  } catch (e) {
    SFIS_HMI_STATE.anim.netConnected = false;
    SFIS_HMI_STATE.anim.phase = 'offline';
    SFIS_HMI_STATE.anim.recvRawText = String(e);
  }
  renderSfisHmiWorkspace();
}

function sfisAddItem(kind, insertAt = -1) {
  const uid = 'sf_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
  let item = { uid, kind, status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' };
  if (kind === 'login') {
    item.login_status = '1';
  } else if (kind === 'get') {
    item.field_key = 'SNA';
    item.custom_field = '';
    item.ref_var = 'sfSNA';
  } else if (kind === 'savelink') {
    item.field_key = 'SNA';
    item.custom_field = '';
    item.save_val = 'TEST_VAL_01';
  } else if (kind === 'rw') {
    item.field_key = 'SNB';
    item.custom_field = '';
    item.save_val = 'TEST_RW_01';
    item.ref_var = 'sfSNB';
  } else if (kind === 'clear') {
    item.field_key = 'SNA';
    item.custom_field = '';
  }
  if (insertAt >= 0 && insertAt <= SFIS_HMI_STATE.items.length) {
    SFIS_HMI_STATE.items.splice(insertAt, 0, item);
  } else {
    SFIS_HMI_STATE.items.push(item);
  }
  renderSfisHmiWorkspace();
}

function sfisRemoveItem(idx) {
  SFIS_HMI_STATE.items.splice(idx, 1);
  renderSfisHmiWorkspace();
}

function sfisUpdateItemField(idx, field, value) {
  const it = SFIS_HMI_STATE.items[idx];
  if (!it) return;
  it[field] = value;
  if (field === 'field_key' && value !== '__CUSTOM__') {
    const clean = String(value || 'Data').replace(/^ITEMINFO_/, 'Item').replace(/[^A-Za-z0-9_]/g, '');
    it.ref_var = 'sf' + clean;
  }
  it.status = 'idle';
  it.resultMsg = '';
  if (field === 'field_key' || field === 'login_status') {
    renderSfisHmiWorkspace();
  } else {
    const prevEl = document.getElementById(`sfisCardPrev_${idx}`);
    if (prevEl) prevEl.textContent = _buildCardExcelPreview(it);
    sfisRenderLiveExcelPreview();
  }
}

function sfisDragCatalogStart(kind, ev) {
  SFIS_HMI_STATE.dragCatalogKind = kind;
  SFIS_HMI_STATE.dragSrcIdx = -1;
  if (ev && ev.dataTransfer) {
    ev.dataTransfer.effectAllowed = 'copy';
    ev.dataTransfer.setData('text/plain', 'catalog:' + kind);
  }
}

function sfisDragItemStart(idx, ev) {
  SFIS_HMI_STATE.dragSrcIdx = idx;
  SFIS_HMI_STATE.dragCatalogKind = '';
  if (ev && ev.dataTransfer) {
    ev.dataTransfer.effectAllowed = 'move';
    ev.dataTransfer.setData('text/plain', 'item:' + idx);
  }
}

function sfisDropOnTrack(targetIdx, ev) {
  if (ev) { ev.preventDefault(); ev.stopPropagation(); }
  const cKind = SFIS_HMI_STATE.dragCatalogKind;
  const srcIdx = SFIS_HMI_STATE.dragSrcIdx;
  SFIS_HMI_STATE.dragCatalogKind = '';
  SFIS_HMI_STATE.dragSrcIdx = -1;
  if (cKind) {
    sfisAddItem(cKind, targetIdx);
    return;
  }
  if (srcIdx >= 0 && srcIdx !== targetIdx && srcIdx < SFIS_HMI_STATE.items.length) {
    const moved = SFIS_HMI_STATE.items.splice(srcIdx, 1)[0];
    const dest = (targetIdx > srcIdx) ? Math.max(0, targetIdx - 1) : targetIdx;
    SFIS_HMI_STATE.items.splice(dest, 0, moved);
    renderSfisHmiWorkspace();
  }
}

async function _callSingleSoap(action, extraParams = {}) {
  const cfg = SFIS_HMI_STATE.config;
  const resp = await fetch('/api/sfis_soap_test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      url: cfg.url,
      action,
      params: {
        device: cfg.device_id,
        isn: cfg.isn,
        tsp: cfg.tsp,
        op: cfg.op,
        ...extraParams
      }
    })
  });
  return await resp.json();
}

function _recordAnimResult(stepTitle, sentCmd, soapData) {
  const ok = !!soapData.passed;
  const offline = !soapData.reachable || soapData.status === 'offline';
  SFIS_HMI_STATE.anim.netConnected = offline ? false : true;
  SFIS_HMI_STATE.anim.phase = offline ? 'offline' : (ok ? 'pass' : 'fail');
  const slots = soapData.slots || {};
  const valStr = slots.P_CAVER || slots.P_CBVER || slots.P_CCVER || '';
  if (valStr) SFIS_HMI_STATE.anim.lastFieldVal = valStr;
  SFIS_HMI_STATE.anim.sentPacketText = sentCmd;
  const lines = [
    `[P_RET] = ${soapData.ret_code ?? '-'}  (${ok ? 'PASS / 成功' : (offline ? 'OFFLINE / 離線' : 'FAIL / 失敗')})`,
    `[P_Msg] = ${soapData.msg || '-'}`,
  ];
  if (valStr) lines.push(`[讀回主欄位 P_CAVER] = ${valStr}`);
  const extraSlots = Object.entries(slots).filter(([, v]) => v).map(([k, v]) => `${k}=${v}`).join('  |  ');
  if (extraSlots) lines.push(`[完整槽位] ${extraSlots}`);
  if (soapData.raw_result) lines.push(`[伺服器吐回原字串]\n${soapData.raw_result}`);
  SFIS_HMI_STATE.anim.recvRawText = lines.join('\n');
  SFIS_HMI_STATE.anim.recvSummary = offline
    ? '無法連線廠區內網'
    : (ok ? (valStr ? `✅ 成功 · 回傳值：${valStr}` : `✅ ${soapData.msg || 'PASS'}`) : `❌ ${soapData.msg || 'FAIL'}`);
  SFIS_HMI_STATE.anim.actionLabel = `${stepTitle} ➔ ${SFIS_HMI_STATE.anim.recvSummary}`;

  const timeStr = new Date().toLocaleTimeString('zh-TW', { hour12: false });
  SFIS_HMI_STATE.anim.history.unshift({
    time: timeStr,
    title: stepTitle,
    ok,
    offline,
    sent: sentCmd,
    recv: SFIS_HMI_STATE.anim.recvRawText,
    summary: SFIS_HMI_STATE.anim.recvSummary
  });
  if (SFIS_HMI_STATE.anim.history.length > 8) SFIS_HMI_STATE.anim.history.length = 8;
}

function sfisSelectHistory(idx) {
  const h = SFIS_HMI_STATE.anim.history[idx];
  if (!h) return;
  SFIS_HMI_STATE.anim.sentPacketText = h.sent;
  SFIS_HMI_STATE.anim.recvRawText = h.recv;
  SFIS_HMI_STATE.anim.recvSummary = h.summary;
  SFIS_HMI_STATE.anim.phase = h.offline ? 'offline' : (h.ok ? 'pass' : 'fail');
  renderSfisHmiWorkspace();
}

function sfisCopyRecvString() {
  const txt = SFIS_HMI_STATE.anim.recvRawText || '';
  if (!txt) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(txt).then(() => {
      const btn = document.getElementById('sfisBtnCopyRecv');
      if (btn) { btn.textContent = '✅ 已複製'; setTimeout(() => { btn.textContent = '📋 複製吐出字串'; }, 1200); }
    });
  }
}

async function sfisHmiRunStep(idx) {
  const it = SFIS_HMI_STATE.items[idx];
  if (!it) return true;
  const meta = _getBlockMeta(it.kind);
  const f = _resolveCardField(it);
  const isn = SFIS_HMI_STATE.config.isn || '(空)';

  if ((it.kind === 'savelink' || it.kind === 'rw') && it.status === 'idle') {
    const okConfirm = confirm(
      `⚠️ 單顆 ISN 寫入保護確認\n\n` +
      `即將對「目前唯一選中 ISN：${isn}」寫入：\n` +
      `• 欄位：#SAVE:${f}\n• 寫入值：${it.save_val || 'TEST_VAL'}\n\n` +
      `（注意：部分廠區 SFIS 在 WTSP_RESULT 成功後可能會推站或消耗這顆測試 ISN，確定現在送出嗎？）`
    );
    if (!okConfirm) return false;
  }

  it.status = 'running';
  it.resultMsg = '通訊傳輸中...';
  SFIS_HMI_STATE.anim.phase = 'sending';
  SFIS_HMI_STATE.anim.actionLabel = `PC 正在透過 SOAP 送出：${meta.title}...`;
  renderSfisHmiWorkspace();

  try {
    let data = {};
    let sentCmd = '';

    if (it.kind === 'login') {
      const stCode = String(it.login_status || '1') === '0' ? 0 : 1;
      sentCmd = `WTSP_LOGINOUT(op="${SFIS_HMI_STATE.config.op}", device="${SFIS_HMI_STATE.config.device_id}", status=${stCode} [${stCode === 1 ? 'Login登入' : 'Logout登出'}])`;
      data = await _callSingleSoap('WTSP_LOGINOUT', { status: stCode });
      if (data.passed) SFIS_HMI_STATE.anim.opLoggedIn = (stCode === 1);
      else if (data.reachable) SFIS_HMI_STATE.anim.opLoggedIn = false;
    } else if (it.kind === 'checkroute') {
      sentCmd = `WTSP_CHKROUTE(ISN="${isn}", device="${SFIS_HMI_STATE.config.device_id}")\nCentimani: :ShowISN,"*(ISN)" ➔ :SfCheckRoute`;
      data = await _callSingleSoap('WTSP_CHKROUTE', { checkFlag: '1', checkData: '', route_type: 1 });
    } else if (it.kind === 'get' || it.kind === 'getversion') {
      const st = _itemToBackendStep(it);
      sentCmd = `WTSP_GETVERSION(ISN="${isn}", type="${st.ver_type}", ChkData="${st.chk_data}")\nCentimani: :SfGetVersion,"*(ISN)","${st.ver_type}","${st.slot_code}","${st.chk_data}",""`;
      data = await _callSingleSoap('WTSP_GETVERSION', { ver_type: st.ver_type, chk_data: st.chk_data, chk_data2: st.chk_data2 });
    } else if (it.kind === 'getimac') {
      sentCmd = `WTSP_GETIMAC(ISN="${isn}", device="${SFIS_HMI_STATE.config.device_id}", imacnum=1)`;
      data = await _callSingleSoap('WTSP_GETIMAC', { imacnum: 1 });
    } else if (it.kind === 'savelink') {
      const val = it.save_val || 'TEST_VAL';
      sentCmd = `WTSP_RESULT(ISN="${isn}", data="#SAVE:${f}=${val};", status=1, TSP="PASS")\nCentimani: :SfSaveLinkData,"${f}","${val}"`;
      data = await _callSingleSoap('WTSP_RESULT', { save_key: f, save_val: val, status: 1, result_tsp: 'PASS' });
    } else if (it.kind === 'rw') {
      const val = it.save_val || 'TEST_RW_01';
      sentCmd = `[1/2 寫入] WTSP_RESULT(#SAVE:${f}=${val})\n[2/2 回讀] WTSP_GETVERSION(ISN_BASEINFO, ChkData="${f}")`;
      const wr = await _callSingleSoap('WTSP_RESULT', { save_key: f, save_val: val, status: 1, result_tsp: 'PASS' });
      if (!wr.passed) {
        data = wr;
      } else {
        SFIS_HMI_STATE.anim.actionLabel = '寫入完成，正在發送第 2 步 GET 回讀比對...';
        renderSfisHmiWorkspace();
        const rd = await _callSingleSoap('WTSP_GETVERSION', { ver_type: 'ISN_BASEINFO', chk_data: f, chk_data2: '' });
        const got = (rd.slots && rd.slots.P_CAVER) ? rd.slots.P_CAVER : '';
        const matchOk = rd.passed && (got === val);
        data = {
          ...rd,
          passed: matchOk,
          msg: matchOk ? `寫入 [${val}] 與回讀 [${got}] 完全一致！` : `寫入 [${val}]，但回讀到 [${got || rd.msg || '空'}]`
        };
      }
    } else if (it.kind === 'clear') {
      sentCmd = `[1/2 試清] WTSP_RESULT(#SAVE:${f}=; status=1)\n[2/2 確認] WTSP_GETVERSION(ISN_BASEINFO, ChkData="${f}")`;
      const wr = await _callSingleSoap('WTSP_RESULT', { data: `#SAVE:${f}=;`, status: 1, result_tsp: 'PASS' });
      if (!wr.passed) {
        data = wr;
      } else {
        const rd = await _callSingleSoap('WTSP_GETVERSION', { ver_type: 'ISN_BASEINFO', chk_data: f, chk_data2: '' });
        const got = (rd.slots && rd.slots.P_CAVER) ? rd.slots.P_CAVER : '';
        data = { ...rd, msg: `清除後回讀值為 [${got || '(空/NULL)'}]` };
      }
    }

    const ok = !!data.passed;
    const offline = !data.reachable || data.status === 'offline';
    it.status = offline ? 'offline' : (ok ? 'pass' : 'fail');
    const slots = data.slots || {};
    const valStr = slots.P_CAVER || slots.P_CBVER || '';
    it.resultMsg = offline
      ? '無法連網'
      : (ok ? (valStr ? `✅ 值：${valStr}` : `✅ ${data.msg || 'PASS'}`) : `❌ ${data.msg || 'FAIL'}`);
    it.lastRaw = data.raw_result || data.msg || '';
    it.sentCmd = sentCmd;
    _recordAnimResult(meta.title, sentCmd, data);
    renderSfisHmiWorkspace();
    return ok;
  } catch (e) {
    it.status = 'fail';
    it.resultMsg = String(e);
    SFIS_HMI_STATE.anim.phase = 'fail';
    SFIS_HMI_STATE.anim.recvRawText = String(e);
    renderSfisHmiWorkspace();
    return false;
  }
}

async function sfisHmiRunAll() {
  if (SFIS_HMI_STATE.isRunning) return;
  const hasWrite = SFIS_HMI_STATE.items.some(it => it.kind === 'savelink' || it.kind === 'rw');
  const isn = SFIS_HMI_STATE.config.isn || '(空)';
  if (hasWrite) {
    const okC = confirm(
      `⚠️ 單顆 ISN 順序實測確認\n\n` +
      `本次只會對單一選中的 ISN [${isn}] 依序執行右側 ${SFIS_HMI_STATE.items.length} 個步驟（包含寫入步驟）。\n` +
      `確定要對這 1 顆 ISN 執行全部步驟嗎？`
    );
    if (!okC) return;
  }
  SFIS_HMI_STATE.isRunning = true;
  renderSfisHmiWorkspace();
  try {
    for (let i = 0; i < SFIS_HMI_STATE.items.length; i++) {
      // Bypass double-confirm per step inside RunAll
      const it = SFIS_HMI_STATE.items[i];
      if (it.status === 'idle' && (it.kind === 'savelink' || it.kind === 'rw')) it.status = 'running';
      const ok = await sfisHmiRunStep(i);
      if (!ok) break;
    }
  } finally {
    SFIS_HMI_STATE.isRunning = false;
    renderSfisHmiWorkspace();
  }
}

async function sfisHmiExport(mode) {
  const cfg = SFIS_HMI_STATE.config;
  const itemsPayload = SFIS_HMI_STATE.items.map(_itemToBackendStep);
  const nonLogin = itemsPayload.filter(x => x.kind !== 'login' && x.kind !== 'logout');
  if (nonLogin.length === 0) {
    alert('右側至少需要 1 張會產出 Excel 步驟的積木（CheckRoute / GET / WRITE / R/W），OP Login 僅供電腦測試與 System.ini 設定。');
    return;
  }
  if (mode === 'insert_current' && (typeof STATE === 'undefined' || !STATE.workspace)) {
    alert('目前尚未開啟任何測試腳本，請改點「📥 抄空白範本產生 SFIS Excel (.xlsx)」。');
    return;
  }
  try {
    const res = await fetch('/api/export_sfis_hmi_script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        items: itemsPayload,
        config: cfg,
        workspace: (mode === 'insert_current' && typeof STATE !== 'undefined') ? STATE.workspace : null
      })
    });
    const data = await res.json();
    if (data.status !== 'ok') {
      alert('匯出失敗：' + (data.message || '未知錯誤'));
      return;
    }
    if (mode === 'insert_current') {
      STATE.workspace = data.workspace;
      STATE.report = data.report;
      if (typeof renderStations === 'function') renderStations();
      if (typeof renderAuditAlerts === 'function') renderAuditAlerts();
      if (typeof switchGenSubMode === 'function') switchGenSubMode('edit');
      alert(`✅ 已將 ${data.inserted_count} 列 SFIS 標準步驟（含 :ShowISN 與 ExecMode=8）插入 [${data.station}] 開頭！\n(同時已寫入 System.ini: SFIS_SkipSaveResultOnFail=${cfg.skip_save_on_fail ? 1 : 0})`);
      return;
    }
    const skipStr = cfg.skip_save_on_fail ? '1（測錯故意不上傳）' : '0';
    alert(
      `✅ 已抄空白母體範本產出專屬 SFIS Excel 驗證檔！\n\n` +
      `• Excel 路徑：${data.excel_path}\n` +
      `• System.ini：SFIS_SkipSaveResultOnFail=${skipStr} + 64碼 Checksum 已簽章\n` +
      `• 健檢結果：${data.audit_report.error_count} Error / ${data.audit_report.warning_count} Warning`
    );
  } catch (e) {
    alert('匯出發生錯誤：' + e);
  }
}

function _renderSfisAnimStageHtml() {
  const s = SFIS_HMI_STATE;
  const a = s.anim;
  const plantObj = SFIS_PLANT_PRESETS.find(x => x.id === s.plantId) || SFIS_PLANT_PRESETS[1];
  const isSending = (a.phase === 'sending');
  const isPass = (a.phase === 'pass');
  const isFail = (a.phase === 'fail');
  const isOffline = (a.phase === 'offline');

  const netColor = a.netConnected === true ? '#16A34A' : (a.netConnected === false ? '#DC2626' : '#94A3B8');
  const opText = a.opLoggedIn === true ? '✅ 已登入' : (a.opLoggedIn === false ? '⬜ 未登入/已登出' : '⏳ 待測 Login');
  const opColor = a.opLoggedIn === true ? '#15803D' : (a.opLoggedIn === false ? '#64748B' : '#94A3B8');
  const dbLedColor = isPass ? '#16A34A' : (isFail ? '#DC2626' : (isOffline ? '#D97706' : '#94A3B8'));
  const lineClass = isSending ? 'sfis-flow-line sending' : (isPass ? 'sfis-flow-line pass' : (isFail ? 'sfis-flow-line fail' : 'sfis-flow-line'));

  const histChips = a.history.length ? a.history.map((h, i) => `
    <button type="button" onclick="sfisSelectHistory(${i})" style="padding:2px 8px; border-radius:999px; font-size:0.75rem; border:1px solid ${h.ok ? '#86EFAC' : '#FCA5A5'}; background:${h.ok ? '#F0FDF4' : '#FEF2F2'}; color:${h.ok ? '#166534' : '#991B1B'}; cursor:pointer; font-weight:700;">
      ${h.time} ${h.ok ? '✅' : '❌'} ${_escH(h.title)}
    </button>
  `).join('') : '<span style="font-size:0.76rem; color:#94A3B8;">尚無操作紀錄</span>';

  return `
    <div style="background:linear-gradient(135deg,#F8FAFC 0%,#EFF6FF 100%); border:1.5px solid #BFDBFE; border-radius:12px; padding:12px 14px; margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
        <div style="font-weight:900; font-size:0.95rem; color:#0F172A;">
          🖥️ 測試 PC ⇄ 雙向雲端 ⇄ SFIS 廠區資料庫（即時動畫模擬台）
        </div>
        <span style="padding:3px 10px; border-radius:999px; font-size:0.8rem; font-weight:800; background:${isPass ? '#DCFCE7' : (isFail ? '#FEE2E2' : (isOffline ? '#FEF3C7' : (isSending ? '#DBEAFE' : '#E2E8F0')))}; color:${isPass ? '#166534' : (isFail ? '#991B1B' : (isOffline ? '#92400E' : (isSending ? '#1D4ED8' : '#334155')))};">
          ${_escH(a.actionLabel)}
        </span>
      </div>

      <!-- 3 節點圖解動畫舞台 -->
      <div class="sfis-anim-stage">
        <!-- 左：產線測試電腦 PC.png -->
        <div class="sfis-node-card ${isSending ? 'pulse-blue' : (isPass ? 'glow-green' : (isFail ? 'glow-red' : ''))}">
          <img src="/images/PC.png" alt="Test PC" style="width:74px; height:74px; object-fit:contain;">
          <div style="font-weight:900; font-size:0.86rem; color:#0F172A; margin-top:4px;">產線測試 PC</div>
          <div style="font-size:0.75rem; color:#334155; display:flex; flex-direction:column; gap:2px; align-items:center; margin-top:4px;">
            <span><i class="sfis-led" style="background:${netColor};"></i> 網路：${a.netConnected === true ? '已通' : (a.netConnected === false ? '未通' : '待測')}</span>
            <span style="color:${opColor}; font-weight:800;">${opText}</span>
            <span class="mono" style="background:#F1F5F9; padding:1px 6px; border-radius:4px;">Dev: <b id="sfisPcDevTxt">${_escH(s.config.device_id)}</b></span>
            <span class="mono" style="background:#FEF9C3; color:#854D0E; padding:1px 6px; border-radius:4px; max-width:165px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${_escH(s.config.isn)}">ISN: <b id="sfisPcIsnTxt">${_escH(s.config.isn || '未填')}</b></span>
          </div>
        </div>

        <!-- 管線 1 -->
        <div class="${lineClass}">
          <span class="sfis-flow-label">${isSending ? '⬆ 送出 SOAP' : (isPass ? '✅ 回傳完成' : 'HTTP POST')}</span>
          <div class="sfis-flow-rail"><span class="sfis-packet"></span></div>
        </div>

        <!-- 中：雙向通道雲 cloud.png -->
        <div class="sfis-node-card sfis-cloud-card ${isSending ? 'cloud-active' : ''}">
          <img src="/images/cloud.png" alt="Bidirectional Cloud" style="width:78px; height:64px; object-fit:contain;">
          <div style="display:flex; gap:6px; margin-top:4px; font-size:0.74rem; font-weight:800;">
            <span style="padding:1px 6px; border-radius:4px; background:${isSending ? '#DBEAFE' : '#F1F5F9'}; color:${isSending ? '#1D4ED8' : '#64748B'};">⬆ 上行請求</span>
            <span style="padding:1px 6px; border-radius:4px; background:${isPass ? '#DCFCE7' : (isFail ? '#FEE2E2' : '#F1F5F9')}; color:${isPass ? '#15803D' : (isFail ? '#B91C1C' : '#64748B')};">⬇ 吐回字串</span>
          </div>
          <div style="font-size:0.74rem; color:#475569; margin-top:3px;">WebService SOAP 通道</div>
        </div>

        <!-- 管線 2 -->
        <div class="${lineClass}">
          <span class="sfis-flow-label">${isSending ? '寫入/查詢 ➔' : (a.lastFieldVal ? '資料回流' : 'DB 查詢')}</span>
          <div class="sfis-flow-rail"><span class="sfis-packet delay"></span></div>
        </div>

        <!-- 右：SFIS 廠區資料庫 database.png -->
        <div class="sfis-node-card ${isPass ? 'glow-green' : (isFail || isOffline ? 'glow-red' : '')}">
          <img src="/images/database.png" alt="SFIS Database" style="width:66px; height:74px; object-fit:contain;">
          <div style="font-weight:900; font-size:0.86rem; color:#0F172A; margin-top:4px;">SFIS 資料庫</div>
          <div style="font-size:0.75rem; color:#334155; display:flex; flex-direction:column; gap:2px; align-items:center; margin-top:4px;">
            <span style="font-weight:800; color:#1D4ED8;">${_escH(plantObj.label)}</span>
            <span><i class="sfis-led" style="background:${dbLedColor};"></i> ${_escH(a.recvSummary)}</span>
            ${a.lastFieldVal ? `<span class="mono" style="background:#DCFCE7; color:#166534; padding:1px 6px; border-radius:4px; max-width:165px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">值: ${_escH(a.lastFieldVal)}</span>` : ''}
          </div>
        </div>
      </div>

      <!-- 正下方：對應吐出字串清晰對照監控欄 -->
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:8px; margin-top:10px;">
        <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:8px 10px;">
          <div style="font-size:0.78rem; font-weight:800; color:#1E40AF; margin-bottom:4px;">📤 送出的指令與參數（Request）</div>
          <pre class="mono" style="margin:0; font-size:0.78rem; color:#0F172A; white-space:pre-wrap; word-break:break-all; max-height:84px; overflow:auto;">${_escH(a.sentPacketText)}</pre>
        </div>
        <div style="background:#0F172A; border:1px solid #334155; border-radius:8px; padding:8px 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-size:0.78rem; font-weight:800; color:#38BDF8;">📥 SFIS 實際吐回字串 &amp; 欄位結果（Response）</span>
            <button id="sfisBtnCopyRecv" type="button" onclick="sfisCopyRecvString()" style="padding:1px 7px; font-size:0.72rem; border-radius:4px; border:1px solid #475569; background:#1E293B; color:#E2E8F0; cursor:pointer;">📋 複製吐出字串</button>
          </div>
          <pre class="mono" style="margin:0; font-size:0.8rem; color:${isPass ? '#86EFAC' : (isFail || isOffline ? '#FCA5A5' : '#E2E8F0')}; white-space:pre-wrap; word-break:break-all; max-height:92px; overflow:auto;">${_escH(a.recvRawText)}</pre>
        </div>
      </div>

      <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:8px;">
        <span style="font-size:0.76rem; font-weight:800; color:#475569;">最近實測紀錄：</span>
        ${histChips}
      </div>
    </div>
  `;
}

function _renderSimpleCardInputs(it, idx) {
  if (it.kind === 'login') {
    const isOut = (String(it.login_status || '1') === '0');
    return `
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <label style="display:inline-flex; align-items:center; gap:4px; cursor:pointer; font-size:0.82rem; font-weight:700; padding:3px 9px; border-radius:6px; border:1px solid ${!isOut ? '#0284C7' : '#CBD5E1'}; background:${!isOut ? '#E0F2FE' : '#FFFFFF'};">
          <input type="radio" name="sfisLoginMod_${idx}" value="1" ${!isOut ? 'checked' : ''} onchange="sfisUpdateItemField(${idx},'login_status','1')"> 🔐 Login 登入
        </label>
        <label style="display:inline-flex; align-items:center; gap:4px; cursor:pointer; font-size:0.82rem; font-weight:700; padding:3px 9px; border-radius:6px; border:1px solid ${isOut ? '#0284C7' : '#CBD5E1'}; background:${isOut ? '#E0F2FE' : '#FFFFFF'};">
          <input type="radio" name="sfisLoginMod_${idx}" value="0" ${isOut ? 'checked' : ''} onchange="sfisUpdateItemField(${idx},'login_status','0')"> 🚪 Logout 登出
        </label>
        <span style="font-size:0.78rem; color:#475569;">使用上方 OP 工號 (${_escH(SFIS_HMI_STATE.config.op)}) 與 DeviceID (${_escH(SFIS_HMI_STATE.config.device_id)})</span>
      </div>`;
  }
  if (it.kind === 'checkroute') {
    return `<div style="font-size:0.81rem; color:#334155;">免填其他設定，自動以目前單顆 ISN + DeviceID 檢查途程。</div>`;
  }

  const fk = it.field_key || it.save_key || it.chk_data || 'SNA';
  const isCustom = (fk === '__CUSTOM__');
  const opts = SFIS_PROXY_FIELDS.map(p => `<option value="${p.key}" ${fk === p.key ? 'selected' : ''}>${_escH(p.label)}</option>`).join('') +
    `<option value="__CUSTOM__" ${isCustom ? 'selected' : ''}>✏️ 自填其他欄位名稱...</option>`;

  const fieldSelectHtml = `
    <label style="font-size:0.79rem; font-weight:700; color:#334155;">目標欄位：
      <select onchange="sfisUpdateItemField(${idx},'field_key',this.value)" style="padding:4px 6px; border:1px solid #94A3B8; border-radius:5px; font-size:0.81rem;">${opts}</select>
    </label>
    ${isCustom ? `<input type="text" value="${_escH(it.custom_field || '')}" placeholder="例：BT1 / SN1" oninput="sfisUpdateItemField(${idx},'custom_field',this.value)" class="mono" style="width:120px; padding:4px 6px; border:1px solid #94A3B8; border-radius:5px; font-size:0.81rem;">` : ''}
  `;

  if (it.kind === 'get' || it.kind === 'getversion') {
    return `<div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">${fieldSelectHtml}<span style="font-size:0.77rem; color:#047857;">✅ 無限次唯讀，直接顯示回傳字串</span></div>`;
  }
  if (it.kind === 'savelink' || it.kind === 'rw') {
    return `
      <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
        ${fieldSelectHtml}
        <label style="font-size:0.79rem; font-weight:700; color:#334155;">寫入值：
          <input type="text" value="${_escH(it.save_val || '')}" placeholder="例：TEST_001" oninput="sfisUpdateItemField(${idx},'save_val',this.value)" class="mono" style="width:170px; padding:4px 7px; border:1px solid #94A3B8; border-radius:5px; font-size:0.81rem;">
        </label>
      </div>`;
  }
  if (it.kind === 'clear') {
    return `
      <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
        ${fieldSelectHtml}
        <span style="font-size:0.76rem; color:#64748B;">送空字串嘗試清除；若該站已被推站，需請 PE 在廠端電腦重清 ISN</span>
      </div>`;
  }
  return '';
}

function sfisRenderLiveExcelPreview() {
  const preEl = document.getElementById('sfisLiveExcelPreview');
  if (!preEl) return;
  const rows = SFIS_HMI_STATE.items.map(_buildCardExcelPreview).filter(Boolean);
  preEl.textContent = rows.length ? rows.join('\n') : '（尚未加入驗證步驟）';
}

function renderSfisHmiWorkspace() {
  const root = document.getElementById('toolsSubPaneSfis');
  if (!root) return;
  const s = SFIS_HMI_STATE;
  const cfg = s.config;
  const curPlant = SFIS_PLANT_PRESETS.find(p => p.id === s.plantId) || SFIS_PLANT_PRESETS[0];

  const plantButtons = SFIS_PLANT_PRESETS.map(p => {
    const active = (s.plantId === p.id);
    return `<button type="button" onclick="sfisSelectPlant('${p.id}')" class="btn" style="padding:4px 10px; font-size:0.81rem; border-radius:999px; ${active ? 'background:#1D4ED8; color:#FFFFFF; border-color:#1D4ED8; font-weight:800;' : 'background:#FFFFFF; color:#334155; border-color:#CBD5E1;'}">${_escH(p.label)}</button>`;
  }).join('');

  const catalogHtml = SFIS_CATALOG_BLOCKS.map(b => `
    <div draggable="true" ondragstart="sfisDragCatalogStart('${b.kind}', event)"
         style="background:${b.bg}; border:1.5px solid ${b.border}; border-radius:8px; padding:8px 10px; cursor:grab; display:flex; justify-content:space-between; align-items:center; gap:8px;">
      <div style="min-width:0;">
        <div style="font-weight:800; font-size:0.86rem; color:#0F172A;">${b.icon} ${_escH(b.title)}</div>
        <div style="font-size:0.75rem; color:#475569; line-height:1.35; margin-top:2px;">${_escH(b.subtitle)}</div>
        <div style="font-size:0.71rem; color:${b.theme}; font-weight:700; margin-top:2px;">${_escH(b.safeNote)}</div>
      </div>
      <button type="button" onclick="sfisAddItem('${b.kind}')" class="btn" style="padding:4px 9px; font-size:0.8rem; background:#FFFFFF; color:${b.theme}; border-color:${b.border}; font-weight:800; flex-shrink:0;">＋加入</button>
    </div>
  `).join('');

  const trackCardsHtml = s.items.map((it, idx) => {
    const meta = _getBlockMeta(it.kind);
    const stColor = it.status === 'pass' ? '#16A34A' : (it.status === 'fail' ? '#DC2626' : (it.status === 'offline' ? '#D97706' : (it.status === 'running' ? '#2563EB' : meta.border)));
    const stBadge = it.status === 'pass' ? '<span style="background:#DCFCE7; color:#166534; padding:2px 8px; border-radius:999px; font-size:0.75rem; font-weight:800;">PASS</span>'
      : (it.status === 'fail' ? '<span style="background:#FEE2E2; color:#991B1B; padding:2px 8px; border-radius:999px; font-size:0.75rem; font-weight:800;">FAIL</span>'
      : (it.status === 'offline' ? '<span style="background:#FEF3C7; color:#92400E; padding:2px 8px; border-radius:999px; font-size:0.75rem; font-weight:800;">離線/未連內網</span>'
      : (it.status === 'running' ? '<span style="background:#DBEAFE; color:#1D4ED8; padding:2px 8px; border-radius:999px; font-size:0.75rem; font-weight:800;">傳送中...</span>'
      : '<span style="background:#F1F5F9; color:#64748B; padding:2px 8px; border-radius:999px; font-size:0.75rem;">待測</span>')));

    return `
      <div draggable="true" ondragstart="sfisDragItemStart(${idx}, event)"
           ondragover="event.preventDefault()" ondrop="sfisDropOnTrack(${idx}, event)"
           style="background:#FFFFFF; border:2px solid ${stColor}; border-radius:9px; padding:9px 12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:6px;">
          <div style="display:flex; align-items:center; gap:7px;">
            <span title="拖曳調整順序" style="cursor:grab; color:#94A3B8; font-weight:900;">⠿</span>
            <span style="background:${meta.bg}; color:${meta.theme}; border:1px solid ${meta.border}; padding:1px 7px; border-radius:5px; font-weight:900; font-size:0.78rem;">#${idx + 1}</span>
            <span style="font-weight:900; font-size:0.9rem; color:#0F172A;">${meta.icon} ${_escH(meta.title)}</span>
            ${stBadge}
          </div>
          <div style="display:flex; gap:6px; align-items:center;">
            <button type="button" onclick="sfisHmiRunStep(${idx})" class="btn" style="padding:3px 10px; font-size:0.79rem; background:#ECFDF5; color:#047857; border-color:#6EE7B7; font-weight:800;">⚡ 實測這步</button>
            <button type="button" onclick="sfisRemoveItem(${idx})" class="btn" style="padding:3px 8px; font-size:0.78rem; background:#FEF2F2; color:#DC2626; border-color:#FECACA;">🗑</button>
          </div>
        </div>
        ${_renderSimpleCardInputs(it, idx)}
        ${it.resultMsg ? `<div class="mono" style="margin-top:6px; padding:4px 8px; border-radius:5px; font-size:0.78rem; background:${it.status === 'pass' ? '#F0FDF4' : '#FEF2F2'}; color:${it.status === 'pass' ? '#166534' : '#991B1B'}; border:1px solid ${it.status === 'pass' ? '#BBF7D0' : '#FECACA'};">${_escH(it.resultMsg)}</div>` : ''}
        <div id="sfisCardPrev_${idx}" class="mono" style="margin-top:5px; font-size:0.74rem; color:#64748B;">${_escH(_buildCardExcelPreview(it))}</div>
      </div>`;
  }).join('');

  const poolTokens = String(s.isnPoolText || '').split(/[\r\n,;]+/).map(x => x.trim()).filter(Boolean);
  const poolBtns = poolTokens.map(tok => `
    <button type="button" onclick="sfisPickIsnFromPool('${_escH(tok)}')" style="padding:2px 8px; border-radius:6px; font-size:0.76rem; border:1px solid ${tok === cfg.isn ? '#2563EB' : '#CBD5E1'}; background:${tok === cfg.isn ? '#DBEAFE' : '#FFFFFF'}; color:${tok === cfg.isn ? '#1E40AF' : '#334155'}; font-weight:${tok === cfg.isn ? '800' : '600'}; cursor:pointer;" class="mono">
      ${tok === cfg.isn ? '🎯 ' : ''}${_escH(tok)}
    </button>`).join('');

  root.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid #C7D2FE; border-radius:12px; padding:14px 16px;">
      <!-- 頂部：簡明標題 + 輔助工具 -->
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
        <div>
          <div style="font-weight:900; font-size:1.05rem; color:#1E1B4B;">🌐 SFIS 模擬測試機台人機（安全單顆 ISN 實測 ＋ 空白範本產出 Excel）</div>
          <div style="font-size:0.82rem; color:#475569;">1) 選廠區 / 改 IP ➔ 2) 左拖右放排步驟 ➔ 3) 單顆 ISN 按實測看吐回字串 ➔ 4) 一鍵抄空白範本產生 SFIS Excel</div>
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <button type="button" onclick="sfisImportFromWorkspaceIni()" class="btn" style="padding:5px 11px; font-size:0.81rem; background:#EFF6FF; color:#1D4ED8; border-color:#93C5FD;">📥 帶入現開 INI</button>
          <button type="button" onclick="openCentimaniAuxTool('CentimaniSFISTest.exe')" class="btn" style="padding:5px 11px; font-size:0.81rem; background:#F8FAFC; color:#334155; border-color:#CBD5E1;">🌐 開官方 SFISTest.exe</button>
        </div>
      </div>

      <!-- 廠區快選 + 可自由修正 WebLink -->
      <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:8px;">
        <span style="font-size:0.82rem; font-weight:800; color:#334155;">🏭 廠區快選：</span>
        ${plantButtons}
        <span style="font-size:0.76rem; color:#64748B;">（${_escH(curPlant.hint || '')}）</span>
      </div>

      <!-- 真正必填的連線設定 -->
      <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:9px; padding:10px 12px; margin-bottom:12px;">
        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:8px;">
          <label style="flex:1; min-width:300px; font-size:0.8rem; font-weight:800; color:#334155;">SFIS_WebLink（可直接修改此廠區正確 IP，系統會記住）
            <input type="text" value="${_escH(cfg.url)}" oninput="sfisSyncConfig('url', this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box; font-size:0.84rem; background:#FFFFFF;">
          </label>
          <button type="button" onclick="toolsCheckSfisLink()" class="btn" style="margin-top:16px; padding:7px 14px; font-size:0.83rem; background:#E0F2FE; color:#0369A1; border-color:#7DD3FC; font-weight:800;">🔍 測內網連通</button>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:8px; align-items:end;">
          <label style="font-size:0.79rem; font-weight:800; color:#334155;">DeviceID (6碼)
            <input type="text" value="${_escH(cfg.device_id)}" oninput="sfisSyncConfig('device_id', this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px 7px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box; font-size:0.83rem;">
          </label>
          <label style="font-size:0.79rem; font-weight:800; color:#334155;">OP 工號 (測 Login)
            <input type="text" value="${_escH(cfg.op)}" oninput="sfisSyncConfig('op', this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px 7px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box; font-size:0.83rem;">
          </label>
          <label style="font-size:0.79rem; font-weight:800; color:#9A3412;">🎯 目前實測單顆 ISN（珍貴保護・單次只打這顆）
            <input type="text" value="${_escH(cfg.isn)}" oninput="sfisSyncConfig('isn', this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px 7px; border:1.5px solid #F59E0B; border-radius:5px; box-sizing:border-box; font-size:0.84rem; background:#FFFBEB; font-weight:800;">
          </label>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button type="button" onclick="sfisToggleIsnPool()" class="btn" style="padding:6px 10px; font-size:0.79rem; background:#FEF9C3; color:#854D0E; border-color:#FDE047; font-weight:800;">📋 備用虛擬工單 (${poolTokens.length}顆) ${s.showIsnPool ? '▴' : '▾'}</button>
          </div>
        </div>
        ${s.showIsnPool ? `
          <div style="margin-top:8px; padding:8px 10px; background:#FFFBEB; border:1px solid #FDE68A; border-radius:7px;">
            <div style="font-size:0.77rem; font-weight:800; color:#92400E; margin-bottom:4px;">📋 先貼入工廠給的備用測試 ISN 清單（點擊下列任一顆切換到槍口實測，絕不會整批打光）：</div>
            <div style="display:grid; grid-template-columns:1fr 1.5fr; gap:8px; align-items:start;">
              <textarea rows="3" oninput="SFIS_HMI_STATE.isnPoolText=this.value" onblur="renderSfisHmiWorkspace()" class="mono" placeholder="一行一顆貼入..." style="width:100%; padding:5px 7px; border:1px solid #FCD34D; border-radius:5px; font-size:0.79rem; box-sizing:border-box;">${_escH(s.isnPoolText)}</textarea>
              <div style="display:flex; flex-wrap:wrap; gap:5px;">${poolBtns || '<span style="font-size:0.76rem; color:#94A3B8;">空白</span>'}</div>
            </div>
          </div>` : ''}
        <details style="margin-top:7px;">
          <summary style="cursor:pointer; font-size:0.77rem; font-weight:700; color:#64748B;">⚙️ 進階產出設定（專案名 / 測試站別 / SFIS_TSP，匯出 Excel 用）</summary>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:8px; margin-top:6px;">
            <label style="font-size:0.77rem; font-weight:700; color:#334155;">專案名稱：
              <input type="text" value="${_escH(cfg.project_name)}" oninput="sfisSyncConfig('project_name', this.value)" class="mono" style="width:100%; padding:4px 6px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;">
            </label>
            <label style="font-size:0.77rem; font-weight:700; color:#334155;">工作表站別：
              <input type="text" value="${_escH(cfg.station)}" oninput="sfisSyncConfig('station', this.value)" class="mono" style="width:100%; padding:4px 6px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;">
            </label>
            <label style="font-size:0.77rem; font-weight:700; color:#334155;">SFIS_TSP：
              <input type="text" value="${_escH(cfg.tsp)}" oninput="sfisSyncConfig('tsp', this.value)" class="mono" style="width:100%; padding:4px 6px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;">
            </label>
          </div>
        </details>
      </div>

      <!-- 核心動畫視覺台 -->
      ${_renderSfisAnimStageHtml()}

      <!-- 下方左右雙欄拖曳與執行區 -->
      <div style="display:grid; grid-template-columns:300px 1fr; gap:14px; align-items:start;">
        <!-- 左欄：極簡積木庫 -->
        <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:9px; padding:10px;">
          <div style="font-weight:900; font-size:0.89rem; color:#0F172A; margin-bottom:8px;">🧱 功能積木（左拖到右，或點 ＋加入）</div>
          <div style="display:flex; flex-direction:column; gap:7px;">${catalogHtml}</div>
        </div>

        <!-- 右欄：測試流程跑道 + 產出 Excel -->
        <div style="display:flex; flex-direction:column; gap:10px;">
          <div ondragover="event.preventDefault()" ondrop="sfisDropOnTrack(${s.items.length}, event)"
               style="background:#F8FAFC; border:2px dashed #93C5FD; border-radius:9px; padding:10px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
              <div style="font-weight:900; font-size:0.9rem; color:#1E293B;">🧪 測試電腦執行順序（共 ${s.items.length} 步・可上下拖曳）</div>
              <button type="button" onclick="sfisHmiRunAll()" ${s.isRunning ? 'disabled' : ''} class="btn" style="padding:5px 14px; font-size:0.83rem; background:#059669; color:#FFFFFF; border:none; border-radius:7px; font-weight:800;">
                ${s.isRunning ? '⏳ 模擬執行中...' : '▶ 依序實測目前這 1 顆 ISN'}
              </button>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px;">
              ${trackCardsHtml || '<div style="text-align:center; padding:18px; color:#64748B;">尚未加入步驟，請從左側拖入或點擊「＋加入」</div>'}
            </div>
          </div>

          <!-- 匯出與 INI 安全開關 -->
          <div style="background:#F0FDF4; border:1.5px solid #86EFAC; border-radius:9px; padding:10px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">
              <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.82rem; font-weight:800; color:#166534;">
                <input type="checkbox" ${cfg.skip_save_on_fail ? 'checked' : ''} onchange="sfisSyncConfig('skip_save_on_fail', this.checked)" style="width:15px; height:15px;">
                🛡️ System.ini 加入 <code>SFIS_SkipSaveResultOnFail=1</code>（測試 FAIL 故意不上傳，避免推進或損耗 ISN）
              </label>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">
              <span style="font-weight:800; font-size:0.85rem; color:#14532D;">📝 將測通流程寫入 Excel（空白標準範本 ＋ SFIS 步驟，ExecMode=8）</span>
              <div style="display:flex; gap:8px; flex-wrap:wrap;">
                <button type="button" onclick="sfisHmiExport('new_template')" class="btn" style="padding:6px 13px; font-size:0.82rem; background:#15803D; color:#FFFFFF; border:none; border-radius:7px; font-weight:800;">📥 抄空白範本產生 SFIS Excel</button>
                <button type="button" onclick="sfisHmiExport('insert_current')" class="btn" style="padding:6px 13px; font-size:0.82rem; background:#FFFFFF; color:#15803D; border:1.5px solid #16A34A; border-radius:7px; font-weight:800;">➕ 插入目前 Excel 開頭</button>
              </div>
            </div>
            <pre id="sfisLiveExcelPreview" class="mono" style="margin:0; font-size:0.75rem; color:#0F172A; background:#FFFFFF; border:1px solid #BBF7D0; border-radius:6px; padding:6px 9px; white-space:pre-wrap; overflow:auto;"></pre>
          </div>
        </div>
      </div>
    </div>
  `;
  sfisRenderLiveExcelPreview();
}
