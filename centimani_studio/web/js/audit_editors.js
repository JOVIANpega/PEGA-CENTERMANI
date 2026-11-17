// Global Config Editor for Script Doctor: DUTs, Instrument, Global.ini
let AUDIT_GLOBAL_TAB = 'duts';

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

function renderGlobalEditorPanel() {
  const box = document.getElementById('auditGlobalEditor');
  if (!box || !STATE.workspace) return;
  const ws = STATE.workspace;
  const duts = ws.duts || [];
  const insts = ws.instruments || [];
  const gSettings = (ws.global_ini && ws.global_ini.Settings) || {};
  const gScripts = (ws.global_ini && ws.global_ini.Scripts) || {};
  const stationNames = Object.keys(ws.stations || {});

  const tabBtn = (id, label) => {
    const active = AUDIT_GLOBAL_TAB === id;
    return `<button onclick="switchGlobalEditorTab('${id}')" class="btn" style="padding:5px 12px; font-size:13px; ${active ? 'background:#2563EB;color:#FFFFFF;border-color:#1D4ED8;font-weight:700;' : 'background:#FFFFFF;color:#334155;border-color:#CBD5E1;'}">${label}</button>`;
  };

  let bodyHtml = '';
  if (AUDIT_GLOBAL_TAB === 'duts') {
    const loadPresets = ['*(Load_1)', '*(Load_2)', '*(Load_3)', '*(Load_4)', 'false'];
    const rowsHtml = duts.map((d, i) => {
      const scanKey = _findKeyByPrefix(d, 'ScanBarcode', 'ScanBarcode({Name,Length,Pattern})');
      const connKey = _findKeyByPrefix(d, 'Connection1', 'Connection1(Type,Name,ConnectString)');
      const loadVal = String(d['Load'] || '');
      const isPreset = loadPresets.includes(loadVal);
      return `
        <tr>
          <td style="white-space:nowrap;">
            <select onchange="onDutLoadSelect(${i}, this.value)" class="mono" style="padding:3px 5px; font-size:12px; border:1px solid #94A3B8; border-radius:4px;">
              ${loadPresets.map(p => `<option value="${_escAttr(p)}" ${loadVal===p?'selected':''}>${p}</option>`).join('')}
              <option value="__CUSTOM__" ${!isPreset?'selected':''}>自訂 (${_escAttr(loadVal)})</option>
            </select>
            ${!isPreset ? `<input value="${_escAttr(loadVal)}" onchange="STATE.workspace.duts[${i}]['Load']=this.value" class="mono" style="width:70px;padding:3px;margin-top:2px;font-size:12px;">` : ''}
          </td>
          <td><input value="${_escAttr(d['DUT Name']||'')}" onchange="STATE.workspace.duts[${i}]['DUT Name']=this.value" class="mono" style="width:140px;padding:4px;font-size:12px;"></td>
          <td><input value="${_escAttr(d['Station']||'')}" onchange="STATE.workspace.duts[${i}]['Station']=this.value" class="mono" style="width:115px;padding:4px;font-size:12px;"></td>
          <td><input value="${_escAttr(d['Parameter']||'')}" onchange="STATE.workspace.duts[${i}]['Parameter']=this.value" class="mono" style="width:165px;padding:4px;font-size:12px;"></td>
          <td><input value="${_escAttr(d['SFIS_DeviceID']||'')}" onchange="STATE.workspace.duts[${i}]['SFIS_DeviceID']=this.value" class="mono" style="width:85px;padding:4px;font-size:12px;"></td>
          <td><input value="${_escAttr(d[scanKey]||'')}" onchange="STATE.workspace.duts[${i}]['${_escAttr(scanKey)}']=this.value" class="mono" style="width:160px;padding:4px;font-size:12px;"></td>
          <td><input value="${_escAttr(d[connKey]||'')}" onchange="STATE.workspace.duts[${i}]['${_escAttr(connKey)}']=this.value" class="mono" style="width:210px;padding:4px;font-size:12px;"></td>
          <td><button class="btn" style="padding:2px 7px;font-size:12px;" onclick="STATE.workspace.duts.splice(${i},1);renderGlobalEditorPanel();">✕</button></td>
        </tr>
      `;
    }).join('');
    bodyHtml = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
        <span style="font-size:12.5px; color:#475569;">提示：Load 欄建議使用下拉選單（<code>*(Load_1)</code> / <code>false</code>），可避免誤填無效字元導致站別無法載入。</span>
        <button onclick="addNewDutRow()" class="btn btn-primary-green" style="padding:4px 10px; font-size:12.5px;">+ 新增 DUT 列</button>
      </div>
      <div style="overflow:auto; max-height:360px;">
        <table class="meas-table">
          <thead><tr><th>Load</th><th>DUT Name</th><th>Station</th><th>Parameter</th><th>SFIS_DeviceID</th><th>ScanBarcode</th><th>Connection1</th><th>刪</th></tr></thead>
          <tbody>${rowsHtml || '<tr><td colspan="8" style="text-align:center;color:#64748B;">此工作簿沒有 DUTs 資料</td></tr>'}</tbody>
        </table>
      </div>
    `;
  } else if (AUDIT_GLOBAL_TAB === 'inst') {
    const rowsHtml = insts.map((inst, i) => `
      <tr>
        <td>
          <div style="display:flex; gap:4px; align-items:center;">
            <input value="${_escAttr(inst['Mount']||'')}" onchange="STATE.workspace.instruments[${i}]['Mount']=this.value" class="mono" style="width:130px;padding:4px;font-size:12px;" placeholder="站名,站名">
            <select onchange="appendMountStation(${i}, this.value); this.value='';" style="padding:3px;font-size:11.5px;max-width:85px;" title="快速加入站別至 Mount">
              <option value="">+站別</option>
              ${stationNames.map(sn => `<option value="${_escAttr(sn)}">${sn}</option>`).join('')}
            </select>
          </div>
        </td>
        <td class="mono" style="font-weight:700;">${_escAttr(inst['Name']||'')}</td>
        <td class="mono" style="font-size:12px; color:#475569;">${_escAttr(inst['ControlDLL']||'')}</td>
        <td><input value="${_escAttr(inst['Settings']||'')}" onchange="STATE.workspace.instruments[${i}]['Settings']=this.value" class="mono" style="width:230px;padding:4px;font-size:12px;"></td>
        <td class="mono" style="font-size:12px;">${_escAttr(inst['Functions']||'')}</td>
        <td><input value="${_escAttr(inst['Version']||'')}" onchange="STATE.workspace.instruments[${i}]['Version']=this.value" class="mono" style="width:72px;padding:4px;font-size:12px;"></td>
      </tr>
    `).join('');
    bodyHtml = `
      <div style="font-size:12.5px; color:#475569; margin-bottom:8px;">提示：可直接修正每台儀器的 <b>Mount</b>（使用右側 <code>+站別</code> 快速追加）、<b>Settings</b>（IP / COM Port / GPIB）與 <b>Version</b>。</div>
      <div style="overflow:auto; max-height:360px;">
        <table class="meas-table">
          <thead><tr><th>Mount (掛載站別)</th><th>Name</th><th>ControlDLL</th><th>Settings</th><th>Functions</th><th>Version</th></tr></thead>
          <tbody>${rowsHtml || '<tr><td colspan="6" style="text-align:center;color:#64748B;">此工作簿沒有 Instrument 資料</td></tr>'}</tbody>
        </table>
      </div>
    `;
  } else {
    const buildKvRows = (secName, obj) => Object.keys(obj).map(k => `
      <tr>
        <td class="mono" style="font-weight:700; color:#1E3A8A;">[${secName}]</td>
        <td class="mono" style="font-weight:700;">${_escAttr(k)}</td>
        <td><input value="${_escAttr(obj[k])}" onchange="STATE.workspace.global_ini['${secName}']['${_escAttr(k)}']=this.value" class="mono" style="width:100%;padding:4px;font-size:12px;box-sizing:border-box;"></td>
        <td><button class="btn" style="padding:2px 7px;font-size:12px;" onclick="delete STATE.workspace.global_ini['${secName}']['${_escAttr(k)}'];renderGlobalEditorPanel();">✕</button></td>
      </tr>
    `).join('');
    bodyHtml = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
        <span style="font-size:12.5px; color:#475569;">修改 <code>Global.ini</code> 的 <code>[Settings]</code>（IP / COM / DAQ）與 <code>[Scripts]</code>（韌體版本 / 延遲變數）。</span>
        <button onclick="addGlobalIniVar()" class="btn btn-primary-green" style="padding:4px 10px; font-size:12.5px;">+ 新增 Global.ini 變數</button>
      </div>
      <div style="overflow:auto; max-height:360px;">
        <table class="meas-table">
          <thead><tr><th>區段</th><th>變數名稱</th><th>設定值</th><th>刪</th></tr></thead>
          <tbody>
            ${buildKvRows('Settings', gSettings)}
            ${buildKvRows('Scripts', gScripts)}
          </tbody>
        </table>
      </div>
    `;
  }

  box.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid #3B82F6; border-radius:8px; padding:12px 14px; margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid #E2E8F0;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="font-weight:700; font-size:14.5px; color:#0F172A;">⚙️ 全域設定微調區</span>
          ${tabBtn('duts', `📋 DUTs (${duts.length})`)}
          ${tabBtn('inst', `🔌 Instrument (${insts.length})`)}
          ${tabBtn('gini', `🧩 Global.ini (${Object.keys(gSettings).length + Object.keys(gScripts).length})`)}
        </div>
        <div style="display:flex; gap:8px;">
          <button onclick="applyGlobalEditorAndReaudit()" class="btn btn-primary-blue" style="padding:5px 14px; font-size:13px;">✔ 套用微調並重跑健檢</button>
          <button onclick="toggleGlobalEditorPanel()" class="btn" style="padding:5px 10px; font-size:13px; background:#E2E8F0; color:#334155;">收合 ▲</button>
        </div>
      </div>
      ${bodyHtml}
    </div>
  `;
}

function onDutLoadSelect(idx, val) {
  if (val !== '__CUSTOM__') {
    STATE.workspace.duts[idx]['Load'] = val;
  }
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
  STATE.workspace.global_ini = STATE.workspace.global_ini || { Settings: {}, Scripts: {} };
  STATE.workspace.global_ini[sec.trim()][k.trim()] = v;
  renderGlobalEditorPanel();
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
  STATE.pendingInserts = STATE.pendingInserts || [];
  const labelMap = { duts: 'DUTs 站別/條碼', inst: 'Instrument 掛載/設定', gini: 'Global.ini 變數' };
  STATE.pendingInserts.push({
    sheet: labelMap[AUDIT_GLOBAL_TAB] || '全域設定',
    inst: '線上微調',
    summary: '已套用微調並完成即時覆檢（請匯出 *_FIXED.xlsx 寫入檔案）'
  });
  renderAuditResults();
  alert('✔ 已套用微調並完成即時覆檢！請確認下方檢查結果，或點擊「💾 立即匯出並驗證」。');
}
