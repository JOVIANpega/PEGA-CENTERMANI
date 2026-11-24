// SFIS WebService Interactive Drag-and-Drop HMI + Live SOAP Tester + Excel Step Generator
const SFIS_PLANT_PRESETS = [
  { id: 'TAIPEI', label: '台北 TAIPEI', url: 'http://172.18.202.12/SFISWebService/SFISTSPWebService.asmx', device: '710001', tsp: 'PEGA,2' },
  { id: 'PTSN_PXD', label: '蘇州 PTSN (PXD)', url: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx', device: '710001', tsp: 'ATLAS,2' },
  { id: 'SZASCD0QA', label: '蘇州 QA (SZASCD0QA)', url: 'http://172.24.255.89/SFISTSP_SZASCD0QA/SFISTSPWebService.asmx', device: '430079', tsp: 'SGC,2' },
  { id: 'PTB', label: '重慶 PTB', url: 'http://ptb-sftsp-n1.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx', device: '710001', tsp: 'ATLAS,2' },
  { id: 'SAGEMCOM', label: 'SAGEMCOM', url: 'http://172.22.255.160/SFISWebService/SFISTSPWebService.asmx', device: '419131', tsp: 'DIW350,2' },
  { id: 'ADB_X740', label: 'ADB_X740', url: 'http://172.22.255.161/sfiswebservice/sfistspwebservice.asmx', device: '421430', tsp: 'X740,2' }
];

const SFIS_CATALOG_BLOCKS = [
  {
    kind: 'login',
    icon: '🔐',
    title: 'OP 登入 / 登出',
    soap: 'WTSP_LOGINOUT',
    desc: '測試工號與站別登入驗證（如 S09166390；部分伺服器免 Login）',
    themeBg: '#F1F5F9',
    themeBorder: '#94A3B8',
    defaults: { op: 'S09166390', password: '', status: 1 }
  },
  {
    kind: 'checkroute',
    icon: '🔍',
    title: 'ISN 刷過 (CheckRoute)',
    soap: 'WTSP_CHKROUTE',
    desc: '驗證條碼 ISN 在此站別與 DeviceID 是否途程正常未鎖站',
    themeBg: '#EEF2FF',
    themeBorder: '#6366F1',
    defaults: { checkFlag: '1', checkData: '', route_type: 1 }
  },
  {
    kind: 'getversion',
    icon: '📥',
    title: 'GET 撈資料 (GetVersion)',
    soap: 'WTSP_GETVERSION',
    desc: '依 type + ChkData 撈取 MAC / SSN / ModelNumber / EPG',
    themeBg: '#F0FDF4',
    themeBorder: '#16A34A',
    defaults: { ver_type: 'ISN_BASEINFO', slot_code: '2', chk_data: 'MAC1', chk_data2: '', ref_var: 'sfMAC' }
  },
  {
    kind: 'getimac',
    icon: '🌐',
    title: 'GET 配發 MAC (GetiMAC)',
    soap: 'WTSP_GETIMAC',
    desc: '依 ISN 讀取／配發設備 MAC 位址',
    themeBg: '#ECFEFF',
    themeBorder: '#0891B2',
    defaults: { slot_code: '2', imacnum: '1', ref_var: 'sfMAC' }
  },
  {
    kind: 'savelink',
    icon: '📤',
    title: 'WRITE 回寫 #SAVE (Result)',
    soap: 'WTSP_RESULT',
    desc: '測試將 #SAVE:Key=Value 資料與 PASS 結果寫回 SFIS DB',
    themeBg: '#FFFBEB',
    themeBorder: '#D97706',
    defaults: { save_key: 'SNB', save_val: '*(gUUID)', result_tsp: 'PASS', error: '' }
  }
];

const SFIS_GET_TYPES = [
  'ISN_BASEINFO', 'ITEMINFO', 'GETSN_BYRULE', 'ITEM_FEATURE_BASEINFO',
  'ISN_BASE_CUSTITEM', 'MOKP_SN', 'MOKP_D_BASEINFO', 'ASSIGN_SSN'
];

const SFIS_HMI_STATE = {
  subTab: 'sfis', // 'sfis' | 'dll'
  presetId: 'PTSN_PXD',
  url: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx',
  project: 'SFIS_DEMO',
  station: 'MB',
  deviceId: '710001',
  tsp: 'ATLAS,2',
  isn: '1B5723090000004',
  op: 'S09166390',
  queue: [
    { kind: 'checkroute', checkFlag: '1', checkData: '', route_type: 1, lastRes: null },
    { kind: 'getversion', ver_type: 'ISN_BASEINFO', slot_code: '2', chk_data: 'MAC1', chk_data2: '', ref_var: 'sfMAC', lastRes: null },
    { kind: 'savelink', save_key: 'SNB', save_val: '*(gUUID)', result_tsp: 'PASS', error: '', lastRes: null }
  ],
  dragPayload: null, // { type: 'catalog', kind } | { type: 'queue', idx }
  lastOutput: null
};

function switchToolsVerifyTab(tab) {
  SFIS_HMI_STATE.subTab = (tab === 'dll') ? 'dll' : 'sfis';
  const sfisPane = document.getElementById('toolsSubPaneSfis');
  const dllPane = document.getElementById('toolsSubPaneDll');
  const btnS = document.getElementById('btnToolsSubSfis');
  const btnD = document.getElementById('btnToolsSubDll');
  if (sfisPane) sfisPane.style.display = (SFIS_HMI_STATE.subTab === 'sfis') ? 'block' : 'none';
  if (dllPane) dllPane.style.display = (SFIS_HMI_STATE.subTab === 'dll') ? 'block' : 'none';
  if (btnS) btnS.className = 'source-mode-tab' + (SFIS_HMI_STATE.subTab === 'sfis' ? ' active' : '');
  if (btnD) btnD.className = 'source-mode-tab' + (SFIS_HMI_STATE.subTab === 'dll' ? ' active' : '');
  if (SFIS_HMI_STATE.subTab === 'sfis') renderSfisHmiWorkspace();
}

function sfisHmiApplyPreset(presetId) {
  const p = SFIS_PLANT_PRESETS.find(x => x.id === presetId);
  if (!p) return;
  SFIS_HMI_STATE.presetId = p.id;
  SFIS_HMI_STATE.url = p.url;
  SFIS_HMI_STATE.deviceId = p.default_device;
  SFIS_HMI_STATE.tsp = p.default_tsp;
  renderSfisHmiWorkspace();
}

function sfisHmiLoadFromWorkspace() {
  const ws = (typeof STATE !== 'undefined' && STATE.workspace) ? STATE.workspace : null;
  if (!ws) {
    alert('目前尚未載入任何 Excel 工作區，可先直接修改上方欄位或選廠區預設值。');
    return;
  }
  const sys = ws.system_ini || {};
  if (sys.SFIS_WebLink) SFIS_HMI_STATE.url = sys.SFIS_WebLink;
  if (sys.SFIS_TSP) SFIS_HMI_STATE.tsp = sys.SFIS_TSP;
  if (sys.StationName) SFIS_HMI_STATE.station = sys.StationName;
  if (ws.project_name) SFIS_HMI_STATE.project = ws.project_name;
  const duts = Array.isArray(ws.duts) ? ws.duts : [];
  if (duts.length > 0 && duts[0].SFIS_DeviceID) {
    let rawDev = String(duts[0].SFIS_DeviceID).trim();
    const glb = (ws.global_ini && ws.global_ini.Settings) || {};
    const m = rawDev.match(/^\*\$\(([^)]+)\)$/);
    if (m && glb[m[1]]) rawDev = String(glb[m[1]]);
    if (rawDev) SFIS_HMI_STATE.deviceId = rawDev;
  }
  renderSfisHmiWorkspace();
}

