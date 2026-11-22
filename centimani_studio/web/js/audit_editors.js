// Task-Oriented Semantic Global Config Editor for Script Doctor
// Filters out unused variables/instruments and splits composite strings into plain-language fields.
let AUDIT_GLOBAL_TAB = 'station_isn';
let INI_DIFF_FILTER_CHANGED_ONLY = false;

function snapshotOriginalInis(ws) {
  if (!ws) return;
  STATE.origGlobalIni = JSON.parse(JSON.stringify(ws.global_ini || { Settings: {}, Scripts: {} }));
  STATE.origSystemIni = JSON.parse(JSON.stringify(ws.system_ini || {}));
}

function _ensureIniSnapshots(ws) {
  if (!ws) return;
  if (!STATE.origGlobalIni) {
    STATE.origGlobalIni = JSON.parse(JSON.stringify(ws.global_ini || { Settings: {}, Scripts: {} }));
  }
  if (!STATE.origSystemIni) {
    STATE.origSystemIni = JSON.parse(JSON.stringify(ws.system_ini || {}));
  }
}

function toggleIniDiffFilter(onlyChanged) {
  INI_DIFF_FILTER_CHANGED_ONLY = Boolean(onlyChanged);
  renderGlobalEditorPanel();
}

function _collectIniDiffEntries(origObj, currObj, fileLabel) {
  const sections = Array.from(new Set([
    ...Object.keys(origObj || {}),
    ...Object.keys(currObj || {})
  ]));
  const entries = [];
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
        file: fileLabel,
        section: sec,
        key: k,
        oldVal: oldVal === null ? '(原本無此項)' : oldVal,
        newVal: newVal === null ? '' : newVal,
        isAdded,
        isModified,
        isChanged
      });
    });
  });
  // 將有異動的項目排在最上方，方便一眼核對
  entries.sort((a, b) => (b.isChanged ? 1 : 0) - (a.isChanged ? 1 : 0));
  return entries;
}

