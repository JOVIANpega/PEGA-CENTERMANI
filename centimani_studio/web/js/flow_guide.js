// Flow Guide Intro Pages & System Settings Manager
let APP_SETTINGS = {
  auto_fullscreen: true,
  show_flow_guide: true,
  auto_open_folder: true,
  auto_checksum: true,
  tic_generic_only: false,
  intro_font_size: 15,
  skip_guides: {}
};

let PENDING_FLOW_TARGET = { tab: 'audit', afterAction: null };

const FLOW_GUIDE_DATA = {
  audit: {
    icon: '🛠️',
    title: '腳本健檢與修復 — 操作流程導覽',
    themeBg: '#E0F2FE',
    themeBorder: '#0284C7',
    btnClass: 'btn-primary-blue',
    btnLabel: '開始使用：腳本健檢 ▶',
    steps: [
      { num: '①', title: '選取檔案', items: ['單一 Excel 腳本', '或整包資料夾掃描'] },
      { num: '②', title: '檢查與微調', items: ['看紅黃燈錯誤明細', '線上改站別/ISN/IP/COM'] },
      { num: '③', title: '補儀器 / 跳轉', items: ['插 NI-6009 / Feasa / RF', '視覺化改 PASS/FAIL 跳轉'] },
      { num: '④', title: '匯出與簽章', items: ['產出 *_FIXED.xlsx', '寫入 Global.ini 與 Checksum'] }
    ],
    tip: '產出物：同目錄 *_FIXED.xlsx（修正儲存格亮黃底標註）＋ Checksum 簽章 ＋ Global.ini'
  },
  gen: {
    icon: '🧩',
    title: '新腳本母體產生器 — 操作流程導覽',
    themeBg: '#DCFCE7',
    themeBorder: '#16A34A',
    btnClass: 'btn-primary-green',
    btnLabel: '開始使用：母體產生器 ▶',
    steps: [
      { num: '①', title: '基本與 ISN', items: ['輸入專案 / 站別 / 槽位', '設定 ISN 與 SFIS/iPLAS 廠區'] },
      { num: '②', title: '骨架與儀器', items: ['勾選標準流程積木', '快選 34 款儀器進入人機'] },
      { num: '③', title: '細部參數', items: ['接線圖點腳位與上下限', '設定韌體 / Ping / Python'] },
      { num: '④', title: '產出測試包', items: ['實機產線測試包', '或無硬體試跑 Dry-Run 版'] }
    ],
    tip: '產出物：標準 16 欄 TestFlow.xlsx ＋ System.ini ＋ Global.ini ＋ Test Item Code 表'
  },
  diagnose: {
    icon: '🩺',
    title: '測試 Log 失敗診斷 — 操作流程導覽',
    themeBg: '#FEF3C7',
    themeBorder: '#D97706',
    btnClass: 'btn-jump',
    btnLabel: '開始使用：Log 診斷 ▶',
    steps: [
      { num: '①', title: '匯入 Log', items: ['選取大型 Log / CSV 檔', '或直接貼上錯誤文字片段'] },
      { num: '②', title: '自動定位異常', items: ['抓出 FAIL 測項與錯誤碼', '計算實測值 vs 規格差距'] },
      { num: '③', title: '節拍與對策', items: ['Phase 耗時 Top5 排行', '產線排查步驟建議'] },
      { num: '④', title: '一鍵匯報', items: ['產生乾淨異常摘要報告', '複製貼至 Teams / 郵件'] }
    ],
    tip: '適用場景：產線 FAIL 快速判讀、找出測試 Cycle Time 瓶頸測項'
  },
  tic: {
    icon: '🏷️',
    title: 'TestID / Error Code 速查 — 操作流程導覽',
    themeBg: '#E0E7FF',
    themeBorder: '#4F46E5',
    btnClass: 'btn-dry',
    btnLabel: '開始使用：代碼速查 ▶',
    steps: [
      { num: '①', title: '自動載入表', items: ['預設載入最新 V2.04 版', '免手動選檔（可換新版）'] },
      { num: '②', title: '關鍵字搜尋', items: ['搜尋中英文 / 7 碼代碼', '即時過濾 Error Code'] },
      { num: '③', title: '篩選通用碼', items: ['勾選僅顯示通用碼', '避免誤用舊專案專屬碼'] },
      { num: '④', title: '複製或套用', items: ['一鍵複製至剪貼簿', '或直接套入健檢/母體'] }
    ],
    tip: '適用場景：撰寫新測項找標準 7 碼代碼，或補齊健檢抓出的缺少 TestID 列'
  }
};