function sfisHmiSyncConfigFromInputs() {
  const g = id => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  };
  const u = g('toolsSfisUrlInput');
  if (u) SFIS_HMI_STATE.url = u;
  const pr = g('sfisHmiProjInput');
  if (pr) SFIS_HMI_STATE.project = pr;
  const st = g('sfisHmiStationInput');
  if (st) SFIS_HMI_STATE.station = st;
  const dv = g('sfisHmiDeviceInput');
  if (dv) SFIS_HMI_STATE.deviceId = dv;
  const tp = g('sfisHmiTspInput');
  if (tp) SFIS_HMI_STATE.tsp = tp;
  const isn = g('sfisHmiIsnInput');
  if (isn) SFIS_HMI_STATE.isn = isn;
  const op = g('sfisHmiOpInput');
  if (op) SFIS_HMI_STATE.op = op;
}

function sfisHmiAddBlock(kind, insertAt = -1) {
  const tpl = SFIS_CATALOG_BLOCKS.find(b => b.kind === kind);
  if (!tpl) return;
  const newItem = Object.assign({ kind: tpl.kind, lastRes: null }, tpl.defaults);
  if (insertAt >= 0 && insertAt <= SFIS_HMI_STATE.queue.length) {
    SFIS_HMI_STATE.queue.splice(insertAt, 0, newItem);
  } else {
    SFIS_HMI_STATE.queue.push(newItem);
  }
  renderSfisHmiWorkspace();
}

