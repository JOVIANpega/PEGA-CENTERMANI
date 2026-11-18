// Flow Guide (Scrollable Detailed Tutorial + Single-Focus Red-Box Screenshots) & System Settings Manager
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
      { num: '①', title: '選取單檔或整包', items: ['單一 Excel 體檢', '整包資料夾批次掃描'] },
      { num: '②', title: '檢視紅黃燈報告', items: ['同類錯誤自動折疊', '自動對比實體 DLL'] },
      { num: '③', title: '微調與補儀器', items: ['站別/ISN/IP/COM 微調', '插 NI-6009 / Feasa / RF'] },
      { num: '④', title: '匯出與簽章', items: ['產出 *_FIXED.xlsx', '寫入 INI 與 Checksum'] }
    ],
    detailedSteps: [
      {
        step: 'Step 1｜「選取單一 Excel」：針對單份測試腳本進行體檢與微調',
        desc: '適合您只想檢查或修改某一個站的 TestFlow Excel 時使用。點選後會跳出檔案視窗，自動讀入同資料夾內的 System.ini 與 Global.ini，並解析所有測試站與 Marco 子工作表，立即列出錯誤與警告明細。',
        img: '/images/guide_audit_1a.png'
      },
      {
        step: 'Step 2｜「掃描整包資料夾」：一次體檢整個專案目錄內所有站別腳本',
        desc: '當整個專案資料夾內包含多個站別的 Excel（例如 Download、MB、RF、OQC 分散在不同檔案）時使用。系統會遞迴掃描全資料夾、略過 *_FIXED 與 old_ 備份檔，一次列出每個檔案的紅綠燈與錯誤數，點擊清單即可切換檢視或「一鍵整包批次修復」。',
        img: '/images/guide_audit_1b.png'
      },
      {
        step: 'Step 3｜檢視紅黃燈體檢報告與自動修補預告',
        desc: '上方紅色橫幅會顯示抓出的錯誤總數（例如 42 個錯誤）、需人工確認數量、從 DUTs 讀取到的 ISN 條碼位數，以及存檔時將自動補齊的數百項格式問題；下方會列出各站錯誤與系統自動修補對策。',
        img: '/images/guide_audit_2.png'
      },
      {
        step: 'Step 4｜工作表燈號篩選、跳轉分支樹與折疊明細',
        desc: '點擊上方工作表膠囊（如 MainBoard 🔴42）可只篩選看該站別的錯誤；點擊綠色「其餘 8 個跳轉區塊邏輯正常」可展開縮排跳轉分支樹檢查邏輯；點擊下方折疊的紅色明細列可檢視具體列號與補齊內容。',
        img: '/images/guide_audit_2b.png'
      },
      {
        step: 'Step 5｜「微調 DUTs / Instrument / Global.ini」分頁 1：站別開關與 ISN',
        desc: '點擊工具列黃色「⚙️ 微調 DUTs / Instrument / Global.ini」會展開全域設定微調區。在第一分頁「站別開關與 ISN」可直接切換站別啟用/停用 (Load=1/0)、修改 DUT 名稱、或一鍵批量套用全部站別的 ISN 條碼位數與字元規則。',
        img: '/images/guide_audit_3.png'
      },
      {
        step: 'Step 6｜全域微調分頁 2：「🌐 網路 IP / Ping / Port」',
        desc: '切換至第二分頁「🌐 網路 IP / Ping / Port」，系統只列出本腳本實際使用的 PCIP_1、DUTIP_1、GoldenIP 與各站 DUT UDP 連線 Port，方便直接修改數值而不用在龐雜的 Global.ini 中翻找。',
        img: '/images/guide_audit_3b.png'
      },
      {
        step: 'Step 7｜全域微調分頁 3：「🔌 儀器掛載與 COM Port」',
        desc: '切換至第三分頁「🔌 儀器掛載與 COM Port」，集中修改待測板 UART COM Port (DUT_UR1)、SFIS 機台編號 (DEVID_1)、DAQ / FeasaLED 裝置代號等變數。以上三個分頁修改完成後，記得點右上角「✓ 套用微調並重跑健檢」。',
        img: '/images/guide_audit_3c.png'
      },
      {
        step: 'Step 8｜點擊「➕ 插入儀器範本」後的彈出設定視窗',
        desc: '點擊紫色「➕ 插入儀器範本」會彈出此視窗：先選取「1. 目標測試站工作表」與「2. 插入位置」（系統強制保證插在 Phase 97 之前且不破壞原有 2:XX / 4:P,F 跳轉），再挑選 34 款儀器或點擊常用儀器快選鈕。',
        img: '/images/guide_audit_4a.png'
      },
      {
        step: 'Step 9｜進入儀器互動人機介面（以 FeasaLED / NI-6009 為例）',
        desc: '在彈窗點擊常用快選鈕或「開啟人機設定▶」，即進入專屬視覺化人機（如 FeasaLED 光纖通道與 RGB/XY 色域設定、NI-6009 32-Pin 點圖接線與 12V 分壓提醒），確認後按套用即自動寫入獨立 Title 區塊並亮黃底標記。',
        img: '/images/guide_audit_4.png'
      },
      {
        step: 'Step 10｜點擊「🔀 編輯跳轉 (PASS/FAIL)」後的視覺化跳轉編輯器',
        desc: '點擊橘色「🔀 編輯跳轉 (PASS/FAIL)」會彈出此視窗，以 Title 區塊為單位免算相對步號：先選取左側「起點」步號，再勾選目標列的「PASS 跳這 / FAIL 跳這」（或直接套用三大快速模板），自動組出 4:P,F 或 2:XX 並重跑體檢。',
        img: '/images/guide_audit_6.png'
      },
      {
        step: 'Step 11｜點擊「🌐 SFIS / iPLAS 開關」後的廠區連線設定視窗',
        desc: '點擊綠色「🌐 SFIS / iPLAS 開關」會彈出此視窗：可直接切換 SFIS_Enable 主開關、從下拉選單快速帶入 PTB / PXD 廠區 SFIS_WebLink 網址，以及設定 iPLAS_Enable 與廠區代碼，按下套用即寫入 System.ini。',
        img: '/images/guide_audit_7.png'
      },
      {
        step: 'Step 12｜點擊「🔌 通訊設定 (改 COM / 轉 SSH)」後的批次轉換視窗',
        desc: '點擊藍色「🔌 通訊設定」會彈出此視窗：可統一修改 UART COM Port、DUT IP 與 SSH 登入帳號，並可勾選將指定工作表內的 :Connect,"UART" / UART@... 指令一鍵批次轉換為 CmdConsole@ssh。',
        img: '/images/guide_audit_8.png'
      },
      {
        step: 'Step 13｜產出「🧪 無硬體試跑版」：無儀器 PC 驗證流程專用',
        desc: '若工程師在辦公桌沒有治具與實體儀器、想先在 Centimani 跑通整體流程與跳轉邏輯，可點「🧪 無硬體試跑版」：系統會自動清空 Instrument / Switch 的 Mount 掛載、將量測列轉為 ExecMode = 6 (Skip) 並清空 :Sf* 驗證。',
        img: '/images/guide_audit_5a.png'
      },
      {
        step: 'Step 14｜「💾 一鍵修好並匯出 (*_FIXED.xlsx)」正式產出與 Checksum 簽章',
        desc: '所有檢查與微調確認無誤後，點擊綠色「💾 一鍵修好並匯出 (*_FIXED.xlsx)」，系統會將補齊的 7 碼 TestID、格式修正與參數微調寫入同目錄 *_FIXED.xlsx（修正處亮黃底），並自動重算 64 碼 Checksum 寫入 System.ini。',
        img: '/images/guide_audit_5b.png'
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
        step: 'Step 1｜填寫專案名稱、站別、槽位數與 ISN 條碼規則',
        desc: '輸入專案代號、站別名稱（如 MB / RF）、多工槽位數（1/2/4 板同步測試），以及掃描條碼的位數與字元規則（系統會即時預覽成標準 {ISN,位數,Pattern} 語法）。',
        img: '/images/guide_gen_1a.png'
      },
      {
        step: 'Step 2｜設定 SFIS / iPLAS 開關與各廠區 WebLink IP',
        desc: '點擊右下角「🌐 設定 SFIS / iPLAS 開關與廠區 IP」會彈出廠區連線設定視窗，可直接從下拉選單切換 PTB / PXD 等廠區 SFIS_WebLink 與開啟/關閉 SFIS、iPLAS，匯出時直接寫入 System.ini。',
        img: '/images/guide_gen_1b.png'
      },
      {
        step: 'Step 3｜（點擊「SFIS / iPLAS 開關」後的彈出視窗畫面）',
        desc: '在彈出視窗中選擇 SFIS_Enable (0=關閉 / 1=啟用) 與廠區代碼即可套用，免去手動查表輸入網址。',
        img: '/images/guide_audit_7.png'
      },
      {
        step: 'Step 4｜Step 2 快速骨架範本（最小骨架 / 基礎上電量測 / 全部取消）',
        desc: '進入 Step 2 後，右上角提供三個快速鍵：「🧩 最小骨架」一鍵勾選 CheckRoute + 治具 + UART + Phase 97；「⚡ 基礎上電量測」額外帶入基礎電源量測；「□ 全部取消」清空所有勾選從頭自選。',
        img: '/images/guide_gen_2c.png'
      },
      {
        step: 'Step 5｜勾選「① 標準測試流程骨架」7 大積木',
        desc: '依需求勾選純流程積木：CheckRoute 路由驗證、氣動治具下壓、UART/ADB/SSH 韌體比對、SFIS 讀取 MAC/69PN、呼叫外部 Python 腳本 (CmdConsole@python.exe)、Ping 連通性測試與 Phase 97 強制斷電收尾。',
        img: '/images/guide_gen_2a.png'
      },
      {
        step: 'Step 6｜「② 常用儀器快選」5 顆一鍵進入人機設定',
        desc: '下方提供 5 顆常用儀器快選鈕（NI-6008/6009 電壓量測、iPower 程控電源、34401A/MDA2700 電表、Feasa LED 色彩亮度、IQxel Wi-Fi RF），點擊後會直接開啟該儀器的專屬介紹與互動人機頁面。',
        img: '/images/guide_gen_2b.png'
      },
      {
        step: 'Step 7｜手動挑選 34 款儀器：儀器介紹 / 圖解接線 / 加入清單',
        desc: '若要選用其他型號，可從「功能分類 → 儀器名稱」挑選 34 款儀器並填寫測項名稱與上下限 (DL/UL)；點「📖 儀器介紹」看外觀接線與手冊、點「🔌 圖解接線設定」進入互動接線、點「➕ 加入清單」直接掛載至本母體。',
        img: '/images/guide_gen_2d.png'
      },
      {
        step: 'Step 8｜（進入「儀器互動人機」設定接線與規格畫面）',
        desc: '點擊快選或「圖解接線設定」後會開啟此互動介面（圖為 FeasaLED / NI-6009 示意），可直覺勾選通道、光纖腳位與上下限，按下套用即自動加入 Step 2 已選儀器清單。',
        img: '/images/guide_audit_4.png'
      },
      {
        step: 'Step 9｜Step 3 確認與填寫細部測試參數',
        desc: '依 Step 2 勾選的積木與儀器動態產生設定卡：可調整韌體比對的連線方式（UART / ADB / SSH）、COM Port、目標韌體版本與查詢指令，以及治具控制 COM Port 與等待上電穩定毫秒數 (ms)。',
        img: '/images/guide_gen_3.png'
      },
      {
        step: 'Step 10A｜Step 4 產出「🧪 無硬體試跑版 (Dry-Run)」',
        desc: '在總覽確認核對專案、ISN 與積木無誤後，若辦公室電腦尚未接上實體儀器，可點藍色「🧪 Finish：產生『無硬體試跑版』」，系統會清空 Mount 並將量測列轉為 ExecMode = 6，供您先在 Centimani 驗證整體流程跳轉。',
        img: '/images/guide_gen_4a.png'
      },
      {
        step: 'Step 10B｜Step 4 產出「🚀 產線實機測試包」（含簽章 + 彈出資料夾）',
        desc: '準備上線實測時，點擊綠色「🚀 Finish：產生『產線實機測試包』」，一次產出標準 16 欄 TestFlow.xlsx、System.ini（含 64 碼 Checksum 簽章）、Global.ini 與 Test Item Code 表，並自動開啟輸出資料夾。',
        img: '/images/guide_gen_4b.png'
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
        step: 'Step 1｜選擇 Log / CSV 檔案（支援數百 KB 大檔快速解析）',
        desc: '點擊「📂 點此選擇要分析的 Log / CSV 檔案」載入 Centimani 產線測試紀錄；若只有幾行終端機錯誤訊息，也可切換上方「📋 模式二：貼上錯誤文字」直接貼上分析。',
        img: '/images/guide_diag_1.png'
      },
      {
        step: 'Step 2｜檢視失敗定位、超標幅度與 Phase 耗時瓶頸',
        desc: '系統會自動列出所有量測數值與規格上下限對比，標註超出幾 V / 幾 dBm，並統計各 Phase 耗時 Top 5 協助找出拖慢 Cycle Time 的瓶頸步驟；重新修改過 Log 後可按右側「🔄 重新解析本檔」。',
        img: '/images/guide_diag_2.png'
      },
      {
        step: 'Step 3｜一鍵複製乾淨異常摘要報告',
        desc: '點擊右上角「📋 複製測試結論摘要」，自動將專案站別、異常測項、實測數據與推測原因整理成純文字摘要，方便直接貼到 Teams 群組或 Mail 回報。',
        img: '/images/guide_diag_3.png'
      },
      {
        step: 'Step 4｜書籤二：切換至「模式二：貼上錯誤文字 / 診斷片段」',
        desc: '若當下沒有完整 .log 檔，只有從黑色主控台視窗或 System Error 彈窗複製出來的幾行文字，可點擊上方第二個書籤切換至文字貼上模式。',
        img: '/images/guide_diag_4.png'
      },
      {
        step: 'Step 5｜貼上錯誤文字並點擊「立即診斷貼上文字」',
        desc: '將錯誤訊息貼入文字框後點擊右下角綠色「🔍 立即診斷貼上文字」，系統會自動比對 Checksum 失敗、SFIS 斷線、儀器鎖定與腳本語法錯誤，立即給出排查步驟。',
        img: '/images/guide_diag_5.png'
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
        step: 'Step 1｜自動載入官方 V2.04 表，輸入關鍵字即時篩選',
        desc: '系統開機已自動載入最新版 Test Item Code V2.04_20250310.xlsx（共 5,200+ 筆代碼），無需手動選檔。直接在搜尋框輸入中文（如「電壓」「LED」）、英文或 7 碼代碼即可搜尋，並建議勾選「僅顯示通用碼」。',
        img: '/images/guide_tic_1.png'
      },
      {
        step: 'Step 2｜在左側搜尋結果選定目標 TestID / Error Code',
        desc: '左側清單會列出符合條件的代碼與中英文說明，點擊任一筆即可選中；也可直接點「雙欄複製」將「Description + Tab + TestID」直接貼入 Excel。',
        img: '/images/guide_tic_2.png'
      },
      {
        step: 'Step 3｜書籤一：套用至母體積木（寫入新產生腳本）',
        desc: '在右側預設的「🧩 方案一：套用至母體積木」頁籤中，展開欲修改的積木步驟，點擊右側「套用」按鈕即可將合法 7 碼代碼直接寫入新腳本母體，並可勾選同步帶入英文 Description。',
        img: '/images/guide_tic_3.png'
      },
      {
        step: 'Step 4｜書籤二：切換至「方案二：寫入現有 Excel」',
        desc: '若是要補齊既有的 TestFlow.xlsx 檔案（例如稽核抓出缺少第 16 欄 TestID），請點擊右側第二個書籤「📄 方案二：寫入現有 Excel」。',
        img: '/images/guide_tic_4.png'
      },
      {
        step: 'Step 5｜方案二：篩選「僅看缺 TestID 列」並寫入存檔',
        desc: '點擊「📂 選擇 Excel 檔案」（若剛在健檢載入過會自動帶入），切換「僅看缺 TestID 列」只列出漏填代碼的步驟，套用後即可直接簽章存回原檔。',
        img: '/images/guide_tic_5.png'
      }
    ],
    tip: '適用場景：撰寫新測項找標準 7 碼代碼，或補齊健檢抓出的缺少 TestID 列'
  }
};

