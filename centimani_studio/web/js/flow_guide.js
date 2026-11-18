// Flow Guide (Scrollable Detailed Tutorial + Flowchart) & System Settings Manager
let APP_SETTINGS = {
  auto_fullscreen: true,
  show_flow_guide: true,
  auto_open_folder: true,
  auto_checksum: true,
  tic_generic_only: false,
  intro_font_size: 15,
  skip_guides: {}
};

try {
  const cached = localStorage.getItem('centimani_app_settings');
  if (cached) APP_SETTINGS = Object.assign({}, APP_SETTINGS, JSON.parse(cached));
} catch (e) {}

let PENDING_FLOW_TARGET = { tab: 'audit', afterAction: null };

const FLOW_GUIDE_DATA = {
  audit: {
    icon: '🛠️',
    title: '腳本健檢與修復 — 完整操作流程與畫面教學',
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
    detailedSteps: [
      {
        step: 'Step 1｜選擇「單一 Excel」或「整包專案資料夾」',
        desc: '進入後點擊上方藍色「📂 選取單一 Excel」開啟既有腳本；若要檢查整個專案目錄內所有站別，可點「📁 掃描整包資料夾」（系統會自動排除 *_FIXED 與 old_ 備份）。',
        mockup: '<div style="background:#F8FAFC;border:1px solid #CBD5E1;border-radius:6px;padding:8px 10px;font-size:12px;"><span style="background:#DBEAFE;color:#1E3A8A;padding:3px 8px;border-radius:4px;font-weight:700;">📂 選取單一 Excel</span> <span style="background:#E0F2FE;color:#0369A1;padding:3px 8px;border-radius:4px;font-weight:700;margin-left:4px;">📁 掃描整包資料夾</span><div style="margin-top:6px;color:#475569;">📍 目前檔案：<code>D:\\...\\TestFlow.xlsx</code></div></div>',
        img: '/images/guide_audit_1.png'
      },
      {
        step: 'Step 2｜檢視體檢報告（紅燈錯誤 / 黃燈人工確認 / 綠燈正常）',
        desc: '上方橫幅會顯示錯誤總數與目前讀取到的 ISN 條碼位數；下方依測試站分頁顯示健康度，同類型的大量錯誤（如 42 筆缺少 TestID）會自動折疊成單一條目方便檢視。',
        mockup: '<div style="background:#FEF2F2;border:1px solid #EF4444;border-radius:6px;padding:8px 10px;font-size:12px;color:#7F1D1D;">🔴 檢查結果：抓出 <b>42 個錯誤</b>（同類錯誤已折疊，存檔時將自動補齊 7 碼 TestID）</div>',
        img: '/images/guide_audit_2.png'
      },
      {
        step: 'Step 3｜線上語意微調（站別開關 / ISN 位數 / IP / COM Port）',
        desc: '點擊「⚙️ 微調 DUTs / Instrument / Global.ini」可切換站別啟用開關、批量修改 ISN 位數、調整 PC/DUT IP 與 Ping IP；若要改 UART COM Port 或將 UART 轉為 SSH，點「🔌 通訊設定」。',
        mockup: '<div style="background:#FFFBEB;border:1px solid #F59E0B;border-radius:6px;padding:8px 10px;font-size:12px;">📋 站別開關 (🟢 啟用 / ⚪ 停用) ｜ 🔢 ISN 位數 [15] ｜ 🌐 網路 IP / Ping ｜ 🔌 儀器掛載</div>',
        img: '/images/guide_audit_3.png'
      },
      {
        step: 'Step 4｜插入儀器測項或調整 PASS/FAIL 跳轉',
        desc: '需要補測項時點「➕ 插入儀器範本」，可直接快選 NI-6009（32-Pin 接線圖）、FeasaLED（光纖色域）、iPower、電表或 IQxel RF（自動補齊 21/22 步 Marco）；點「🔀 編輯跳轉」可用打勾方式設定 4:P,F 跳轉。',
        mockup: '<div style="background:#F5F3FF;border:1px solid #8B5CF6;border-radius:6px;padding:8px 10px;font-size:12px;color:#5B21B6;">⚡ 快選：NI-6009 ｜ iPower ｜ 34401A ｜ FeasaLED ｜ IQxel RF（先看介紹頁 → 再進人機）</div>',
        img: '/images/guide_audit_4.png'
      },
      {
        step: 'Step 5｜一鍵修好並匯出（或產出無硬體試跑版）',
        desc: '確認待匯出異動清單無誤後，點擊「💾 一鍵修好並匯出 (*_FIXED.xlsx)」，系統會自動於原資料夾產出修復檔（異動儲存格亮黃底標記），並同步更新 Global.ini、System.ini 與 64 碼 Checksum。',
        mockup: '<div style="background:#DCFCE7;border:1px solid #22C55E;border-radius:6px;padding:8px 10px;font-size:12px;color:#14532D;">✅ 已匯出 <code>*_FIXED.xlsx</code> ＋ 寫入 Checksum ＋ 覆檢 0 錯誤</div>',
        img: '/images/guide_audit_5.png'
      }
    ],
    tip: '產出物：同目錄 *_FIXED.xlsx（修正儲存格亮黃底標註）＋ Checksum 簽章 ＋ Global.ini'
  },
  gen: {
    icon: '🧩',
    title: '新腳本母體產生器 — 完整操作流程與畫面教學',
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
    detailedSteps: [
      {
        step: 'Step 1｜基本資料、ISN 條碼與 SFIS / iPLAS 廠區設定',
        desc: '填入專案名稱、站別（如 MB / RF）、多工槽位數（1/2/4）與 ISN 碼數規則；若有廠區過站需求，點「🌐 設定 SFIS / iPLAS 開關與廠區 IP」直接從下拉選單選廠區。',
        mockup: '<div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:6px;padding:8px 10px;font-size:12px;">專案：<code>PEGA_NEW</code> ｜ 站別：<code>MB</code> ｜ ISN：<code>{ISN,15,[0-9A-Z]}</code> ｜ SFIS：OFF/ON</div>',
        img: '/images/guide_gen_1.png'
      },
      {
        step: 'Step 2｜勾選標準流程骨架 ＋ 選用測試儀器',
        desc: '上方勾選開機流程骨架（CheckRoute、治具下壓、UART 韌體比對、SFIS、Phase 97 收尾）；下方點擊常用儀器快選鈕（NI-6009 / iPower / 電表 / FeasaLED / IQxel）直接進入儀器介紹與人機設定。',
        mockup: '<div style="background:#EFF6FF;border:1px solid #93C5FD;border-radius:6px;padding:8px 10px;font-size:12px;">① 流程積木打勾 → ② 儀器快選（自動進入介紹頁與人機設定加入清單）</div>',
        img: '/images/guide_gen_2.png'
      },
      {
        step: 'Step 3｜填寫各流程積木細部參數',
        desc: '檢視已設定完成的 NI-6009 電壓通道摘要（可點按鈕再次修改），並填寫 UART/ADB/SSH 韌體版本指令、Python 腳本路徑或 Ping IP 清單。',
        mockup: '<div style="background:#F8FAFC;border:1px solid #CBD5E1;border-radius:6px;padding:8px 10px;font-size:12px;">⚡ NI-6009 通道摘要 ｜ 🔌 UART/SSH 韌體版本比對設定</div>',
        img: '/images/guide_gen_3.png'
      },
      {
        step: 'Step 4｜總覽核對並產出完整產線測試包',
        desc: '確認所有參數後，可選擇「🧪 產生無硬體試跑版 (Dry-Run)」先在辦公室驗證流程，或點擊「🚀 產生產線實機測試包」一次產出 Excel、System.ini、Global.ini 與 Test Item Code。',
        mockup: '<div style="background:#DCFCE7;border:1px solid #22C55E;border-radius:6px;padding:8px 10px;font-size:12px;">📁 自動輸出至 <code>output_system/&lt;專案_站別&gt;/System/</code> 並彈出資料夾</div>',
        img: '/images/guide_gen_4.png'
      }
    ],
    tip: '產出物：標準 16 欄 TestFlow.xlsx ＋ System.ini ＋ Global.ini ＋ Test Item Code 表'
  },
  diagnose: {
    icon: '🩺',
    title: '測試 Log 失敗診斷 — 完整操作流程與畫面教學',
    themeBg: '#FEF3C7',
    themeBorder: '#D97706',
    btnClass: 'btn-jump',
    btnLabel: '開始使用：Log 診斷 ▶',
    steps: [
      { num: '①', title: '匯入 Log', items: ['選取大檔 Log / CSV 檔', '或直接貼上錯誤文字片段'] },
      { num: '②', title: '自動定位異常', items: ['抓出 FAIL 測項與錯誤碼', '計算實測值 vs 規格差距'] },
      { num: '③', title: '節拍與對策', items: ['Phase 耗時 Top5 排行', '產線排查步驟建議'] },
      { num: '④', title: '一鍵匯報', items: ['產生乾淨異常摘要報告', '複製貼至 Teams / 郵件'] }
    ],
    detailedSteps: [
      {
        step: 'Step 1｜選取 Log 檔案或貼上錯誤文字',
        desc: '支援數百 KB 的完整 Centimani Log / CSV 檔案直接選取解析，也可切換「貼上文字」模式貼入終端機片段。',
        mockup: '<div style="background:#FFFBEB;border:1px solid #FBBF24;border-radius:6px;padding:8px 10px;font-size:12px;">📄 選取 Log 檔 / 貼上文字 ➔ 點擊「🔍 開始分析」</div>',
        img: '/images/guide_diag_1.png'
      },
      {
        step: 'Step 2｜檢視失敗定位、數值超標差距與 Phase 耗時排行',
        desc: '系統自動抓出所有實測值與規格上下限並標示超標幅度，同時列出耗時最長的前 5 個 Phase 協助優化測試時間 (CT)。',
        mockup: '<div style="background:#FEF2F2;border:1px solid #EF4444;border-radius:6px;padding:8px 10px;font-size:12px;color:#7F1D1D;">❌ VCC_3V3 實測 2.91V (規格 3.15~3.45V，低於下限 -0.24V)</div>',
        img: '/images/guide_diag_2.png'
      },
      {
        step: 'Step 3｜複製異常摘要報告回報產線',
        desc: '點擊「📋 複製異常摘要」，即可將整理好的錯誤測項、根因推測與實測數據貼至 Teams 或郵件。',
        mockup: '<div style="background:#F0FDF4;border:1px solid #4ADE80;border-radius:6px;padding:8px 10px;font-size:12px;">✔ 已複製純淨異常摘要至剪貼簿</div>',
        img: '/images/guide_diag_3.png'
      }
    ],
    tip: '適用場景：產線 FAIL 快速判讀、找出測試 Cycle Time 瓶頸測項'
  },
  tic: {
    icon: '🏷️',
    title: 'TestID / Error Code 速查 — 完整操作流程與畫面教學',
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
    detailedSteps: [
      {
        step: 'Step 1｜自動載入官方 Test Item Code V2.04（免選檔）',
        desc: '進入頁面後系統已預設載入最新版 Test Item Code V2.04_20250310.xlsx；僅當未來有更新版本（如 V2.05）時才需點「📂 更換檔案」。',
        mockup: '<div style="background:#EEF2FF;border:1px solid #818CF8;border-radius:6px;padding:8px 10px;font-size:12px;">📚 目前載入：<code>Test Item Code V2.04_20250310.xlsx</code></div>',
        img: '/images/guide_tic_1.png'
      },
      {
        step: 'Step 2｜輸入中英文關鍵字或 Error Code 即時搜尋',
        desc: '在搜尋框輸入如「電壓」、「LED」、「UART」、「BRPW024」即可即時篩選，建議勾選「僅顯示通用碼」優先採用跨機種標準碼。',
        mockup: '<div style="background:#F8FAFC;border:1px solid #CBD5E1;border-radius:6px;padding:8px 10px;font-size:12px;">🔍 [ 電壓 ] ☑ 僅顯示通用碼 ➔ <code>BRPW024</code> / <code>BRPW033</code></div>',
        img: '/images/guide_tic_2.png'
      },
      {
        step: 'Step 3｜一鍵複製或直接套用至母體 / 健檢腳本',
        desc: '找到目標代碼後可直接複製（Description + TestID），或直接套用到目前「母體產生器」積木與「腳本健檢」載入中的工作表列。',
        mockup: '<div style="background:#DCFCE7;border:1px solid #4ADE80;border-radius:6px;padding:8px 10px;font-size:12px;">📋 複製代碼 ｜ ✨ 套用至現有 Excel 指定列</div>',
        img: '/images/guide_tic_3.png'
      }
    ],
    tip: '適用場景：撰寫新測項找標準 7 碼代碼，或補齊健檢抓出的缺少 TestID 列'
  }
};

