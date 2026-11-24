// SFIS WebService Split-Pane Animated HMI & Single-ISN Verification + Excel Script Builder

let SFIS_PLANT_PRESETS = [
  {
    id: 'PTB_PROD',
    label: '巴淡 PTB 正式機 (10.176.33.13)',
    url: 'http://10.176.33.13/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2'
  },
  {
    id: 'PTB_QA',
    label: '巴淡 PTB 測試機 (BTARDB0QA)',
    url: 'http://172.24.255.10/SFISWebService_BTARDB0QA/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2'
  },
  {
    id: 'PTB_F1',
    label: '巴淡 PTB F1 (可編輯自填 IP)',
    url: 'http://172.24.255.113/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2'
  },
  {
    id: 'TY3_PROD',
    label: '桃園三廠 TY3 正式機 (pxd-sftsp-n3)',
    url: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2'
  },
  {
    id: 'TY3_QA',
    label: '桃園三廠 TY3 測試機 (XDNPDB0QA)',
    url: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService_XDNPDB0QA/sfistspwebservice.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2'
  },
  {
    id: 'SUZHOU_PROD',
    label: '蘇州正式機 (.248.15)',
    url: 'http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx',
    defaultDevice: '710001',
    defaultTsp: 'ATLAS,2'
  },
  {
    id: 'SUZHOU_QA',
    label: '蘇州測試機 (SZASCD0QA)',
    url: 'http://172.24.255.10/SFISWebService_SZASCD0QA/SFISTSPWebService.asmx',
    defaultDevice: '430079',
    defaultTsp: 'ATLAS,2'
  }
];