function sfisHmiRemoveBlock(idx) {
  SFIS_HMI_STATE.queue.splice(idx, 1);
  renderSfisHmiWorkspace();
}

function sfisHmiUpdateField(idx, field, val) {
  if (!SFIS_HMI_STATE.queue[idx]) return;
  SFIS_HMI_STATE.queue[idx][field] = val;
  renderSfisHmiWorkspace();
}

function sfisHmiOnDragStartCatalog(e, kind) {
  SFIS_HMI_STATE.dragPayload = { type: 'catalog', kind };
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy';
}

function sfisHmiOnDragStartQueue(e, idx) {
  SFIS_HMI_STATE.dragPayload = { type: 'queue', idx };
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
}

function sfisHmiOnDrop(e, targetIdx = -1) {
  e.preventDefault();
  const payload = SFIS_HMI_STATE.dragPayload;
  SFIS_HMI_STATE.dragPayload = null;
  if (!payload) return;
  if (payload.type === 'catalog') {
    sfisHmiAddBlock(payload.kind, targetIdx);
    return;
  }
  if (payload.type === 'queue') {
    const from = payload.idx;
    if (from < 0 || from >= SFIS_HMI_STATE.queue.length) return;
    const [moved] = SFIS_HMI_STATE.queue.splice(from, 1);
    let dst = (targetIdx >= 0) ? targetIdx : SFIS_HMI_STATE.queue.length;
    if (targetIdx > from) dst -= 1;
    dst = Math.max(0, Math.min(SFIS_HMI_STATE.queue.length, dst));
    SFIS_HMI_STATE.queue.splice(dst, 0, moved);
    renderSfisHmiWorkspace();
  }
}

function _sfisExcelPreviewForItem(item) {
  if (item.kind === 'login') {
    return '由 System.ini (SFIS_AutoLogin=1) 自動登入，無需額外佔測試列';
  }
  if (item.kind === 'checkroute') {
    return 'Send: :ShowISN,"*(ISN)" ➔ :SfCheckRoute  |  ExecMode: 8  |  TestID: OTCH013';
  }
  if (item.kind === 'getversion') {
    const rv = String(item.ref_var || 'sfData').replace(/^\$/, '');
    return `Send: :SfGetVersion,"*(ISN)","${item.ver_type || 'ISN_BASEINFO'}","${item.slot_code || '2'}","${item.chk_data || ''}","${item.chk_data2 || ''}"  |  Ref: $${rv}:lwString;  |  EM: 8  |  OTFX085`;
  }
  if (item.kind === 'getimac') {
    const rv = String(item.ref_var || 'sfMAC').replace(/^\$/, '');
    return `Send: :SfGetiMAC,"*(ISN)","1","${item.imacnum || '1'}","${item.slot_code || '2'}"  |  Ref: $${rv}:SubString,"0","12":lwString;  |  EM: 8  |  OTFX085`;
  }
  if (item.kind === 'savelink') {
    const k = String(item.save_key || 'SNB').replace(/^#SAVE:/i, '');
    return `Send: :SfSaveLinkData,"${k}","${item.save_val || '*(gUUID)'}"  |  ExecMode: 8  |  TestID: OTFX064`;
  }
  return '';
}

function _sfisSoapPayloadForItem(item) {
  const s = SFIS_HMI_STATE;
  const base = {
    programId: 'Centimani',
    programPassword: '',
    device: s.deviceId,
    isn: s.isn,
    tsp: s.tsp
  };
  if (item.kind === 'login') {
    return {
      action: 'WTSP_LOGINOUT',
      params: Object.assign(base, { op: item.op || s.op, password: item.password || '', status: Number(item.status || 1) })
    };
  }
  if (item.kind === 'checkroute') {
    return {
      action: 'WTSP_CHKROUTE',
      params: Object.assign(base, { checkFlag: item.checkFlag || '1', checkData: item.checkData || '', route_type: Number(item.route_type || 1) })
    };
  }
  if (item.kind === 'getversion') {
    return {
      action: 'WTSP_GETVERSION',
      params: Object.assign(base, { ver_type: item.ver_type || 'ISN_BASEINFO', chk_data: item.chk_data || '', chk_data2: item.chk_data2 || '' })
    };
  }
  if (item.kind === 'getimac') {
    return {
      action: 'WTSP_GETIMAC',
      params: Object.assign(base, { status: 1, imacnum: Number(item.imacnum || 1) })
    };
  }
  return {
    action: 'WTSP_RESULT',
    params: Object.assign(base, {
      save_key: item.save_key || 'SNB',
      save_val: item.save_val || '*(gUUID)',
      result_tsp: item.result_tsp || 'PASS',
      error: item.error || '',
      status: 1,
      cpk_flag: ''
    })
  };
}

async function sfisHmiRunStep(idx) {
  sfisHmiSyncConfigFromInputs();
  const item = SFIS_HMI_STATE.queue[idx];
  if (!item) return;
  const { action, params } = _sfisSoapPayloadForItem(item);
  item.lastRes = { status: 'running', msg: '正在發送 SOAP 請求...' };
  renderSfisHmiWorkspace();
  try {
    const res = await fetch('/api/sfis_soap_test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: SFIS_HMI_STATE.url, action, params })
    });
    const d = await res.json();
    item.lastRes = d;
    SFIS_HMI_STATE.lastOutput = Object.assign({ step_idx: idx + 1, action }, d);
  } catch (err) {
    item.lastRes = { status: 'offline', passed: false, ret_code: 'ERR', msg: String(err && err.message ? err.message : err) };
    SFIS_HMI_STATE.lastOutput = Object.assign({ step_idx: idx + 1, action }, item.lastRes);
  }
  renderSfisHmiWorkspace();
}