function applyLoadedSettings(s) {
  if (!s) return;
  APP_SETTINGS = Object.assign({}, APP_SETTINGS, s);
  if (APP_SETTINGS.intro_font_size && typeof setIntroFontSize === 'function') {
    setIntroFontSize(parseInt(APP_SETTINGS.intro_font_size, 10) || 15);
  }
  const chkTic = document.getElementById('chkTicGenericOnly');
  if (chkTic) chkTic.checked = !!APP_SETTINGS.tic_generic_only;
}

async function saveAppSettings(patch) {
  APP_SETTINGS = Object.assign({}, APP_SETTINGS, patch || {});
  try {
    const res = await fetch('/api/save_settings', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ settings: APP_SETTINGS })
    });
    const data = await res.json();
    if (data.status === 'ok' && data.settings) {
      APP_SETTINGS = data.settings;
    }
  } catch (e) {
    console.warn('saveAppSettings failed:', e);
  }
}

function enterModule(tab, afterAction = null) {
  const skipMap = APP_SETTINGS.skip_guides || {};
  if (!APP_SETTINGS.show_flow_guide || skipMap[tab] || !FLOW_GUIDE_DATA[tab]) {
    switchTab(tab);
    if (typeof afterAction === 'function') afterAction();
    return;
  }
  PENDING_FLOW_TARGET = { tab, afterAction };
  renderFlowGuidePage(tab);
}