function applyLoadedSettings(s) {
  if (!s) return;
  APP_SETTINGS = Object.assign({}, APP_SETTINGS, s);
  try { localStorage.setItem('centimani_app_settings', JSON.stringify(APP_SETTINGS)); } catch (e) {}
  const fs = parseInt(APP_SETTINGS.intro_font_size, 10) || 15;
  document.body.style.fontSize = fs + 'px';
  if (typeof setIntroFontSize === 'function') {
    setIntroFontSize(fs);
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

function jumpToFlowStep(idx) {
  const el = document.getElementById('flowStepCard_' + idx);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  const prevShadow = el.style.boxShadow;
  el.style.boxShadow = '0 0 0 3px #2563EB, 0 6px 16px rgba(37, 99, 235, 0.18)';
  setTimeout(() => {
    el.style.boxShadow = prevShadow || '';
  }, 1200);
}

function renderFlowGuidePage(tab) {
  const d = FLOW_GUIDE_DATA[tab];
  if (!d) { switchTab(tab); return; }

  const fs = parseInt(APP_SETTINGS.intro_font_size || 15, 10);
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

  const quickJumpHtml = (d.detailedSteps || []).map((ds, idx) => {
    const parts = String(ds.step || '').split('｜');
    const stepTag = (parts[0] || ('Step ' + (idx + 1))).trim();
    const rawTitle = (parts[1] || '').replace(/[「」『』]/g, '').trim();
    const shortTitle = rawTitle.length > 10 ? rawTitle.slice(0, 10) + '…' : rawTitle;
    return `<button type="button" class="flow-step-pill" onclick="jumpToFlowStep(${idx})" title="${ds.step}">
      <span style="background:#FACC15; color:#0F172A; font-weight:800; padding:1px 6px; border-radius:4px; border:1px solid #CA8A04;">${stepTag}</span>
      ${shortTitle ? `<span>${shortTitle}</span>` : ''}
    </button>`;
  }).join('');

  const detailCardsHtml = (d.detailedSteps || []).map((ds, idx) => {
    const parts = String(ds.step || '').split('｜');
    const stepTag = (parts[0] || ('Step ' + (idx + 1))).trim();
    const stepTitle = parts.slice(1).join('｜').trim();
    const headerHtml = stepTitle
      ? `<span style="display:inline-block; background:#FACC15; color:#0F172A; font-weight:800; padding:2px 10px; border-radius:6px; border:1px solid #CA8A04; margin-right:8px;">${stepTag}</span><span>${stepTitle}</span>`
      : `<span>${ds.step}</span>`;
    return `
    <div id="flowStepCard_${idx}" style="scroll-margin-top:16px; background:#F8FAFC; border:1px solid #CBD5E1; border-left:4px solid ${d.themeBorder}; border-radius:8px; padding:14px 16px; transition:box-shadow 0.25s ease;">
      <div style="display:flex; align-items:center; flex-wrap:wrap; gap:4px; font-weight:700; font-size:${fs + 1}px; color:#0F172A; margin-bottom:8px;">${headerHtml}</div>
      <div class="flow-guide-desc" style="font-size:${fs}px; color:#334155; line-height:1.65; margin-bottom:10px;">${ds.desc}</div>
      <div style="text-align:center; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:8px;">
        <img src="${ds.img}" alt="${ds.step}"
             style="max-width:100%; max-height:380px; border-radius:6px; border:1px solid #CBD5E1; cursor:zoom-in;"
             onclick="window.open(this.src, '_blank')"
             title="點擊開啟原尺寸大圖">
      </div>
    </div>
  `;
  }).join('');

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

      <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 14px; font-size:${fs - 1}px; color:#1E293B; margin-bottom:14px;">
        💡 <b>說明：</b>${d.tip}
      </div>

      <div style="margin-bottom:16px;">
        <div style="font-weight:700; font-size:15px; color:#0F172A; margin-bottom:8px;">📖 詳細操作步驟與單項紅框教學（共 ${d.detailedSteps.length} 步，點擊下方快捷鍵可跳轉至對應步驟）</div>
        <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px; padding:10px 12px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px;">
          ${quickJumpHtml}
        </div>
        <div style="display:flex; flex-direction:column; gap:12px;">
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
    <div style="background:#FFFFFF; border:1.5px solid #E11D48; border-radius:12px; padding:20px 24px; max-width:860px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-bottom:12px; border-bottom:1px solid #E2E8F0; margin-bottom:16px;">
        <div>
          <h2 style="margin:0; font-size:19px; color:#0F172A;">⚙️ 系統與環境設定 (Preferences)</h2>
          <div style="font-size:13px; color:#64748B; margin-top:2px;">勾選後即時保存至 config.json，字體大小會即時套用至全站</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span id="settingsSaveStatus" style="display:none; padding:4px 10px; border-radius:6px; border:1px solid #4ADE80; font-size:12.5px; font-weight:700;"></span>
          <button onclick="switchTab('home')" class="btn" style="background:#E2E8F0; color:#1E293B; border-color:#94A3B8;">◀ 返回首頁</button>
        </div>
      </div>

      <div style="display:flex; flex-direction:column; gap:12px;">
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
            <div style="font-weight:700; color:#0F172A;">全站介面與教學說明預設字體大小</div>
            <div style="font-size:12.5px; color:#64748B;">切換後立即放大 / 縮小全站文字、流程教學與儀器介紹頁</div>
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