async function sfisHmiRunAll() {
  for (let i = 0; i < SFIS_HMI_STATE.queue.length; i++) {
    await sfisHmiRunStep(i);
    if (SFIS_HMI_STATE.queue[i].lastRes && SFIS_HMI_STATE.queue[i].lastRes.reachable === false) {
      break;
    }
  }
}

async function sfisHmiExport(mode) {
  sfisHmiSyncConfigFromInputs();
  const s = SFIS_HMI_STATE;
  const payload = {
    mode: mode === 'insert_current' ? 'insert_current' : 'new_template',
    items: s.queue,
    config: {
      url: s.url,
      project_name: s.project,
      station: s.station,
      device_id: s.deviceId,
      tsp: s.tsp,
      isn: s.isn,
      sfis_enable: '1'
    }
  };
  if (mode === 'insert_current') {
    if (!STATE.workspace) {
      alert('目前尚未開啟任何編修中的 Excel 工作區，將改為您產生獨立 SFIS 驗證範本 Excel。');
      payload.mode = 'new_template';
    } else {
      payload.workspace = STATE.workspace;
    }
  }
  try {
    const res = await fetch('/api/export_sfis_hmi_script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status !== 'ok') {
      alert(data.message || '產出 SFIS 腳本失敗');
      return;
    }
    if (data.mode === 'insert_current') {
      _applyAuditLoadedPayload({
        file_path: STATE.selectedPath || `${s.project}_${s.station}.xlsx`,
        workspace: data.workspace,
        report: data.report,
        isn_info: STATE.isnInfo
      });
      STATE.pendingInserts = STATE.pendingInserts || [];
      STATE.pendingInserts.push({
        sheet: data.station || s.station,
        inst: 'SFIS WebService',
        summary: `已插入 ${data.inserted_count} 列標準 SFIS 指令（ExecMode=8）並同步 System.ini`
      });
      alert(`✅ 已成功將 ${data.inserted_count} 列 SFIS 標準步驟（含 :ShowISN 與 ExecMode=8）插入 [${data.station}] 並更新 System.ini！\n將切換至「既有腳本編修」檢視與匯出。`);
      switchGenSubMode('edit');
    } else if (typeof showExportCompleteModal === 'function') {
      showExportCompleteModal({
        title: '🎉 SFIS 實機驗證範本 Excel 匯出完成（已開啟輸出資料夾）',
        excelPath: data.excel_path,
        guideTxtPath: data.guide_txt_path || '',
        outputDir: data.output_dir,
        centimaniDirExists: true,
        missingDlls: [],
        missingDrivers: [],
        summaryHtml: `<div>• <b>步驟數：</b>共 ${data.total_steps} 列標準 SFIS 腳本（<code>0 Error</code> · 免硬體 DLL）</div>`
      });
    }
  } catch (err) {
    alert('匯出 SFIS 腳本時發生異常：' + (err && err.message ? err.message : err));
  }
}