function renderFlowGuidePage(tab) {
  const d = FLOW_GUIDE_DATA[tab];
  if (!d) { switchTab(tab); return; }

  const stepsHtml = d.steps.map((st, idx) => `
    <div style="display:flex; align-items:stretch; flex:1; min-width:170px; gap:8px;">
      <div style="flex:1; background:#FFFFFF; border:1.5px solid ${d.themeBorder}; border-radius:10px; padding:12px 14px; box-shadow:0 2px 6px rgba(15,23,42,0.06);">
        <div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
          <span style="background:${d.themeBg}; color:#0F172A; font-weight:700; font-size:13px; padding:2px 8px; border-radius:999px; border:1px solid ${d.themeBorder};">${st.num}</span>
          <span style="font-weight:700; font-size:15px; color:#0F172A;">${st.title}</span>
        </div>
        <ul style="margin:0 0 0 16px; padding:0; font-size:13px; color:#334155; line-height:1.55;">
          ${st.items.map(it => `<li>${it}</li>`).join('')}
        </ul>
      </div>
      ${idx < d.steps.length - 1 ? '<div style="display:flex; align-items:center; font-size:20px; font-weight:700; color:#64748B;">➔</div>' : ''}
    </div>
  `).join('');

  const box = document.getElementById('panelFlowGuide');
  box.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid ${d.themeBorder}; border-radius:12px; padding:20px 24px;">
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; padding-bottom:12px; border-bottom:1.5px solid ${d.themeBg};">
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:28px; background:${d.themeBg}; padding:6px 10px; border-radius:8px;">${d.icon}</span>
          <h2 style="margin:0; font-size:19px; color:#0F172A;">${d.title}</h2>
        </div>
        <button onclick="switchTab('home')" class="btn" style="background:#E2E8F0; color:#1E293B; border-color:#94A3B8;">◀ 返回首頁</button>
      </div>

      <div style="display:flex; flex-wrap:wrap; gap:10px; margin:18px 0; align-items:stretch;">
        ${stepsHtml}
      </div>

      <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 14px; font-size:13.5px; color:#1E293B; margin-bottom:16px;">
        💡 <b>說明：</b>${d.tip}
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; padding-top:12px; border-top:1px solid #E2E8F0;">
        <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer; font-weight:700; font-size:13.5px; color:#475569; user-select:none;">
          <input type="checkbox" id="chkSkipThisFlowGuide" style="width:17px; height:17px; cursor:pointer;">
          下次不再顯示此流程說明（可在首頁「⚙️ 系統與環境設定」重新開啟）
        </label>
        <button onclick="confirmFlowGuideProceed()" class="btn ${d.btnClass}" style="padding:9px 22px; font-size:14.5px;">
          ${d.btnLabel}
        </button>
      </div>
    </div>
  `;

  ['panelHome', 'panelAudit', 'panelDiagnose', 'panelGen', 'panelTic', 'panelSettings', 'panelNi6009', 'panelInstIntro', 'panelInstHmi'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
  box.style.display = 'block';
}

async function confirmFlowGuideProceed() {
  const { tab, afterAction } = PENDING_FLOW_TARGET;
  const skipChk = document.getElementById('chkSkipThisFlowGuide');
  if (skipChk && skipChk.checked) {
    const skipMap = Object.assign({}, APP_SETTINGS.skip_guides || {});
    skipMap[tab] = true;
    await saveAppSettings({ skip_guides: skipMap });
  }
  switchTab(tab);
  if (typeof afterAction === 'function') afterAction();
}

function renderSettingsPanel() {
  const s = APP_SETTINGS;
  const skipCnt = Object.values(s.skip_guides || {}).filter(Boolean).length;
  const fs = parseInt(s.intro_font_size || 15, 10);
  const box = document.getElementById('panelSettings');
  if (!box) return;
  box.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid #94A3B8; border-radius:12px; padding:20px 24px; max-width:860px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-bottom:12px; border-bottom:1px solid #E2E8F0; margin-bottom:16px;">
        <div>
          <h2 style="margin:0; font-size:19px; color:#0F172A;">⚙️ 系統與環境設定 (Preferences)</h2>
          <div style="font-size:13px; color:#64748B; margin-top:2px;">所有選項會自動保存至 config.json，下次開啟程式自動套用</div>
        </div>
        <button onclick="switchTab('home')" class="btn" style="background:#E2E8F0; color:#1E293B; border-color:#94A3B8;">◀ 返回首頁</button>
      </div>

      <div style="display:flex; flex-direction:column; gap:12px; font-size:14px;">
        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" ${s.auto_fullscreen ? 'checked' : ''} onchange="saveAppSettings({auto_fullscreen:this.checked})" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A;">啟動時自動全螢幕 / 最大化瀏覽器視窗</div>
            <div style="font-size:12.5px; color:#64748B;">開啟工具時自動將 Chrome / Edge 視窗最大化（下次啟動生效）</div>
          </div>
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" ${s.show_flow_guide ? 'checked' : ''} onchange="saveAppSettings({show_flow_guide:this.checked})" style="width:18px; height:18px;">
          <div style="flex:1;">
            <div style="font-weight:700; color:#0F172A;">進入功能前顯示「流程圖導覽說明頁」</div>
            <div style="font-size:12.5px; color:#64748B;">點選首頁 4 張功能卡時，先顯示 4 步驟流程圖再開始作業（目前已略過 ${skipCnt} 個模組）</div>
          </div>
          ${skipCnt > 0 ? `<button onclick="event.preventDefault(); resetAllSkipGuides();" class="btn" style="padding:4px 10px; font-size:12px; background:#DBEAFE; color:#1E3A8A;">🔄 重設所有導覽顯示</button>` : ''}
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" ${s.auto_open_folder ? 'checked' : ''} onchange="saveAppSettings({auto_open_folder:this.checked})" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A;">匯出 *_FIXED.xlsx 或新母體後自動開啟輸出資料夾</div>
            <div style="font-size:12.5px; color:#64748B;">存檔完成時自動彈出 Windows 檔案總管方便直接開啟檔案</div>
          </div>
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" ${s.tic_generic_only ? 'checked' : ''} onchange="saveAppSettings({tic_generic_only:this.checked}); applyLoadedSettings({tic_generic_only:this.checked});" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A;">代碼速查預設勾選「僅顯示通用 TestID / Error Code」</div>
            <div style="font-size:12.5px; color:#64748B;">進入 TestID 速查頁面時優先顯示各機種通用代碼（預設已自動載入 V2.04）</div>
          </div>
        </label>

        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px;">
          <div>
            <div style="font-weight:700; color:#0F172A;">儀器介紹與人機頁預設字體大小</div>
            <div style="font-size:12.5px; color:#64748B;">調整儀器規格與說明文字的預設閱讀字級</div>
          </div>
          <div style="display:inline-flex; gap:6px;">
            <button onclick="saveAppSettings({intro_font_size:13}); applyLoadedSettings({intro_font_size:13}); renderSettingsPanel();" class="btn" style="padding:4px 12px; font-size:12.5px; ${fs===13?'background:#2563EB;color:#fff;border-color:#1D4ED8;':''}">小 (13px)</button>
            <button onclick="saveAppSettings({intro_font_size:15}); applyLoadedSettings({intro_font_size:15}); renderSettingsPanel();" class="btn" style="padding:4px 12px; font-size:12.5px; ${fs===15?'background:#2563EB;color:#fff;border-color:#1D4ED8;':''}">中 (15px)</button>
            <button onclick="saveAppSettings({intro_font_size:17}); applyLoadedSettings({intro_font_size:17}); renderSettingsPanel();" class="btn" style="padding:4px 12px; font-size:12.5px; ${fs===17?'background:#2563EB;color:#fff;border-color:#1D4ED8;':''}">大 (17px)</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function resetAllSkipGuides() {
  await saveAppSettings({ show_flow_guide: true, skip_guides: {} });
  renderSettingsPanel();
  alert('已重設，下次點擊各功能卡片時會再次顯示流程圖導覽。');
}
