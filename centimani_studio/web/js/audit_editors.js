// Task-Oriented Semantic Global Config Editor & Side-by-Side Live INI Workbench (Plan A)
// Left Panel: Intuitive Controls (SFIS/iPLAS switches + Script's Active COM/IP/Hardware vars)
// Right Panel: Live Synchronized Before -> After (舊值 ➔ 新值) Diff + Real INI File Highlighted Preview + One-Click Save & Pop Up INI

let AUDIT_GLOBAL_TAB = 'ini_diff';
let INI_PREVIEW_FILE_TAB = 'auto'; // 'auto' | 'Global.ini' | 'System.ini'

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

function setSystemIniValueLive(key, val) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.system_ini[key] = String(val);
  INI_PREVIEW_FILE_TAB = 'System.ini';
  _recordPendingIniNotice(`System.ini: ${key}=${val}`);
  renderGlobalEditorPanel();
}

function setGlobalIniValueLive(sec, key, val, rerenderFull = true) {
  if (!STATE.workspace) return;
  _ensureIniSnapshots(STATE.workspace);
  STATE.workspace.global_ini = STATE.workspace.global_ini || { Settings: {}, Scripts: {} };
  STATE.workspace.global_ini[sec] = STATE.workspace.global_ini[sec] || {};
  STATE.workspace.global_ini[sec][key] = String(val);
  INI_PREVIEW_FILE_TAB = 'Global.ini';
  _recordPendingIniNotice(`Global.ini [${sec}] ${key}=${val}`);
  if (rerenderFull) {
    renderGlobalEditorPanel();
  } else {
    _refreshIniRightPaneOnly();
  }
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

function switchIniPreviewFileTab(tab) {
  INI_PREVIEW_FILE_TAB = tab;
  _refreshIniRightPaneOnly();
}

function _buildRightPaneHtml(ws) {
  _ensureIniSnapshots(ws);
  const gEntries = _collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini');
  const sEntries = _collectIniDiffEntries(STATE.origSystemIni, ws.system_ini, 'System.ini');
  const gChanged = gEntries.filter(e => e.isChanged);
  const sChanged = sEntries.filter(e => e.isChanged);
  const allChanged = [...sChanged, ...gChanged];

  let activeFile = INI_PREVIEW_FILE_TAB;
  if (activeFile === 'auto') {
    activeFile = (sChanged.length > 0 && gChanged.length === 0) ? 'System.ini' : 'Global.ini';
  }

  // 1. 上半部：本次已修改項目一覽表（同一列嚴格對齊：參數名 | 舊值 ➔ 新值 | 還原）
  let diffSummaryHtml = '';
  if (allChanged.length === 0) {
    diffSummaryHtml = `
      <div style="background:#F8FAFC; border:1.5px dashed #CBD5E1; border-radius:8px; padding:14px 16px; color:#475569; font-size:12.5px; line-height:1.6;">
        💡 <b>目前尚無任何異動項目。</b><br>
        請直接在左側面板切換 <b>SFIS / iPLAS 開關</b> 或修改 <b>COM Port / IP 位址</b>，此處會即時以「<span style="color:#DC2626;text-decoration:line-through;">修改前舊值</span> ➔ <span style="color:#15803D;font-weight:700;">修改後新值</span>」逐列對齊呈現！
      </div>
    `;
  } else {
    const rows = allChanged.map(e => `
      <tr style="background:#F0FDF4; border-bottom:1px solid #BBF7D0;">
        <td style="padding:6px 8px;">
          <span style="background:${e.file === 'System.ini' ? '#EDE9FE' : '#DBEAFE'}; color:${e.file === 'System.ini' ? '#5B21B6' : '#1E40AF'}; font-weight:800; font-size:11px; padding:1px 6px; border-radius:4px;" class="mono">${_escAttr(e.file)}</span>
          <span class="mono" style="font-weight:800; font-size:12.5px; color:#0F172A; margin-left:4px;">${_escAttr(e.key)}</span>
          <div style="font-size:11.5px; color:#475569; margin-top:2px;">${_escAttr(e.desc)}</div>
        </td>
        <td style="padding:6px 8px; white-space:nowrap;">
          <span class="mono" style="background:#FEE2E2; color:#B91C1C; padding:2px 7px; border-radius:4px; text-decoration:line-through; font-size:12px;">${_escAttr(e.oldVal)}</span>
          <span style="margin:0 6px; font-weight:900; color:#16A34A;">➔</span>
          <span class="mono" style="background:#DCFCE7; color:#15803D; border:1px solid #86EFAC; padding:2px 8px; border-radius:4px; font-weight:800; font-size:12.5px;">${_escAttr(e.newVal)}</span>
        </td>
        <td style="padding:6px 8px; text-align:right; width:56px;">
          <button onclick="revertSingleIniKey('${_escAttr(e.file)}','${_escAttr(e.section)}','${_escAttr(e.key)}')" class="btn" style="padding:2px 8px; font-size:11.5px; background:#FFFFFF; color:#475569; border:1px solid #CBD5E1;" title="還原此項為原始設定值">↩ 還原</button>
        </td>
      </tr>
    `).join('');

    diffSummaryHtml = `
      <div style="border:1.5px solid #22C55E; border-radius:8px; overflow:hidden; background:#FFFFFF;">
        <div style="background:#DCFCE7; padding:7px 12px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #86EFAC;">
          <span style="font-weight:800; font-size:13px; color:#14532D;">✨ 本次已修改項目對照（共 ${allChanged.length} 項：舊值 ➔ 新值）</span>
          <button onclick="revertAllIniChanges()" class="btn" style="padding:2px 10px; font-size:11.5px; background:#FFFFFF; color:#B91C1C; border:1px solid #FCA5A5; font-weight:700;">↩ 全部還原</button>
        </div>
        <div style="max-height:175px; overflow:auto;">
          <table style="width:100%; border-collapse:collapse;">
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  // 2. 下半部：真實 INI 檔案全文預覽（有改的那幾行自動亮綠底高亮＋顯示舊值）
  const { usedVars } = _collectUsedVarsAndInstruments(ws);
  let previewLinesHtml = '';
  if (activeFile === 'System.ini') {
    const sectionsOrder = ['System', 'SFIS', 'iPLAS', 'CSVReport', 'IpFinder'];
    sectionsOrder.forEach(sec => {
      const secItems = sEntries.filter(e => e.section === sec);
      if (secItems.length === 0) return;
      previewLinesHtml += `<div style="color:#0369A1; font-weight:800; margin-top:6px;">[${_escAttr(sec)}]</div>`;
      secItems.forEach(e => {
        if (e.isChanged) {
          previewLinesHtml += `
            <div style="background:#DCFCE7; border-left:3.5px solid #16A34A; padding:2px 8px; margin:2px 0; border-radius:3px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
              <span><b style="color:#0F172A;">${_escAttr(e.key)}</b>=<b style="color:#15803D;">${_escAttr(e.newVal)}</b></span>
              <span style="font-size:11.5px; color:#B91C1C; font-weight:700;">⬅ 原本: ${_escAttr(e.oldVal)}（${_escAttr(e.desc)}）</span>
            </div>
          `;
        } else {
          previewLinesHtml += `<div style="padding:1px 8px; color:#334155;"><span>${_escAttr(e.key)}=${_escAttr(e.newVal)}</span> <span style="color:#94A3B8; font-size:11px;">// ${_escAttr(e.desc)}</span></div>`;
        }
      });
    });
  } else {
    ['Settings', 'Scripts'].forEach(sec => {
      const secItems = gEntries.filter(e => e.section === sec);
      if (secItems.length === 0) return;
      // 優先把「已修改」與「本腳本實際使用」的變數排在前面
      secItems.sort((a, b) => {
        const scoreA = (a.isChanged ? 10 : 0) + (usedVars.has(a.key) ? 5 : 0);
        const scoreB = (b.isChanged ? 10 : 0) + (usedVars.has(b.key) ? 5 : 0);
        return scoreB - scoreA;
      });
      previewLinesHtml += `<div style="color:#0369A1; font-weight:800; margin-top:6px;">[${_escAttr(sec)}]</div>`;
      secItems.forEach(e => {
        const isUsed = usedVars.has(e.key) || /^(DUT_UR1|DUTIP_1|PCIP_1|DAQ_1|LED_AZ1|LOAD_1|DEVID_1|FW_VERSION)$/i.test(e.key);
        if (e.isChanged) {
          previewLinesHtml += `
            <div style="background:#DCFCE7; border-left:3.5px solid #16A34A; padding:2px 8px; margin:2px 0; border-radius:3px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
              <span><b style="color:#0F172A;">${_escAttr(e.key)}</b>=<b style="color:#15803D;">${_escAttr(e.newVal)}</b></span>
              <span style="font-size:11.5px; color:#B91C1C; font-weight:700;">⬅ 原本: ${_escAttr(e.oldVal)}（${_escAttr(e.desc)}）</span>
            </div>
          `;
        } else if (isUsed) {
          previewLinesHtml += `<div style="padding:1px 8px; color:#1E293B;"><span>${_escAttr(e.key)}=${_escAttr(e.newVal)}</span> <span style="color:#64748B; font-size:11px;">// ${_escAttr(e.desc)}</span></div>`;
        } else {
          previewLinesHtml += `<div style="padding:1px 8px; color:#94A3B8; font-size:11.5px;"><span>${_escAttr(e.key)}=${_escAttr(e.newVal)}</span></div>`;
        }
      });
    });
  }

  return `
    <div style="display:flex; flex-direction:column; gap:10px; height:100%;">
      ${diffSummaryHtml}
      <div style="border:1px solid #CBD5E1; border-radius:8px; overflow:hidden; background:#FFFFFF; flex:1; display:flex; flex-direction:column;">
        <div style="background:#F1F5F9; padding:6px 10px; border-bottom:1px solid #CBD5E1; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
          <span style="font-weight:800; font-size:12.5px; color:#1E293B;">📄 真實 INI 檔案預覽（綠底為本次修改行）</span>
          <div style="display:flex; gap:4px;">
            <button onclick="switchIniPreviewFileTab('Global.ini')" class="btn" style="padding:2px 10px; font-size:12px; ${activeFile === 'Global.ini' ? 'background:#2563EB;color:#FFF;font-weight:700;' : 'background:#FFF;color:#334155;'}">
              Global.ini ${gChanged.length > 0 ? `(${gChanged.length} 改)` : ''}
            </button>
            <button onclick="switchIniPreviewFileTab('System.ini')" class="btn" style="padding:2px 10px; font-size:12px; ${activeFile === 'System.ini' ? 'background:#2563EB;color:#FFF;font-weight:700;' : 'background:#FFF;color:#334155;'}">
              System.ini ${sChanged.length > 0 ? `(${sChanged.length} 改)` : ''}
            </button>
          </div>
        </div>
        <div class="mono" style="padding:8px 10px; font-size:12px; line-height:1.55; max-height:220px; overflow:auto; background:#FAFAFA;">
          ${previewLinesHtml}
        </div>
      </div>
      <div id="iniSaveResultBanner" style="display:none; background:#DCFCE7; border:1.5px solid #22C55E; border-radius:6px; padding:8px 12px;"></div>
      <div style="background:#F0FDF4; border:1.5px solid #86EFAC; border-radius:8px; padding:10px 12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
          <button onclick="saveAndOpenModifiedIni('global')" class="btn" style="padding:4px 10px; font-size:12px; background:#FFFFFF; color:#1E40AF; border:1px solid #93C5FD; font-weight:700;">📄 存檔並開 Global.ini</button>
          <button onclick="saveAndOpenModifiedIni('system')" class="btn" style="padding:4px 10px; font-size:12px; background:#FFFFFF; color:#5B21B6; border:1px solid #C4B5FD; font-weight:700;">⚙️ 存檔並開 System.ini</button>
        </div>
        <button onclick="saveAndOpenModifiedIni('auto')" class="btn btn-primary-green" style="padding:7px 18px; font-size:13.5px; font-weight:800; box-shadow:0 2px 6px rgba(22,163,74,0.25);">
          💾 確認存檔並立即彈出剛剛改的 INI
        </button>
      </div>
    </div>
  `;
}