function renderSfisHmiWorkspace() {
  const host = document.getElementById('toolsSubPaneSfis');
  if (!host) return;
  const s = SFIS_HMI_STATE;
  const esc = v => String(v === undefined || v === null ? '' : v).replace(/[<>&"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));

  const presetBtns = SFIS_PLANT_PRESETS.map(p => {
    const active = (s.url === p.url);
    return `<button type="button" onclick="sfisHmiApplyPreset('${p.id}')" class="filter-pill ${active ? 'active' : ''}" style="font-size:0.78rem;">${esc(p.label)}</button>`;
  }).join('');

  const catalogHtml = SFIS_CATALOG_BLOCKS.map(b => `
    <div draggable="true" ondragstart="sfisHmiOnDragStartCatalog(event, '${b.kind}')"
         style="background:${b.themeBg}; border:1.5px solid ${b.themeBorder}; border-radius:8px; padding:9px 11px; margin-bottom:8px; cursor:grab;">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
        <span style="font-weight:900; font-size:0.87rem; color:#0F172A;">${b.icon} ${esc(b.title)}</span>
        <button type="button" onclick="sfisHmiAddBlock('${b.kind}')" class="btn btn-primary-blue" style="padding:2px 8px; font-size:0.76rem; font-weight:800;">＋ 加入</button>
      </div>
      <div style="font-size:0.77rem; color:#334155; margin-top:3px;">${esc(b.desc)}</div>
      <div class="mono" style="font-size:0.72rem; color:#475569; margin-top:2px;">SOAP: ${esc(b.soap)}</div>
    </div>
  `).join('');

  const queueHtml = s.queue.length === 0
    ? `<div style="text-align:center; padding:2rem 1rem; color:#64748B; border:1.5px dashed #94A3B8; border-radius:8px; background:#F8FAFC;">請從左側拖曳或點擊「＋ 加入」SFIS 積木至此排程</div>`
    : s.queue.map((item, idx) => {
        const meta = SFIS_CATALOG_BLOCKS.find(b => b.kind === item.kind) || SFIS_CATALOG_BLOCKS[1];
        const r = item.lastRes;
        let statusPill = `<span style="background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; border-radius:999px; padding:1px 8px; font-size:0.74rem; font-weight:800;">⏳ 待測</span>`;
        if (r) {
          if (r.status === 'running') {
            statusPill = `<span style="background:#EFF6FF; color:#1D4ED8; border:1px solid #93C5FD; border-radius:999px; padding:1px 8px; font-size:0.74rem; font-weight:800;">⏳ 送測中</span>`;
          } else if (r.passed) {
            statusPill = `<span style="background:#DCFCE7; color:#166534; border:1px solid #4ADE80; border-radius:999px; padding:1px 8px; font-size:0.74rem; font-weight:800;">🟢 PASS (RET=${esc(r.ret_code)})</span>`;
          } else if (r.reachable === false) {
            statusPill = `<span style="background:#FFFBEB; color:#B45309; border:1px solid #FBBF24; border-radius:999px; padding:1px 8px; font-size:0.74rem; font-weight:800;">⚠️ 離線/無內網</span>`;
          } else {
            statusPill = `<span style="background:#FEE2E2; color:#B91C1C; border:1px solid #F87171; border-radius:999px; padding:1px 8px; font-size:0.74rem; font-weight:800;">🔴 FAIL (${esc(r.ret_code)})</span>`;
          }
        }

        let fieldsHtml = '';
        if (item.kind === 'login') {
          fieldsHtml = `
            <div style="display:grid; grid-template-columns:1fr 1fr 120px; gap:8px;">
              <label style="font-size:0.78rem; font-weight:700;">OP 工號<input value="${esc(item.op || s.op)}" onchange="sfisHmiUpdateField(${idx},'op',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">密碼 (可留空)<input value="${esc(item.password || '')}" onchange="sfisHmiUpdateField(${idx},'password',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">動作<select onchange="sfisHmiUpdateField(${idx},'status',this.value)" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"><option value="1" ${String(item.status)!=='0'?'selected':''}>1=Login</option><option value="0" ${String(item.status)==='0'?'selected':''}>0=Logout</option></select></label>
            </div>`;
        } else if (item.kind === 'checkroute') {
          fieldsHtml = `
            <div style="display:grid; grid-template-columns:120px 1fr; gap:8px;">
              <label style="font-size:0.78rem; font-weight:700;">CheckFlag<input value="${esc(item.checkFlag || '1')}" onchange="sfisHmiUpdateField(${idx},'checkFlag',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">CheckData (選填)<input value="${esc(item.checkData || '')}" onchange="sfisHmiUpdateField(${idx},'checkData',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
            </div>`;
        } else if (item.kind === 'getversion') {
          const typeOpts = SFIS_GET_TYPES.map(t => `<option value="${t}" ${item.ver_type===t?'selected':''}>${t}</option>`).join('');
          const slotOpts = [
            ['2', '2 (P_CAVER)'], ['3', '3 (P_CBVER)'], ['4', '4 (P_CCVER)'],
            ['5', '5 (P_CDVER)'], ['6', '6 (P_IAVER)'], ['7', '7 (P_IBVER)']
          ].map(([c, lbl]) => `<option value="${c}" ${String(item.slot_code||'2')===c?'selected':''}>${lbl}</option>`).join('');
          fieldsHtml = `
            <div style="display:grid; grid-template-columns:1.2fr 1fr 1fr 0.9fr 0.9fr; gap:7px;">
              <label style="font-size:0.78rem; font-weight:700;">type<select onchange="sfisHmiUpdateField(${idx},'ver_type',this.value)" style="width:100%; margin-top:2px; padding:4px 6px; border:1px solid #94A3B8; border-radius:4px;">${typeOpts}</select></label>
              <label style="font-size:0.78rem; font-weight:700;">ChkData<input value="${esc(item.chk_data || '')}" placeholder="如 MAC1 / SN1" onchange="sfisHmiUpdateField(${idx},'chk_data',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 6px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">ChkData2<input value="${esc(item.chk_data2 || '')}" placeholder="選填" onchange="sfisHmiUpdateField(${idx},'chk_data2',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 6px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">回傳槽<select onchange="sfisHmiUpdateField(${idx},'slot_code',this.value)" style="width:100%; margin-top:2px; padding:4px 6px; border:1px solid #94A3B8; border-radius:4px;">${slotOpts}</select></label>
              <label style="font-size:0.78rem; font-weight:700;">Excel 變數<input value="${esc(item.ref_var || 'sfMAC')}" onchange="sfisHmiUpdateField(${idx},'ref_var',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 6px; border:1px solid #94A3B8; border-radius:4px;"></label>
            </div>`;
        } else if (item.kind === 'getimac') {
          fieldsHtml = `
            <div style="display:grid; grid-template-columns:100px 100px 1fr; gap:8px;">
              <label style="font-size:0.78rem; font-weight:700;">數量 imacnum<input value="${esc(item.imacnum || '1')}" onchange="sfisHmiUpdateField(${idx},'imacnum',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">回傳槽<input value="${esc(item.slot_code || '2')}" onchange="sfisHmiUpdateField(${idx},'slot_code',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">Excel 變數名<input value="${esc(item.ref_var || 'sfMAC')}" onchange="sfisHmiUpdateField(${idx},'ref_var',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
            </div>`;
        } else {
          fieldsHtml = `
            <div style="display:grid; grid-template-columns:1fr 1.3fr 110px; gap:8px;">
              <label style="font-size:0.78rem; font-weight:700;">#SAVE Key (欄位名)<input value="${esc(item.save_key || 'SNB')}" placeholder="如 SNB / SN_UNI" onchange="sfisHmiUpdateField(${idx},'save_key',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">寫入 Value / 變數<input value="${esc(item.save_val || '*(gUUID)')}" onchange="sfisHmiUpdateField(${idx},'save_val',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
              <label style="font-size:0.78rem; font-weight:700;">TSP 結果<input value="${esc(item.result_tsp || 'PASS')}" onchange="sfisHmiUpdateField(${idx},'result_tsp',this.value)" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
            </div>`;
        }

        const stepMsg = r && r.msg ? `<div style="margin-top:5px; font-size:0.78rem; color:${r.passed ? '#166534' : (r.reachable===false ? '#B45309' : '#B91C1C')}; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:4px; padding:4px 8px;"><b>SFIS 回覆：</b>${esc(r.msg)}</div>` : '';

        return `
          <div draggable="true"
               ondragstart="sfisHmiOnDragStartQueue(event, ${idx})"
               ondragover="event.preventDefault()"
               ondrop="sfisHmiOnDrop(event, ${idx})"
               style="background:#FFFFFF; border:1.5px solid ${meta.themeBorder}; border-left:5px solid ${meta.themeBorder}; border-radius:8px; padding:9px 12px; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:6px;">
              <div style="display:flex; align-items:center; gap:7px;">
                <span style="cursor:grab; color:#64748B; font-weight:900;">⠿</span>
                <span style="background:#0F172A; color:#FFFFFF; border-radius:4px; padding:1px 6px; font-size:0.74rem; font-weight:800;">#${String(idx + 1).padStart(2, '0')}</span>
                <span style="font-weight:900; font-size:0.9rem; color:#0F172A;">${meta.icon} ${esc(meta.title)}</span>
                ${statusPill}
              </div>
              <div style="display:flex; gap:6px;">
                <button type="button" onclick="sfisHmiRunStep(${idx})" class="btn btn-primary-green" style="padding:3px 10px; font-size:0.78rem; font-weight:800;">⚡ 單步實測</button>
                <button type="button" onclick="sfisHmiRemoveBlock(${idx})" class="btn" style="padding:3px 8px; font-size:0.78rem; background:#FEF2F2; color:#B91C1C; border-color:#FCA5A5;">🗑️</button>
              </div>
            </div>
            ${fieldsHtml}
            ${stepMsg}
            <div class="mono" style="margin-top:6px; font-size:0.75rem; color:#334155; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:4px; padding:4px 8px;">
              📄 ${_sfisExcelPreviewForItem(item)}
            </div>
          </div>
        `;
      }).join('');

  const out = s.lastOutput;
  let outHtml = `<div style="color:#64748B; font-size:0.82rem;">點擊任一張卡片「⚡ 單步實測」或下方「▶ 一鍵依序實測」，這裡將顯示 SFIS SOAP 真實回傳（<code>P_RET</code>、<code>P_Msg</code>、<code>P_CAVER~P_IBVER</code>）與請求 XML。</div>`;
  if (out) {
    const slotEntries = Object.entries(out.slots || {}).filter(([, v]) => v);
    const slotsStr = slotEntries.length > 0
      ? slotEntries.map(([k, v]) => `<span class="mono" style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:4px; padding:2px 6px; margin-right:6px;"><b>${esc(k)}</b>: ${esc(v)}</span>`).join('')
      : '<span style="color:#64748B;">（無 P_CA~IB 槽位回傳值）</span>';
    outHtml = `
      <div style="font-size:0.83rem; line-height:1.6;">
        <div><b>最新實測：</b>步驟 #${out.step_idx} (<code>${esc(out.action)}</code>) ｜ 狀態：<b style="color:${out.passed ? '#15803D' : '#DC2626'};">${out.passed ? '🟢 PASS' : (out.reachable === false ? '⚠️ 離線/無法連線' : '🔴 FAIL')} (RET=${esc(out.ret_code)})</b></div>
        <div><b>P_Msg：</b><span class="mono">${esc(out.msg || '-')}</span></div>
        <div style="margin-top:3px;"><b>輸出槽位：</b>${slotsStr}</div>
        <details style="margin-top:5px;">
          <summary style="cursor:pointer; font-size:0.78rem; color:#334155; font-weight:700;">🔍 檢視 SOAP Request XML / 原始回應</summary>
          <pre class="mono" style="max-height:140px; overflow:auto; background:#0F172A; color:#E2E8F0; padding:8px; border-radius:6px; font-size:0.74rem; margin-top:4px;">${esc(out.soap_request || '')}\n\n--- RAW RESULT ---\n${esc(out.raw_result || '')}</pre>
        </details>
      </div>
    `;
  }

  host.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid #A5B4FC; border-top:4px solid #4F46E5; border-radius:10px; padding:14px 18px; margin-bottom:12px;">
      <!-- 頂部廠區快選與連線參數 -->
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
        <div>
          <h3 style="margin:0; color:#312E81; font-size:1.08rem;">🌐 SFIS 互動人機（ISN 刷過 / GET / WRITE ＋ 生成寫入 Excel）</h3>
          <div style="font-size:0.82rem; color:#475569;">依 <code>WEB_SFIS V2.0</code> (<code>SFISTSPWebService.asmx</code>) 架構打造：先拖曳排好步驟與參數實測，測通直接產生 <code>ExecMode=8</code> 標準腳本。</div>
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <button type="button" onclick="sfisHmiLoadFromWorkspace()" class="btn" style="padding:5px 11px; font-size:0.82rem; background:#EEF2FF; color:#3730A3; border-color:#A5B4FC; font-weight:800;">📥 帶入目前 Excel INI</button>
          <button type="button" onclick="openCentimaniAuxTool('CentimaniSFISTest.exe')" class="btn" style="padding:5px 11px; font-size:0.82rem; background:#F8FAFC; color:#1E293B; border-color:#94A3B8; font-weight:800;">🌐 開官方 SFISTest.exe</button>
        </div>
      </div>

      <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:10px;">
        <span style="font-size:0.8rem; font-weight:800; color:#334155;">🏭 廠區快選 (DS.xml)：</span>
        ${presetBtns}
      </div>

      <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px; margin-bottom:12px;">
        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:8px;">
          <label style="flex:1; min-width:260px; font-size:0.8rem; font-weight:800; color:#1E293B;">
            SFIS_WebLink (.asmx)
            <input id="toolsSfisUrlInput" type="text" value="${esc(s.url)}" onchange="sfisHmiSyncConfigFromInputs()" class="mono" style="width:100%; margin-top:2px; padding:5px 9px; border:1px solid #94A3B8; border-radius:5px; font-size:0.8rem;">
          </label>
          <button type="button" onclick="toolsCheckSfisLink()" class="btn btn-primary-blue" style="margin-top:16px; padding:6px 12px; font-size:0.82rem; font-weight:800;">🔍 測內網 SFIS 連通</button>
        </div>
        <div id="toolsSfisCheckOut" style="display:none; margin-bottom:8px; padding:6px 10px; border-radius:6px; font-size:0.82rem;"></div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px;">
          <label style="font-size:0.78rem; font-weight:700;">專案名稱<input id="sfisHmiProjInput" value="${esc(s.project)}" onchange="sfisHmiSyncConfigFromInputs()" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
          <label style="font-size:0.78rem; font-weight:700;">測試站別<input id="sfisHmiStationInput" value="${esc(s.station)}" onchange="sfisHmiSyncConfigFromInputs()" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
          <label style="font-size:0.78rem; font-weight:700;">DeviceID (6碼)<input id="sfisHmiDeviceInput" value="${esc(s.deviceId)}" onchange="sfisHmiSyncConfigFromInputs()" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
          <label style="font-size:0.78rem; font-weight:700;">SFIS_TSP<input id="sfisHmiTspInput" value="${esc(s.tsp)}" onchange="sfisHmiSyncConfigFromInputs()" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
          <label style="font-size:0.78rem; font-weight:700;">測試條碼 ISN<input id="sfisHmiIsnInput" value="${esc(s.isn)}" onchange="sfisHmiSyncConfigFromInputs()" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
          <label style="font-size:0.78rem; font-weight:700;">OP 工號<input id="sfisHmiOpInput" value="${esc(s.op)}" onchange="sfisHmiSyncConfigFromInputs()" class="mono" style="width:100%; margin-top:2px; padding:4px 7px; border:1px solid #94A3B8; border-radius:4px;"></label>
        </div>
      </div>

      <!-- 雙欄人機工作台：左積木庫 + 右拖曳實測流 -->
      <div style="display:grid; grid-template-columns:300px minmax(0, 1fr); gap:12px; align-items:start;">
        <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:10px; padding:10px 12px;">
          <div style="font-weight:900; font-size:0.9rem; color:#1E293B; margin-bottom:8px;">🃏 SFIS 積木庫（點擊或拖至右側）</div>
          ${catalogHtml}
        </div>
        <div ondragover="event.preventDefault()" ondrop="sfisHmiOnDrop(event, -1)"
             style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:10px; padding:10px 12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
            <span style="font-weight:900; font-size:0.9rem; color:#1E293B;">🧱 已排定驗證流程（共 ${s.queue.length} 步 · 可拖曳調整順序）</span>
            <button type="button" onclick="sfisHmiRunAll()" class="btn btn-primary-green" style="padding:5px 14px; font-size:0.84rem; font-weight:900;">▶ 一鍵依序實測全部</button>
          </div>
          ${queueHtml}
        </div>
      </div>

      <!-- 底部即時 SOAP 回應檢視 + 匯出/寫入 Excel -->
      <div id="sfisHmiSoapOutputBox" style="margin-top:12px; background:#F1F5F9; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
        ${outHtml}
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-top:12px; padding-top:10px; border-top:1px solid #E2E8F0;">
        <div style="font-size:0.82rem; color:#475569;">
          ✅ 匯出時自動補齊 <code>:ShowISN</code>、強制 <code>ExecMode=8</code>、寫入標準 <code>TestID</code> 與更新 <code>System.ini / DUTs</code>。
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button type="button" id="btnSfisHmiExportNew" onclick="sfisHmiExport('new_template')" class="btn btn-primary-blue" style="padding:8px 16px; font-size:0.88rem; font-weight:900;">
            💾 產生獨立 SFIS 驗證 Excel 範本
          </button>
          <button type="button" id="btnSfisHmiInsertCurrent" onclick="sfisHmiExport('insert_current')" class="btn" style="padding:8px 16px; font-size:0.88rem; font-weight:900; background:#EDE9FE; color:#5B21B6; border-color:#A78BFA;">
            ➕ 插入目前編修中腳本
          </button>
        </div>
      </div>
    </div>
  `;
}
