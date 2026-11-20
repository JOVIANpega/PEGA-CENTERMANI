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
    icon: '🔍',
    title: '腳本健檢與自動修復 — 完整操作流程與畫面教學',
    themeBg: '#E0F2FE',
    themeBorder: '#0284C7',
    btnClass: 'btn-primary-blue',
    btnLabel: '開始使用：腳本健檢 ▶',
    steps: [
      { num: '①', title: '選取單一 Excel', jumpIdx: 0, items: ['單份腳本即時體檢', '自動比對 System.ini'] },
      { num: '②', title: '掃描整包資料夾', jumpIdx: 1, items: ['遞迴掃描專案內多站', '支援一鍵整包批次修復'] },
      { num: '③', title: '紅黃燈體檢報告', jumpIdx: 2, items: ['抓出缺碼與格式錯誤', '自動讀取 ISN 條碼位數'] },
      { num: '④', title: '燈號篩選與跳轉樹', jumpIdx: 3, items: ['依工作表過濾異常站', '展開跳轉樹檢查邏輯'] },
      { num: '⑤', title: '一鍵修好或前往編修', jumpIdx: 4, items: ['自動補碼匯出 *_FIXED', '或帶入 02 編修中心'] }
    ],
    detailedSteps: [
      {
        step: 'Step 1｜「選取單一 Excel」：針對單份測試腳本進行快速體檢',
        desc: '適合您只想檢查某一個站的 TestFlow Excel 時使用。點選後自動讀入同資料夾內的 System.ini 與 Global.ini，檢查 16 欄格式、必填 TestID、ExecMode 與跳轉邏輯。',
        img: '/images/guide_audit_1a.png'
      },
      {
        step: 'Step 2｜「掃描整包資料夾」：一次體檢專案目錄內所有站別 Excel',
        desc: '當一個專案目錄下分散了多個站別的 Excel（如 Download、MB、RF、OQC）時使用。系統會遞迴掃描全資料夾、自動略過 *_FIXED、old_* 備份檔與 Test Item Code 表，一次列出所有檔案的紅綠燈與錯誤數，並支援「一鍵整包批次修復」（自動備份原 INI 為 .bak）。',
        img: '/images/guide_audit_1b.png'
      },
      {
        step: 'Step 3｜檢視紅黃燈體檢報告與自動修補預告',
        desc: '上方紅色橫幅顯示抓出的錯誤總數（如缺少第 16 欄 TestID）、需人工確認數量、從 DUTs 讀取到的 ISN 條碼位數，以及存檔時將自動補齊的數百項格式問題。',
        img: '/images/guide_audit_2.png'
      },
      {
        step: 'Step 4｜工作表燈號篩選、跳轉分支樹與折疊明細',
        desc: '點擊上方工作表膠囊（如 MainBoard 🔴42）可只篩選看該站別的錯誤；點擊綠色「跳轉區塊邏輯正常」可展開縮排分支樹檢查跳轉；點擊下方折疊明細列可檢視具體列號。',
        img: '/images/guide_audit_2b.png'
      },
      {
        step: 'Step 5｜「💾 一鍵修好並匯出 (*_FIXED.xlsx)」自動補碼與簽章',
        desc: '若只需自動修補格式與缺漏的 7 碼 TestID，直接點擊綠色「💾 一鍵修好並匯出 (*_FIXED.xlsx)」，系統將於同目錄產出修復檔（修正處亮黃底）並自動重算 64 碼 Checksum 寫入 System.ini。',
        img: '/images/guide_audit_5b.png'
      },
      {
        step: 'Step 6｜「✏️ 帶入此檔前往編修 ▶」無縫切換至 02 編修中心',
        desc: '若檢視完報告需要手動插入新儀器、改 PASS/FAIL 跳轉、改 COM / 轉 SSH 或微調全域變數，點擊紫色「✏️ 帶入此檔前往編修 ▶」即可免重新選檔直接跳轉至「02 腳本建立與編修中心」的書籤二。',
        img: '/images/guide_audit_to_editor.png'
      }
    ],
    tip: '定位：高頻快速檢查單檔或整包專案腳本；需要新增儀器或修改流程時，可一鍵帶入「02 腳本建立與編修中心」'
  },
  gen: {
    icon: '🛠️',
    title: '腳本建立與編修中心 — 完整操作流程與畫面教學',
    themeBg: '#DCFCE7',
    themeBorder: '#16A34A',
    btnClass: 'btn-primary-green',
    btnLabel: '開始使用：建立與編修中心 ▶',
    steps: [
      { num: '①', title: '書籤一：建新母體', jumpIdx: 0, items: ['專案 / ISN / 廠區設定', '4 步精靈從 0 → 1 建檔'] },
      { num: '②', title: '骨架與 34 款儀器', jumpIdx: 3, items: ['7 大標準流程積木', '快選儀器進入互動人機'] },
      { num: '③', title: '書籤二：既有編修', jumpIdx: 11, items: ['載入既有 TestFlow.xlsx', '無限次 1 → N 編修維護'] },
      { num: '④', title: '插儀器 / 跳轉 / 通訊', jumpIdx: 12, items: ['34 款儀器 & RGB 多色', '視覺化跳轉與全域微調'] },
      { num: '⑤', title: '安全暫存與匯出', jumpIdx: 19, items: ['原 Excel 保持不動', '產出試跑版或 *_FIXED'] }
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
        step: 'Step 10B｜書籤一：產出「🚀 產線實機測試包」（含簽章 + 彈出資料夾）',
        desc: '準備上線實測時，點擊綠色「🚀 Finish：產生『產線實機測試包』」，一次產出標準 16 欄 TestFlow.xlsx、System.ini（含 64 碼 Checksum 簽章）、Global.ini 與 Test Item Code 表，並自動開啟輸出資料夾。',
        img: '/images/guide_gen_4b.png'
      },
      {
        step: 'Step 11｜書籤二：切換至「✏️ 既有腳本編修與加儀器 (1 → N)」',
        desc: '日常專案維護要修改既有 Excel 時，請點上方「✏️ 書籤二：既有腳本編修與加儀器」，點擊「📂 選擇要編修的 TestFlow.xlsx」（若剛在 01 健檢載入過會自動帶入），右上角可隨時切回健檢報告或開啟原檔。',
        img: '/images/guide_editor_tab.png'
      },
      {
        step: 'Step 12｜書籤二 A 區：選目標站別 → 插入儀器 / 編輯跳轉',
        desc: '左卡「A. 測試站流程與儀器編修」先從右上角選定目標工作表（如 Download / MainBoard），再點「➕ 插入儀器範本 (34 款人機)」或「🔀 編輯跳轉 (PASS/FAIL)」。',
        img: '/images/guide_editor_zone_a.png'
      },
      {
        step: 'Step 13｜點擊「➕ 插入儀器範本」後的設定視窗',
        desc: '選擇插入位置（系統保證插在 Phase 97 之前不破壞原有跳轉）與 34 款儀器或常用快選，點擊「開啟人機設定▶」即可進入圖解互動人機（支援 FeasaLED RGB 多色批次、NI-6009 多通道、IQxel RF 多組 Tx/Rx）。',
        img: '/images/guide_audit_4a.png'
      },
      {
        step: 'Step 14｜點擊「🔀 編輯跳轉 (PASS/FAIL)」後的視覺化跳轉編輯器',
        desc: '以 Title 區塊為單位免算相對步號：選取左側起點後直接勾選目標列的「PASS 跳這 / FAIL 跳這」（或套用三大快速模板），自動組出 4:P,F 或 2:XX 並重跑驗證。',
        img: '/images/guide_audit_6.png'
      },
      {
        step: 'Step 15｜書籤二 B 區：全域環境與通訊設定 (INI / DUTs)',
        desc: '右卡「B. 全域環境與通訊設定」集中管理整包專案的 System.ini、Global.ini 與 DUTs：包含 SFIS/iPLAS 廠區連線、改 COM/轉 SSH 以及全域微調 3 分頁。',
        img: '/images/guide_editor_zone_b.png'
      },
      {
        step: 'Step 16｜點擊「🔌 通訊設定」後的改 COM / 批次轉 SSH 視窗',
        desc: '可統一修改 UART COM Port、DUT IP 與 SSH 帳號，並勾選將指定工作表內的 UART 指令一鍵批次轉換為 CmdConsole@ssh。',
        img: '/images/guide_audit_8.png'
      },
      {
        step: 'Step 17｜全域微調分頁 1：站別開關與 ISN 條碼規則',
        desc: '點擊「⚙️ 微調 DUTs / Instrument / Global.ini」後會直接內嵌展開於下方。第一分頁可切換站別啟用/停用 (Load=1/0)、修改 DUT 名稱與一鍵批量套用全部站別的 ISN 條碼位數。',
        img: '/images/guide_audit_3.png'
      },
      {
        step: 'Step 18｜全域微調分頁 2：網路 IP / Ping / Port',
        desc: '第二分頁只列出本腳本實際使用的 PCIP_1、DUTIP_1、GoldenIP 與各站連線 Port，免翻找龐雜的 Global.ini。',
        img: '/images/guide_audit_3b.png'
      },
      {
        step: 'Step 19｜全域微調分頁 3：儀器掛載與 COM Port',
        desc: '第三分頁集中修改待測板 COM Port、SFIS 機台編號 (DEVID_1) 與 DAQ / FeasaLED 裝置代號，修改完成後點「✓ 套用微調並重跑健檢」。',
        img: '/images/guide_audit_3c.png'
      },
      {
        step: 'Step 20｜書籤二底部：安全暫存與匯出（原檔不動，產出 *_FIXED.xlsx）',
        desc: '所有編修先暫存於記憶體並條列於待匯出清單，確認無誤後點擊「🧪 匯出無硬體試跑版」或綠色「💾 寫入並匯出 (*_FIXED.xlsx)」產出新檔（新增區塊亮黃底）並重算 64 碼 Checksum。',
        img: '/images/guide_editor_export.png'
      }
    ],
    tip: '書籤一用於首次從 0 建立新母體；書籤二用於專案全生命週期無限次新增儀器、改跳轉與微調環境'
  },
  diagnose: {
    icon: '🩺',
    title: '測試 Log 失敗診斷 — 完整操作流程與畫面教學',
    themeBg: '#FEF3C7',
    themeBorder: '#D97706',
    btnClass: 'btn-jump',
    btnLabel: '開始使用：Log 診斷 ▶',
    steps: [
      { num: '①', title: '載入 Log 檔案', jumpIdx: 0, items: ['選取 .log / .csv 大檔', '支援修改後重新解析'] },
      { num: '②', title: '自動定位與瓶頸', jumpIdx: 1, items: ['抓出 FAIL 與超標幅度', 'Phase 耗時 Top5 排行'] },
      { num: '③', title: '一鍵複製摘要', jumpIdx: 2, items: ['整理純文字結論報告', '直接貼至 Teams / 郵件'] },
      { num: '④', title: '書籤二：貼上文字', jumpIdx: 3, items: ['貼上黑窗 / 彈窗錯誤', '免完整檔案立即診斷'] },
      { num: '⑤', title: '即時給予對策', jumpIdx: 4, items: ['比對 Checksum / SFIS', '提供產線排查步驟'] }
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
      { num: '①', title: '自動載入 V2.04', jumpIdx: 0, items: ['開機預載最新官方表', '支援篩選僅顯示通用碼'] },
      { num: '②', title: '搜尋與雙欄複製', jumpIdx: 1, items: ['中英文 / TestID 搜尋', '雙欄複製直接貼 Excel'] },
      { num: '③', title: '方案一：套用母體', jumpIdx: 2, items: ['寫入新腳本母體積木', '可同步帶入英文描述'] },
      { num: '④', title: '方案二：寫入 Excel', jumpIdx: 3, items: ['切換第二書籤選 Excel', '接續健檢檔案直接補碼'] },
      { num: '⑤', title: '篩選缺碼並存檔', jumpIdx: 4, items: ['僅看缺 TestID 列', '套用後直接簽章存回'] }
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
  document.documentElement.style.fontSize = fs + 'px';
  document.body.style.fontSize = fs + 'px';

  // 根據字型層級動態調整標題與各層級比例 (最高 19px)
  let h1Size = '22px';
  let h2Size = '19px';
  let h3Size = '17px';
  let subSize = '13.5px';
  if (fs === 13) {
    h1Size = '19px';
    h2Size = '17px';
    h3Size = '15px';
    subSize = '12px';
  } else if (fs === 17) {
    h1Size = '24px';
    h2Size = '19px';
    h3Size = '18px';
    subSize = '15px';
  }
  document.documentElement.style.setProperty('--app-font-size', fs + 'px');
  document.documentElement.style.setProperty('--app-h2-size', h2Size);
  document.documentElement.style.setProperty('--app-sub-size', subSize);

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
  const stepsHtml = d.steps.map((st, idx) => {
    const jIdx = typeof st.jumpIdx === 'number' ? st.jumpIdx : idx;
    const targetStep = (d.detailedSteps && d.detailedSteps[jIdx]) ? String(d.detailedSteps[jIdx].step).split('｜')[0].trim() : `Step ${jIdx + 1}`;
    return `
    <div style="display:flex; align-items:stretch; flex:1; min-width:165px; gap:6px;">
      <div class="flow-stage-card" onclick="jumpToFlowStep(${jIdx})" title="點擊跳轉至 ${targetStep}"
           style="flex:1; background:#FFFFFF; border:1.5px solid ${d.themeBorder}; border-top:4px solid ${d.themeBorder}; border-radius:10px; padding:11px 12px; box-shadow:0 2px 6px rgba(15,23,42,0.06); display:flex; flex-direction:column; justify-content:space-between;">
        <div>
          <div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
            <span style="background:${d.themeBg}; color:#0F172A; font-weight:800; font-size:12.5px; padding:2px 8px; border-radius:999px; border:1px solid ${d.themeBorder};">${st.num}</span>
            <span style="font-weight:700; font-size:14.5px; color:#0F172A;">${st.title}</span>
          </div>
          <ul style="margin:0 0 8px 16px; padding:0; font-size:12.5px; color:#334155; line-height:1.5;">
            ${st.items.map(it => `<li>${it}</li>`).join('')}
          </ul>
        </div>
        <div style="font-size:11.5px; font-weight:700; color:${d.themeBorder}; text-align:right;">跳至 ${targetStep} ▶</div>
      </div>
      ${idx < d.steps.length - 1 ? '<div style="display:flex; align-items:center; font-size:18px; font-weight:700; color:#64748B;">➔</div>' : ''}
    </div>
  `;
  }).join('');

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
