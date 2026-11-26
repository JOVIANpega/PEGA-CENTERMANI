// Flow Guide (Scrollable Detailed Tutorial + Single-Focus Red-Box Screenshots) & System Settings Manager
let APP_SETTINGS = {
  auto_fullscreen: true,
  show_flow_guide: true,
  show_top_refresh: true,
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
      { num: '①', title: '選擇 Excel 檔案', jumpIdx: 0, items: ['單份腳本即時體檢', '自動比對 System.ini'] },
      { num: '②', title: '掃描整包資料夾', jumpIdx: 1, items: ['遞迴掃描專案內多站', '支援一鍵整包批次修復'] },
      { num: '③', title: '紅黃燈體檢報告', jumpIdx: 2, items: ['抓出缺碼與格式錯誤', '自動讀取 ISN 條碼位數'] },
      { num: '④', title: '左側欄與跳轉分支', jumpIdx: 3, items: ['異常工作表自動置頂', '展開跳轉樹檢查邏輯'] },
      { num: '⑤', title: '一鍵修好並匯出', jumpIdx: 4, items: ['自動補碼與格式修正', '重算 Checksum 寫回原檔旁'] }
    ],
    detailedSteps: [
      {
        stageIdx: 0,
        step: 'Step 1｜「選擇 Excel 檔案」：針對單份測試腳本進行快速體檢',
        desc: '適合您只想檢查某一個站的 TestFlow Excel 時使用（亦可直接從下方最近紀錄清單一鍵載入）。點選後自動讀入同資料夾內的 System.ini 與 Global.ini，檢查 16 欄格式、必填 TestID、ExecMode 與跳轉邏輯。',
        img: '/images/guide_audit_1a.png'
      },
      {
        stageIdx: 1,
        step: 'Step 2｜「掃描整包資料夾」：一次體檢專案目錄內所有站別 Excel',
        desc: '當一個專案目錄下分散了多個站別的 Excel（如 Download、MB、RF、OQC）時使用。系統會遞迴掃描全資料夾、自動略過 *_FIXED、old_* 備份檔與 Test Item Code 表，一次列出所有檔案的紅綠燈與錯誤數，並支援「一鍵整包批次修復」（自動備份原 INI 為 .bak）。',
        img: '/images/guide_audit_1b.png'
      },
      {
        stageIdx: 2,
        step: 'Step 3｜檢視紅黃燈體檢報告與自動修補預告',
        desc: '上方橫幅顯示抓出的錯誤總數（如缺少第 16 欄 TestID）、需人工確認數量、從 DUTs 讀取到的 ISN 條碼位數，以及匯出時將自動補齊的機械式格式問題。',
        img: '/images/guide_audit_2.png'
      },
      {
        stageIdx: 3,
        step: 'Step 4｜工作表燈號篩選、跳轉分支樹與折疊明細',
        desc: '點擊上方工作表膠囊（如 MainBoard 🔴42）可只篩選看該站別的錯誤；點擊綠色「跳轉區塊邏輯正常」可展開縮排分支樹檢查跳轉；點擊下方折疊明細列可檢視具體列號。',
        img: '/images/guide_audit_2b.png'
      },
      {
        stageIdx: 4,
        step: 'Step 5｜「💾 一鍵修好並匯出 (*_FIXED.xlsx)」自動補碼與簽章',
        desc: '若要自動修補格式與缺漏的 7 碼 TestID，直接點擊右上角綠色「💾 一鍵修好並匯出 (*_FIXED.xlsx)」，系統將於同目錄產出修復檔（修正處亮黃底）、重算 64 碼 Checksum 寫入 System.ini、開啟資料夾並彈窗檢查缺漏實機 DLL。',
        img: '/images/guide_audit_5b.png'
      }
    ],
    tip: '定位：專注於高頻快速健檢單檔或整包專案腳本並一鍵修補匯出；若需插入儀器、改流程或調整 INI，請使用主畫面的「02 腳本建立與編修中心」'
  },
  gen: {
    icon: '🛠️',
    title: '腳本建立與編修中心 — 完整操作流程與畫面教學',
    themeBg: '#DCFCE7',
    themeBorder: '#16A34A',
    btnClass: 'btn-primary-green',
    btnLabel: '開始使用：建立與編修中心 ▶',
    steps: [
      { num: '①', title: '選 2 主模式＋獨立工具', jumpIdx: 0, items: ['既有編修(1→N) / 首次範本(0→1)', '實機測試 SFIS/DLL 已獨立至首頁'] },
      { num: '②', title: '既有腳本：分區編修', jumpIdx: 1, items: ['INI 獨立存檔 / 積木排序 / 跳轉', '新增測試站與跨檔複製 Sheet'] },
      { num: '③', title: '首次範本：積木拖曳建母體', jumpIdx: 6, items: ['積木拖曳 & 📦群組方框', '逐頁設定 + TestID + 語法體檢'] },
      { num: '④', title: '可用儀器庫 & 實機驗證', jumpIdx: 10, items: ['搜尋/規格/缺 DLL/人機與 MCS', 'SFIS (ISN/GET/WRITE) 與 DLLtest'] },
      { num: '⑤', title: '匯出與實機 DLL 檢查', jumpIdx: 12, items: ['必開目錄＋缺 DLL/驅動提醒', '對齊 DLL 版號與詢問開 Excel'] }
    ],
    detailedSteps: [
      {
        stageIdx: 0,
        step: 'Step 1｜選擇 2 大主力作業模式（既有編修 / 首次範本）與右上 4 項獨立工具',
        desc: '進入「02 腳本建立與編修中心」後，主畫面提供兩大主力模式：日常改版選「01 既有腳本編修 (1→N)」；全新開案選「02 產生首次範本 (0→1)」。右上角 4 顆獨立工具為「🧪 生單台儀器範例」、「🛡️ 實機測試 SFIS / DLL」、「📖 語法寫法小抄」與「🏷️ 批次補換 TestID」。',
        img: '/images/guide_editor_tab.png'
      },
      {
        stageIdx: 1,
        step: 'Step 2｜既有腳本編修：載入 TestFlow.xlsx 或跨檔案複製整張 Sheet',
        desc: '點擊「選擇要編修的 TestFlow.xlsx」或從最近使用紀錄快選載入；若要把別份 Excel 的測站或儀器頁完整搬移過來，可點「📋 跨檔案複製整張 Sheet」（支援系統視窗瀏覽選檔與最近檔案下拉、優先呼叫 Excel 原生複製保留欄寬/合併格/顏色/驗證，並自動備份 .bak）。',
        img: '/images/guide_editor_zone_a.png'
      },
      {
        stageIdx: 1,
        step: 'Step 3｜既有腳本編修（01 System.ini / 02 Global.ini）：支援獨立存檔彈記事本',
        desc: '點選第 1 格（System.ini）可使用「🛠️ 工程調試 (Debug=1)」/「🏭 正式量產 (Debug=0)」一鍵切換與出廠廠區 6 選 1（同時連動 SFIS_WebLink 與 iPLAS_Site）；第 2 格（Global.ini）提供一拖四槽位 LOAD_1~4、⚡ 一鍵同步 PC/DUT 同網段 IP 與 60+ 進階變數搜尋過濾。異動處原地黃底標示並可「💾 直接存檔並彈出 INI 記事本」免重匯整份 Excel。',
        img: '/images/guide_audit_7.png'
      },
      {
        stageIdx: 1,
        step: 'Step 4｜既有腳本編修（03 Flow Sort）：積木順序排序、淡藍標記與指令預覽',
        desc: '點選第 3 格開啟積木排序器：可直接修改 Phase 數字插隊或拖拉對調，支援「📋 複製整段 / 🧹 刪除 / ＋ 插入新測項」與「⛶ 全螢幕檢視」，右側即時預覽 Command │ Send 指令與變數相依診斷；匯出時修改過順序的區塊標上柔和淡藍色 (#E8F4FD) 且開啟 Excel 自動鎖定該測試站 Sheet。',
        img: '/images/guide_audit_6.png'
      },
      {
        stageIdx: 1,
        step: 'Step 5｜既有腳本編修（04 Jump & Retry / 05 站別 ISN 與儀器掛載）',
        desc: '第 4 格可視覺化設定每步 PASS/FAIL 跳轉目標並附帶 SKU 分流範例與彩色 ExecMode (0~9) 速查；第 5 格支援一鍵「＋ 新增測試站」（同時自動建立對應 Excel 工作表）、批量調整全站 ISN 條碼位數，並在折疊區微調外部儀器掛載與連線設定。',
        img: '/images/guide_audit_3.png'
      },
      {
        stageIdx: 1,
        step: 'Step 6｜既有腳本編修底部：安全暫存匯出（無硬體試跑版 / *_FIXED.xlsx）',
        desc: '編修完成後於底部點擊「🧪 匯出無硬體試跑版」或「💾 寫入並匯出 Excel (*_FIXED.xlsx)」，系統會自動順編、補齊安全收尾、計算 64 碼 Checksum，先開啟輸出目錄並彈窗顯示實機 DLL 檢查與詢問是否開啟 Excel。',
        img: '/images/guide_editor_export.png'
      },
      {
        stageIdx: 2,
        step: 'Step 7｜產生首次範本：左右分欄測試積木庫拖曳排順序（支援 📦 群組方框）',
        desc: '進入「產生首次範本 🧱 積木拖曳編排」後，預設帶入 開始/條碼/chkRoute/指令/清理/結束 6 塊骨架。從左欄將 指令/等待/儀器/SKU/SFIS 拖進右欄測試序列；需要同一 Phase 混排多塊時可拖入 📦 群組方框並展開置入子積木，亦可點擊「🪄 一鍵自動排最佳順序」或「🔄 恢復預設 6 塊」。',
        img: '/images/guide_gen_1a.png'
      },
      {
        stageIdx: 2,
        step: 'Step 8｜逐頁設定（一頁一塊）：基礎參數 ＋ 進階 TestID 即時關鍵字搜尋',
        desc: '點擊「開始逐塊設定」依底部彩灰進度條逐頁設定（群組子積木自動編為 #3.1、#3.2），支援貼上 Log 反白自動推導擷取公式、勾選動作後自動加 :Delay，以及在右上「⚙️ 顯示進階細項設定」中即時搜尋 7 碼 TestID（如打「電流」選 BRME027）與檢視連動 INI 預覽。',
        img: '/images/guide_gen_2a.png'
      },
      {
        stageIdx: 2,
        step: 'Step 9｜專屬互動積木（外接儀器 / 多 SKU 分流 / SFIS 讀寫）',
        desc: '紅標「🧪 儀器」與「🎯 SKU」可直接嵌入同頁切換實機儀器型號（NI-6008 / FeasaLED / PPH1503 / IQxel RF）與多品種 4:P,F 分流設定；SFIS 積木可雙向呼叫「SFIS 流程積木編輯頁」實測後帶回。',
        img: '/images/guide_gen_3.png'
      },
      {
        stageIdx: 2,
        step: 'Step 10｜流程總覽確認與自動語法體檢產出',
        desc: '總覽頁採用與拖曳畫面相同的積木流程檢視（點擊任一積木立即修改，群組點 ▼ 展開），匯出前預設自動執行 16 欄語法與結構體檢，完成後立即開啟 Excel 並條列實際寫入之 INI 設定摘要。',
        img: '/images/guide_gen_4b.png'
      },
      {
        stageIdx: 3,
        step: 'Step 11｜插入儀器範本 Step 1：左欄可用儀器庫 ＋ 右欄測試序列',
        desc: '左欄支援關鍵字搜尋、分類篩選與「📖 查看儀器規格/接線簡介」；左右兩欄皆即時以紅框標示本機 Device\\ 缺少的「❌ 缺 DLL」。點擊「＋ 加入」或拖曳儀器至右欄排列順序，再點「✅ 確認以上儀器清單」。需要驗證 SFIS（ISN 刷過／GET／WRITE）或單測 DLL 時可切到首頁「🛡️ 實機測試 SFIS / DLL」。',
        img: '/images/guide_gen_2d.png'
      },
      {
        stageIdx: 3,
        step: 'Step 12｜插入儀器選擇「⚡ 懶人快速版」或「🎛️ 專業細部版」（含 RF MCS 子表）',
        desc: '選「⚡ 懶人快速版」自動為每台儀器生成至少 3 個代表性測項；選「🎛️ 專業細部版」可進 Step 2 調整測項、上下限與開啟 NI-6009 / FeasaLED / IQxel RF 互動人機（IQxel 會自動產生 WIFI Tx/Rx MCS 子工作表），匯出時自動僅保留選用儀器＋Phase 97 IPOWER2401 並對齊真實 DLL 版號。',
        img: '/images/guide_audit_4.png'
      },
      {
        stageIdx: 4,
        step: 'Step 13｜匯出保障：必開輸出目錄 ＋ 缺漏 DLL / 驅動檢查 ＋ 詢問開啟 Excel',
        desc: '系統啟動會自動偵測並記憶本機 Centimani 主程式目錄 (centimani_dir，亦可在「⚙️ 系統設定」手動變更)。每次匯出時一律先開啟輸出資料夾，並於置中彈窗顯示缺少的實機 DLL 與系統驅動檢查（如 NI-DAQmx nicaiu.dll），再由您決定是否立即開啟 Excel。',
        img: '/images/guide_audit_5b.png'
      }
    ],
    tip: '點擊上方「①～⑤ 五大階段卡片」即可篩選對應步驟；支援既有腳本快捷編修、從 0 建新母體、可用儀器庫、語法小抄與 SFIS/DLL 實機驗證'
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
      { num: '④', title: '模式二：貼上文字', jumpIdx: 3, items: ['貼上黑窗 / 彈窗錯誤', '免完整檔案立即診斷'] },
      { num: '⑤', title: '即時給予對策', jumpIdx: 4, items: ['比對 Checksum / SFIS', '提供產線排查步驟'] }
    ],
    detailedSteps: [
      {
        stageIdx: 0,
        step: 'Step 1｜選擇 Log / CSV 檔案（支援數百 KB 大檔快速解析）',
        desc: '點擊「📂 點此選擇要分析的 Log / CSV 檔案」載入 Centimani 產線測試紀錄；若只有幾行終端機錯誤訊息，也可切換上方「📋 模式二：貼上錯誤文字」直接貼上分析。',
        img: '/images/guide_diag_1.png'
      },
      {
        stageIdx: 1,
        step: 'Step 2｜檢視失敗定位、超標幅度與 Phase 耗時瓶頸',
        desc: '系統會自動列出所有量測數值與規格上下限對比，標註超出幾 V / 幾 dBm，並統計各 Phase 耗時 Top 5 協助找出拖慢 Cycle Time 的瓶頸步驟；重新修改過 Log 後可按右側「🔄 重新解析本檔」。',
        img: '/images/guide_diag_2.png'
      },
      {
        stageIdx: 2,
        step: 'Step 3｜一鍵複製乾淨異常摘要報告',
        desc: '點擊右上角「📋 複製測試結論摘要」，自動將專案站別、異常測項、實測數據與推測原因整理成純文字摘要，方便直接貼到 Teams 群組或 Mail 回報。',
        img: '/images/guide_diag_3.png'
      },
      {
        stageIdx: 3,
        step: 'Step 4｜模式二：切換至「模式二：貼上錯誤文字 / 診斷片段」',
        desc: '若當下沒有完整 .log 檔，只有從黑色主控台視窗或 System Error 彈窗複製出來的幾行文字，可點擊上方第二個切換鈕進入文字貼上模式。',
        img: '/images/guide_diag_4.png'
      },
      {
        stageIdx: 4,
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
      { num: '④', title: '方案二：寫入 Excel', jumpIdx: 3, items: ['切換第二頁籤選 Excel', '接續健檢檔案直接補碼'] },
      { num: '⑤', title: '篩選缺碼並存檔', jumpIdx: 4, items: ['僅看缺 TestID 列', '套用後直接簽章存回'] }
    ],
    detailedSteps: [
      {
        stageIdx: 0,
        step: 'Step 1｜自動載入官方 V2.04 表，輸入關鍵字即時篩選',
        desc: '系統開機已自動載入最新版 Test Item Code V2.04 檔案（共 5,200+ 筆代碼），無需手動選檔。直接在搜尋框輸入中文（如「電壓」「LED」）、英文或 7 碼代碼即可搜尋，並建議勾選「僅顯示通用碼」。',
        img: '/images/guide_tic_1.png'
      },
      {
        stageIdx: 1,
        step: 'Step 2｜在左側搜尋結果選定目標 TestID / Error Code',
        desc: '左側清單會列出符合條件的代碼與中英文說明，點擊任一筆即可選中；也可直接點「雙欄複製」將「Description + Tab + TestID」直接貼入 Excel。',
        img: '/images/guide_tic_2.png'
      },
      {
        stageIdx: 2,
        step: 'Step 3｜方案一：套用至母體積木（寫入新產生腳本）',
        desc: '在右側預設的「🧩 方案一：套用至母體積木」頁籤中，展開欲修改的積木步驟，點擊右側「套用」按鈕即可將合法 7 碼代碼直接寫入新腳本母體，並可勾選同步帶入英文 Description。',
        img: '/images/guide_tic_3.png'
      },
      {
        stageIdx: 3,
        step: 'Step 4｜方案二：切換至「方案二：寫入現有 Excel」',
        desc: '若是要補齊既有的 TestFlow.xlsx 檔案（例如稽核抓出缺少第 16 欄 TestID），請點擊右側第二個分頁「📄 方案二：寫入現有 Excel」。',
        img: '/images/guide_tic_4.png'
      },
      {
        stageIdx: 4,
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

  // 根據字型層級動態調整標題與各層級比例 (最高 19px 內文，標題相應縮放)
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
    h2Size = '20px';
    h3Size = '18px';
    subSize = '15px';
  } else if (fs === 19) {
    h1Size = '26px';
    h2Size = '22px';
    h3Size = '20px';
    subSize = '16.5px';
  }
  document.documentElement.style.setProperty('--app-font-size', fs + 'px');
  document.documentElement.style.setProperty('--app-scale', (fs / 15).toFixed(4));
  document.documentElement.style.setProperty('--app-h2-size', h2Size);
  document.documentElement.style.setProperty('--app-sub-size', subSize);
  document.body.style.fontSize = fs + 'px';

  if (typeof setIntroFontSize === 'function') {
    setIntroFontSize(fs);
  }
  const chkTic = document.getElementById('chkTicGenericOnly');
  if (chkTic) chkTic.checked = !!APP_SETTINGS.tic_generic_only;

  const btnRef = document.getElementById('btnTopRefresh');
  if (btnRef) {
    btnRef.style.display = (APP_SETTINGS.show_top_refresh !== false) ? 'inline-flex' : 'none';
  }

  // 若目前正在瀏覽導覽頁，即時套用新字體大小重繪
  const fgEl = document.getElementById('panelFlowGuide');
  if (fgEl && fgEl.style.display === 'block' && PENDING_FLOW_TARGET && PENDING_FLOW_TARGET.tab) {
    renderFlowGuidePage(PENDING_FLOW_TARGET.tab);
  }
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

let FLOW_GUIDE_STAGE_FILTER = {};

function selectFlowGuideStage(tab, stageIdx) {
  const cur = (FLOW_GUIDE_STAGE_FILTER[tab] !== undefined) ? FLOW_GUIDE_STAGE_FILTER[tab] : 'ALL';
  FLOW_GUIDE_STAGE_FILTER[tab] = (cur === stageIdx) ? 'ALL' : stageIdx;
  renderFlowGuidePage(tab);
  const secEl = document.getElementById('flowGuideDetailsSection');
  if (secEl) secEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderFlowGuidePage(tab) {
  const d = FLOW_GUIDE_DATA[tab];
  if (!d) { switchTab(tab); return; }

  const activeStage = (FLOW_GUIDE_STAGE_FILTER[tab] !== undefined) ? FLOW_GUIDE_STAGE_FILTER[tab] : 'ALL';
  const fs = parseInt(APP_SETTINGS.intro_font_size || 15, 10);
  const stepsHtml = d.steps.map((st, idx) => {
    const isSel = (activeStage === idx);
    const hasStageMapping = (d.detailedSteps || []).some(ds => typeof ds.stageIdx === 'number');
    const stageSteps = hasStageMapping
      ? (d.detailedSteps || []).filter(ds => ds.stageIdx === idx)
      : [d.detailedSteps[typeof st.jumpIdx === 'number' ? st.jumpIdx : idx]].filter(Boolean);
    const stepCountHint = stageSteps.length > 0 ? `查看 ${stageSteps.length} 步說明 ▶` : '檢視步驟 ▶';
    return `
    <div style="display:flex; align-items:stretch; flex:1; min-width:165px; gap:6px;">
      <div class="flow-stage-card" onclick="${hasStageMapping ? `selectFlowGuideStage('${tab}', ${idx})` : `jumpToFlowStep(${typeof st.jumpIdx === 'number' ? st.jumpIdx : idx})`}" title="點擊查看「${st.title}」詳細步驟"
           style="flex:1; background:${isSel ? d.themeBg : '#FFFFFF'}; border:${isSel ? '2.5px' : '1.5px'} solid ${d.themeBorder}; border-top:4px solid ${d.themeBorder}; border-radius:10px; padding:11px 12px; box-shadow:${isSel ? '0 6px 16px rgba(15,23,42,0.14)' : '0 2px 6px rgba(15,23,42,0.06)'}; display:flex; flex-direction:column; justify-content:space-between; cursor:pointer; transition:all 0.16s ease;">
        <div>
          <div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
            <span style="background:${isSel ? d.themeBorder : d.themeBg}; color:${isSel ? '#FFFFFF' : '#0F172A'}; font-weight:800; font-size:0.83rem; padding:2px 8px; border-radius:999px; border:1px solid ${d.themeBorder};">${st.num}</span>
            <span style="font-weight:700; font-size:0.97rem; color:#0F172A;">${st.title}</span>
          </div>
          <ul style="margin:0 0 8px 16px; padding:0; font-size:0.85rem; color:#334155; line-height:1.5;">
            ${st.items.map(it => `<li>${it}</li>`).join('')}
          </ul>
        </div>
        <div style="font-size:0.78rem; font-weight:800; color:${d.themeBorder}; text-align:right;">${isSel ? '✓ 目前篩選中（點此顯示全部）' : stepCountHint}</div>
      </div>
      ${idx < d.steps.length - 1 ? '<div style="display:flex; align-items:center; font-size:1.2rem; font-weight:700; color:#64748B;">➔</div>' : ''}
    </div>
  `;
  }).join('');

  const filteredDetails = (activeStage === 'ALL')
    ? (d.detailedSteps || [])
    : (d.detailedSteps || []).filter(ds => ds.stageIdx === activeStage);

  const detailCardsHtml = filteredDetails.map((ds, idx) => {
    const parts = String(ds.step || '').split('｜');
    const stepTag = (parts[0] || ('Step ' + (idx + 1))).trim();
    const stepTitle = parts.slice(1).join('｜').trim();
    const headerHtml = stepTitle
      ? `<span style="display:inline-block; background:#FACC15; color:#0F172A; font-weight:800; padding:2px 10px; border-radius:6px; border:1px solid #CA8A04; margin-right:8px;">${stepTag}</span><span>${stepTitle}</span>`
      : `<span>${ds.step}</span>`;
    return `
    <div id="flowStepCard_${idx}" style="scroll-margin-top:16px; background:#F8FAFC; border:1px solid #CBD5E1; border-left:4px solid ${d.themeBorder}; border-radius:8px; padding:14px 16px; transition:box-shadow 0.25s ease;">
      <div style="display:flex; align-items:center; flex-wrap:wrap; gap:4px; font-weight:700; font-size:1.05rem; color:#0F172A; margin-bottom:8px;">${headerHtml}</div>
      <div class="flow-guide-desc" style="font-size:1rem; color:#334155; line-height:1.65; margin-bottom:10px;">${ds.desc}</div>
      <div style="text-align:center; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:8px;">
        <img src="${ds.img}" alt="${ds.step}"
             onerror="this.parentElement.style.display='none'"
             style="max-width:100%; max-height:380px; border-radius:6px; border:1px solid #CBD5E1; cursor:zoom-in;"
             onclick="window.open(this.src, '_blank')"
             title="點擊開啟原尺寸大圖">
      </div>
    </div>
  `;
  }).join('');

  const stageTitleLabel = (activeStage !== 'ALL' && d.steps[activeStage])
    ? `${d.steps[activeStage].num} ${d.steps[activeStage].title}（共 ${filteredDetails.length} 步）`
    : `全部步驟（共 ${(d.detailedSteps || []).length} 步，點上方階段卡片可快速篩選）`;

  const box = document.getElementById('panelFlowGuide');
  box.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid ${d.themeBorder}; border-radius:12px; padding:20px 24px;">
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; padding-bottom:12px; border-bottom:1.5px solid ${d.themeBg};">
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:1.85rem; background:${d.themeBg}; padding:6px 10px; border-radius:8px;">${d.icon}</span>
          <h2 style="margin:0; font-size:1.27rem; color:#0F172A;">${d.title}</h2>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <button onclick="switchTab('home')" class="btn" style="background:#E2E8F0; color:#1E293B; border-color:#94A3B8;">◀ 返回首頁</button>
          <button onclick="confirmFlowGuideProceed()" class="btn ${d.btnClass}" style="padding:7px 16px; font-size:0.9rem;">${d.btnLabel}</button>
        </div>
      </div>

      <div style="display:flex; flex-wrap:wrap; gap:10px; margin:16px 0; align-items:stretch;">
        ${stepsHtml}
      </div>

      <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 14px; font-size:0.92rem; color:#1E293B; margin-bottom:14px;">
        💡 <b>說明：</b>${d.tip}
      </div>

      <div id="flowGuideDetailsSection" style="margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
          <div style="font-weight:700; font-size:1rem; color:#0F172A;">📖 詳細操作步驟說明 — ${stageTitleLabel}</div>
          ${activeStage !== 'ALL' ? `<button type="button" onclick="FLOW_GUIDE_STAGE_FILTER['${tab}']='ALL'; renderFlowGuidePage('${tab}');" class="btn" style="padding:4px 12px; font-size:0.85rem; background:#EFF6FF; color:#1D4ED8; border:1px solid #93C5FD; font-weight:800;">📋 顯示全部 ${(d.detailedSteps || []).length} 步</button>` : ''}
        </div>
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${detailCardsHtml}
        </div>
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; padding-top:12px; border-top:1px solid #E2E8F0;">
        <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer; font-weight:700; font-size:0.9rem; color:#475569; user-select:none;">
          <input type="checkbox" id="chkSkipThisFlowGuide" style="width:17px; height:17px; cursor:pointer;">
          下次不再顯示此流程說明（可在首頁右上角「⚙️ 系統與環境設定」重新開啟）
        </label>
        <button onclick="confirmFlowGuideProceed()" class="btn ${d.btnClass}" style="padding:9px 22px; font-size:0.97rem;">
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
  const cmProf = (typeof STATE !== 'undefined' && STATE.centimaniProfile) ? STATE.centimaniProfile : {};
  const niLineHtml = cmProf.exists
    ? (cmProf.ni_daqmx_installed
      ? '<span style="color:#15803D; font-weight:700;">✅ NI-DAQmx 系統驅動：已安裝</span>'
      : '<span style="color:#DC2626; font-weight:800;">⚠️ NI-DAQmx 系統驅動：未安裝（缺 nicaiu.dll，Office 電腦測試 NI6008 請勾 Phase=-1）</span>')
    : '';
  box.innerHTML = `
    <div style="background:#FFFFFF; border:1.5px solid #E11D48; border-radius:12px; padding:20px 24px; max-width:860px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-bottom:12px; border-bottom:1px solid #E2E8F0; margin-bottom:16px;">
        <div>
          <h2 style="margin:0; font-size:1.27rem; color:#0F172A;">⚙️ 系統與環境設定 (Preferences)</h2>
          <div style="font-size:0.87rem; color:#64748B; margin-top:2px;">勾選後即時保存至 config.json，字體大小會即時套用至全站</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span id="settingsSaveStatus" style="display:none; padding:4px 10px; border-radius:6px; border:1px solid #4ADE80; font-size:0.85rem; font-weight:700;"></span>
          <button onclick="switchTab('home')" class="btn" style="background:#E2E8F0; color:#1E293B; border-color:#94A3B8;">◀ 返回首頁</button>
        </div>
      </div>

      <div style="display:flex; flex-direction:column; gap:12px;">
        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkFullscreen" ${s.auto_fullscreen ? 'checked' : ''} onchange="saveAppSettings({auto_fullscreen:this.checked})" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A; font-size:0.97rem;">啟動時自動全螢幕 / 最大化瀏覽器視窗</div>
            <div style="font-size:0.85rem; color:#64748B;">開啟工具時自動將 Chrome / Edge 視窗最大化（下次重啟 .bat 生效）</div>
          </div>
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkFlowGuide" ${s.show_flow_guide ? 'checked' : ''} onchange="saveAppSettings({show_flow_guide:this.checked})" style="width:18px; height:18px;">
          <div style="flex:1;">
            <div style="font-weight:700; color:#0F172A; font-size:0.97rem;">進入功能前顯示「流程圖導覽說明頁」</div>
            <div style="font-size:0.85rem; color:#64748B;">點選首頁功能卡時先顯示操作流程圖與教學（目前已略過 ${skipCnt} 個模組）</div>
          </div>
          ${skipCnt > 0 ? `<button onclick="event.preventDefault(); resetAllSkipGuides();" class="btn" style="padding:4px 10px; font-size:0.82rem; background:#DBEAFE; color:#1E3A8A;">🔄 重設所有導覽顯示</button>` : ''}
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkOpenFolder" ${s.auto_open_folder ? 'checked' : ''} onchange="saveAppSettings({auto_open_folder:this.checked})" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A; font-size:0.97rem;">匯出時自動開啟輸出資料夾（Excel 改由彈窗確認後開啟）</div>
            <div style="font-size:0.85rem; color:#64748B;">匯出 *_FIXED.xlsx、新母體或儀器範本時一律先開啟 Windows 資料夾，並於畫面彈窗顯示 DLL 檢查後由您決定是否開啟 Excel</div>
          </div>
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkTicGeneric" ${s.tic_generic_only ? 'checked' : ''} onchange="saveAppSettings({tic_generic_only:this.checked}); applyLoadedSettings({tic_generic_only:this.checked});" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A; font-size:0.97rem;">代碼速查預設勾選「僅顯示通用 TestID / Error Code」</div>
            <div style="font-size:0.85rem; color:#64748B;">進入 TestID 速查頁面時優先顯示各機種通用代碼（預設已自動載入 V2.04）</div>
          </div>
        </label>

        <label style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer;">
          <input type="checkbox" id="setChkTopRefresh" ${s.show_top_refresh !== false ? 'checked' : ''} onchange="saveAppSettings({show_top_refresh:this.checked}); applyLoadedSettings({show_top_refresh:this.checked});" style="width:18px; height:18px;">
          <div>
            <div style="font-weight:700; color:#0F172A; font-size:0.97rem;">頂部導覽列顯示「🔄 重新整理」開發按鈕</div>
            <div style="font-size:0.85rem; color:#64748B;">開發測試階段建議勾選方便重載；正式上線使用時可取消勾選讓頂部更精簡</div>
          </div>
        </label>

        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px;">
          <div>
            <div style="font-weight:700; color:#0F172A; font-size:0.97rem;">全站介面與教學說明預設字體大小</div>
            <div style="font-size:0.85rem; color:#64748B;">切換後立即等比放大 / 縮小全站文字、功能說明、流程教學與儀器介紹頁</div>
          </div>
          <div style="display:inline-flex; gap:6px;">
            <button onclick="saveAppSettings({intro_font_size:13}); applyLoadedSettings({intro_font_size:13}); renderSettingsPanel();" class="btn" style="padding:4px 12px; font-size:0.85rem; ${fs===13?'background:#2563EB;color:#fff;border-color:#1D4ED8;':''}">小 (13px)</button>
            <button onclick="saveAppSettings({intro_font_size:15}); applyLoadedSettings({intro_font_size:15}); renderSettingsPanel();" class="btn" style="padding:4px 12px; font-size:0.85rem; ${fs===15?'background:#2563EB;color:#fff;border-color:#1D4ED8;':''}">中 (15px)</button>
            <button onclick="saveAppSettings({intro_font_size:17}); applyLoadedSettings({intro_font_size:17}); renderSettingsPanel();" class="btn" style="padding:4px 12px; font-size:0.85rem; ${fs===17?'background:#2563EB;color:#fff;border-color:#1D4ED8;':''}">大 (17px)</button>
            <button onclick="saveAppSettings({intro_font_size:19}); applyLoadedSettings({intro_font_size:19}); renderSettingsPanel();" class="btn" style="padding:4px 12px; font-size:0.85rem; ${fs===19?'background:#2563EB;color:#fff;border-color:#1D4ED8;':''}">特大 (19px)</button>
          </div>
        </div>

        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; padding:10px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px;">
          <div style="flex:1; min-width:220px;">
            <div style="font-weight:700; color:#0F172A; font-size:0.97rem;">本機 Centimani 主程式目錄（檢查 <code>Device\\*.dll</code> 與 <code>LoadScript.dll</code>）</div>
            <div class="mono" style="font-size:0.82rem; color:#334155; margin-top:2px; word-break:break-all;">${s.centimani_dir || '尚未指定（啟動時自動搜尋專案目錄內）'}</div>
            ${niLineHtml ? `<div style="font-size:0.84rem; margin-top:4px;">${niLineHtml}</div>` : ''}
          </div>
          <button onclick="pickCentimaniDir()" class="btn btn-primary-blue" style="padding:5px 14px; font-size:0.85rem;">📁 指定 / 變更目錄</button>
        </div>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:16px; padding-top:12px; border-top:1px solid #E2E8F0;">
        <button onclick="confirmAndSaveSettingsBtn()" class="btn btn-primary-green" style="padding:8px 20px; font-size:0.95rem;">💾 確認並儲存設定</button>
      </div>
    </div>
  `;
}

async function confirmAndSaveSettingsBtn() {
  const showRef = document.getElementById('setChkTopRefresh') ? document.getElementById('setChkTopRefresh').checked : true;
  await saveAppSettings({
    auto_fullscreen: document.getElementById('setChkFullscreen').checked,
    show_flow_guide: document.getElementById('setChkFlowGuide').checked,
    show_top_refresh: showRef,
    auto_open_folder: document.getElementById('setChkOpenFolder').checked,
    tic_generic_only: document.getElementById('setChkTicGeneric').checked
  }, true);
  applyLoadedSettings({ show_top_refresh: showRef });
}

async function resetAllSkipGuides() {
  await saveAppSettings({ show_flow_guide: true, skip_guides: {} }, true);
  renderSettingsPanel();
}