function updateIniFromDiffView(fileLabel, sec, key, val) {
  if (!STATE.workspace) return;
  if (fileLabel === 'Global.ini') {
    STATE.workspace.global_ini = STATE.workspace.global_ini || {};
    STATE.workspace.global_ini[sec] = STATE.workspace.global_ini[sec] || {};
    STATE.workspace.global_ini[sec][key] = val;
  } else {
    STATE.workspace.system_ini = STATE.workspace.system_ini || {};
    STATE.workspace.system_ini[sec] = STATE.workspace.system_ini[sec] || {};
    STATE.workspace.system_ini[sec][key] = val;
  }
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
  // 更新快照基準或保留對照並顯示成功橫幅
  const banner = document.getElementById('iniSaveResultBanner');
  if (banner) {
    banner.style.display = 'block';
    banner.innerHTML = `
      <div style="font-weight:800; color:#14532D; font-size:13.5px;">🎉 已成功寫入 INI 設定檔並直接彈出 Notepad 檢視（未開啟 Excel）！</div>
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
  // Match "UDP","LAN","*$(PCIP_1),192.168.100.10,2345,0,10000"
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

function _describeGlobalVar(k) {
  if (/^PCIP_/i.test(k)) return 'PC 端網卡 IP';
  if (/^DUTIP_/i.test(k)) return '待測板 DUT IP';
  if (/^GoldenIP/i.test(k)) return '黃金機台 / 伺服器 IP';
  if (/^DUT_UR/i.test(k)) return '待測板 UART COM Port';
  if (/^PCUART_fixture/i.test(k)) return '治具氣動控制 COM Port';
  if (/^PCUART/i.test(k)) return 'PC 端序列埠 COM Port';
  if (/^DAQ_/i.test(k)) return 'NI-6008 / 6009 裝置代碼';
  if (/^LED_AZ/i.test(k)) return 'FeasaLED COM Port';
  if (/^LED_Light/i.test(k)) return 'FeasaLED 通道編號';
  if (/^DUT_Login/i.test(k)) return 'SSH / Console 登入帳號';
  if (/^LOAD_/i.test(k)) return '槽位載入開關';
  if (/^DEVID_/i.test(k)) return 'SFIS 機台設備編號';
  if (/^FW_VERSION/i.test(k)) return '目標韌體版本號';
  return '腳本自訂變數';
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
  const { usedVars, usedInstRefs } = _collectUsedVarsAndInstruments(ws);

  const tabBtn = (id, label) => {
    const active = AUDIT_GLOBAL_TAB === id;
    return `<button onclick="switchGlobalEditorTab('${id}')" class="btn" style="padding:5px 12px; font-size:13px; ${active ? 'background:#2563EB;color:#FFFFFF;border-color:#1D4ED8;font-weight:700;' : 'background:#FFFFFF;color:#334155;border-color:#CBD5E1;'}">${label}</button>`;
  };

  let bodyHtml = '';
  if (AUDIT_GLOBAL_TAB === 'station_isn') {
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
        <td><input value="${_escAttr(gSettings[k])}" onchange="STATE.workspace.global_ini['Settings']['${_escAttr(k)}']=this.value" class="mono" style="width:100%;padding:4px;font-size:12.5px;box-sizing:border-box;"></td>
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
    // Tab 3: Used Instruments & Used Global.ini COM/HW vars (with unused collapsed)
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

    const hwKeysSettings = Object.keys(gSettings).filter(k => !/IP/i.test(k) && (usedVars.has(k) || /^(DUT_UR1|DAQ_1|LED_AZ1)$/i.test(k)));
    const hwKeysScripts = Object.keys(gScripts).filter(k => usedVars.has(k) || /^(FW_VERSION)$/i.test(k));
    const unusedKeysSettings = Object.keys(gSettings).filter(k => !/IP/i.test(k) && !hwKeysSettings.includes(k));

    const kvRow = (sec, k, val) => `
      <tr>
        <td style="font-size:12px; color:#475569;">${_describeGlobalVar(k)}</td>
        <td class="mono" style="font-weight:700; color:#1E3A8A;">[${sec}] ${k}</td>
        <td><input value="${_escAttr(val)}" onchange="STATE.workspace.global_ini['${sec}']['${_escAttr(k)}']=this.value" class="mono" style="width:100%;padding:4px;font-size:12px;box-sizing:border-box;"></td>
      </tr>
    `;

    bodyHtml = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
        <span style="font-size:12.5px; color:#475569;">僅顯示本腳本<b>實際使用中</b>的儀器（${activeInsts.length} 台）與 <b>COM / 硬體變數</b>（${hwKeysSettings.length + hwKeysScripts.length} 項）。</span>
        <button onclick="addGlobalIniVar()" class="btn btn-primary-green" style="padding:3px 10px; font-size:12px;">+ 新增 Global.ini 變數</button>
      </div>
      <div style="overflow:auto; max-height:360px; display:flex; flex-direction:column; gap:10px;">
        <table class="meas-table">
          <thead><tr><th>用途說明</th><th>Global.ini 變數</th><th>設定值</th></tr></thead>
          <tbody>
            ${hwKeysSettings.map(k => kvRow('Settings', k, gSettings[k])).join('')}
            ${hwKeysScripts.map(k => kvRow('Scripts', k, gScripts[k])).join('')}
          </tbody>
        </table>
        <table class="meas-table">
          <thead><tr><th>Mount (掛載站別)</th><th>儀器名稱</th><th>Settings (IP / COM / GPIB)</th><th>Functions</th><th>Version</th></tr></thead>
          <tbody>${activeInsts.map(renderInstRow).join('') || '<tr><td colspan="5" style="text-align:center;color:#64748B;">目前測站尚無掛載使用中之儀器</td></tr>'}</tbody>
        </table>
        ${idleInsts.length > 0 ? `
          <details style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:6px 10px;">
            <summary style="cursor:pointer; font-weight:700; font-size:12.5px; color:#475569;">📦 顯示其餘未使用的型錄儀器（共 ${idleInsts.length} 台）</summary>
            <table class="meas-table" style="margin-top:6px;">
              <thead><tr><th>Mount</th><th>儀器名稱</th><th>Settings</th><th>Functions</th><th>Version</th></tr></thead>
              <tbody>${idleInsts.map(renderInstRow).join('')}</tbody>
            </table>
          </details>
        ` : ''}
        ${unusedKeysSettings.length > 0 ? `
          <details style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:6px 10px;">
            <summary style="cursor:pointer; font-weight:700; font-size:12.5px; color:#475569;">🧩 顯示其餘未引用的 Global.ini 變數（共 ${unusedKeysSettings.length} 項）</summary>
            <table class="meas-table" style="margin-top:6px;">
              <tbody>${unusedKeysSettings.map(k => kvRow('Settings', k, gSettings[k])).join('')}</tbody>
            </table>
          </details>
        ` : ''}
      </div>
    `;
  } else if (AUDIT_GLOBAL_TAB === 'ini_diff') {
    _ensureIniSnapshots(ws);
    const gEntries = _collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini');
    const sEntries = _collectIniDiffEntries(STATE.origSystemIni, ws.system_ini, 'System.ini');
    const allEntries = [...gEntries, ...sEntries];
    const changedCount = allEntries.filter(e => e.isChanged).length;
    const shownEntries = INI_DIFF_FILTER_CHANGED_ONLY ? allEntries.filter(e => e.isChanged) : allEntries;

    const leftRows = shownEntries.map(e => {
      const rowBg = e.isChanged ? '#FEF2F2' : '#FFFFFF';
      const valCol = e.isChanged ? '#DC2626' : '#334155';
      return `
        <tr style="background:${rowBg};">
          <td class="mono" style="font-size:11.5px; color:#64748B;">${_escAttr(e.file)}</td>
          <td class="mono" style="font-size:12px; font-weight:700; color:#1E293B;">[${_escAttr(e.section)}] ${_escAttr(e.key)}</td>
          <td class="mono" style="font-size:12px; color:${valCol}; ${e.isChanged ? 'font-weight:700; text-decoration:line-through;' : ''}">${_escAttr(e.oldVal)}</td>
        </tr>
      `;
    }).join('');

    const rightRows = shownEntries.map(e => {
      const rowBg = e.isChanged ? '#ECFDF5' : '#FFFFFF';
      const badge = e.isAdded
        ? '<span style="background:#0284C7;color:#FFF;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:700;margin-left:4px;">✨新增</span>'
        : (e.isModified ? '<span style="background:#16A34A;color:#FFF;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:700;margin-left:4px;">✏️已改</span>' : '');
      return `
        <tr style="background:${rowBg};">
          <td class="mono" style="font-size:11.5px; color:#64748B;">${_escAttr(e.file)}</td>
          <td class="mono" style="font-size:12px; font-weight:700; color:#1E293B;">[${_escAttr(e.section)}] ${_escAttr(e.key)} ${badge}</td>
          <td>
            <input value="${_escAttr(e.newVal)}"
              onchange="updateIniFromDiffView('${_escAttr(e.file)}','${_escAttr(e.section)}','${_escAttr(e.key)}',this.value)"
              class="mono"
              style="width:100%; padding:3px 6px; font-size:12px; box-sizing:border-box; border:1px solid ${e.isChanged ? '#16A34A' : '#CBD5E1'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; font-weight:${e.isChanged ? '700' : '400'}; color:#0F172A; border-radius:4px;">
          </td>
        </tr>
      `;
    }).join('');

    bodyHtml = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:10px; background:#F0FDF4; border:1.5px solid #86EFAC; border-radius:8px; padding:10px 14px;">
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
          <span style="font-weight:800; font-size:13.5px; color:#14532D;">🆚 INI 修改前後左右對照視窗（目前已修改 <span style="color:#DC2626; font-size:15px;">${changedCount}</span> 項設定）</span>
          <button onclick="toggleIniDiffFilter(true)" class="btn" style="padding:3px 10px; font-size:12px; ${INI_DIFF_FILTER_CHANGED_ONLY ? 'background:#16A34A;color:#FFF;font-weight:700;' : 'background:#FFF;color:#334155;'}">🔍 只看已修改項 (${changedCount})</button>
          <button onclick="toggleIniDiffFilter(false)" class="btn" style="padding:3px 10px; font-size:12px; ${!INI_DIFF_FILTER_CHANGED_ONLY ? 'background:#2563EB;color:#FFF;font-weight:700;' : 'background:#FFF;color:#334155;'}">📋 顯示全部 (${allEntries.length})</button>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button onclick="saveAndOpenModifiedIni('auto')" class="btn btn-primary-green" style="padding:6px 16px; font-size:13px; font-weight:800; box-shadow:0 2px 6px rgba(22,163,74,0.25);">
            💾 存檔並彈出剛剛改的 INI (免開 Excel)
          </button>
          <button onclick="saveAndOpenModifiedIni('global')" class="btn" style="padding:5px 11px; font-size:12px; background:#EFF6FF; color:#1E40AF; border:1px solid #93C5FD; font-weight:700;">
            📄 存檔並彈出 Global.ini
          </button>
          <button onclick="saveAndOpenModifiedIni('system')" class="btn" style="padding:5px 11px; font-size:12px; background:#EFF6FF; color:#1E40AF; border:1px solid #93C5FD; font-weight:700;">
            ⚙️ 存檔並彈出 System.ini
          </button>
        </div>
      </div>
      <div id="iniSaveResultBanner" style="display:none; background:#DCFCE7; border:1.5px solid #22C55E; border-radius:6px; padding:8px 12px; margin-bottom:10px;"></div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
        <div style="border:1.5px solid #FCA5A5; border-radius:8px; overflow:hidden; background:#FFFFFF;">
          <div style="background:#FEF2F2; padding:7px 12px; font-weight:800; font-size:13px; color:#991B1B; border-bottom:1px solid #FCA5A5;">
            ⬅️ 左視窗：修改前（原始 Global.ini / System.ini）
          </div>
          <div style="max-height:360px; overflow:auto;">
            <table class="meas-table" style="margin:0;">
              <thead><tr><th>檔案</th><th>[區段] 參數名稱</th><th>原始設定值</th></tr></thead>
              <tbody>${leftRows || '<tr><td colspan="3" style="text-align:center;color:#64748B;padding:18px;">目前尚無任何異動項目</td></tr>'}</tbody>
            </table>
          </div>
        </div>
        <div style="border:1.5px solid #86EFAC; border-radius:8px; overflow:hidden; background:#FFFFFF;">
          <div style="background:#DCFCE7; padding:7px 12px; font-weight:800; font-size:13px; color:#14532D; border-bottom:1px solid #86EFAC;">
            ➡️ 右視窗：修改後（最新設定值，可直接於右側欄位微調）
          </div>
          <div style="max-height:360px; overflow:auto;">
            <table class="meas-table" style="margin:0;">
              <thead><tr><th>檔案</th><th>[區段] 參數名稱</th><th>修改後設定值（可編輯）</th></tr></thead>
              <tbody>${rightRows || '<tr><td colspan="3" style="text-align:center;color:#64748B;padding:18px;">目前尚無任何異動項目</td></tr>'}</tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  _ensureIniSnapshots(ws);
  const totalIniChanges = [
    ..._collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini'),
    ..._collectIniDiffEntries(STATE.origSystemIni, ws.system_ini, 'System.ini')
  ].filter(e => e.isChanged).length;

  box.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid #3B82F6; border-radius:8px; padding:12px 14px; margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid #E2E8F0;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="font-weight:700; font-size:14.5px; color:#0F172A;">⚙️ 全域設定微調區</span>
          ${tabBtn('station_isn', `📋 站別開關與 ISN (${duts.length})`)}
          ${tabBtn('net_ip', '🌐 網路 IP / Ping / Port')}
          ${tabBtn('inst_com', '🔌 儀器掛載與 COM Port')}
          ${tabBtn('ini_diff', `🆚 INI 左右對照與存檔彈出 (${totalIniChanges})`)}
        </div>
        <div style="display:flex; gap:8px;">
          <button onclick="saveAndOpenModifiedIni('auto')" class="btn btn-primary-green" style="padding:5px 14px; font-size:13px; font-weight:800;">💾 存檔並彈出 INI</button>
          <button onclick="applyGlobalEditorAndReaudit()" class="btn btn-primary-blue" style="padding:5px 14px; font-size:13px;">✔ 套用微調並看左右對照</button>
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
  STATE.workspace.global_ini = STATE.workspace.global_ini || { Settings: {}, Scripts: {} };
  STATE.workspace.global_ini[sec.trim()][k.trim()] = v;
  renderGlobalEditorPanel();
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
    inst: 'Global.ini / 線上微調',
    summary: '已套用微調並完成即時覆檢（可於左右視窗核對 INI 並直接存檔彈出 INI，或匯出 *_FIXED.xlsx）'
  });
  AUDIT_GLOBAL_TAB = 'ini_diff';
  renderGlobalEditorPanel();
  renderAuditResults();
}