function applyLoadedSettings(s) {
  if (!s) return;
  APP_SETTINGS = Object.assign({}, APP_SETTINGS, s);
  try { localStorage.setItem('centimani_app_settings', JSON.stringify(APP_SETTINGS)); } catch (e) {}
  if (APP_SETTINGS.intro_font_size && typeof setIntroFontSize === 'function') {
    setIntroFontSize(parseInt(APP_SETTINGS.intro_font_size, 10) || 15);
  }
  const chkTic = document.getElementById('chkTicGenericOnly');
  if (chkTic) chkTic.checked = !!APP_SETTINGS.tic_generic_only;
}

async function saveAppSettings(patch, showToast = true) {
  APP_SETTINGS = Object.assign({}, APP_SETTINGS, patch || {});
  try { localStorage.setItem('centimani_app_settings', JSON.stringify(APP_SETTINGS)); } catch (e) {}

  let okServer = false;
  try {
    const res = await fetch('/api/save_settings', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ settings: APP_SETTINGS })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'ok' && data.settings) {
        APP_SETTINGS = data.settings;
        okServer = true;
      }
    }
  } catch (e) {
    console.warn('saveAppSettings failed:', e);
  }

  if (showToast) {
    const st = document.getElementById('settingsSaveStatus');
    if (st) {
      st.style.display = 'inline-flex';
      if (okServer) {
        st.style.background = '#DCFCE7';
        st.style.color = '#166534';
        st.style.borderColor = '#4ADE80';
        st.textContent = '✅ 已即時儲存至 config.json';
      } else {
        st.style.background = '#FEF3C7';
        st.style.color = '#92400E';
        st.style.borderColor = '#F59E0B';
        st.textContent = '⚠️ 已暫存於瀏覽器（若需寫入 config.json 請重啟 .bat）';
      }
    }
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

  const detailCardsHtml = (d.detailedSteps || []).map((ds, i) => `
    <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-left:4px solid ${d.themeBorder}; border-radius:8px; padding:14px 16px;">
      <div style="font-weight:700; font-size:15px; color:#0F172A; margin-bottom:6px;">${ds.step}</div>
      <div style="font-size:13.5px; color:#334155; line-height:1.65; margin-bottom:10px;">${ds.desc}</div>
      <div style="text-align:center; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:8px;">
        <img src="${ds.img}" alt="${ds.step}"
             style="max-width:100%; max-height:420px; border-radius:6px; border:1px solid #CBD5E1; cursor:zoom-in;"
             onclick="window.open(this.src, '_blank')"
             title="點擊開啟原尺寸大圖"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <div style="display:none; text-align:left;">${ds.mockup}</div>
      </div>
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
        <div style="display:flex; gap:8px; align-items:center;">
          <button onclick="switchTab('home')" class="btn" style="background:#E2E8F0; color:#1E293B; border-color:#94A3B8;">◀ 返回首頁</button>
          <button onclick="confirmFlowGuideProceed()" class="btn ${d.btnClass}" style="padding:7px 16px; font-size:13.5px;">${d.btnLabel}</button>
        </div>
      </div>

      <div style="display:flex; flex-wrap:wrap; gap:10px; margin:16px 0; align-items:stretch;">
        ${stepsHtml}
      </div>

      <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 14px; font-size:13.5px; color:#1E293B; margin-bottom:14px;">
        💡 <b>說明：</b>${d.tip}
      </div>

      <div style="margin-bottom:16px;">
        <div style="font-weight:700; font-size:14.5px; color:#0F172A; margin-bottom:10px;">📖 詳細操作步驟與畫面對照教學（向下捲動閱讀，支援放入實機截圖至 IMAGES/）</div>
        <div style="display:flex; flex-direction:column; gap:10px;">
          ${detailCardsHtml}
        </div>
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
    await saveAppSettings({ skip_guides: skipMap }, false);
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
          <div style="font-size:13px; color:#64748B; margin-top:2px;">勾選後即時保存至 config.json，亦可按下方確認鈕完成儲存</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span id="settingsSaveStatus" style="display:none; padding:4px 10px; border-radius:6px; border:1px solid #4ADE80; font-size:12.5px; font-weight:700;"></span>
          <button onclick="switchTab('home')" class="btn" style="background:#E2E8F0; color:#1E293B; border-color:#94A3B8;">◀ 返回首頁</button>
        </div>
      </div>

      <div style="display:flex; flex-direction:column; gap:12px; font-size:14px;">
        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkFullscreen" ${s.auto_fullscreen ? 'checked' : ''} onchange="saveAppSettings({auto_fullscreen:this.checked})" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A;">啟動時自動全螢幕 / 最大化瀏覽器視窗</div>
            <div style="font-size:12.5px; color:#64748B;">開啟工具時自動將 Chrome / Edge 視窗最大化（下次重啟 .bat 生效）</div>
          </div>
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkFlowGuide" ${s.show_flow_guide ? 'checked' : ''} onchange="saveAppSettings({show_flow_guide:this.checked})" style="width:18px; height:18px;">
          <div style="flex:1;">
            <div style="font-weight:700; color:#0F172A;">進入功能前顯示「流程圖導覽說明頁」</div>
            <div style="font-size:12.5px; color:#64748B;">點選首頁功能卡時先顯示操作流程圖與教學（目前已略過 ${skipCnt} 個模組）</div>
          </div>
          ${skipCnt > 0 ? `<button onclick="event.preventDefault(); resetAllSkipGuides();" class="btn" style="padding:4px 10px; font-size:12px; background:#DBEAFE; color:#1E3A8A;">🔄 重設所有導覽顯示</button>` : ''}
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkOpenFolder" ${s.auto_open_folder ? 'checked' : ''} onchange="saveAppSettings({auto_open_folder:this.checked})" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A;">匯出 *_FIXED.xlsx 或新母體後自動開啟輸出資料夾</div>
            <div style="font-size:12.5px; color:#64748B;">存檔完成時自動彈出 Windows 檔案總管方便直接開啟檔案</div>
          </div>
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkTicGeneric" ${s.tic_generic_only ? 'checked' : ''} onchange="saveAppSettings({tic_generic_only:this.checked}); applyLoadedSettings({tic_generic_only:this.checked});" style="width:18px; height:18px;">
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

      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:16px; padding-top:12px; border-top:1px solid #E2E8F0;">
        <button onclick="confirmAndSaveSettingsBtn()" class="btn btn-primary-green" style="padding:8px 20px; font-size:14px;">💾 確認並儲存設定</button>
      </div>
    </div>
  `;
}

async function confirmAndSaveSettingsBtn() {
  await saveAppSettings({
    auto_fullscreen: document.getElementById('setChkFullscreen').checked,
    show_flow_guide: document.getElementById('setChkFlowGuide').checked,
    auto_open_folder: document.getElementById('setChkOpenFolder').checked,
    tic_generic_only: document.getElementById('setChkTicGeneric').checked
  }, true);
}

async function resetAllSkipGuides() {
  await saveAppSettings({ show_flow_guide: true, skip_guides: {} }, true);
  renderSettingsPanel();
}