function _refreshIniRightPaneOnly() {
  const pane = document.getElementById('iniLiveRightPane');
  if (pane && STATE.workspace) {
    pane.innerHTML = _buildRightPaneHtml(STATE.workspace);
  }
  const badge = document.getElementById('iniTabDiffCountBadge');
  if (badge && STATE.workspace) {
    const total = [
      ..._collectIniDiffEntries(STATE.origGlobalIni, STATE.workspace.global_ini, 'Global.ini'),
      ..._collectIniDiffEntries(STATE.origSystemIni, STATE.workspace.system_ini, 'System.ini')
    ].filter(e => e.isChanged).length;
    badge.textContent = `(${total})`;
  }
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
      <div style="font-weight:800; color:#14532D; font-size:13px;">🎉 已成功寫入硬碟並直接以記事本 (Notepad) 彈出剛剛修改的 INI 檔！</div>
      <div class="mono" style="font-size:11.5px; color:#166534; margin-top:3px; word-break:break-all;">
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
  const gScripts = (ws.global_ini && ws.global_ini.Scripts) || {};
  const sysIni = ws.system_ini || {};
  const stationNames = Object.keys(ws.stations || {});
  const { usedVars, usedInstRefs } = _collectUsedVarsAndInstruments(ws);

  const tabBtn = (id, labelHtml) => {
    const active = AUDIT_GLOBAL_TAB === id;
    return `<button onclick="switchGlobalEditorTab('${id}')" class="btn" style="padding:5px 12px; font-size:13px; ${active ? 'background:#2563EB;color:#FFFFFF;border-color:#1D4ED8;font-weight:700;' : 'background:#FFFFFF;color:#334155;border-color:#CBD5E1;'}">${labelHtml}</button>`;
  };

  let bodyHtml = '';
  if (AUDIT_GLOBAL_TAB === 'ini_diff') {
    // ================= 方案 A：左邊直覺設定面板 + 右邊真實 INI 即時對照與存檔彈出 =================
    const mkSysToggle = (key, label, onText = '🟢 開啟 (1)', offText = '⚪ 關閉 (0)') => {
      const curVal = String(sysIni[key] !== undefined ? sysIni[key] : '0').trim();
      const origVal = String((STATE.origSystemIni || {})[key] !== undefined ? STATE.origSystemIni[key] : curVal).trim();
      const isOn = curVal === '1' || curVal.toLowerCase() === 'true';
      const isMod = curVal !== origVal;
      return `
        <div style="background:${isMod ? '#F0FDF4' : '#F8FAFC'}; border:1px solid ${isMod ? '#22C55E' : '#CBD5E1'}; border-radius:6px; padding:7px 10px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
          <div>
            <div style="font-weight:700; font-size:12.5px; color:#0F172A;">${label} ${isMod ? '<span style="color:#16A34A;font-size:11px;">✏️已改</span>' : ''}</div>
            <div class="mono" style="font-size:11px; color:#64748B;">[System.ini] ${key}</div>
          </div>
          <div style="display:flex; gap:4px;">
            <button onclick="setSystemIniValueLive('${key}','1')" class="btn" style="padding:3px 9px; font-size:11.5px; ${isOn ? 'background:#16A34A;color:#FFF;font-weight:800;border-color:#15803D;' : 'background:#FFF;color:#64748B;'}">${onText}</button>
            <button onclick="setSystemIniValueLive('${key}','0')" class="btn" style="padding:3px 9px; font-size:11.5px; ${!isOn ? 'background:#334155;color:#FFF;font-weight:800;border-color:#1E293B;' : 'background:#FFF;color:#64748B;'}">${offText}</button>
          </div>
        </div>
      `;
    };

    const mkSysInput = (key, label, widthPx = 120) => {
      const curVal = String(sysIni[key] !== undefined ? sysIni[key] : '');
      const origVal = String((STATE.origSystemIni || {})[key] !== undefined ? STATE.origSystemIni[key] : curVal);
      const isMod = curVal !== origVal;
      return `
        <div style="background:${isMod ? '#F0FDF4' : '#F8FAFC'}; border:1px solid ${isMod ? '#22C55E' : '#CBD5E1'}; border-radius:6px; padding:6px 10px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
          <div>
            <div style="font-weight:700; font-size:12px; color:#0F172A;">${label}</div>
            <div class="mono" style="font-size:11px; color:#64748B;">${key}</div>
          </div>
          <input value="${_escAttr(curVal)}" oninput="setSystemIniValueLive('${key}',this.value)" class="mono"
            style="width:${widthPx}px; padding:4px 7px; font-size:12px; border:1px solid ${isMod ? '#16A34A' : '#94A3B8'}; background:${isMod ? '#DCFCE7' : '#FFF'}; border-radius:4px; font-weight:${isMod ? '700' : '400'};">
        </div>
      `;
    };

    // 篩選本腳本實際用到的 Global.ini 變數 + 已修改的變數 + 核心通訊變數
    const gEntries = _collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini');
    const activeGlobalEntries = [];
    const idleGlobalEntries = [];
    gEntries.forEach(e => {
      const isCore = usedVars.has(e.key) || /^(DUT_UR1|DUTIP_1|PCIP_1|DAQ_1|LED_AZ1|LED_Light1|LOAD_1|DEVID_1|FW_VERSION)$/i.test(e.key);
      if (e.isChanged || isCore) activeGlobalEntries.push(e);
      else idleGlobalEntries.push(e);
    });

    const mkGlobalRow = (e) => `
      <tr style="background:${e.isChanged ? '#F0FDF4' : '#FFFFFF'};">
        <td style="font-size:12px; color:#334155; padding:5px 8px;">
          <div style="font-weight:700; color:#0F172A;">${_escAttr(e.desc)}</div>
          <div class="mono" style="font-size:11px; color:#1E40AF;">[${_escAttr(e.section)}] ${_escAttr(e.key)}</div>
        </td>
        <td style="padding:5px 8px;">
          <input value="${_escAttr(e.newVal)}"
            oninput="setGlobalIniValueLive('${_escAttr(e.section)}','${_escAttr(e.key)}',this.value,false)"
            onchange="setGlobalIniValueLive('${_escAttr(e.section)}','${_escAttr(e.key)}',this.value,true)"
            class="mono"
            style="width:100%; padding:4px 7px; font-size:12.5px; box-sizing:border-box; border:1px solid ${e.isChanged ? '#16A34A' : '#94A3B8'}; background:${e.isChanged ? '#DCFCE7' : '#FFFFFF'}; font-weight:${e.isChanged ? '700' : '400'}; border-radius:4px;">
        </td>
      </tr>
    `;

    bodyHtml = `
      <div style="display:grid; grid-template-columns: 1.05fr 1fr; gap:14px; align-items:start;">
        <!-- ⬅️ 左視窗：直覺控制面板 -->
        <div style="border:1.5px solid #93C5FD; border-radius:8px; background:#FFFFFF; overflow:hidden;">
          <div style="background:#EFF6FF; padding:8px 12px; border-bottom:1px solid #93C5FD; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-weight:800; font-size:13.5px; color:#1E3A8A;">⬅️ 左視窗：直覺調整設定（點擊開關或輸入即刻連動右側）</span>
            <button onclick="addGlobalIniVar()" class="btn" style="padding:2px 9px; font-size:11.5px; background:#FFFFFF; color:#1E40AF; border:1px solid #60A5FA; font-weight:700;">+ 新增變數</button>
          </div>
          <div style="padding:10px 12px; max-height:480px; overflow:auto; display:flex; flex-direction:column; gap:10px;">
            <div style="font-weight:800; font-size:12.5px; color:#475569; border-bottom:1px solid #E2E8F0; padding-bottom:4px;">
              🌐 1. System.ini 產線過站與系統開關
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
              ${mkSysToggle('SFIS_Enable', 'SFIS 過站總開關')}
              ${mkSysToggle('SFIS_LinkIPLAS', 'SFIS 連動 iPLAS')}
              ${mkSysToggle('iPLAS_Enable', 'iPLAS 資料上傳')}
              ${mkSysToggle('DebugMode', '除錯模式 (免簽章)', '🟢 調試 (1)', '🔒 量產 (0)')}
              ${mkSysInput('SFIS_TSP', 'SFIS 站別路由碼', 110)}
              ${mkSysInput('iPLAS_Site', 'iPLAS 廠區代碼', 85)}
            </div>

            <div style="font-weight:800; font-size:12.5px; color:#475569; border-bottom:1px solid #E2E8F0; padding-bottom:4px; margin-top:4px;">
              🔌 2. Global.ini 本腳本實際使用之 COM / IP / 硬體參數（共 ${activeGlobalEntries.length} 項）
            </div>
            <table class="meas-table" style="margin:0;">
              <thead><tr><th style="width:48%;">參數用途與名稱</th><th>目前設定值（直接輸入即同步預覽）</th></tr></thead>
              <tbody>${activeGlobalEntries.map(mkGlobalRow).join('')}</tbody>
            </table>

            ${idleGlobalEntries.length > 0 ? `
              <details style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:6px 10px;">
                <summary style="cursor:pointer; font-weight:700; font-size:12px; color:#64748B;">📦 展開其餘未引用的備用 Global.ini 變數（共 ${idleGlobalEntries.length} 項，預設收合防干擾）</summary>
                <table class="meas-table" style="margin-top:6px;">
                  <tbody>${idleGlobalEntries.map(mkGlobalRow).join('')}</tbody>
                </table>
              </details>
            ` : ''}
          </div>
        </div>

        <!-- ➡️ 右視窗：即時修改前後對照 & 真實 INI 預覽 & 一鍵存檔彈出 -->
        <div id="iniLiveRightPane">
          ${_buildRightPaneHtml(ws)}
        </div>
      </div>
    `;
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

  const totalIniChanges = [
    ..._collectIniDiffEntries(STATE.origGlobalIni, ws.global_ini, 'Global.ini'),
    ..._collectIniDiffEntries(STATE.origSystemIni, ws.system_ini, 'System.ini')
  ].filter(e => e.isChanged).length;

  box.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid #3B82F6; border-radius:8px; padding:12px 14px; margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid #E2E8F0;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="font-weight:700; font-size:14.5px; color:#0F172A;">⚙️ 全域與 INI 設定工作台</span>
          ${tabBtn('ini_diff', `🆚 INI 左改右看對照與存檔 <span id="iniTabDiffCountBadge">(${totalIniChanges})</span>`)}
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