const DEFAULT_VIRTUAL_MOS = [
  { date: '9月21日', model: 'PL AURORA1A/V200/TAA', pn: '90AA221000S0', qty: 5, reason: 'Aurora SFIS 驗線', mo: '26951603', seq_digits: 5, seq_start: 1, note: 'TECO' },
  { date: '9月21日', model: 'PL AURORA1B/V250/TAA', pn: '90AA221000K0', qty: 5, reason: 'Aurora SFIS 驗線', mo: '26951604', seq_digits: 5, seq_start: 1, note: 'TECO' },
  { date: '9月21日', model: 'PL AURORA3A/V400/TAA', pn: '90AA221000B0', qty: 5, reason: 'Aurora SFIS 驗線', mo: '26951605', seq_digits: 5, seq_start: 1, note: 'TECO' },
  { date: '9月21日', model: 'PL AURORA3B/V450/TAA', pn: '90AA221001B0', qty: 5, reason: 'Aurora SFIS 驗線', mo: '26951606', seq_digits: 5, seq_start: 1, note: 'TECO' },
  { date: '9月21日', model: 'PL AURORA5A/V800/TAA', pn: '90AA221000Z0', qty: 5, reason: 'Aurora SFIS 驗線', mo: '26951607', seq_digits: 5, seq_start: 1, note: 'TECO' },
  { date: '9月21日', model: 'PL AURORA5B/V850/TAA', pn: '90AA22100120', qty: 5, reason: 'Aurora SFIS 驗線', mo: '26951608', seq_digits: 5, seq_start: 1, note: 'TECO' }
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

const SFIS_GETVERSION_TYPES = [
  { value: 'ISN_BASEINFO', label: 'ISN_BASEINFO (SNA~SNG / MAC1 / SSN)' },
  { value: 'ITEMINFO', label: 'ITEMINFO (關聯 60 / 80 階序號)' },
  { value: 'MOKP_SN', label: 'MOKP_SN (關鍵組件明細 如 W3G / HD)' },
  { value: 'GET_IVMAC_NEW', label: 'GET_IVMAC_NEW (GUID1/2 + MAC1)' },
  { value: 'ITEM_FEATURE_BASEINFO', label: 'ITEM_FEATURE_BASEINFO (ModelNumber / EPG)' },
  { value: 'GETSN_BYRULE', label: 'GETSN_BYRULE (依規則配號)' },
  { value: 'ASSIGN_SSN', label: 'ASSIGN_SSN (配發出貨 SSN)' }
];

const SFIS_CATALOG_BLOCKS = [
  { kind: 'login', icon: '🔐', title: 'Login / Logout', desc: '測電腦與 OP 通否', theme: '#0284C7', bg: '#F0F9FF', border: '#7DD3FC' },
  { kind: 'checkroute', icon: '🔍', title: 'CheckRoute 過站', desc: '刷單顆 ISN 途程', theme: '#2563EB', bg: '#EFF6FF', border: '#93C5FD' },
  { kind: 'get', icon: '📥', title: 'GET 查欄位', desc: '支援 0~7 堆疊拆解＋Ref 切字', theme: '#059669', bg: '#ECFDF5', border: '#6EE7B7' },
  { kind: 'getimac', icon: '📡', title: 'GET iMAC', desc: '取用配對 MAC 位址', theme: '#0D9488', bg: '#F0FDFA', border: '#5EEAD4' },
  { kind: 'getlabel', icon: '🏷', title: 'GET 標籤', desc: 'WTSP_GETLABEL 條碼查詢', theme: '#6366F1', bg: '#EEF2FF', border: '#A5B4FC' },
  { kind: 'savelink', icon: '📤', title: 'WRITE 寫欄位', desc: '⚠️ 可能推站慎按', theme: '#D97706', bg: '#FFFBEB', border: '#FCD34D' },
  { kind: 'rw', icon: '🔄', title: 'R/W 寫＋回讀', desc: '寫後立即 GET 比對', theme: '#7C3AED', bg: '#F5F3FF', border: '#C4B5FD' },
  { kind: 'clear', icon: '🧹', title: 'CLEAR 清空試探', desc: '寫空值並回讀', theme: '#475569', bg: '#F8FAFC', border: '#CBD5E1' }
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
  return found ? found.url : SFIS_PLANT_PRESETS[0].url;
}

const SFIS_HMI_STATE = {
  activeSubTab: 'hub', // 'hub' | 'real' | 'mock' | 'dll'
  mockMode: false, // false = 實機工廠內網 | true = 本機模擬 SFIS 內網 (無網全測)
  leftPanePct: parseFloat(localStorage.getItem('centimani_sfis_left_pct') || '46') || 46,
  profilesLoaded: false,
  showPlantEditor: false,
  selectedMoIdx: 0,
  virtualMos: JSON.parse(JSON.stringify(DEFAULT_VIRTUAL_MOS)),
  usedIsns: [],
  plantId: 'PTB_PROD',
  config: {
    url: _getEffectivePlantUrl('PTB_PROD'),
    project_name: 'SFIS_VERIFY',
    station: 'MB',
    device_id: '710001',
    tsp: 'ATLAS,2',
    op: 'S09166390',
    isn: '2695160300001',
    skip_save_on_fail: true
  },
  isnPoolText: '2695160300001\n2695160300002\n2695160300003\n2695160300004\n2695160300005',
  // 鎖定頭尾骨架：Step 1 登入 (鎖定) -> Step 2 CheckRoute (鎖定) -> [中間由 User 增減] -> Last 登出 (鎖定)
  items: [
    { uid: 'sf_head_login', kind: 'login', login_status: '1', locked: 'login', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' },
    { uid: 'sf_head_route', kind: 'checkroute', locked: 'checkroute', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' },
    { uid: 'sf_tail_logout', kind: 'login', login_status: '0', locked: 'logout', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' }
  ],
  selectedUid: 'sf_head_route',
  anim: {
    phase: 'idle', // 'idle' | 'sending' | 'pass' | 'fail' | 'offline'
    stage: 'idle', // 'idle' | 'to_cloud' | 'to_db' | 'to_pc'
    packetText: '',
    slowDemo: (localStorage.getItem('centimani_sfis_slow_demo') !== '0'),
    actionLabel: '待機就緒 — 點選左側卡片或按 ▶ 依序實測',
    opLoggedIn: null,
    netConnected: null,
    lastFieldVal: '',
    responseExpanded: true, // 右下黑底終端預設常駐顯示
    responseViewMode: 'all', // 'all' | 'latest' | 'selected'
    logs: [] // 累積所有積木實測之送出與吐回完整字串
  },
  isRunning: false,
  dragSrcIdx: -1,
  dropTargetIdx: -1,
  dropPos: 'before',
  dragSortMode: 'swap', // 'swap' 碰牌對調 | 'insert' 插牌移位
  dragCatalogKind: ''
};

function _enforceSfisSkeleton() {
  const arr = Array.isArray(SFIS_HMI_STATE.items) ? SFIS_HMI_STATE.items : [];
  let headLogin = arr.find(x => x && (x.locked === 'login' || (x.kind === 'login' && String(x.login_status || '1') === '1')));
  let headRoute = arr.find(x => x && (x.locked === 'checkroute' || x.kind === 'checkroute'));
  let tailLogout = arr.find(x => x && (x.locked === 'logout' || (x.kind === 'login' && String(x.login_status || '1') === '0')));

  headLogin = headLogin ? Object.assign(headLogin, { kind: 'login', login_status: '1', locked: 'login' })
    : { uid: 'sf_head_login', kind: 'login', login_status: '1', locked: 'login', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' };
  headRoute = headRoute ? Object.assign(headRoute, { kind: 'checkroute', locked: 'checkroute' })
    : { uid: 'sf_head_route', kind: 'checkroute', locked: 'checkroute', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' };
  tailLogout = tailLogout ? Object.assign(tailLogout, { kind: 'login', login_status: '0', locked: 'logout' })
    : { uid: 'sf_tail_logout', kind: 'login', login_status: '0', locked: 'logout', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' };

  const middle = arr.filter(x => x && x !== headLogin && x !== headRoute && x !== tailLogout && x.kind !== 'login' && x.kind !== 'checkroute')
    .map(x => { x.locked = ''; return x; });

  SFIS_HMI_STATE.items = [headLogin, headRoute, ...middle, tailLogout];
  if (!SFIS_HMI_STATE.items.some(x => x.uid === SFIS_HMI_STATE.selectedUid)) {
    SFIS_HMI_STATE.selectedUid = headRoute.uid;
  }
}

function sfisSelectDeckCard(uid) {
  SFIS_HMI_STATE.selectedUid = uid;
  renderSfisHmiWorkspace();
}

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

function _escCentimaniArg(raw) {
  let s = String(raw == null ? '' : raw);
  s = s.replace(/\\/g, '\\\\');
  s = s.replace(/([",*/:;])/g, '\\$1');
  s = s.replace(/\}/g, '}}');
  return s;
}

function _buildCentimaniRefExpr(it) {
  const f = _resolveCardField(it);
  const vn = String(it.ref_var || ('sf_' + f.replace(/[^A-Za-z0-9_]/g, ''))).trim().replace(/^\$+/, '') || 'sfData';
  const rm = it.ref_mode || 'raw';
  if (rm === 'split') {
    const delim = _escCentimaniArg(it.ref_delim || ';');
    const idx = parseInt(it.ref_seg_idx || 0, 10) || 0;
    return `$${vn}:SplitString,"${delim}","${idx}":Trim;`;
  }
  if (rm === 'within') {
    const l = _escCentimaniArg(it.ref_left || '');
    const r = _escCentimaniArg(it.ref_right || '');
    return `$${vn}:WithinString,"${l}","${r}","":Trim;`;
  }
  if (rm === 'ma') {
    const mk = _escCentimaniArg(it.ref_marker || ':');
    return `$${vn}:maString,"${mk}":Trim;`;
  }
  if (rm === 'mb') {
    const mk = _escCentimaniArg(it.ref_marker || ';');
    return `$${vn}:mbString,"${mk}":Trim;`;
  }
  if (rm === 'substr') {
    const st = parseInt(it.ref_sub_start || 0, 10) || 0;
    const ln = parseInt(it.ref_sub_len || 12, 10) || 12;
    return `$${vn}:SubString,"${st}","${ln}";`;
  }
  if (rm === 'getmac2') {
    return `$${vn}:getMAC2;`;
  }
  return `$${vn}:lwString;`;
}

function _previewCentimaniSlice(rawText, it) {
  const txt = String(rawText == null ? '' : rawText);
  if (!txt) return '';
  const rm = it.ref_mode || 'raw';
  if (rm === 'split') {
    const delim = it.ref_delim || ';';
    const idx = parseInt(it.ref_seg_idx || 0, 10) || 0;
    const parts = txt.split(delim);
    return (parts[idx] != null ? parts[idx] : '').trim();
  }
  if (rm === 'within') {
    const l = it.ref_left || '';
    const r = it.ref_right || '';
    const p1 = l ? txt.indexOf(l) : 0;
    if (p1 < 0) return '(找不到左界)';
    const start = p1 + l.length;
    const p2 = r ? txt.indexOf(r, start) : txt.length;
    return (p2 < 0 ? txt.slice(start) : txt.slice(start, p2)).trim();
  }
  if (rm === 'ma') {
    const mk = it.ref_marker || ':';
    const p = txt.indexOf(mk);
    return p >= 0 ? txt.slice(p + mk.length).trim() : '(找不到關鍵字)';
  }
  if (rm === 'mb') {
    const mk = it.ref_marker || ';';
    const p = txt.indexOf(mk);
    return p >= 0 ? txt.slice(0, p).trim() : txt;
  }
  if (rm === 'substr') {
    const st = parseInt(it.ref_sub_start || 0, 10) || 0;
    const ln = parseInt(it.ref_sub_len || 12, 10) || 12;
    return txt.substr(st, ln);
  }
  if (rm === 'getmac2') {
    const m = txt.replace(/[^0-9A-Fa-f]/g, '').match(/[0-9A-Fa-f]{12}/);
    return m ? m[0].toUpperCase() : '(無12碼MAC)';
  }
  return txt;
}

function _itemToBackendStep(it) {
  const k = it.kind;
  const f = _resolveCardField(it);
  if (k === 'get' || k === 'getversion') {
    const refExpr = _buildCentimaniRefExpr(it);
    if (!it.ver_type && f === 'ITEMINFO_60') return { kind: 'getversion', ver_type: 'ITEMINFO', slot_code: it.slot_code || '4', chk_data: '', chk_data2: '', ref_var: it.ref_var || 'sf60ISN', ref_expr: refExpr };
    if (!it.ver_type && f === 'ITEMINFO_80') return { kind: 'getversion', ver_type: 'ITEMINFO', slot_code: it.slot_code || '5', chk_data: '', chk_data2: '', ref_var: it.ref_var || 'sf80ISN', ref_expr: refExpr };
    if (!it.ver_type && f === 'SSN') return { kind: 'getversion', ver_type: 'ISN_BASEINFO', slot_code: it.slot_code || '3', chk_data: 'SSN', chk_data2: '', ref_var: it.ref_var || 'sfSSN', ref_expr: refExpr };
    const vt = it.ver_type || 'ISN_BASEINFO';
    const chk1 = (vt === 'ITEMINFO') ? (it.chk_data || '') : (it.chk_data !== undefined && it.field_key === '__CUSTOM__' ? it.chk_data : (f === 'ITEMINFO_60' || f === 'ITEMINFO_80' ? '' : f));
    return {
      kind: 'getversion',
      ver_type: vt,
      slot_code: String(it.slot_code || '2'),
      chk_data: it.ver_type === 'ITEM_FEATURE_BASEINFO' || it.ver_type === 'MOKP_SN' || it.ver_type === 'GETSN_BYRULE' ? (it.chk_data || f) : chk1,
      chk_data2: it.chk_data2 || '',
      ref_var: it.ref_var || ('sf_' + f.replace(/[^A-Za-z0-9_]/g, '')),
      ref_expr: refExpr
    };
  }
  if (k === 'getimac') return { kind: 'getimac', slot_code: it.slot_code || '2', imacnum: '1', ref_var: it.ref_var || 'sfMAC', ref_expr: _buildCentimaniRefExpr(it) };
  if (k === 'getlabel') return { kind: 'login' }; // WebService lookup helper
  if (k === 'savelink') return { kind: 'savelink', save_key: f, save_val: it.save_val || 'TEST_VAL' };
  if (k === 'rw') return { kind: 'rw', save_key: f, save_val: it.save_val || 'TEST_RW_01', ref_var: it.ref_var || ('sf_' + f.replace(/[^A-Za-z0-9_]/g, '')) };
  if (k === 'clear') return { kind: 'clear', save_key: f };
  if (k === 'login') return { kind: String(it.login_status || '1') === '0' ? 'logout' : 'login' };
  return { kind: k };
}

function _buildCardExcelPreview(it) {
  if (!it) return '';
  const k = it.kind;
  const f = _resolveCardField(it);
  if (k === 'login') {
    return String(it.login_status || '1') === '0'
      ? 'SOAP: WTSP_LOGINOUT(status=0 登出)'
      : 'SOAP: WTSP_LOGINOUT(status=1 登入) — System.ini SFIS_AutoLogin=1';
  }
  if (k === 'checkroute') return ':ShowISN,"*(ISN)" ➔ :SfCheckRoute  |  ExecMode: 8';
  if (k === 'get' || k === 'getversion') {
    const st = _itemToBackendStep(it);
    return `:SfGetVersion,"*(ISN)","${st.ver_type}","${st.slot_code}","${st.chk_data}","${st.chk_data2}"  |  Ref: ${st.ref_expr}  |  EM: 8`;
  }
  if (k === 'getimac') {
    const st = _itemToBackendStep(it);
    return `:SfGetiMAC,"*(ISN)","1","1","${st.slot_code}"  |  Ref: ${st.ref_expr}  |  EM: 8`;
  }
  if (k === 'getlabel') return 'SOAP: WTSP_GETLABEL（線邊標籤資料查詢輔助，不寫入測試步驟）';
  if (k === 'savelink') return `:SfSaveLinkData,"${f}","${it.save_val || 'TEST_VAL'}"  |  EM: 8`;
  if (k === 'rw') return `:SfSaveLinkData,"${f}","${it.save_val || 'TEST_RW_01'}" ➔ :SfGetVersion(...,"${f}","")  |  EM: 8`;
  if (k === 'clear') return `:SfSaveLinkData,"${f}","" (試寫空值清空) + 回讀確認`;
  return '';
}

async function _loadSfisProfilesOnce() {
  if (SFIS_HMI_STATE.profilesLoaded) return;
  SFIS_HMI_STATE.profilesLoaded = true;
  try {
    const res = await fetch('/api/sfis_hmi_profiles');
    const d = await res.json();
    if (d && d.status === 'ok') {
      if (Array.isArray(d.plants) && d.plants.length) {
        SFIS_PLANT_PRESETS = d.plants.map(p => ({
          id: p.id,
          label: p.label,
          url: p.url,
          defaultDevice: p.defaultDevice || p.default_device || '710001',
          defaultTsp: p.defaultTsp || p.default_tsp || 'ATLAS,2'
        }));
      }
      if (Array.isArray(d.virtual_mos) && d.virtual_mos.length) {
        SFIS_HMI_STATE.virtualMos = d.virtual_mos;
      }
      if (Array.isArray(d.used_isns)) {
        SFIS_HMI_STATE.usedIsns = d.used_isns;
      }
      const curP = SFIS_PLANT_PRESETS.find(x => x.id === SFIS_HMI_STATE.plantId) || SFIS_PLANT_PRESETS[0];
      if (curP) {
        SFIS_HMI_STATE.plantId = curP.id;
        SFIS_HMI_STATE.config.url = _getEffectivePlantUrl(curP.id);
      }
      renderSfisHmiWorkspace();
    }
  } catch (e) {}
}

async function _saveSfisProfilesToBackend(partObj) {
  try {
    await fetch('/api/sfis_hmi_profiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(partObj)
    });
  } catch (e) {}
}

function setActiveToolsHubCard(key) {
  ['real', 'mock', 'dll'].forEach(k => {
    const el = document.getElementById('toolsHubCard_' + k);
    if (el) el.classList.toggle('active', k === key);
  });
}

function switchToolsVerifyTab(subTab) {
  let target = subTab || 'hub';
  if (target === 'sfis') target = SFIS_HMI_STATE.mockMode ? 'mock' : 'real';
  if (!['hub', 'real', 'mock', 'dll'].includes(target)) target = 'hub';

  const wasMock = !!SFIS_HMI_STATE.mockMode;
  SFIS_HMI_STATE.activeSubTab = target;
  if (target === 'mock' || target === 'real') {
    const nextMock = (target === 'mock');
    SFIS_HMI_STATE.mockMode = nextMock;
    if (nextMock !== wasMock) {
      SFIS_HMI_STATE.anim.phase = 'idle';
      SFIS_HMI_STATE.anim.opLoggedIn = null;
      SFIS_HMI_STATE.anim.netConnected = nextMock ? true : null;
      SFIS_HMI_STATE.anim.logs = [];
      SFIS_HMI_STATE.items.forEach(it => { it.status = 'idle'; it.resultMsg = ''; it.lastRaw = ''; it.lastSlots = null; });
      SFIS_HMI_STATE.anim.actionLabel = nextMock
        ? '🧪 本機模擬 SFIS 內網就緒 — 按右側 ⚡ 即可無網全測'
        : '🌐 實機工廠內網連線模式 — 將真實連線至 WebLink';
    }
  }

  const hubEl = document.getElementById('toolsVerifyHub');
  const sfisPane = document.getElementById('toolsSubPaneSfis');
  const dllPane = document.getElementById('toolsSubPaneDll');
  const backAccBtn = document.getElementById('btnToolsBackToAcc');
  const modeTitleEl = document.getElementById('genCurrentModeTitle');

  if (hubEl) hubEl.style.display = (target === 'hub') ? 'block' : 'none';
  if (sfisPane) sfisPane.style.display = (target === 'real' || target === 'mock') ? 'block' : 'none';
  if (dllPane) dllPane.style.display = (target === 'dll') ? 'block' : 'none';
  if (backAccBtn) backAccBtn.style.display = (target === 'hub') ? 'none' : 'inline-flex';
  if (modeTitleEl) {
    const tMap = {
      hub: '🛡️ 實機驗證中心（SFIS) — 請選擇驗證卡牌',
      real: '🛡️ 實機驗證中心（SFIS) — 🌐 實機工廠內網 (OA / 產線)',
      mock: '🛡️ 實機驗證中心（SFIS) — 🧪 本機模擬內網 (無網全測)',
      dll: '🛡️ 實機驗證中心（SFIS) — 🔩 儀器 DLL 與系統驅動檢查'
    };
    modeTitleEl.textContent = tMap[target] || '🛡️ 實機驗證中心（SFIS)';
  }

  if (target === 'real' || target === 'mock') {
    renderSfisHmiWorkspace();
    _loadSfisProfilesOnce();
  }
}

function sfisSelectPlant(plantId) {
  const p = SFIS_PLANT_PRESETS.find(x => x.id === plantId);
  if (!p) return;
  SFIS_HMI_STATE.plantId = p.id;
  SFIS_HMI_STATE.config.url = _getEffectivePlantUrl(p.id);
  SFIS_HMI_STATE.config.device_id = p.defaultDevice || '710001';
  SFIS_HMI_STATE.config.tsp = p.defaultTsp || 'ATLAS,2';
  renderSfisHmiWorkspace();
}

function sfisTogglePlantEditor() {
  SFIS_HMI_STATE.showPlantEditor = !SFIS_HMI_STATE.showPlantEditor;
  renderSfisHmiWorkspace();
}

function sfisSaveEditedPlant() {
  const lbl = (document.getElementById('sfisEdPlantLabel') || {}).value || '';
  const url = (document.getElementById('sfisEdPlantUrl') || {}).value || '';
  const dev = (document.getElementById('sfisEdPlantDev') || {}).value || '710001';
  if (!lbl.trim() || !url.trim()) { alert('請填寫廠區名稱與 WebLink 網址'); return; }
  const idx = SFIS_PLANT_PRESETS.findIndex(x => x.id === SFIS_HMI_STATE.plantId);
  if (idx >= 0) {
    SFIS_PLANT_PRESETS[idx].label = lbl.trim();
    SFIS_PLANT_PRESETS[idx].url = url.trim();
    SFIS_PLANT_PRESETS[idx].defaultDevice = dev.trim() || '710001';
    SFIS_HMI_STATE.config.url = url.trim();
    SFIS_HMI_STATE.config.device_id = dev.trim() || '710001';
    _saveCustomPlantUrl(SFIS_PLANT_PRESETS[idx].id, url.trim());
    _saveSfisProfilesToBackend({ plants: SFIS_PLANT_PRESETS });
    SFIS_HMI_STATE.showPlantEditor = false;
    renderSfisHmiWorkspace();
  }
}

function sfisAddCustomPlant() {
  const lbl = (document.getElementById('sfisEdPlantLabel') || {}).value || '';
  const url = (document.getElementById('sfisEdPlantUrl') || {}).value || '';
  const dev = (document.getElementById('sfisEdPlantDev') || {}).value || '710001';
  if (!lbl.trim() || !url.trim()) { alert('請填寫新廠區名稱與 WebLink 網址'); return; }
  const newId = 'CUSTOM_' + Date.now();
  SFIS_PLANT_PRESETS.push({
    id: newId,
    label: lbl.trim(),
    url: url.trim(),
    defaultDevice: dev.trim() || '710001',
    defaultTsp: SFIS_HMI_STATE.config.tsp || 'ATLAS,2'
  });
  SFIS_HMI_STATE.plantId = newId;
  SFIS_HMI_STATE.config.url = url.trim();
  SFIS_HMI_STATE.config.device_id = dev.trim() || '710001';
  _saveCustomPlantUrl(newId, url.trim());
  _saveSfisProfilesToBackend({ plants: SFIS_PLANT_PRESETS });
  SFIS_HMI_STATE.showPlantEditor = false;
  renderSfisHmiWorkspace();
}

function sfisDeleteCurrentPlant() {
  if (SFIS_PLANT_PRESETS.length <= 1) { alert('至少需保留 1 個廠區選項'); return; }
  const cur = SFIS_PLANT_PRESETS.find(x => x.id === SFIS_HMI_STATE.plantId);
  if (!cur || !confirm(`確定從下拉選單移除「${cur.label}」嗎？`)) return;
  SFIS_PLANT_PRESETS = SFIS_PLANT_PRESETS.filter(x => x.id !== cur.id);
  SFIS_HMI_STATE.plantId = SFIS_PLANT_PRESETS[0].id;
  SFIS_HMI_STATE.config.url = _getEffectivePlantUrl(SFIS_HMI_STATE.plantId);
  _saveSfisProfilesToBackend({ plants: SFIS_PLANT_PRESETS });
  SFIS_HMI_STATE.showPlantEditor = false;
  renderSfisHmiWorkspace();
}

function sfisExpandMoIsns(moRow) {
  if (!moRow || !moRow.mo) return [];
  const base = String(moRow.mo).trim();
  const qty = Math.min(50, Math.max(1, parseInt(moRow.qty || 5, 10) || 5));
  const digits = Math.min(8, Math.max(1, parseInt(moRow.seq_digits || 5, 10) || 5));
  const start = Math.max(0, parseInt(moRow.seq_start || 1, 10) || 1);
  const out = [];
  for (let i = 0; i < qty; i++) {
    out.push(base + String(start + i).padStart(digits, '0'));
  }
  return out;
}

function sfisSelectMoRow(idx) {
  SFIS_HMI_STATE.selectedMoIdx = idx;
  const row = SFIS_HMI_STATE.virtualMos[idx];
  if (row) {
    const list = sfisExpandMoIsns(row);
    if (list.length) {
      SFIS_HMI_STATE.isnPoolText = list.join('\n');
      const unused = list.find(x => !SFIS_HMI_STATE.usedIsns.includes(x));
      SFIS_HMI_STATE.config.isn = unused || list[0];
    }
  }
  renderSfisHmiWorkspace();
}

function sfisUpdateMoCell(idx, field, val) {
  const row = SFIS_HMI_STATE.virtualMos[idx];
  if (!row) return;
  row[field] = (field === 'qty' || field === 'seq_digits' || field === 'seq_start') ? (parseInt(val, 10) || 1) : String(val || '');
  _saveSfisProfilesToBackend({ virtual_mos: SFIS_HMI_STATE.virtualMos });
  if (idx === SFIS_HMI_STATE.selectedMoIdx && (field === 'mo' || field === 'qty' || field === 'seq_digits' || field === 'seq_start')) {
    const list = sfisExpandMoIsns(row);
    if (list.length) SFIS_HMI_STATE.isnPoolText = list.join('\n');
    renderSfisHmiWorkspace();
  }
}

function sfisAddMoRow() {
  SFIS_HMI_STATE.virtualMos.push({
    date: '今日',
    model: 'NEW_MODEL',
    pn: '90AA...',
    qty: 5,
    reason: 'SFIS 驗線',
    mo: '26951609',
    seq_digits: 5,
    seq_start: 1,
    note: ''
  });
  SFIS_HMI_STATE.selectedMoIdx = SFIS_HMI_STATE.virtualMos.length - 1;
  _saveSfisProfilesToBackend({ virtual_mos: SFIS_HMI_STATE.virtualMos });
  renderSfisHmiWorkspace();
}

function sfisRemoveMoRow(idx) {
  if (SFIS_HMI_STATE.virtualMos.length <= 1) return;
  SFIS_HMI_STATE.virtualMos.splice(idx, 1);
  SFIS_HMI_STATE.selectedMoIdx = Math.min(SFIS_HMI_STATE.selectedMoIdx, SFIS_HMI_STATE.virtualMos.length - 1);
  _saveSfisProfilesToBackend({ virtual_mos: SFIS_HMI_STATE.virtualMos });
  renderSfisHmiWorkspace();
}

function sfisToggleUsedIsn(isnVal) {
  const idx = SFIS_HMI_STATE.usedIsns.indexOf(isnVal);
  if (idx >= 0) SFIS_HMI_STATE.usedIsns.splice(idx, 1);
  else SFIS_HMI_STATE.usedIsns.push(isnVal);
  _saveSfisProfilesToBackend({ used_isns: SFIS_HMI_STATE.usedIsns });
  renderSfisHmiWorkspace();
}

function _matchPlantIdByUrl(url) {
  const low = String(url || '').toLowerCase();
  const custom = _loadCustomPlantUrls();
  for (const p of SFIS_PLANT_PRESETS) {
    const u1 = (custom[p.id] || '').toLowerCase();
    if (u1 && low === u1) return p.id;
    if (low === p.url.toLowerCase()) return p.id;
  }
  if (low.includes('10.176.33.13')) return 'PTB_PROD';
  if (low.includes('btardb0qa')) return 'PTB_QA';
  if (low.includes('xdnpdb0qa')) return 'TY3_QA';
  if (low.includes('pxd-sftsp')) return 'TY3_PROD';
  if (low.includes('szascd0qa')) return 'SUZHOU_QA';
  if (low.includes('172.24.248.15')) return 'SUZHOU_PROD';
  return SFIS_HMI_STATE.plantId;
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

function sfisPickIsnFromPool(isnVal) {
  const clean = String(isnVal || '').trim();
  if (!clean) return;
  SFIS_HMI_STATE.config.isn = clean;
  renderSfisHmiWorkspace();
}

function _applyImportedIniFields(srcLabel, dataCfg) {
  const cfg = SFIS_HMI_STATE.config;
  const changes = [];
  if (dataCfg.url) {
    cfg.url = String(dataCfg.url).split(',')[0].trim();
    SFIS_HMI_STATE.plantId = _matchPlantIdByUrl(cfg.url);
    changes.push(`SFIS_WebLink = ${cfg.url}`);
  }
  if (dataCfg.tsp) {
    cfg.tsp = String(dataCfg.tsp).trim();
    changes.push(`SFIS_TSP = ${cfg.tsp}`);
  }
  if (dataCfg.device_id) {
    cfg.device_id = String(dataCfg.device_id).trim();
    changes.push(`DeviceID = ${cfg.device_id}`);
  }
  if (dataCfg.op) {
    cfg.op = String(dataCfg.op).trim();
    changes.push(`OP 工號 = ${cfg.op}`);
  }
  if (dataCfg.station) {
    cfg.station = String(dataCfg.station).trim();
    changes.push(`站別 = ${cfg.station}`);
  }
  if (dataCfg.project_name) {
    cfg.project_name = String(dataCfg.project_name).trim();
  }
  if (dataCfg.isn && dataCfg.isn !== '111111111111111') {
    cfg.isn = String(dataCfg.isn).trim();
    changes.push(`參考 ISN = ${cfg.isn}`);
  }
  if (dataCfg.skip_save_on_fail !== undefined) {
    cfg.skip_save_on_fail = !!dataCfg.skip_save_on_fail;
    changes.push(`SkipSaveResultOnFail = ${cfg.skip_save_on_fail ? 1 : 0}`);
  }
  SFIS_HMI_STATE.anim.actionLabel = `📥 已帶入 ${srcLabel}`;
  _pushResponseLog('📥 帶入 INI 設定', `來源：${srcLabel}`, {
    passed: true,
    reachable: true,
    ret_code: 'INI_LOADED',
    msg: changes.length ? changes.join(' | ') : '已完成讀取（與目前設定相同）',
    raw_result: changes.join('\n')
  });
  renderSfisHmiWorkspace();
  alert(`✅ 已從「${srcLabel}」成功帶入：\n\n` + (changes.length ? changes.map(x => '• ' + x).join('\n') : '• 設定與目前相同'));
}

async function sfisImportFromWorkspaceIni() {
  const hasWs = (typeof STATE !== 'undefined' && STATE.workspace);
  const ws = hasWs ? STATE.workspace : null;
  const sys = (ws && ws.system_ini) ? ws.system_ini : {};
  const glb = (ws && ws.global_ini && ws.global_ini.Settings) ? ws.global_ini.Settings : {};
  const dutDev = (ws && Array.isArray(ws.duts) && ws.duts[0] && ws.duts[0].SFIS_DeviceID) ? String(ws.duts[0].SFIS_DeviceID).trim() : '';
  const devFromWs = glb.DEVID_1 || (dutDev && !dutDev.includes('*$(') ? dutDev : '');

  if (ws && (sys.SFIS_WebLink || sys.SFIS_TSP || devFromWs)) {
    const srcName = (typeof STATE !== 'undefined' && STATE.selectedPath) ? STATE.selectedPath : (ws.project_name || '已開啟之專案');
    _applyImportedIniFields(`已開腳本 (${srcName})`, {
      url: sys.SFIS_WebLink || '',
      tsp: sys.SFIS_TSP || '',
      station: sys.StationName || '',
      device_id: devFromWs,
      op: sys.SFIS_LoginID || '',
      isn: sys.SFIS_GetDateISN || '',
      project_name: ws.project_name || '',
      skip_save_on_fail: sys.SFIS_SkipSaveResultOnFail !== undefined ? (String(sys.SFIS_SkipSaveResultOnFail).trim() === '1') : undefined
    });
    return;
  }

  // 若網頁尚未開啟任何含 System.ini 之 Excel，改呼叫 Windows 原生選檔直接挑選 System.ini / Global.ini
  try {
    const res = await fetch('/api/pick_sfis_ini', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pick: true })
    });
    const d = await res.json();
    if (d.status === 'cancelled') return;
    if (d.status === 'ok' && d.config) {
      _applyImportedIniFields(d.config.source_path || '本機 INI 檔', d.config);
      return;
    }
    alert(d.message || '無法讀取該 INI 檔案');
  } catch (e) {
    alert('開啟 INI 選檔失敗：' + e);
  }
}

function _pushResponseLog(stepTitle, sentCmd, soapData, uid = '') {
  const ok = !!soapData.passed;
  const offline = !soapData.reachable || soapData.status === 'offline';
  const slots = soapData.slots || {};
  const valStr = slots.P_CAVER || slots.P_CBVER || slots.P_CCVER || '';
  if (valStr) SFIS_HMI_STATE.anim.lastFieldVal = valStr;

  const lines = [];
  lines.push(`P_RET = ${soapData.ret_code ?? '-'}  (${ok ? 'PASS' : (offline ? 'OFFLINE' : 'FAIL')})`);
  lines.push(`P_Msg = ${soapData.msg || '-'}`);
  if (valStr) lines.push(`讀回主值 (P_CAVER) = ${valStr}`);
  const extraSlots = Object.entries(slots).filter(([, v]) => v).map(([k, v]) => `${k}=${v}`).join(' | ');
  if (extraSlots) lines.push(`完整槽位 = ${extraSlots}`);
  if (soapData.raw_result && soapData.raw_result !== soapData.msg) {
    lines.push(`伺服器原始吐回 = ${soapData.raw_result}`);
  }
  const timeStr = new Date().toLocaleTimeString('zh-TW', { hour12: false });
  const summary = offline
    ? '無法連通內網'
    : (ok ? (valStr ? `✅ 值：${valStr}` : `✅ ${soapData.msg || 'PASS'}`) : `❌ ${soapData.msg || 'FAIL'}`);

  SFIS_HMI_STATE.anim.logs.unshift({
    uid: uid || '',
    time: timeStr,
    title: stepTitle,
    ok,
    offline,
    sent: sentCmd,
    recv: lines.join('\n'),
    summary
  });
  if (SFIS_HMI_STATE.anim.logs.length > 20) SFIS_HMI_STATE.anim.logs.length = 20;
}

function sfisClearLogs() {
  SFIS_HMI_STATE.anim.logs = [];
  SFIS_HMI_STATE.anim.actionLabel = '已清空顯示紀錄';
  renderSfisHmiWorkspace();
}

function sfisSetRespViewMode(mode) {
  SFIS_HMI_STATE.anim.responseViewMode = ['latest', 'selected'].includes(mode) ? mode : 'all';
  renderSfisHmiWorkspace();
}

function sfisCopyRecvString() {
  const a = SFIS_HMI_STATE.anim;
  const list = (a.responseViewMode === 'selected')
    ? a.logs.filter(l => l.uid && l.uid === SFIS_HMI_STATE.selectedUid)
    : ((a.responseViewMode === 'latest' && a.logs.length) ? [a.logs[0]] : a.logs);
  const txt = list.map(l => `[${l.time}] ${l.title}\n>> ${l.sent}\n<< ${l.recv}`).join('\n\n');
  if (!txt) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(txt).then(() => {
      const btn = document.getElementById('sfisBtnCopyRecv');
      if (btn) { btn.textContent = '✅ 已複製'; setTimeout(() => { btn.textContent = '📋 複製'; }, 1200); }
    });
  }
}

function sfisSetMockMode(isMock) {
  SFIS_HMI_STATE.mockMode = !!isMock;
  SFIS_HMI_STATE.activeSubTab = !!isMock ? 'mock' : 'real';
  SFIS_HMI_STATE.anim.phase = 'idle';
  SFIS_HMI_STATE.anim.opLoggedIn = null;
  SFIS_HMI_STATE.anim.netConnected = isMock ? true : null;
  SFIS_HMI_STATE.anim.logs = [];
  SFIS_HMI_STATE.items.forEach(it => {
    it.status = 'idle';
    it.resultMsg = '';
    it.lastRaw = '';
    it.lastSlots = null;
  });
  SFIS_HMI_STATE.anim.actionLabel = isMock
    ? '🧪 已切至「本機模擬 SFIS 內網」— 已清除先前離線狀態，可立即按右側 ⚡ 全測'
    : '🌐 已切回「實機工廠內網」— 將真實連線至 WebLink';
  const modeTitleEl = document.getElementById('genCurrentModeTitle');
  if (modeTitleEl) {
    modeTitleEl.textContent = isMock
      ? '🛡️ 實機驗證中心（SFIS) — 🧪 本機模擬內網 (無網全測)'
      : '🛡️ 實機驗證中心（SFIS) — 🌐 實機工廠內網 (OA / 產線)';
  }
  renderSfisHmiWorkspace();
}

function sfisStartSplitDrag(ev) {
  if (ev) ev.preventDefault();
  const layoutEl = document.getElementById('sfisSplitLayout');
  if (!layoutEl) return;
  const resizerEl = layoutEl.querySelector('.sfis-split-resizer');
  if (resizerEl) resizerEl.classList.add('dragging');
  document.body.style.userSelect = 'none';
  document.body.style.cursor = 'col-resize';

  const onMove = (mEv) => {
    const rect = layoutEl.getBoundingClientRect();
    if (!rect.width) return;
    let pct = ((mEv.clientX - rect.left) / rect.width) * 100;
    pct = Math.max(28, Math.min(72, pct));
    SFIS_HMI_STATE.leftPanePct = Number(pct.toFixed(2));
    layoutEl.style.setProperty('--sfis-left-w', SFIS_HMI_STATE.leftPanePct + '%');
  };
  const onUp = () => {
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
    if (resizerEl) resizerEl.classList.remove('dragging');
    try { localStorage.setItem('centimani_sfis_left_pct', String(SFIS_HMI_STATE.leftPanePct || 46)); } catch (e) {}
  };
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

function sfisResetSplitWidth() {
  SFIS_HMI_STATE.leftPanePct = 46;
  try { localStorage.setItem('centimani_sfis_left_pct', '46'); } catch (e) {}
  const layoutEl = document.getElementById('sfisSplitLayout');
  if (layoutEl) layoutEl.style.setProperty('--sfis-left-w', '46%');
}

async function sfisResetMockDb() {
  _LOCAL_MOCK_SFIS_DB.routed.clear();
  _LOCAL_MOCK_SFIS_DB.fields = {};
  try {
    await fetch('/api/sfis_mock_reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  } catch (e) {}
  SFIS_HMI_STATE.usedIsns = [];
  SFIS_HMI_STATE.items.forEach(it => { it.status = 'idle'; it.resultMsg = ''; });
  SFIS_HMI_STATE.anim.phase = 'idle';
  SFIS_HMI_STATE.anim.actionLabel = '↺ 已重置本機模擬資料庫與 ISN 過站狀態';
  _pushResponseLog('↺ 重置模擬 DB', 'Mock DB Reset', { passed: true, reachable: true, ret_code: 'RESET_OK', msg: '已還原所有虛擬工單 ISN 過站與代用欄位值' });
  renderSfisHmiWorkspace();
}

function sfisPickSlotIndex(cardIdx, slotCode) {
  const it = SFIS_HMI_STATE.items[cardIdx];
  if (!it) return;
  it.slot_code = String(slotCode);
  renderSfisHmiWorkspace();
}

function sfisPickSegment(cardIdx, delim, segIdx) {
  const it = SFIS_HMI_STATE.items[cardIdx];
  if (!it) return;
  it.ref_mode = 'split';
  it.ref_delim = delim;
  it.ref_seg_idx = segIdx;
  renderSfisHmiWorkspace();
}

async function toolsCheckSfisLink() {
  if (SFIS_HMI_STATE.mockMode) {
    SFIS_HMI_STATE.anim.netConnected = true;
    SFIS_HMI_STATE.anim.phase = 'pass';
    SFIS_HMI_STATE.anim.actionLabel = '✅ 本機模擬 SFIS 內網就緒（無需連公司內網）';
    _pushResponseLog('🔍 測內網連通 (模擬)', 'Mock Intranet Self-Check', { passed: true, reachable: true, ret_code: 'MOCK_200', msg: '本機模擬 SFIS Server 運作中（吐出真實 LOG 格式與 0~7 堆疊資料）' });
    renderSfisHmiWorkspace();
    return;
  }
  const url = String(SFIS_HMI_STATE.config.url || '').trim();
  if (!url) { alert('請先選擇廠區或輸入 SFIS_WebLink 網址'); return; }
  SFIS_HMI_STATE.anim.phase = 'sending';
  SFIS_HMI_STATE.anim.actionLabel = '測試機台 ➔ SFIS 連通確認中...';
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
      ? `✅ 內網連通正常 (HTTP ${d.http_code})`
      : '⚠️ 無法連通 SFIS（在外網可點上方切換「🧪 本機模擬 SFIS 內網」）';
    _pushResponseLog('🔍 測內網連通', `HTTP 預檢 ${url}`, {
      passed: !!d.reachable,
      reachable: !!d.reachable,
      ret_code: d.reachable ? `HTTP_${d.http_code}` : 'OFFLINE',
      msg: d.message || (d.reachable ? 'HTTP 200 OK' : 'Connection failed'),
      raw_result: d.message || ''
    });
  } catch (e) {
    SFIS_HMI_STATE.anim.netConnected = false;
    SFIS_HMI_STATE.anim.phase = 'offline';
    _pushResponseLog('🔍 測內網連通', `HTTP 預檢 ${url}`, { passed: false, reachable: false, ret_code: 'ERR', msg: String(e) });
  }
  renderSfisHmiWorkspace();
}

function sfisAddItem(kind, insertAt = -1) {
  _enforceSfisSkeleton();
  if (kind === 'login' || kind === 'checkroute') {
    const pick = SFIS_HMI_STATE.items.find(x => x.kind === kind);
    if (pick) SFIS_HMI_STATE.selectedUid = pick.uid;
    renderSfisHmiWorkspace();
    return;
  }
  const uid = 'sf_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
  let item = { uid, kind, locked: '', status: 'idle', resultMsg: '', lastRaw: '', sentCmd: '' };
  if (kind === 'get') {
    item.ver_type = 'ISN_BASEINFO';
    item.field_key = 'SNA';
    item.custom_field = '';
    item.chk_data = 'SNA';
    item.chk_data2 = '';
    item.slot_code = '2';
    item.ref_var = 'sfSNA';
    item.ref_mode = 'raw';
    item.ref_delim = ';';
    item.ref_seg_idx = 0;
  } else if (kind === 'getimac') {
    item.slot_code = '2';
    item.ref_var = 'sfMAC';
    item.ref_mode = 'substr';
    item.ref_sub_start = 0;
    item.ref_sub_len = 12;
  } else if (kind === 'getlabel') {
    item.label_type = 'ISN';
  } else if (kind === 'savelink') { item.field_key = 'SNA'; item.custom_field = ''; item.save_val = 'TEST_VAL_01'; }
  else if (kind === 'rw') { item.field_key = 'SNB'; item.custom_field = ''; item.save_val = 'TEST_RW_01'; item.ref_var = 'sfSNB'; }
  else if (kind === 'clear') { item.field_key = 'SNA'; item.custom_field = ''; }

  const tailIdx = Math.max(2, SFIS_HMI_STATE.items.length - 1);
  const clampedIdx = (insertAt >= 2 && insertAt <= tailIdx) ? insertAt : tailIdx;
  SFIS_HMI_STATE.items.splice(clampedIdx, 0, item);
  SFIS_HMI_STATE.selectedUid = item.uid;
  renderSfisHmiWorkspace();
}

function sfisRemoveItem(idx) {
  _enforceSfisSkeleton();
  const it = SFIS_HMI_STATE.items[idx];
  if (!it || it.locked) return;
  const wasSel = (SFIS_HMI_STATE.selectedUid === it.uid);
  SFIS_HMI_STATE.items.splice(idx, 1);
  if (wasSel) {
    const nextItem = SFIS_HMI_STATE.items[Math.min(idx, SFIS_HMI_STATE.items.length - 1)] || SFIS_HMI_STATE.items[1];
    if (nextItem) SFIS_HMI_STATE.selectedUid = nextItem.uid;
  }
  renderSfisHmiWorkspace();
}

function sfisClearAllItems() {
  _enforceSfisSkeleton();
  // 只清空中間自訂測項，保留 #1 Login / #2 CheckRoute / 最後 Logout 固定骨架
  if (SFIS_HMI_STATE.items.length > 3) {
    SFIS_HMI_STATE.items.splice(2, SFIS_HMI_STATE.items.length - 3);
  }
  SFIS_HMI_STATE.selectedUid = SFIS_HMI_STATE.items[1] ? SFIS_HMI_STATE.items[1].uid : '';
  renderSfisHmiWorkspace();
}

function sfisUpdateItemField(idx, field, value) {
  const it = SFIS_HMI_STATE.items[idx];
  if (!it) return;
  it[field] = value;
  if (field === 'field_key' && value !== '__CUSTOM__') {
    const clean = String(value || 'Data').replace(/^ITEMINFO_/, 'Item').replace(/[^A-Za-z0-9_]/g, '');
    it.ref_var = 'sf' + clean;
    if (value === 'ITEMINFO_60') { it.ver_type = 'ITEMINFO'; it.slot_code = '4'; it.chk_data = ''; }
    else if (value === 'ITEMINFO_80') { it.ver_type = 'ITEMINFO'; it.slot_code = '5'; it.chk_data = ''; }
    else if (value === 'SSN') { it.ver_type = 'ISN_BASEINFO'; it.slot_code = '3'; it.chk_data = 'SSN'; }
    else { it.chk_data = value; }
  }
  if (field === 'ver_type') {
    if (value === 'ITEMINFO') { it.slot_code = '4'; it.chk_data = ''; it.chk_data2 = ''; }
    else if (value === 'MOKP_SN') { it.slot_code = '2'; it.chk_data = 'W3G'; it.chk_data2 = ''; }
    else if (value === 'GET_IVMAC_NEW') { it.slot_code = '2'; it.chk_data = ''; it.chk_data2 = ''; }
    else if (value === 'ITEM_FEATURE_BASEINFO') { it.slot_code = '4'; it.chk_data = 'AURORA'; it.chk_data2 = 'ModelNumber'; }
  }
  if (['field_key', 'login_status', 'ver_type', 'ref_mode', 'slot_code', 'ref_delim'].includes(field)) {
    renderSfisHmiWorkspace();
  } else {
    const prevEl = document.getElementById(`sfisCardPrev_${idx}`);
    if (prevEl) prevEl.textContent = _buildCardExcelPreview(it);
    const sliceEl = document.getElementById(`sfisSlicePrev_${idx}`);
    if (sliceEl) {
      const slotMap = { '2': 'P_CAVER', '3': 'P_CBVER', '4': 'P_CCVER', '5': 'P_CDVER', '6': 'P_IAVER', '7': 'P_IBVER' };
      const sKey = slotMap[String(it.slot_code || '2')] || 'P_CAVER';
      const rawTxt = (it.lastSlots && it.lastSlots[sKey]) || '';
      const valCut = _previewCentimaniSlice(rawTxt, it);
      sliceEl.textContent = rawTxt ? `預期切出：${valCut}  |  Ref: ${_buildCentimaniRefExpr(it)}` : `Ref: ${_buildCentimaniRefExpr(it)}`;
    }
    sfisRenderLiveExcelPreview();
  }
}

function sfisSetDragSortMode(mode) {
  SFIS_HMI_STATE.dragSortMode = (mode === 'insert') ? 'insert' : 'swap';
  renderSfisHmiWorkspace();
}

function sfisMoveStep(idx, delta) {
  _enforceSfisSkeleton();
  const arr = SFIS_HMI_STATE.items;
  const it = arr[idx];
  const minMid = 2;
  const maxMid = arr.length - 2;
  const target = idx + delta;
  if (!it || it.locked || target < minMid || target > maxMid) return;
  const moved = arr.splice(idx, 1)[0];
  arr.splice(target, 0, moved);
  SFIS_HMI_STATE.selectedUid = moved.uid;
  renderSfisHmiWorkspace();
}

function sfisPrepCardDrag(cardEl, ev) {
  if (!cardEl || !ev) return;
  if (cardEl.classList.contains('locked')) {
    cardEl.setAttribute('draggable', 'false');
    return;
  }
  const blocked = ev.target && ev.target.closest('input, select, textarea, button, label, details, a');
  cardEl.setAttribute('draggable', blocked ? 'false' : 'true');
}

function sfisDragItemStart(idx, ev) {
  const it = SFIS_HMI_STATE.items[idx];
  if (!it || it.locked) { if (ev) ev.preventDefault(); return; }
  SFIS_HMI_STATE.dragSrcIdx = idx;
  SFIS_HMI_STATE.dragCatalogKind = '';
  if (ev && ev.dataTransfer) {
    ev.dataTransfer.effectAllowed = 'move';
    ev.dataTransfer.setData('text/plain', 'item:' + idx);
  }
  const card = document.getElementById(`sfisDeckCard_${idx}`) || document.getElementById(`sfisTrackCard_${idx}`);
  if (card) card.classList.add('is-dragging');
}

function sfisCardDragOver(ev, targetIdx) {
  ev.preventDefault();
  const targetItem = SFIS_HMI_STATE.items[targetIdx];
  if (!targetItem || targetItem.locked) return;
  if (SFIS_HMI_STATE.dragSrcIdx < 0 || SFIS_HMI_STATE.dragSrcIdx === targetIdx) return;
  const card = document.getElementById(`sfisDeckCard_${targetIdx}`) || document.getElementById(`sfisTrackCard_${targetIdx}`);
  if (!card) return;
  document.querySelectorAll('.sfis-deck-card, .sfis-track-card').forEach(c => {
    c.classList.remove('drop-swap', 'drop-before', 'drop-after');
  });
  if (SFIS_HMI_STATE.dragSortMode === 'swap') {
    card.classList.add('drop-swap');
    SFIS_HMI_STATE.dropTargetIdx = targetIdx;
  } else {
    const r = card.getBoundingClientRect();
    const isBefore = (ev.clientX - r.left) < (r.width / 2);
    SFIS_HMI_STATE.dropTargetIdx = targetIdx;
    SFIS_HMI_STATE.dropPos = isBefore ? 'before' : 'after';
    card.classList.add(isBefore ? 'drop-before' : 'drop-after');
  }
}

function sfisCardDragLeave(targetIdx) {
  const card = document.getElementById(`sfisDeckCard_${targetIdx}`) || document.getElementById(`sfisTrackCard_${targetIdx}`);
  if (card) card.classList.remove('drop-swap', 'drop-before', 'drop-after');
}

function sfisCardDragEnd() {
  SFIS_HMI_STATE.dragSrcIdx = -1;
  SFIS_HMI_STATE.dropTargetIdx = -1;
  document.querySelectorAll('.sfis-deck-card, .sfis-track-card').forEach(c => {
    c.classList.remove('is-dragging', 'drop-swap', 'drop-before', 'drop-after');
  });
}

function sfisDropOnTrack(targetIdx, ev) {
  if (ev) { ev.preventDefault(); ev.stopPropagation(); }
  _enforceSfisSkeleton();
  const cKind = SFIS_HMI_STATE.dragCatalogKind;
  const srcIdx = SFIS_HMI_STATE.dragSrcIdx;
  const dropPos = SFIS_HMI_STATE.dropPos || 'before';
  sfisCardDragEnd();
  SFIS_HMI_STATE.dragCatalogKind = '';
  const tailIdx = Math.max(2, SFIS_HMI_STATE.items.length - 1);
  if (cKind) { sfisAddItem(cKind, targetIdx); return; }
  const srcItem = SFIS_HMI_STATE.items[srcIdx];
  const tgtItem = SFIS_HMI_STATE.items[targetIdx];
  if (!srcItem || srcItem.locked) return;
  if (targetIdx >= 2 && targetIdx < tailIdx && tgtItem && !tgtItem.locked && srcIdx !== targetIdx) {
    if (SFIS_HMI_STATE.dragSortMode === 'swap') {
      const tmp = SFIS_HMI_STATE.items[srcIdx];
      SFIS_HMI_STATE.items[srcIdx] = SFIS_HMI_STATE.items[targetIdx];
      SFIS_HMI_STATE.items[targetIdx] = tmp;
    } else {
      const moved = SFIS_HMI_STATE.items.splice(srcIdx, 1)[0];
      let dest = targetIdx;
      if (srcIdx < targetIdx) dest = (dropPos === 'before') ? targetIdx - 1 : targetIdx;
      else dest = (dropPos === 'before') ? targetIdx : targetIdx + 1;
      dest = Math.max(2, Math.min(SFIS_HMI_STATE.items.length - 1, dest));
      SFIS_HMI_STATE.items.splice(dest, 0, moved);
    }
    SFIS_HMI_STATE.selectedUid = srcItem.uid;
    renderSfisHmiWorkspace();
  }
}

const _LOCAL_MOCK_SFIS_DB = { routed: new Set(), fields: {} };

function _runLocalBrowserSfisMock(action, params = {}) {
  const p = params || {};
  const act = String(action || '').trim();
  const isn = String(p.isn || '2695160300001').trim() || '2695160300001';
  const device = String(p.device || '710001').trim() || '710001';
  const op = String(p.op || 'S09166390').trim() || 'S09166390';
  if (!_LOCAL_MOCK_SFIS_DB.fields[isn]) {
    _LOCAL_MOCK_SFIS_DB.fields[isn] = {
      SNA: 'NULL', SNB: 'TEST_SNB_DEFAULT', SNC: 'PID_AURORA_1A',
      SND: 'SSN_90AA2210', SNE: 'NULL', SNF: 'NULL', SNG: 'NULL',
      MAC1: '48210B47E42C', SSN: `SSN_${isn.slice(-6)}`
    };
  }
  const store = _LOCAL_MOCK_SFIS_DB.fields[isn];
  const sep = '\x1f';
  if (act === 'WTSP_LOGINOUT') {
    const st = (p.status !== undefined && p.status !== '') ? parseInt(p.status, 10) : 1;
    const raw = (st === 0) ? `1Logout OK (${op} @ ${device})` : `1Welcome using Pegatron SFIS:${op}(模擬OP)${op}OP`;
    return { status: 'ok', reachable: true, is_mock: true, http_code: 200, passed: true, ret_code: '1', msg: raw, slots: {}, raw_result: raw };
  }
  if (act === 'WTSP_CHKROUTE') {
    if (_LOCAL_MOCK_SFIS_DB.routed.has(isn)) {
      const msg = `Route Error: ISN [${isn}] 已於本機模擬資料庫過站完成（可點重置模擬DB清站）`;
      return { status: 'ok', reachable: true, is_mock: true, http_code: 200, passed: false, ret_code: '0', msg, slots: {}, raw_result: `0${sep}${msg}` };
    }
    const msg = `ISN [${isn}] Route OK @ Device [${device}] (本機模擬內網)`;
    return { status: 'ok', reachable: true, is_mock: true, http_code: 200, passed: true, ret_code: '1', msg, slots: {}, raw_result: `1${sep}${msg}` };
  }
  if (act === 'WTSP_GETVERSION') {
    const vt = String(p.ver_type || 'ISN_BASEINFO').trim().toUpperCase();
    const c1 = String(p.chk_data || '').trim();
    const c2 = String(p.chk_data2 || '').trim();
    const slots = { P_CAVER: '', P_CBVER: '', P_CCVER: '', P_CDVER: '', P_IAVER: '', P_IBVER: '' };
    let msg = '';
    if (vt === 'ITEMINFO') {
      slots.P_CAVER = '1';
      slots.P_CBVER = 'PL_AURORA/PEGA;';
      slots.P_CCVER = `60_${isn}`;
      slots.P_CDVER = `90AA221000S0_${isn.slice(-5)}`;
      msg = `TYPE:[ITEMINFO] GET INFO ISN:[${isn}/60_${isn}] TYPE:[ITEMINFO] OK!!`;
    } else if (vt === 'MOKP_SN') {
      slots.P_CAVER = `SN:90AA221000S0_${isn.slice(-5)};IMEI:35888109${isn.slice(-5)};SW:V1.0.6;`;
      slots.P_CBVER = '90AA221000S0';
      msg = `TYPE:[MOKP_SN] OK!! (${c1 || 'MB'})`;
    } else if (vt === 'GET_IVMAC_NEW') {
      slots.P_CAVER = `GUID1:AA11${isn.slice(-4)};GUID2:BB22${isn.slice(-4)};MAC1:48210B47E42C;`;
      msg = 'TYPE:[GET_IVMAC_NEW] OK!!';
    } else if (vt === 'ITEM_FEATURE_BASEINFO') {
      slots.P_CAVER = `${isn};90AA-221000S0`;
      slots.P_CBVER = `${isn};69B35-AURORA`;
      slots.P_CCVER = `;${c1 || 'AURORA'};${c2 || 'ModelNumber'};PL_AURORA1A;1;`;
      slots.P_CDVER = 'N/A';
      msg = 'TYPE:[ITEM_FEATURE_BASEINFO] OK!!';
    } else if (vt === 'GETSN_BYRULE') {
      slots.P_CAVER = `M${isn.slice(-8)}01,`;
      msg = `TYPE:[GETSN_BYRULE] M${isn.slice(-8)}01, DATA GOT!!`;
    } else if (vt === 'ASSIGN_SSN') {
      slots.P_CAVER = `[ITEM2,CUSTITEMNM,1]SSN${isn.slice(-7)}`;
      msg = 'TYPE:[ASSIGN_SSN] OK!!';
    } else {
      const val = store[c1] || store[c1.toUpperCase()] || `MOCK_${c1 || 'DATA'}`;
      slots.P_CAVER = val;
      slots.P_CBVER = `90AA221000S0;${val};`;
      slots.P_CCVER = `KEY:${c1 || 'MAC1'};VAL:${val};DATE:2026/11/24;`;
      msg = `TYPE:[${vt}] DATA GOT!! (${c1 || 'ISN_BASEINFO'})`;
    }
    const raw = ['1', msg, slots.P_CAVER, slots.P_CBVER, slots.P_CCVER, slots.P_CDVER, slots.P_IAVER, slots.P_IBVER].join(sep);
    return { status: 'ok', reachable: true, is_mock: true, http_code: 200, passed: true, ret_code: '1', msg, slots, raw_result: raw };
  }
  if (act === 'WTSP_GETIMAC') {
    const macs = `${store.MAC1 || '48210B47E42C'},48210B47E42D`;
    const msg = `GETIMAC OK (${macs})`;
    return { status: 'ok', reachable: true, is_mock: true, http_code: 200, passed: true, ret_code: '1', msg, slots: { P_CAVER: macs }, raw_result: `1${sep}${msg}${sep}${macs}` };
  }
  if (act === 'WTSP_GETLABEL') {
    const lbl = `ISN:${isn};PN:90AA221000S0;QTY:1;`;
    const msg = `GETLABEL OK (${lbl})`;
    return { status: 'ok', reachable: true, is_mock: true, http_code: 200, passed: true, ret_code: '1', msg, slots: { P_CAVER: lbl }, raw_result: `1${sep}${msg}${sep}${lbl}` };
  }
  if (act === 'WTSP_RESULT') {
    let dataStr = String(p.data || '').trim();
    const sk = String(p.save_key || '').trim();
    const sv = String(p.save_val || '');
    if (!dataStr && sk) dataStr = `#SAVE:${sk}=${sv};`;
    const rx = /#SAVE:([^=;]+)=([^;]*)/gi;
    let m;
    while ((m = rx.exec(dataStr)) !== null) {
      const k = m[1].trim().split(':')[0];
      store[k] = m[2].trim() || 'NULL';
    }
    const st = (p.status !== undefined && p.status !== '') ? parseInt(p.status, 10) : 1;
    if (st === 1) _LOCAL_MOCK_SFIS_DB.routed.add(isn);
    const msg = `P_RET=1 RESULT SAVED (Mock): ${dataStr || 'PASS'}`;
    return { status: 'ok', reachable: true, is_mock: true, http_code: 200, passed: true, ret_code: '1', msg, slots: {}, raw_result: `1${sep}${msg}` };
  }
  const msg = `${act} Mock OK`;
  return { status: 'ok', reachable: true, is_mock: true, http_code: 200, passed: true, ret_code: '1', msg, slots: {}, raw_result: `1${sep}${msg}` };
}

async function _callSingleSoap(action, extraParams = {}) {
  const cfg = SFIS_HMI_STATE.config;
  const fullParams = { device: cfg.device_id, isn: cfg.isn, tsp: cfg.tsp, op: cfg.op, ...extraParams };
  // 若使用者選「本機模擬 SFIS 內網」且偵測後端仍為尚未重啟的舊版伺服器，直接在瀏覽器引擎即時執行模擬，免等逾時
  if (SFIS_HMI_STATE.mockMode && window.__SERVER_BUILD__ && window.__SERVER_BUILD__ !== 'Build v0.8.045') {
    return _runLocalBrowserSfisMock(action, fullParams);
  }
  try {
    const resp = await fetch('/api/sfis_soap_test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: cfg.url,
        action,
        mock: !!SFIS_HMI_STATE.mockMode,
        params: fullParams
      })
    });
    const data = await resp.json();
    // 雙重保險：即使舊版後端忽略 mock:true 誤跑實網而逾時，在模擬模式下仍自動接手回傳模擬 PASS
    if (SFIS_HMI_STATE.mockMode && (!data || data.is_mock !== true)) {
      return _runLocalBrowserSfisMock(action, fullParams);
    }
    return data;
  } catch (err) {
    if (SFIS_HMI_STATE.mockMode) {
      return _runLocalBrowserSfisMock(action, fullParams);
    }
    throw err;
  }
}

function sfisToggleSlowDemo(checked) {
  SFIS_HMI_STATE.anim.slowDemo = !!checked;
  try { localStorage.setItem('centimani_sfis_slow_demo', checked ? '1' : '0'); } catch (e) {}
  renderSfisHmiWorkspace();
}

function _sfisSleep(ms) {
  return ms > 0 ? new Promise(r => setTimeout(r, ms)) : Promise.resolve();
}

async function sfisHmiRunStep(idx, skipConfirm = false, overrideAnimTotalMs = null) {
  const it = SFIS_HMI_STATE.items[idx];
  if (!it) return true;
  SFIS_HMI_STATE.selectedUid = it.uid;
  const meta = _getBlockMeta(it.kind);
  const f = _resolveCardField(it);
  const isn = SFIS_HMI_STATE.config.isn || '(空)';

  if (!skipConfirm && (it.kind === 'savelink' || it.kind === 'rw')) {
    const okConfirm = confirm(
      `⚠️ 單顆 ISN 寫入保護確認\n\n` +
      `即將對「目前唯一選中 ISN：${isn}」執行寫入：\n` +
      `• 欄位：#SAVE:${f}\n• 寫入值：${it.save_val || 'TEST_VAL'}\n\n確定送出嗎？`
    );
    if (!okConfirm) return false;
  }

  const totalAnimMs = (overrideAnimTotalMs !== null)
    ? overrideAnimTotalMs
    : ((SFIS_HMI_STATE.anim.slowDemo !== false) ? 3000 : 0);
  const segMs = totalAnimMs > 0 ? Math.round(totalAnimMs / 3) : 0;

  it.status = 'running';
  it.resultMsg = '通訊傳輸中...';
  SFIS_HMI_STATE.anim.phase = 'sending';
  SFIS_HMI_STATE.anim.stage = 'to_cloud';
  SFIS_HMI_STATE.anim.packetText = `⬆ ${meta.title}`;
  SFIS_HMI_STATE.anim.actionLabel = `#${idx + 1} PC ➔ 雲端發送中...`;
  renderSfisHmiWorkspace();

  const _execSoap = async () => {
    let data = {};
    let sentCmd = '';
    if (it.kind === 'login') {
      const stCode = String(it.login_status || '1') === '0' ? 0 : 1;
      sentCmd = `WTSP_LOGINOUT(op="${SFIS_HMI_STATE.config.op}", device="${SFIS_HMI_STATE.config.device_id}", status=${stCode} [${stCode === 1 ? 'Login' : 'Logout'}])`;
      data = await _callSingleSoap('WTSP_LOGINOUT', { status: stCode });
    } else if (it.kind === 'checkroute') {
      sentCmd = `WTSP_CHKROUTE(ISN="${isn}", device="${SFIS_HMI_STATE.config.device_id}")`;
      data = await _callSingleSoap('WTSP_CHKROUTE', { checkFlag: '1', checkData: '', route_type: 1 });
    } else if (it.kind === 'get' || it.kind === 'getversion') {
      const st = _itemToBackendStep(it);
      sentCmd = `WTSP_GETVERSION(ISN="${isn}", type="${st.ver_type}", ChkData="${st.chk_data}")`;
      data = await _callSingleSoap('WTSP_GETVERSION', { ver_type: st.ver_type, chk_data: st.chk_data, chk_data2: st.chk_data2 });
    } else if (it.kind === 'getimac') {
      sentCmd = `WTSP_GETIMAC(ISN="${isn}", device="${SFIS_HMI_STATE.config.device_id}")`;
      data = await _callSingleSoap('WTSP_GETIMAC', { imacnum: 1 });
    } else if (it.kind === 'getlabel') {
      sentCmd = `WTSP_GETLABEL(ISN="${isn}", type="${it.label_type || 'ISN'}", DEV="${SFIS_HMI_STATE.config.device_id}")`;
      data = await _callSingleSoap('WTSP_GETLABEL', { label_type: it.label_type || 'ISN' });
    } else if (it.kind === 'savelink') {
      const val = it.save_val || 'TEST_VAL';
      sentCmd = `WTSP_RESULT(ISN="${isn}", data="#SAVE:${f}=${val};", status=1, TSP="PASS")`;
      data = await _callSingleSoap('WTSP_RESULT', { save_key: f, save_val: val, status: 1, result_tsp: 'PASS' });
    } else if (it.kind === 'rw') {
      const val = it.save_val || 'TEST_RW_01';
      sentCmd = `[1/2 WRITE] #SAVE:${f}=${val} ➔ [2/2 GET] ${f}`;
      const wr = await _callSingleSoap('WTSP_RESULT', { save_key: f, save_val: val, status: 1, result_tsp: 'PASS' });
      if (!wr.passed) {
        data = wr;
      } else {
        const rd = await _callSingleSoap('WTSP_GETVERSION', { ver_type: 'ISN_BASEINFO', chk_data: f, chk_data2: '' });
        const got = (rd.slots && rd.slots.P_CAVER) ? rd.slots.P_CAVER : '';
        const matchOk = rd.passed && (got === val);
        data = {
          ...rd,
          passed: matchOk,
          msg: matchOk ? `寫入 [${val}] 與回讀 [${got}] 一致` : `寫入 [${val}]，回讀 [${got || rd.msg || '空'}]`
        };
      }
    } else if (it.kind === 'clear') {
      sentCmd = `[1/2 CLEAR] #SAVE:${f}=; ➔ [2/2 GET] ${f}`;
      const wr = await _callSingleSoap('WTSP_RESULT', { data: `#SAVE:${f}=;`, status: 1, result_tsp: 'PASS' });
      if (!wr.passed) {
        data = wr;
      } else {
        const rd = await _callSingleSoap('WTSP_GETVERSION', { ver_type: 'ISN_BASEINFO', chk_data: f, chk_data2: '' });
        const got = (rd.slots && rd.slots.P_CAVER) ? rd.slots.P_CAVER : '';
        data = { ...rd, msg: `清除後回讀值 [${got || '(空/NULL)'}]` };
      }
    }
    return { data, sentCmd };
  };

  try {
    // 立即於背景平行發送 SOAP，同時進行第 1 階段動畫 (PC ➔ 雲端)
    const soapPromise = _execSoap();
    if (segMs > 0) {
      await _sfisSleep(segMs);
      SFIS_HMI_STATE.anim.stage = 'to_db';
      SFIS_HMI_STATE.anim.actionLabel = `#${idx + 1} 雲端 ➔ SFIS DB 查詢/寫入中...`;
      renderSfisHmiWorkspace();
    }

    const [{ data, sentCmd }] = await Promise.all([soapPromise, _sfisSleep(segMs)]);
    const ok = !!data.passed;
    const offline = !data.reachable || data.status === 'offline';

    if (segMs > 0) {
      // 第 3 階段動畫：DB 吐回結果沿原路飛回 PC
      SFIS_HMI_STATE.anim.stage = 'to_pc';
      SFIS_HMI_STATE.anim.phase = offline ? 'offline' : (ok ? 'pass' : 'fail');
      SFIS_HMI_STATE.anim.packetText = ok ? `⬇ P_RET=1 ✅` : (offline ? '⬇ 離線 ⚠️' : '⬇ FAIL ❌');
      SFIS_HMI_STATE.anim.actionLabel = `#${idx + 1} SFIS DB ➔ 傳回結果至測試 PC...`;
      renderSfisHmiWorkspace();
      await _sfisSleep(segMs);
    }

    if (it.kind === 'login') {
      const stCode = String(it.login_status || '1') === '0' ? 0 : 1;
      if (data.passed) SFIS_HMI_STATE.anim.opLoggedIn = (stCode === 1);
      else if (data.reachable) SFIS_HMI_STATE.anim.opLoggedIn = false;
    }

    SFIS_HMI_STATE.anim.stage = 'idle';
    SFIS_HMI_STATE.anim.packetText = '';
    SFIS_HMI_STATE.anim.netConnected = !offline;
    SFIS_HMI_STATE.anim.phase = offline ? 'offline' : (ok ? 'pass' : 'fail');
    it.status = offline ? 'offline' : (ok ? 'pass' : 'fail');
    const slots = data.slots || {};
    const valStr = slots.P_CAVER || slots.P_CBVER || '';
    const detailTxt = offline
      ? ((data.msg || '無法連通廠區內網') + (SFIS_HMI_STATE.mockMode ? '' : '（目前非工廠內網，可重選「🧪 本機模擬」演練）'))
      : (ok ? (valStr ? `✅ 值：${valStr} (${data.msg || 'PASS'})` : `✅ ${data.msg || 'PASS'}`) : `❌ ${data.msg || 'FAIL'}`);
    it.resultMsg = detailTxt;
    it.lastRaw = data.raw_result || data.msg || '';
    it.lastRetCode = data.ret_code || '-';
    it.lastMsg = data.msg || '';
    it.lastSlots = slots;
    it.sentCmd = sentCmd;
    SFIS_HMI_STATE.anim.actionLabel = `#${idx + 1} ${meta.title} ➔ ${ok ? '✅ PASS' : (offline ? '⚠️ 離線' : '❌ FAIL')}`;
    if (ok && (it.kind === 'savelink' || it.kind === 'rw') && isn && !SFIS_HMI_STATE.usedIsns.includes(isn)) {
      SFIS_HMI_STATE.usedIsns.push(isn);
      _saveSfisProfilesToBackend({ used_isns: SFIS_HMI_STATE.usedIsns });
    }
    _pushResponseLog(`#${idx + 1} ${meta.title}`, sentCmd, data, it.uid);
    renderSfisHmiWorkspace();
    return ok;
  } catch (e) {
    SFIS_HMI_STATE.anim.stage = 'idle';
    SFIS_HMI_STATE.anim.packetText = '';
    it.status = 'fail';
    it.resultMsg = String(e);
    SFIS_HMI_STATE.anim.phase = 'fail';
    _pushResponseLog(`#${idx + 1} ${meta.title}`, 'Request Error', { passed: false, reachable: false, ret_code: 'ERR', msg: String(e) }, it.uid);
    renderSfisHmiWorkspace();
    return false;
  }
}

async function sfisHmiRunAll() {
  if (SFIS_HMI_STATE.isRunning || !SFIS_HMI_STATE.items.length) return;
  const hasWrite = SFIS_HMI_STATE.items.some(it => it.kind === 'savelink' || it.kind === 'rw');
  const isn = SFIS_HMI_STATE.config.isn || '(空)';
  if (hasWrite) {
    const okC = confirm(
      `⚠️ 單顆 ISN 順序實測確認\n\n` +
      `本次只會對單一選中的 ISN [${isn}] 依序執行右側 ${SFIS_HMI_STATE.items.length} 個步驟（包含寫入步驟）。\n` +
      `確定開始執行嗎？`
    );
    if (!okC) return;
  }
  SFIS_HMI_STATE.isRunning = true;
  renderSfisHmiWorkspace();
  const perStepMs = (SFIS_HMI_STATE.anim.slowDemo !== false) ? 1200 : 0;
  try {
    for (let i = 0; i < SFIS_HMI_STATE.items.length; i++) {
      const ok = await sfisHmiRunStep(i, true, perStepMs);
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
    alert('右側至少需要 1 張會產出 Excel 步驟的積木（CheckRoute / GET / WRITE / R/W），Login 僅作連通與 System.ini 設定。');
    return;
  }
  if (mode === 'insert_current' && (typeof STATE === 'undefined' || !STATE.workspace)) {
    alert('目前尚未開啟任何測試腳本，請改點「📥 抄空白範本產生 SFIS Excel」。');
    return;
  }
  try {
    const res = await fetch('/api/export_sfis_hmi_script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        open_excel: true,
        items: itemsPayload,
        config: cfg,
        workspace: (mode === 'insert_current' && typeof STATE !== 'undefined') ? STATE.workspace : null
      })
    });
    const data = await res.json();
    if (data.status !== 'ok') { alert('匯出失敗：' + (data.message || '未知錯誤')); return; }
    if (mode === 'insert_current') {
      STATE.workspace = data.workspace;
      STATE.report = data.report;
      if (typeof renderStations === 'function') renderStations();
      if (typeof renderAuditAlerts === 'function') renderAuditAlerts();
      if (typeof switchGenSubMode === 'function') switchGenSubMode('edit');
      alert(`✅ 已將 ${data.inserted_count} 列 SFIS 標準步驟（含 :ShowISN 與 ExecMode=8）插入 [${data.station}] 開頭！\n(System.ini: SFIS_SkipSaveResultOnFail=${cfg.skip_save_on_fail ? 1 : 0})`);
      return;
    }
    const skipStr = cfg.skip_save_on_fail ? '1（測錯故意不上傳）' : '0';
    alert(
      `✅ 已抄空白母體範本產出專屬 SFIS Excel 驗證檔，並已自動開啟輸出目錄與 Excel！\n\n` +
      `• Excel 路徑：${data.excel_path}\n` +
      `• System.ini：SFIS_SkipSaveResultOnFail=${skipStr} + Checksum 已簽章\n` +
      `• 健檢結果：${data.audit_report.error_count} Error / ${data.audit_report.warning_count} Warning`
    );
  } catch (e) {
    alert('匯出發生錯誤：' + e);
  }
}

function _renderSimpleCardInputs(it, idx) {
  if (it.kind === 'login') {
    const isOut = (String(it.login_status || '1') === '0');
    return `
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <label style="display:inline-flex; align-items:center; gap:4px; cursor:pointer; font-size:0.8rem; font-weight:700; padding:3px 9px; border-radius:6px; border:1px solid ${!isOut ? '#0284C7' : '#CBD5E1'}; background:${!isOut ? '#E0F2FE' : '#FFFFFF'};">
          <input type="radio" name="sfisLoginMod_${idx}" value="1" ${!isOut ? 'checked' : ''} onchange="sfisUpdateItemField(${idx},'login_status','1')"> 🔐 Login 登入
        </label>
        <label style="display:inline-flex; align-items:center; gap:4px; cursor:pointer; font-size:0.8rem; font-weight:700; padding:3px 9px; border-radius:6px; border:1px solid ${isOut ? '#0284C7' : '#CBD5E1'}; background:${isOut ? '#E0F2FE' : '#FFFFFF'};">
          <input type="radio" name="sfisLoginMod_${idx}" value="0" ${isOut ? 'checked' : ''} onchange="sfisUpdateItemField(${idx},'login_status','0')"> 🚪 Logout 登出
        </label>
      </div>`;
  }
  if (it.kind === 'checkroute') {
    return '';
  }

  const fk = it.field_key || it.save_key || it.chk_data || 'SNA';
  const isCustom = (fk === '__CUSTOM__');
  const opts = SFIS_PROXY_FIELDS.map(p => `<option value="${p.key}" ${fk === p.key ? 'selected' : ''}>${_escH(p.label)}</option>`).join('') +
    `<option value="__CUSTOM__" ${isCustom ? 'selected' : ''}>✏️ 自填其他欄位...</option>`;

  const fieldSelectHtml = `
    <label style="font-size:0.78rem; font-weight:700; color:#334155;">欄位：
      <select onchange="sfisUpdateItemField(${idx},'field_key',this.value)" style="padding:3px 6px; border:1px solid #94A3B8; border-radius:5px; font-size:0.8rem;">${opts}</select>
    </label>
    ${isCustom ? `<input type="text" value="${_escH(it.custom_field || '')}" placeholder="例：BT1 / SN1" oninput="sfisUpdateItemField(${idx},'custom_field',this.value)" class="mono" style="width:110px; padding:3px 6px; border:1px solid #94A3B8; border-radius:5px; font-size:0.8rem;">` : ''}
  `;

  if (it.kind === 'get' || it.kind === 'getversion' || it.kind === 'getimac') {
    const isImac = (it.kind === 'getimac');
    const vt = it.ver_type || 'ISN_BASEINFO';
    const vtOpts = SFIS_GETVERSION_TYPES.map(t => `<option value="${t.value}" ${vt === t.value ? 'selected' : ''}>${_escH(t.label)}</option>`).join('');
    const curSlotCode = String(it.slot_code || '2');
    const slotList = [
      { code: '2', name: 'P_CAVER' },
      { code: '3', name: 'P_CBVER' },
      { code: '4', name: 'P_CCVER' },
      { code: '5', name: 'P_CDVER' },
      { code: '6', name: 'P_IAVER' },
      { code: '7', name: 'P_IBVER' }
    ];
    const hasRan = !!it.lastSlots;
    const slotMap = { '2': 'P_CAVER', '3': 'P_CBVER', '4': 'P_CCVER', '5': 'P_CDVER', '6': 'P_IAVER', '7': 'P_IBVER' };
    const pickedKey = slotMap[curSlotCode] || 'P_CAVER';
    const pickedRawVal = (it.lastSlots && it.lastSlots[pickedKey]) ? String(it.lastSlots[pickedKey]) : '';
    const slicedVal = pickedRawVal ? _previewCentimaniSlice(pickedRawVal, it) : '';
    const refExprStr = _buildCentimaniRefExpr(it);

    let slotsGridHtml = '';
    if (hasRan) {
      const renderSlotRow = (sl) => {
        const val = String((it.lastSlots && it.lastSlots[sl.name]) || '');
        const isSel = (curSlotCode === sl.code);
        return `
          <div style="display:flex; align-items:center; gap:5px; padding:2px 5px; border-radius:4px; background:${isSel ? '#DBEAFE' : '#FFFFFF'}; border:1px solid ${isSel ? '#3B82F6' : '#E2E8F0'};">
            <span class="mono" style="font-size:0.75rem; font-weight:900; color:#1E40AF; min-width:74px;">[${sl.code}] ${sl.name}</span>
            <span class="mono" style="flex:1; font-size:0.76rem; color:${val ? '#0F172A' : '#94A3B8'}; word-break:break-all;">${_escH(val || '(空)')}</span>
            <button type="button" onclick="sfisPickSlotIndex(${idx},'${sl.code}')" style="padding:1px 6px; font-size:0.72rem; border-radius:4px; border:1px solid ${isSel ? '#1D4ED8' : '#94A3B8'}; background:${isSel ? '#1D4ED8' : '#F8FAFC'}; color:${isSel ? '#FFFFFF' : '#334155'}; cursor:pointer; font-weight:800;">
              ${isSel ? `✓ 已選第${sl.code}格` : `選第${sl.code}格`}
            </button>
          </div>`;
      };
      const nonEmptyExists = slotList.some(sl => String((it.lastSlots && it.lastSlots[sl.name]) || '').trim() !== '');
      const visibleSlots = [];
      const emptySlots = [];
      slotList.forEach(sl => {
        const val = String((it.lastSlots && it.lastSlots[sl.name]) || '').trim();
        const isSel = (curSlotCode === sl.code);
        if (val || isSel || (!nonEmptyExists && sl.code === '2')) visibleSlots.push(sl);
        else emptySlots.push(sl);
      });
      const emptyRangeLbl = emptySlots.length
        ? (emptySlots.length > 1 ? `[${emptySlots[0].code}]~[${emptySlots[emptySlots.length - 1].code}]` : `[${emptySlots[0].code}]`)
        : '';
      const emptyFoldHtml = emptySlots.length ? `
        <details class="sfis-empty-slots-fold" style="margin-top:3px;">
          <summary style="cursor:pointer; font-size:0.74rem; font-weight:700; color:#64748B; padding:2px 4px;">▸ 折疊 ${emptySlots.length} 格無資料欄位（${emptyRangeLbl}・需要時點擊展開）</summary>
          <div style="display:flex; flex-direction:column; gap:3px; margin-top:4px;">${emptySlots.map(renderSlotRow).join('')}</div>
        </details>` : '';
      slotsGridHtml = `
        <div style="margin-top:6px; background:#F8FAFC; border:1px solid #BFDBFE; border-radius:6px; padding:6px 8px;">
          <div style="font-size:0.76rem; font-weight:800; color:#1E3A8A; margin-bottom:4px;">
            🎯 SFIS [0~7] 堆疊回傳位置（[0]P_RET=${_escH(it.lastRetCode || '-')} · [1]P_Msg=${_escH((it.lastMsg || '').slice(0, 42))}）：
          </div>
          <div style="display:flex; flex-direction:column; gap:3px;">${visibleSlots.map(renderSlotRow).join('')}</div>
          ${emptyFoldHtml}
        </div>`;
    }

    let segBtnsHtml = '';
    if (pickedRawVal && (pickedRawVal.includes(';') || pickedRawVal.includes(','))) {
      const autoDelim = pickedRawVal.includes(';') ? ';' : ',';
      const segs = pickedRawVal.split(autoDelim).filter((x, i, a) => !(i === a.length - 1 && x === ''));
      segBtnsHtml = `<div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px; align-items:center;"><span style="font-size:0.71rem; color:#475569; font-weight:700;">快速點切段(${autoDelim === ';' ? '分號;' : '逗號,'})：</span>` +
        segs.map((sg, si) => `<button type="button" onclick="sfisPickSegment(${idx},'${autoDelim}',${si})" style="padding:1px 6px; font-size:0.71rem; border-radius:4px; border:1px solid ${(it.ref_mode === 'split' && parseInt(it.ref_seg_idx, 10) === si) ? '#059669' : '#CBD5E1'}; background:${(it.ref_mode === 'split' && parseInt(it.ref_seg_idx, 10) === si) ? '#DCFCE7' : '#FFFFFF'}; cursor:pointer;" class="mono">[${si}] ${_escH(sg)}</button>`).join('') + `</div>`;
    }

    const rm = it.ref_mode || 'raw';
    const refExtraInputs = rm === 'split'
      ? `<label style="font-size:0.72rem;">分隔字:<input type="text" value="${_escH(it.ref_delim || ';')}" oninput="sfisUpdateItemField(${idx},'ref_delim',this.value)" class="mono" style="width:36px; padding:2px 4px; border:1px solid #94A3B8; border-radius:4px;"></label>
         <label style="font-size:0.72rem;">第N段(0起):<input type="number" min="0" value="${parseInt(it.ref_seg_idx || 0, 10) || 0}" oninput="sfisUpdateItemField(${idx},'ref_seg_idx',this.value)" class="mono" style="width:42px; padding:2px 4px; border:1px solid #94A3B8; border-radius:4px;"></label>`
      : (rm === 'within'
        ? `<label style="font-size:0.72rem;">左界:<input type="text" value="${_escH(it.ref_left || 'SN:')}" oninput="sfisUpdateItemField(${idx},'ref_left',this.value)" class="mono" style="width:70px; padding:2px 4px; border:1px solid #94A3B8; border-radius:4px;"></label>
           <label style="font-size:0.72rem;">右界:<input type="text" value="${_escH(it.ref_right || ';')}" oninput="sfisUpdateItemField(${idx},'ref_right',this.value)" class="mono" style="width:65px; padding:2px 4px; border:1px solid #94A3B8; border-radius:4px;"></label>`
        : (rm === 'ma' || rm === 'mb'
          ? `<label style="font-size:0.72rem;">定位字:<input type="text" value="${_escH(it.ref_marker || (rm === 'ma' ? ':' : ';'))}" oninput="sfisUpdateItemField(${idx},'ref_marker',this.value)" class="mono" style="width:70px; padding:2px 4px; border:1px solid #94A3B8; border-radius:4px;"></label>`
          : (rm === 'substr'
            ? `<label style="font-size:0.72rem;">起始:<input type="number" min="0" value="${parseInt(it.ref_sub_start || 0, 10) || 0}" oninput="sfisUpdateItemField(${idx},'ref_sub_start',this.value)" class="mono" style="width:44px; padding:2px 4px; border:1px solid #94A3B8; border-radius:4px;"></label>
               <label style="font-size:0.72rem;">長度:<input type="number" min="1" value="${parseInt(it.ref_sub_len || 12, 10) || 12}" oninput="sfisUpdateItemField(${idx},'ref_sub_len',this.value)" class="mono" style="width:46px; padding:2px 4px; border:1px solid #94A3B8; border-radius:4px;"></label>`
            : '')));

    const topInputs = isImac
      ? `<span style="font-size:0.78rem; font-weight:700; color:#0F766E;">WTSP_GETIMAC 配發/讀取 MAC（結果於第 2 格起）</span>`
      : `<div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
           <label style="font-size:0.76rem; font-weight:700;">type:<select onchange="sfisUpdateItemField(${idx},'ver_type',this.value)" style="padding:3px 5px; border:1px solid #94A3B8; border-radius:5px; font-size:0.77rem; max-width:190px;">${vtOpts}</select></label>
           ${vt === 'ISN_BASEINFO' ? fieldSelectHtml : `<label style="font-size:0.76rem; font-weight:700;">ChkData:<input type="text" value="${_escH(it.chk_data || '')}" oninput="sfisUpdateItemField(${idx},'chk_data',this.value)" class="mono" style="width:88px; padding:3px 5px; border:1px solid #94A3B8; border-radius:5px; font-size:0.77rem;"></label><label style="font-size:0.76rem; font-weight:700;">Chk2:<input type="text" value="${_escH(it.chk_data2 || '')}" oninput="sfisUpdateItemField(${idx},'chk_data2',this.value)" class="mono" style="width:85px; padding:3px 5px; border:1px solid #94A3B8; border-radius:5px; font-size:0.77rem;"></label>`}
           <label style="font-size:0.76rem; font-weight:700;">取第<select onchange="sfisUpdateItemField(${idx},'slot_code',this.value)" style="padding:2px 4px; border:1px solid #3B82F6; border-radius:4px; font-size:0.77rem;">${slotList.map(sl => `<option value="${sl.code}" ${curSlotCode === sl.code ? 'selected' : ''}>${sl.code} (${sl.name})</option>`).join('')}</select>格</label>
         </div>`;

    return `
      ${topInputs}
      ${slotsGridHtml}
      <div style="margin-top:6px; background:#ECFDF5; border:1px solid #A7F3D0; border-radius:6px; padding:5px 8px;">
        <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
          <span style="font-size:0.74rem; font-weight:800; color:#065F46;">✂️ Ref 找字串：</span>
          <select onchange="sfisUpdateItemField(${idx},'ref_mode',this.value)" style="padding:2px 5px; border:1px solid #6EE7B7; border-radius:4px; font-size:0.75rem;">
            <option value="raw" ${rm === 'raw' ? 'selected' : ''}>全取 (不切)</option>
            <option value="split" ${rm === 'split' ? 'selected' : ''}>依分隔字切段 (:SplitString)</option>
            <option value="within" ${rm === 'within' ? 'selected' : ''}>前後關鍵字夾取 (:WithinString)</option>
            <option value="ma" ${rm === 'ma' ? 'selected' : ''}>抓特定字後面 (:maString)</option>
            <option value="mb" ${rm === 'mb' ? 'selected' : ''}>抓特定字前面 (:mbString)</option>
            <option value="substr" ${rm === 'substr' ? 'selected' : ''}>固定位置長度 (:SubString)</option>
            <option value="getmac2" ${rm === 'getmac2' ? 'selected' : ''}>自動抓 12 碼 MAC (:getMAC2)</option>
          </select>
          ${refExtraInputs}
          <label style="font-size:0.73rem; font-weight:700;">變數:<input type="text" value="${_escH(it.ref_var || 'sfData')}" oninput="sfisUpdateItemField(${idx},'ref_var',this.value)" class="mono" style="width:76px; padding:2px 4px; border:1px solid #94A3B8; border-radius:4px;"></label>
        </div>
        ${segBtnsHtml}
        <div id="sfisSlicePrev_${idx}" class="mono" style="margin-top:4px; font-size:0.72rem; color:#047857; font-weight:800; word-break:break-all;">
          ${pickedRawVal ? `預期切出：${_escH(slicedVal)}  |  ` : ''}Ref 公式：${_escH(refExprStr)}
        </div>
      </div>`;
  }
  if (it.kind === 'getlabel') {
    return `<label style="font-size:0.78rem; font-weight:700;">標籤 Type：<input type="text" value="${_escH(it.label_type || 'ISN')}" oninput="sfisUpdateItemField(${idx},'label_type',this.value)" class="mono" style="width:110px; padding:3px 6px; border:1px solid #94A3B8; border-radius:5px;"></label>`;
  }
  if (it.kind === 'savelink' || it.kind === 'rw') {
    return `
      <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
        ${fieldSelectHtml}
        <label style="font-size:0.78rem; font-weight:700; color:#334155;">寫入值：
          <input type="text" value="${_escH(it.save_val || '')}" placeholder="例：TEST_001" oninput="sfisUpdateItemField(${idx},'save_val',this.value)" class="mono" style="width:145px; padding:3px 6px; border:1px solid #94A3B8; border-radius:5px; font-size:0.8rem;">
        </label>
      </div>`;
  }
  if (it.kind === 'clear') {
    return `<div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">${fieldSelectHtml}</div>`;
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
  _enforceSfisSkeleton();
  const s = SFIS_HMI_STATE;
  const cfg = s.config;
  const a = s.anim;
  const curPlant = SFIS_PLANT_PRESETS.find(p => p.id === s.plantId) || SFIS_PLANT_PRESETS[0];

  const plantOptions = SFIS_PLANT_PRESETS.map(p =>
    `<option value="${p.id}" ${s.plantId === p.id ? 'selected' : ''}>${_escH(p.label)}</option>`
  ).join('');

  const isSending = (a.phase === 'sending');
  const isPass = (a.phase === 'pass');
  const isFail = (a.phase === 'fail');
  const isOffline = (a.phase === 'offline');
  const netColor = a.netConnected === true ? '#16A34A' : (a.netConnected === false ? '#DC2626' : '#94A3B8');
  const opText = a.opLoggedIn === true ? '✅ 已登入' : (a.opLoggedIn === false ? '⬜ 未登入/登出' : '⏳ 待測');
  const opColor = a.opLoggedIn === true ? '#15803D' : (a.opLoggedIn === false ? '#64748B' : '#94A3B8');
  const dbLedColor = isPass ? '#16A34A' : (isFail ? '#DC2626' : (isOffline ? '#D97706' : '#94A3B8'));
  const lineClass = isSending ? 'sfis-flow-line sending' : (isPass ? 'sfis-flow-line pass' : (isFail ? 'sfis-flow-line fail' : 'sfis-flow-line'));

  const showList = (a.responseViewMode === 'selected')
    ? a.logs.filter(l => l.uid && l.uid === s.selectedUid)
    : ((a.responseViewMode === 'latest' && a.logs.length) ? [a.logs[0]] : a.logs);
  const logsHtml = showList.length ? showList.map(l => `
    <div style="border-bottom:1px dashed #334155; padding:5px 0;">
      <div style="display:flex; justify-content:space-between; gap:6px; font-size:0.77rem; font-weight:800; color:${l.ok ? '#86EFAC' : (l.offline ? '#FDE68A' : '#FCA5A5')};">
        <span>[${l.time}] ${_escH(l.title)}</span>
        <span>${_escH(l.summary)}</span>
      </div>
      <div class="mono" style="font-size:0.74rem; color:#94A3B8; margin-top:2px;">&gt;&gt; ${_escH(l.sent)}</div>
      <pre class="mono" style="margin:2px 0 0 0; font-size:0.76rem; color:#E2E8F0; white-space:pre-wrap; word-break:break-all;">${_escH(l.recv)}</pre>
    </div>`).join('')
    : `<div class="mono" style="font-size:0.79rem; color:#94A3B8; padding:6px 0;">${a.responseViewMode === 'selected' ? '此卡片尚無實測紀錄，請按上方「⚡ 實測這步」或左側「▶ 依序實測全部」。' : '尚無實測輸出。點左邊任張撲克牌按「⚡ 實測這步」或「▶ 依序實測全部步驟」，結果都會即時顯示在這裡。'}</div>`;

  const curMo = s.virtualMos[s.selectedMoIdx] || s.virtualMos[0];
  const expandedMoIsns = sfisExpandMoIsns(curMo);
  const poolBtns = expandedMoIsns.map(tok => {
    const isUsed = s.usedIsns.includes(tok);
    const isCur = (tok === cfg.isn);
    return `
      <span style="display:inline-flex; align-items:center; gap:2px; border:1px solid ${isCur ? '#2563EB' : (isUsed ? '#94A3B8' : '#CBD5E1')}; background:${isCur ? '#DBEAFE' : (isUsed ? '#F1F5F9' : '#FFFFFF')}; border-radius:5px; padding:1px 4px;">
        <button type="button" onclick="sfisPickIsnFromPool('${_escH(tok)}')" style="border:none; background:transparent; padding:1px 4px; font-size:0.75rem; color:${isCur ? '#1E40AF' : (isUsed ? '#64748B' : '#0F172A')}; font-weight:${isCur ? '800' : '600'}; cursor:pointer; text-decoration:${isUsed ? 'line-through' : 'none'};" class="mono">
          ${isCur ? '🎯 ' : ''}${_escH(tok)}
        </button>
        <button type="button" onclick="sfisToggleUsedIsn('${_escH(tok)}')" title="${isUsed ? '取消已寫記號' : '手動標記已寫過'}" style="border:none; background:transparent; font-size:0.68rem; color:${isUsed ? '#16A34A' : '#94A3B8'}; cursor:pointer; padding:0 2px;">${isUsed ? '✓已用' : '○'}</button>
      </span>`;
  }).join('');

  const moRowsHtml = s.virtualMos.map((m, mi) => {
    const isSel = (mi === s.selectedMoIdx);
    return `
      <tr style="background:${isSel ? '#EFF6FF' : '#FFFFFF'};">
        <td><input type="text" value="${_escH(m.date)}" onchange="sfisUpdateMoCell(${mi},'date',this.value)" style="width:52px; font-size:0.72rem; padding:2px 3px; border:1px solid #CBD5E1; border-radius:3px;"></td>
        <td><input type="text" value="${_escH(m.model)}" onchange="sfisUpdateMoCell(${mi},'model',this.value)" style="width:128px; font-size:0.72rem; padding:2px 3px; border:1px solid #CBD5E1; border-radius:3px;"></td>
        <td><input type="text" value="${_escH(m.pn)}" onchange="sfisUpdateMoCell(${mi},'pn',this.value)" class="mono" style="width:94px; font-size:0.71rem; padding:2px 3px; border:1px solid #CBD5E1; border-radius:3px;"></td>
        <td><input type="number" min="1" max="50" value="${_escH(m.qty)}" onchange="sfisUpdateMoCell(${mi},'qty',this.value)" style="width:36px; font-size:0.72rem; padding:2px 3px; border:1px solid #CBD5E1; border-radius:3px;"></td>
        <td><input type="text" value="${_escH(m.mo)}" onchange="sfisUpdateMoCell(${mi},'mo',this.value)" class="mono" style="width:74px; font-size:0.72rem; padding:2px 3px; border:1px solid #3B82F6; border-radius:3px; font-weight:800;"></td>
        <td><input type="number" min="1" max="8" value="${_escH(m.seq_digits || 5)}" onchange="sfisUpdateMoCell(${mi},'seq_digits',this.value)" title="流水號位數" style="width:34px; font-size:0.72rem; padding:2px 3px; border:1px solid #CBD5E1; border-radius:3px;"></td>
        <td style="white-space:nowrap;">
          <button type="button" onclick="sfisSelectMoRow(${mi})" style="padding:2px 6px; font-size:0.71rem; border-radius:4px; border:1px solid ${isSel ? '#2563EB' : '#94A3B8'}; background:${isSel ? '#2563EB' : '#F8FAFC'}; color:${isSel ? '#FFFFFF' : '#334155'}; cursor:pointer; font-weight:800;">展開</button>
          <button type="button" onclick="sfisRemoveMoRow(${mi})" style="padding:2px 4px; font-size:0.7rem; border-radius:4px; border:1px solid #FECACA; background:#FEF2F2; color:#DC2626; cursor:pointer;">✕</button>
        </td>
      </tr>`;
  }).join('');

  // 中間步驟按鈕：頭尾 Login/CheckRoute/Logout 固定鎖定，不提供重複加入
  const quickAddBtns = SFIS_CATALOG_BLOCKS.filter(b => b.kind !== 'login' && b.kind !== 'checkroute').map(b => `
    <button type="button" draggable="true" ondragstart="sfisDragCatalogStart('${b.kind}', event)"
            onclick="sfisAddItem('${b.kind}')" title="${_escH(b.desc)}"
            class="btn" style="padding:4px 9px; font-size:0.78rem; background:${b.bg}; color:${b.theme}; border:1px solid ${b.border}; font-weight:800;">
      ＋ ${b.icon} ${_escH(b.title)}
    </button>`).join('');

  const deckCardsHtml = s.items.map((it, idx) => {
    const meta = _getBlockMeta(it.kind);
    const isLocked = !!it.locked;
    const isActive = (it.uid === s.selectedUid);
    const isOut = (it.kind === 'login' && String(it.login_status || '1') === '0');
    const cardTitle = it.kind === 'login' ? (isOut ? 'Logout 登出' : 'Login 登入') : meta.title;
    const cardIcon = it.kind === 'login' ? (isOut ? '🚪' : '🔐') : meta.icon;
    const subTag = (it.kind === 'get' || it.kind === 'savelink' || it.kind === 'rw' || it.kind === 'clear')
      ? (_resolveCardField(it) || it.ver_type || '')
      : (it.locked === 'login' ? '起點登入' : (it.locked === 'checkroute' ? '途程過站' : (it.locked === 'logout' ? '收尾登出' : '')));

    const stCls = it.status === 'running' ? 'status-running' : (it.status === 'pass' ? 'status-pass' : ((it.status === 'fail' || it.status === 'offline') ? 'status-fail' : ''));
    const stPill = it.status === 'pass' ? '<span style="background:#DCFCE7; color:#166534; padding:1px 5px; border-radius:999px; font-size:0.69rem; font-weight:800;">PASS</span>'
      : (it.status === 'fail' ? '<span style="background:#FEE2E2; color:#991B1B; padding:1px 5px; border-radius:999px; font-size:0.69rem; font-weight:800;">FAIL</span>'
      : (it.status === 'offline' ? '<span style="background:#FEF3C7; color:#92400E; padding:1px 5px; border-radius:999px; font-size:0.69rem; font-weight:800;">離線</span>'
      : (it.status === 'running' ? '<span style="background:#DBEAFE; color:#1D4ED8; padding:1px 5px; border-radius:999px; font-size:0.69rem; font-weight:800;">跑中</span>'
      : '<span style="background:#F1F5F9; color:#64748B; padding:1px 5px; border-radius:999px; font-size:0.69rem;">待測</span>')));

    const isMidFirst = (idx === 2);
    const isMidLast = (idx === s.items.length - 2);
    const footerCtrl = isLocked
      ? `<span style="font-size:0.69rem; font-weight:800; color:#475569; background:#E2E8F0; padding:1px 5px; border-radius:4px;">🔒 骨架鎖定</span>`
      : `<div style="display:flex; gap:2px; align-items:center;" onclick="event.stopPropagation()">
           <button type="button" onclick="sfisMoveStep(${idx}, -1)" ${isMidFirst ? 'disabled' : ''} style="padding:1px 5px; font-size:0.7rem; border:1px solid #CBD5E1; border-radius:4px; background:#F8FAFC; cursor:pointer;" title="往前移">◀</button>
           <button type="button" onclick="sfisMoveStep(${idx}, 1)" ${isMidLast ? 'disabled' : ''} style="padding:1px 5px; font-size:0.7rem; border:1px solid #CBD5E1; border-radius:4px; background:#F8FAFC; cursor:pointer;" title="往後移">▶</button>
           <button type="button" onclick="sfisRemoveItem(${idx})" style="padding:1px 5px; font-size:0.7rem; border:1px solid #FECACA; border-radius:4px; background:#FEF2F2; color:#DC2626; cursor:pointer;" title="移除此中間步驟">✕</button>
         </div>`;

    return `
      <div id="sfisDeckCard_${idx}" class="sfis-deck-card ${isLocked ? 'locked' : ''} ${isActive ? 'active' : ''} ${stCls}"
           draggable="${isLocked ? 'false' : 'true'}"
           onmousedown="sfisPrepCardDrag(this, event)"
           ondragstart="sfisDragItemStart(${idx}, event)"
           ondragover="sfisCardDragOver(event, ${idx})"
           ondragleave="sfisCardDragLeave(${idx})"
           ondrop="sfisDropOnTrack(${idx}, event)"
           ondragend="sfisCardDragEnd()"
           onclick="sfisSelectDeckCard('${_escH(it.uid)}')"
           style="border-color:${isActive ? '#2563EB' : (stCls ? '' : meta.border)};">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:3px;">
          <span style="background:${meta.bg}; color:${meta.theme}; border:1px solid ${meta.border}; padding:1px 5px; border-radius:4px; font-weight:900; font-size:0.72rem;">#${idx + 1}</span>
          ${stPill}
        </div>
        <div style="text-align:center; padding:2px 0;">
          <div style="font-size:1.15rem; line-height:1.1;">${cardIcon}</div>
          <div style="font-weight:900; font-size:0.81rem; color:#0F172A; margin-top:2px;">${_escH(cardTitle)}</div>
          ${subTag ? `<div class="mono" style="font-size:0.71rem; color:#475569; margin-top:1px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${_escH(subTag)}</div>` : ''}
        </div>
        <div style="display:flex; justify-content:center; align-items:center;">${footerCtrl}</div>
      </div>`;
  }).join('');

  const selIdxRaw = s.items.findIndex(x => x.uid === s.selectedUid);
  const selIdx = selIdxRaw >= 0 ? selIdxRaw : Math.min(1, s.items.length - 1);
  const selItem = s.items[selIdx];
  const selMeta = _getBlockMeta(selItem.kind);
  const selIsOut = (selItem.kind === 'login' && String(selItem.login_status || '1') === '0');
  const selTitle = selItem.kind === 'login' ? (selIsOut ? 'Logout 登出' : 'Login 登入') : selMeta.title;
  const selIcon = selItem.kind === 'login' ? (selIsOut ? '🚪' : '🔐') : selMeta.icon;
  const selStBadge = selItem.status === 'pass' ? '<span style="background:#DCFCE7; color:#166534; padding:1px 8px; border-radius:999px; font-size:0.76rem; font-weight:800;">PASS</span>'
    : (selItem.status === 'fail' ? '<span style="background:#FEE2E2; color:#991B1B; padding:1px 8px; border-radius:999px; font-size:0.76rem; font-weight:800;">FAIL</span>'
    : (selItem.status === 'offline' ? '<span style="background:#FEF3C7; color:#92400E; padding:1px 8px; border-radius:999px; font-size:0.76rem; font-weight:800;">離線/未連網</span>'
    : (selItem.status === 'running' ? '<span style="background:#DBEAFE; color:#1D4ED8; padding:1px 8px; border-radius:999px; font-size:0.76rem; font-weight:800;">傳送中</span>'
    : '<span style="background:#F1F5F9; color:#64748B; padding:1px 8px; border-radius:999px; font-size:0.76rem;">待測</span>')));
  const selOfflineBtn = (selItem.status === 'offline' && !s.mockMode)
    ? `<div style="margin-top:6px;"><button type="button" onclick="sfisSetMockMode(true); sfisHmiRunAll();" class="btn" style="padding:3px 9px; font-size:0.79rem; background:#FEF3C7; color:#92400E; border:1px solid #F59E0B; font-weight:800;">🧪 目前非工廠內網 — 一鍵改用本機模擬並重測</button></div>`
    : '';
  const selLockedNote = selItem.locked
    ? `<div style="font-size:0.8rem; color:#475569; margin-bottom:5px; font-weight:700;">🔒 基本骨架步驟：${selItem.locked === 'login' ? 'Step 1 OP 登入驗證（對應 Excel System.ini SFIS_AutoLogin=1）' : (selItem.locked === 'checkroute' ? 'Step 2 ISN 途程刷過檢查（匯出時轉為 Phase 0 :ShowISN + :SfCheckRoute）' : '最後結尾 OP 登出保護（匯出時接續 Phase 97 :CloseMessage 收尾）')}</div>`
    : '';
  const selInputsHtml = selItem.locked ? selLockedNote : (_renderSimpleCardInputs(selItem, selIdx) || '<div style="font-size:0.8rem; color:#475569;">點擊上方「⚡ 實測這步」立即驗證。</div>');

  const latestLog = a.logs[0] || null;
  const respSummaryBadge = latestLog
    ? `<span style="padding:1px 7px; border-radius:999px; font-size:0.76rem; font-weight:800; background:${latestLog.ok ? '#14532D' : (latestLog.offline ? '#78350F' : '#7F1D1D')}; color:${latestLog.ok ? '#86EFAC' : (latestLog.offline ? '#FDE68A' : '#FCA5A5')};">${_escH(latestLog.title)} · ${_escH(latestLog.summary)}</span>`
    : '<span style="font-size:0.76rem; color:#94A3B8;">尚無紀錄</span>';

  const isMock = !!s.mockMode;
  const hmiWrapBg = isMock ? 'linear-gradient(180deg, #FEF9C3 0%, #FDE68A 100%)' : '#FFFFFF';
  const hmiWrapBorder = isMock ? '#D97706' : '#C7D2FE';
  const cfgBoxBg = isMock ? '#FFFDF5' : '#F8FAFC';
  const cfgBoxBorder = isMock ? '#F59E0B' : '#CBD5E1';
  const stageWrapBg = isMock ? 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)' : 'linear-gradient(135deg,#F8FAFC 0%,#EFF6FF 100%)';
  const stageWrapBorder = isMock ? '#D97706' : '#BFDBFE';
  const trackBg = isMock ? '#FFFDF5' : '#F8FAFC';
  const trackBorder = isMock ? '#F59E0B' : '#93C5FD';
  const serverStale = (window.__SERVER_BUILD__ && window.__SERVER_BUILD__ !== 'Build v0.8.045');

  const stageBannerHtml = `
      <!-- 跨雙欄頂部寬幅即時動畫舞台 (PC.png ⇄ cloud.png ⇄ database.png) -->
      <div id="sfisTopStageWrap" style="background:${stageWrapBg}; border:1.5px solid ${stageWrapBorder}; border-radius:10px; padding:7px 11px; margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span style="font-weight:900; font-size:0.86rem; color:#0F172A;">🖥️ 機台 ⇄ SFIS 即時動畫</span>
            <label style="display:inline-flex; align-items:center; gap:4px; font-size:0.74rem; font-weight:800; color:#1E40AF; background:#FFFFFF; border:1px solid #93C5FD; border-radius:999px; padding:1px 7px; cursor:pointer;" title="開啟後單步實測會展演 3 秒三段式封包來回（一鍵全測為每步 1.2 秒）；關閉則零延遲即時出結果">
              <input type="checkbox" ${a.slowDemo !== false ? 'checked' : ''} onchange="sfisToggleSlowDemo(this.checked)" style="width:13px; height:13px;">
              <span>🎬 3秒動畫展演</span>
            </label>
          </div>
          <span style="padding:2px 9px; border-radius:999px; font-size:0.75rem; font-weight:800; background:${isPass ? '#DCFCE7' : (isFail ? '#FEE2E2' : (isOffline ? '#FEF3C7' : (isSending ? '#DBEAFE' : '#E2E8F0')))}; color:${isPass ? '#166534' : (isFail ? '#991B1B' : (isOffline ? '#92400E' : (isSending ? '#1D4ED8' : '#334155')))};">${_escH(a.actionLabel)}</span>
        </div>
        <div class="sfis-anim-stage">
          <div class="sfis-node-card sfis-node-card-wide ${a.stage === 'to_cloud' ? 'pulse-blue' : (isPass && a.stage === 'idle' ? 'glow-green' : ((isFail || isOffline) && a.stage === 'idle' ? 'glow-red' : ''))}">
            <img src="/images/PC.png" alt="Test PC" style="width:42px; height:42px; object-fit:contain; flex-shrink:0;">
            <div style="min-width:0;">
              <div style="font-weight:900; font-size:0.8rem; color:#0F172A;">測試 PC <span style="font-size:0.71rem; color:${opColor};"><i class="sfis-led" style="background:${netColor};"></i>${opText}</span></div>
              <div class="mono" style="font-size:0.71rem; color:#334155; display:flex; align-items:center; gap:5px; margin-top:2px;">
                <span>Dev:<b id="sfisPcDevTxt">${_escH(cfg.device_id)}</b></span>
                <span style="color:#854D0E; background:#FEF9C3; padding:0 4px; border-radius:3px; max-width:118px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${_escH(cfg.isn)}"><b id="sfisPcIsnTxt">${_escH(cfg.isn || '-')}</b></span>
              </div>
            </div>
          </div>
          <div class="${a.stage === 'to_cloud' ? 'sfis-flow-line sending' : (a.stage === 'to_pc' ? (isPass ? 'sfis-flow-line returning-pass' : 'sfis-flow-line returning-fail') : lineClass)}">
            <span class="sfis-flow-label">${a.stage === 'to_cloud' && a.packetText ? `<span class="sfis-packet-badge">${_escH(a.packetText)}</span>` : (a.stage === 'to_pc' && a.packetText ? `<span class="sfis-packet-badge ${isPass ? 'back-ok' : 'back-err'}">${_escH(a.packetText)}</span>` : (isPass ? '✅ 通' : 'SOAP'))}</span>
            <div class="sfis-flow-rail"><span class="sfis-packet"></span></div>
          </div>
          <div class="sfis-node-card sfis-node-card-wide sfis-cloud-card ${(a.stage === 'to_cloud' || a.stage === 'to_db' || a.stage === 'to_pc') ? 'cloud-active' : ''}">
            <img src="/images/cloud.png" alt="Cloud" style="width:44px; height:36px; object-fit:contain; flex-shrink:0;">
            <div style="display:flex; flex-direction:column; gap:2px;">
              <span style="font-size:0.75rem; font-weight:900; color:#0F172A;">WebService</span>
              <div style="display:flex; gap:3px; font-size:0.68rem; font-weight:800;">
                <span style="padding:1px 4px; border-radius:3px; background:${(a.stage === 'to_cloud' || a.stage === 'to_db') ? '#2563EB' : '#F1F5F9'}; color:${(a.stage === 'to_cloud' || a.stage === 'to_db') ? '#FFFFFF' : '#64748B'};">⬆發</span>
                <span style="padding:1px 4px; border-radius:3px; background:${(a.stage === 'to_pc' || isPass) ? '#16A34A' : (isFail ? '#DC2626' : '#F1F5F9')}; color:${(a.stage === 'to_pc' || isPass || isFail) ? '#FFFFFF' : '#64748B'};">⬇回</span>
              </div>
            </div>
          </div>
          <div class="${a.stage === 'to_db' ? 'sfis-flow-line sending' : (a.stage === 'to_pc' ? (isPass ? 'sfis-flow-line returning-pass' : 'sfis-flow-line returning-fail') : lineClass)}">
            <span class="sfis-flow-label">${a.stage === 'to_db' && a.packetText ? `<span class="sfis-packet-badge">${_escH(a.packetText)}</span>` : (a.stage === 'to_pc' ? '⬇ 回傳' : 'DB')}</span>
            <div class="sfis-flow-rail"><span class="sfis-packet"></span></div>
          </div>
          <div class="sfis-node-card sfis-node-card-wide ${a.stage === 'to_db' ? 'glow-amber' : (isPass && a.stage !== 'to_cloud' ? 'glow-green' : ((isFail || isOffline) && a.stage !== 'to_cloud' ? 'glow-red' : ''))}">
            <img src="/images/database.png" alt="SFIS DB" style="width:38px; height:42px; object-fit:contain; flex-shrink:0;">
            <div>
              <div style="font-weight:900; font-size:0.8rem; color:#0F172A;">SFIS DB</div>
              <div style="font-size:0.72rem; font-weight:800; color:#1D4ED8;">${_escH(curPlant.label.split(' ')[0])} <span style="font-weight:700; color:#334155;"><i class="sfis-led" style="background:${dbLedColor};"></i>${a.stage === 'to_db' ? '處理中...' : (isPass ? 'PASS' : (isFail ? 'FAIL' : (isOffline ? '離線' : '待機')))}</span></div>
            </div>
          </div>
        </div>
      </div>`;

  root.innerHTML = `
    <div id="sfisHmiWrap" class="sfis-hmi-wrap ${isMock ? 'sfis-mode-mock' : 'sfis-mode-real'}" style="background:${hmiWrapBg}; border:2px solid ${hmiWrapBorder}; border-radius:12px; padding:12px 14px; font-size:var(--app-font-size, 15px); transition:background 0.22s ease, border-color 0.22s ease;">
      ${serverStale ? '<div style="margin-bottom:8px; padding:5px 10px; border-radius:7px; background:#FEE2E2; color:#991B1B; border:1px solid #FCA5A5; font-size:0.79rem; font-weight:800;">⚠️ 偵測到後端伺服器仍為舊版，請重雙擊 啟動_Centimani腳本工具.bat（模擬目前由瀏覽器引擎自動接手）</div>' : ''}
      ${stageBannerHtml}

      <!-- 精簡頂部單列連線與單顆 ISN 設定區 -->
      <div id="sfisCompactEnvBar" style="background:${cfgBoxBg}; border:1.5px solid ${cfgBoxBorder}; border-radius:9px; padding:8px 11px; margin-bottom:10px;">
        <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
          <label style="display:inline-flex; align-items:center; gap:4px; font-size:0.83rem; font-weight:800; color:#1E293B;">
            <span>🏭 廠區</span>
            <select onchange="sfisSelectPlant(this.value)" style="padding:4px 7px; border:1.5px solid #3B82F6; border-radius:6px; font-weight:800; font-size:0.82rem; background:#FFFFFF;">${plantOptions}</select>
          </label>
          <button type="button" onclick="sfisTogglePlantEditor()" class="btn" style="padding:4px 8px; font-size:0.79rem; background:${s.showPlantEditor ? '#DBEAFE' : '#FFFFFF'}; color:#1E40AF; border-color:#93C5FD; font-weight:800;" title="修改目前廠區名稱/IP 或新增廠區">✏️ 改/增</button>
          <button type="button" onclick="sfisImportFromWorkspaceIni()" class="btn" style="padding:4px 8px; font-size:0.79rem; background:#EFF6FF; color:#1D4ED8; border-color:#93C5FD; font-weight:800;" title="自動從目前開啟的專案或挑選工廠 System.ini / Global.ini 一鍵帶入設定">📥 帶入 INI</button>
          <button type="button" onclick="openCentimaniAuxTool('CentimaniSFISTest.exe')" class="btn" style="padding:4px 7px; font-size:0.79rem; background:#FFFFFF; color:#334155; border-color:#CBD5E1;" title="開啟原廠 CentimaniSFISTest.exe">🌐</button>

          <input type="text" value="${_escH(cfg.url)}" oninput="sfisSyncConfig('url', this.value)" class="mono" placeholder="SFIS_WebLink (.asmx)" style="flex:1; min-width:210px; padding:4px 8px; border:1px solid #94A3B8; border-radius:5px; font-size:0.79rem; background:#FFFFFF;">
          <button type="button" onclick="toolsCheckSfisLink()" class="btn" style="padding:4px 10px; font-size:0.8rem; background:#E0F2FE; color:#0369A1; border-color:#7DD3FC; font-weight:800;">🔍 測連通</button>

          <label style="display:inline-flex; align-items:center; gap:3px; font-size:0.77rem; font-weight:800; color:#334155;">Dev
            <input type="text" value="${_escH(cfg.device_id)}" oninput="sfisSyncConfig('device_id', this.value)" class="mono" style="width:68px; padding:4px 5px; border:1px solid #94A3B8; border-radius:5px; font-size:0.79rem;">
          </label>
          <label style="display:inline-flex; align-items:center; gap:3px; font-size:0.77rem; font-weight:800; color:#334155;">OP
            <input type="text" value="${_escH(cfg.op)}" oninput="sfisSyncConfig('op', this.value)" class="mono" style="width:90px; padding:4px 5px; border:1px solid #94A3B8; border-radius:5px; font-size:0.79rem;">
          </label>
          <label style="display:inline-flex; align-items:center; gap:4px; font-size:0.77rem; font-weight:800; color:#9A3412;">🎯 ISN
            <input type="text" value="${_escH(cfg.isn)}" oninput="sfisSyncConfig('isn', this.value)" class="mono" style="width:136px; padding:4px 6px; border:1.5px solid #F59E0B; border-radius:5px; font-size:0.8rem; background:#FFFBEB; font-weight:800;">
          </label>
        </div>

        ${s.showPlantEditor ? `
          <div style="background:#EFF6FF; border:1px solid #93C5FD; border-radius:7px; padding:8px; margin-top:7px;">
            <div style="font-size:0.75rem; font-weight:800; color:#1E3A8A; margin-bottom:5px;">✏️ 修改此廠區或新增為自訂廠區（自動儲存保留）：</div>
            <div style="display:grid; grid-template-columns:1fr 90px 1fr; gap:6px; margin-bottom:6px;">
              <input id="sfisEdPlantLabel" type="text" value="${_escH(curPlant.label)}" placeholder="廠區顯示名稱" style="padding:4px 6px; border:1px solid #94A3B8; border-radius:4px; font-size:0.78rem;">
              <input id="sfisEdPlantDev" type="text" value="${_escH(curPlant.defaultDevice || '710001')}" placeholder="DevID" class="mono" style="padding:4px 6px; border:1px solid #94A3B8; border-radius:4px; font-size:0.78rem;">
              <input id="sfisEdPlantUrl" type="text" value="${_escH(cfg.url)}" placeholder="http://.../SFISTSPWebService.asmx" class="mono" style="padding:4px 6px; border:1px solid #94A3B8; border-radius:4px; font-size:0.77rem;">
            </div>
            <div style="display:flex; gap:6px; flex-wrap:wrap;">
              <button type="button" onclick="sfisSaveEditedPlant()" class="btn" style="padding:3px 9px; font-size:0.75rem; background:#2563EB; color:#FFFFFF; border:none;">💾 儲存修改</button>
              <button type="button" onclick="sfisAddCustomPlant()" class="btn" style="padding:3px 9px; font-size:0.75rem; background:#059669; color:#FFFFFF; border:none;">＋ 另存為新廠區</button>
              <button type="button" onclick="sfisDeleteCurrentPlant()" class="btn" style="padding:3px 8px; font-size:0.75rem; background:#FEF2F2; color:#DC2626; border-color:#FECACA;">🗑 刪除此項</button>
            </div>
          </div>` : ''}

        <details style="margin-top:6px;">
          <summary style="cursor:pointer; font-size:0.76rem; font-weight:800; color:#92400E;">📋 虛擬工單與 5 碼 ISN 範本 (MO: ${_escH(curMo ? curMo.mo : '')}・共 ${s.virtualMos.length} 筆，可修改) / ⚙️ 進階 (專案/站別/TSP) ▾</summary>
          <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #CBD5E1; display:flex; flex-direction:column; gap:7px;">
            <div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="font-size:0.73rem; color:#92400E; font-weight:800;">規則：虛擬工單 ＋ 流水號（預設 5 碼如 <code>2695160300001~00005</code>，改寫自動存檔）</span>
                <button type="button" onclick="sfisAddMoRow()" style="padding:2px 7px; font-size:0.72rem; border-radius:4px; border:1px solid #F59E0B; background:#FFFBEB; color:#92400E; cursor:pointer; font-weight:800;">＋ 新增工單</button>
              </div>
              <div style="overflow-x:auto; border:1px solid #E2E8F0; border-radius:5px;">
                <table style="width:100%; border-collapse:collapse; font-size:0.72rem; text-align:left;">
                  <thead>
                    <tr style="background:#F1F5F9; color:#334155;">
                      <th style="padding:3px 4px;">日期</th><th style="padding:3px 4px;">機種</th><th style="padding:3px 4px;">料號</th>
                      <th style="padding:3px 4px;">數量</th><th style="padding:3px 4px;">虛擬工單</th><th style="padding:3px 4px;">碼數</th><th style="padding:3px 4px;">操作</th>
                    </tr>
                  </thead>
                  <tbody>${moRowsHtml}</tbody>
                </table>
              </div>
              <div style="margin-top:5px; font-size:0.72rem; font-weight:800; color:#334155;">工單 [${_escH(curMo ? curMo.mo : '')}] 展開序號（點任 1 顆載入槍口實測）：</div>
              <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px;">${poolBtns}</div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; border-top:1px dashed #CBD5E1; padding-top:6px;">
              <label style="font-size:0.74rem; font-weight:700;">專案名稱<input type="text" value="${_escH(cfg.project_name)}" oninput="sfisSyncConfig('project_name', this.value)" class="mono" style="width:100%; padding:3px 5px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
              <label style="font-size:0.74rem; font-weight:700;">站別分頁<input type="text" value="${_escH(cfg.station)}" oninput="sfisSyncConfig('station', this.value)" class="mono" style="width:100%; padding:3px 5px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
              <label style="font-size:0.74rem; font-weight:700;">SFIS_TSP<input type="text" value="${_escH(cfg.tsp)}" oninput="sfisSyncConfig('tsp', this.value)" class="mono" style="width:100%; padding:3px 5px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
            </div>
          </div>
        </details>
      </div>

      <!-- 雙欄抽卡牌桌：左 = 鎖定頭尾 (Login/CheckRoute/.../Logout) 抽卡牌桌；右 = 選中卡片設定 + 黑底吐出終端 -->
      <div id="sfisSplitLayout" class="sfis-split-layout" style="--sfis-left-w:${s.leftPanePct || 46}%;">

        <!-- 左視窗：中間步驟膠囊列 + 抽卡牌桌 -->
        <div style="display:flex; flex-direction:column; gap:10px; min-width:0;">
          <div id="sfisQuickAddBox" style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:9px; padding:8px 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:6px;">
              <span style="font-size:0.81rem; font-weight:900; color:#0F172A;">➕ 新增中間自訂測項（頭尾鎖定自動保留）：</span>
              <div style="display:flex; gap:5px; flex-wrap:wrap; align-items:center;">
                ${isMock ? `<button type="button" onclick="sfisResetMockDb()" class="btn" style="padding:3px 8px; font-size:0.75rem; background:#FEF3C7; color:#92400E; border-color:#F59E0B; font-weight:800;">↺ 重置 DB</button>` : ''}
                <button type="button" onclick="sfisClearAllItems()" class="btn" style="padding:3px 8px; font-size:0.75rem; background:#FFFFFF; color:#64748B; border-color:#CBD5E1;" title="保留 Login / CheckRoute / Logout，僅清空自訂測項">清空中間區</button>
                <button type="button" onclick="sfisHmiRunAll()" ${s.isRunning ? 'disabled' : ''} class="btn" style="padding:4px 11px; font-size:0.8rem; background:#059669; color:#FFFFFF; border:none; border-radius:6px; font-weight:800;">
                  ${s.isRunning ? '⏳ 執行中...' : '▶ 依序實測全部步驟'}
                </button>
              </div>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:5px;">${quickAddBtns}</div>
          </div>

          <div style="background:${trackBg}; border:2px dashed ${trackBorder}; border-radius:9px; padding:9px 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:8px;">
              <span style="font-size:0.79rem; font-weight:900; color:#334155;">🃏 流程抽卡牌桌（共 ${s.items.length} 步・點任一卡片即於右側設定與檢視回傳）</span>
              <div style="display:inline-flex; gap:4px;">
                <button type="button" onclick="sfisSetDragSortMode('swap')" style="padding:2px 7px; font-size:0.72rem; border-radius:5px; cursor:pointer; font-weight:800; border:1px solid ${s.dragSortMode !== 'insert' ? '#2563EB' : '#CBD5E1'}; background:${s.dragSortMode !== 'insert' ? '#2563EB' : '#FFFFFF'}; color:${s.dragSortMode !== 'insert' ? '#FFFFFF' : '#334155'};">🔀 碰牌對調</button>
                <button type="button" onclick="sfisSetDragSortMode('insert')" style="padding:2px 7px; font-size:0.72rem; border-radius:5px; cursor:pointer; font-weight:800; border:1px solid ${s.dragSortMode === 'insert' ? '#2563EB' : '#CBD5E1'}; background:${s.dragSortMode === 'insert' ? '#2563EB' : '#FFFFFF'}; color:${s.dragSortMode === 'insert' ? '#FFFFFF' : '#334155'};">📌 插牌移位</button>
              </div>
            </div>
            <div id="sfisPokerDeckGrid" class="sfis-deck-grid">${deckCardsHtml}</div>
          </div>
        </div>

        <!-- 中間可拖曳調寬分割線 -->
        <div class="sfis-split-resizer" onmousedown="sfisStartSplitDrag(event)" ondblclick="sfisResetSplitWidth()" title="左右拖曳調整雙視窗寬度（雙擊還原預設 46%）"></div>

        <!-- 右視窗：選中卡片專屬參數面板 ＋ SFIS 實際吐回字串終端 -->
        <div style="display:flex; flex-direction:column; gap:10px; min-width:0;">
          <div id="sfisSelectedCardPanel" style="background:#FFFFFF; border:2px solid #3B82F6; border-radius:10px; padding:10px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:8px; padding-bottom:6px; border-bottom:1px solid #E2E8F0;">
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="background:${selMeta.bg}; color:${selMeta.theme}; border:1px solid ${selMeta.border}; padding:2px 7px; border-radius:5px; font-weight:900; font-size:0.8rem;">#${selIdx + 1}</span>
                <span style="font-weight:900; font-size:0.95rem; color:#0F172A;">${selIcon} ${_escH(selTitle)}</span>
                ${selStBadge}
              </div>
              <div style="display:flex; gap:5px; align-items:center;">
                <button type="button" onclick="sfisHmiRunStep(${selIdx})" class="btn" style="padding:4px 11px; font-size:0.8rem; background:#ECFDF5; color:#047857; border-color:#6EE7B7; font-weight:800;">⚡ 實測這步</button>
                ${selItem.locked ? '<span style="font-size:0.75rem; font-weight:800; color:#475569; background:#F1F5F9; padding:3px 8px; border-radius:5px; border:1px solid #CBD5E1;">🔒 鎖定骨架</span>' : `<button type="button" onclick="sfisRemoveItem(${selIdx})" class="btn" style="padding:4px 8px; font-size:0.78rem; background:#FEF2F2; color:#DC2626; border-color:#FECACA;">🗑 刪除</button>`}
              </div>
            </div>
            ${selInputsHtml}
            ${selOfflineBtn}
          </div>

          <details id="sfisResponseDetails" ${a.responseExpanded ? 'open' : ''} ontoggle="SFIS_HMI_STATE.anim.responseExpanded=this.open"
                   style="background:#0F172A; border:1.5px solid #334155; border-radius:10px; padding:9px 11px;">
            <summary style="cursor:pointer; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; list-style:none;">
              <span style="font-size:0.84rem; font-weight:800; color:#38BDF8;">📥 SFIS 實際吐回字串 &amp; 欄位結果（共 ${a.logs.length} 筆）▾</span>
              <span style="display:inline-flex; align-items:center; gap:6px;">${respSummaryBadge}</span>
            </summary>
            <div style="margin-top:8px; padding-top:7px; border-top:1px solid #1E293B;">
              <div style="display:flex; justify-content:flex-end; gap:4px; align-items:center; flex-wrap:wrap; margin-bottom:6px;">
                <button type="button" onclick="sfisSetRespViewMode('selected')" style="padding:2px 7px; font-size:0.76rem; border-radius:4px; border:1px solid #475569; background:${a.responseViewMode === 'selected' ? '#2563EB' : '#1E293B'}; color:#F8FAFC; cursor:pointer;">🎯 目前這步</button>
                <button type="button" onclick="sfisSetRespViewMode('all')" style="padding:2px 7px; font-size:0.76rem; border-radius:4px; border:1px solid #475569; background:${a.responseViewMode === 'all' ? '#2563EB' : '#1E293B'}; color:#F8FAFC; cursor:pointer;">全部(${a.logs.length})</button>
                <button type="button" onclick="sfisSetRespViewMode('latest')" style="padding:2px 7px; font-size:0.76rem; border-radius:4px; border:1px solid #475569; background:${a.responseViewMode === 'latest' ? '#2563EB' : '#1E293B'}; color:#F8FAFC; cursor:pointer;">最新</button>
                <button id="sfisBtnCopyRecv" type="button" onclick="sfisCopyRecvString()" style="padding:2px 8px; font-size:0.76rem; border-radius:4px; border:1px solid #475569; background:#1E293B; color:#E2E8F0; cursor:pointer;">📋 複製</button>
                <button type="button" onclick="sfisClearLogs()" style="padding:2px 7px; font-size:0.76rem; border-radius:4px; border:1px solid #475569; background:#1E293B; color:#FCA5A5; cursor:pointer;">🗑 清空</button>
              </div>
              <div id="sfisLogsContainer">${logsHtml}</div>
            </div>
          </details>
        </div>
      </div>

      <!-- 底部全寬：產出標準 SFIS Excel 與即時預覽 -->
      <div style="margin-top:10px; background:#F0FDF4; border:1.5px solid #86EFAC; border-radius:9px; padding:9px 12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">
          <label style="display:inline-flex; align-items:center; gap:5px; cursor:pointer; font-size:0.8rem; font-weight:800; color:#166534;">
            <input type="checkbox" ${cfg.skip_save_on_fail ? 'checked' : ''} onchange="sfisSyncConfig('skip_save_on_fail', this.checked)" style="width:14px; height:14px;">
            🛡️ <code>SFIS_SkipSaveResultOnFail=1</code>（失敗不上傳保護 ISN；產檔自動略過 Login/Logout 改由 INI 登入）
          </label>
          <div style="display:flex; gap:7px; flex-wrap:wrap;">
            <button type="button" onclick="sfisHmiExport('new_template')" class="btn" style="padding:5px 12px; font-size:0.81rem; background:#15803D; color:#FFFFFF; border:none; border-radius:6px; font-weight:800;">📥 抄空白範本產生 SFIS Excel</button>
            <button type="button" onclick="sfisHmiExport('insert_current')" class="btn" style="padding:5px 11px; font-size:0.81rem; background:#FFFFFF; color:#15803D; border:1.5px solid #16A34A; border-radius:6px; font-weight:800;">➕ 插入現開 Excel 開頭</button>
          </div>
        </div>
        <details>
          <summary style="cursor:pointer; font-size:0.77rem; font-weight:800; color:#14532D;">📝 展開預覽將寫入之 Excel 標準指令 (ExecMode=8) ▾</summary>
          <pre id="sfisLiveExcelPreview" class="mono" style="margin:6px 0 0 0; font-size:0.73rem; color:#0F172A; background:#FFFFFF; border:1px solid #BBF7D0; border-radius:6px; padding:6px 8px; white-space:pre-wrap; overflow:auto;"></pre>
        </details>
      </div>
    </div>
  `;
  sfisRenderLiveExcelPreview();
}
