// =========================================================================
// Centimani Studio - 問編寫問題（白話直覺回答 + 精簡 Excel 改前/改後對比引擎）
// 依據 perter_SCRIPT_11102026 (10 大實戰站別) 與 Centimani 官方規格整理
// =========================================================================

const QA_SCENARIOS = [
  {
    id: 'qa_retry_where',
    badge: '🔁 重試 & 跳轉',
    cardTitle: 'Retry 重試次數與失敗跳轉怎麼改？',
    cardHint: '改 Title 最後數字 (,3) 或 ExecMode (1 / 2:0 / 4:P,F)',
    theme: '#DBEAFE',
    accent: '#1D4ED8',
    chipText: 'retry 哪裡改',
    keywords: 'retry 重試 重測 次數 幾次 哪裡 改 title execmode system.ini retrycount 1 2:0 4: 跳轉 退回 回溯',
    directSteps: [
      { col: '改 Title 欄最後數字', what: '控制「整組測項」失敗最多重跑幾次', ex: '0,Voltage Check,3  ➔  改成  0,Voltage Check,5（重跑 5 次）' },
      { col: '改 ExecMode 欄', what: '控制「單一步驟」失敗後要怎麼做', ex: '1 = 原地重試這一行 ｜ 2:0 = 退回這個 Title 第 0 行重跑 ｜ 0 = 不重試直接判 Fail' },
      { col: '改 System.ini (選用)', what: '控制整套系統的預設重試上限', ex: 'RetryCount=3（通常維持預設，個別項目改 Title 即可）' }
    ],
    previewCols: ['Phase', 'Title', 'Send', 'ExecMode', '說明'],
    highlightCols: ['Title', 'ExecMode'],
    sampleRows: [
      { Phase: '1', Title: '0,Measure Voltage,5', Send: ':ObtainDevice', ExecMode: '0', '說明': '👈 改這裡的「,5」＝ 這整個 Title 最多重試 5 次' },
      { Phase: '', Title: '', Send: 'UART@ping\\r\\n', ExecMode: '1', '說明': '👈 ExecMode=1 ＝ 只原地重試這一行指令' },
      { Phase: '', Title: '', Send: 'UART@check_ok\\r\\n', ExecMode: '2:0', '說明': '👈 ExecMode=2:0 ＝ 這行失敗就退回第 0 行重新來過' },
      { Phase: '', Title: '', Send: ':ReleaseDevice', ExecMode: '3', '說明': '👈 收尾釋放必寫 3（失敗也一定要繼續釋放）' }
    ],
    tip: '⚠️ 2:X 的數字是從「所屬 Title 第 1 列」算第 0 步（不可寫得比目前步驟還後面）；且該 Title 後面必須填次數（例如 ,3）或省略，不可寫成 ,0 否則不會重跑！',
    sourceRef: 'perter_SCRIPT_11102026（02. RF / 06. SUBQT / 08. UF 等站別實戰規則）'
  },
  {
    id: 'qa_pause_skip',
    badge: '⏸️ 暫停 / 跳過',
    cardTitle: '我要怎麼暫停這一個 Phase / Title / 單行？',
    cardHint: '改 Phase=-1（停整段）、Title=2,名稱（停單項）或 ExecMode=6',
    theme: '#FEF3C7',
    accent: '#B45309',
    chipText: '怎麼暫停這一個 Phase',
    keywords: '暫停 停用 跳過 略過 關閉 不測 註解 pause skip disable phase -1 title 2 execmode 6 開關',
    directSteps: [
      { col: '改 Phase 欄為 -1', what: '暫停「整個 Phase」（底下全部 Title 都不執行）', ex: '原本 Phase 寫 3  ➔  改成 -1（恢復時改回 3 即可，免刪步驟）' },
      { col: '改 Title 開頭為 2,', what: '只暫停「這一個 Title 小區塊」（其他 Title 照跑）', ex: '0,Sub Test,3  ➔  改成  2,Sub Test,3（2 = Skip 該區塊）' },
      { col: '改 ExecMode 欄為 6', what: '只跳過「這一行」指令', ex: '原本寫 1  ➔  改成 6（只略過該列，常用於暫關某條指令）' },
      { col: '寫 *$(開關變數),Title', what: '想改 Global.ini 就能遠端開關', ex: 'Title 寫 *$(RL),Delay，在 Global.ini [Scripts] 設 RL=0 跑 / RL=2 停' }
    ],
    previewCols: ['Phase', 'Title', 'Send', 'ExecMode', '說明'],
    highlightCols: ['Phase', 'Title', 'ExecMode'],
    sampleRows: [
      { Phase: '-1', Title: '0,Sub-G Set Offset,5', Send: ':ObtainDevice', ExecMode: '0', '說明': '① Phase 改 -1：整個 Phase 暫停不跑' },
      { Phase: '5', Title: '2,WIFI CH13 Test,3', Send: 'CH13,...', ExecMode: '1', '說明': '② Title 開頭 0 改 2：只跳過這一組 Title' },
      { Phase: '', Title: '', Send: ':Dev.OutOnOff,"OFF"', ExecMode: '6', '說明': '③ ExecMode 改 6：只跳過這 1 行' }
    ],
    tip: '💡 如果一個 Phase 底下有 3 個 Title，只想停第 2 個請改「Title=2,名稱」；改「Phase=-1」會把整個 Phase 一起停掉！',
    sourceRef: 'perter_SCRIPT_11102026（02. RF Phase=-1 出現 14 次；全 corpus Title=2 出現 275 次；ExecMode=6 出現 1,073 次）'
  },
  {
    id: 'qa_instrument_once',
    badge: '🧪 儀器單次綁定',
    cardTitle: 'Instrument 欄何時寫、何時必須留空？',
    cardHint: '寫在區塊第 1 列（填 Functions 名稱），後續 :Dev.* / :ReleaseDevice 全留空',
    theme: '#DCFCE7',
    accent: '#15803D',
    chipText: 'Instrument 何時留空',
    keywords: 'instrument 留空 重複 連續 寫一次 寫幾次 functions voltage led_test powerswitch obtaindevice releasedevice subdevice devuart',
    directSteps: [
      { col: '第 1 列寫 Functions 名稱', what: '填 Instrument 表裡的功能名稱（不是填儀器 Name）', ex: '填 Voltage / LED_Test / SetON / OUTONOFF / RST / MeasWIFI' },
      { col: '同區塊底下全部留空', what: '緊接的 :Delay、:Dev.*、:ReleaseDevice 不用再重複寫', ex: '只有切換成下一種功能（如 MeasWIFI ➔ GenWIFI）才需再寫一次' },
      { col: 'Sub=1 子裝置寫法', what: '例如 DevUart / vnxRFSW，Instrument 欄不寫，改在 Send 呼叫', ex: ':ObtainSubDevice,"DevUart" ➔ :sDev.Send ➔ :ReleaseSubDevice' }
    ],
    previewCols: ['Phase', 'Title', 'Instrument', 'Send', 'ExecMode'],
    highlightCols: ['Instrument'],
    sampleRows: [
      { Phase: '1', Title: '0,Measure 3.3V Rail,3', Instrument: 'Voltage', Send: ':ObtainDevice', ExecMode: '0' },
      { Phase: '', Title: '', Instrument: '', Send: ':Delay,"1500"', ExecMode: '0' },
      { Phase: '', Title: '', Instrument: '', Send: ':Dev.VOLTAGE,"RSE,1000,0,1,2"', ExecMode: '0' },
      { Phase: '', Title: '', Instrument: '', Send: ':ReleaseDevice', ExecMode: '3' }
    ],
    tip: '⚠️ 確認 Instrument 分頁該儀器的 Mount 欄有填目前測站名稱（如 MB），否則上機執行會找不到 Device！',
    sourceRef: 'perter_SCRIPT_11102026（02. RF / 06. SUBQT / 07. SFR / 09. ACOUSTIC 全採用區塊首列單次宣告）'
  },
  {
    id: 'qa_multi_title',
    badge: '🧩 Phase / Title 階層',
    cardTitle: '同一個 Phase 底下怎麼寫多個 Title？',
    cardHint: 'Phase 只寫在第一個 Title 的首列，底下每個子項目各自寫一次 Title',
    theme: '#E0E7FF',
    accent: '#4338CA',
    chipText: '同個 Phase 寫多個 Title',
    keywords: 'phase title 多個 底下 下面 只寫一次 合併 共用 階層 結構',
    directSteps: [
      { col: 'Phase 只寫在「整個大階段第 1 列」', what: '把相關的數個小測項歸在同一個大階段下', ex: '例如 Phase 5（WIFI TX 測試）只在第 1 筆寫 5，後面第 2~24 筆 Phase 都留空' },
      { col: '每個小測項首列寫一次 Title', what: '每個 Title 各自獨立計算步數 (0, 1, 2...) 與重試', ex: 'Title 欄寫 0,WIFI CH1,3，底下細部步驟留空；換下一項再寫 0,WIFI CH6,3' }
    ],
    previewCols: ['Phase', 'Title', 'Marco', 'Instrument', 'Send'],
    highlightCols: ['Phase', 'Title'],
    sampleRows: [
      { Phase: '5', Title: '0,Set TX Index', Marco: '', Instrument: 'WIFI 2.4G', Send: ':SetVal,"$txIndex","21"' },
      { Phase: '', Title: '0,WIFI CH1 Tx Test,3', Marco: 'TX', Instrument: '', Send: '2412_OFDM,11ag_54,1,...' },
      { Phase: '', Title: '0,WIFI CH6 Tx Test,3', Marco: 'TX', Instrument: '', Send: '2442_OFDM,11ag_54,7,...' }
    ],
    tip: '💡 區域變數（沒加 $）和 ExecMode 2:X 步號都是跟著「Title」重置，不是跟著 Phase 重置！所以拆分 Title 既獨立又好維護。',
    sourceRef: 'perter_SCRIPT_11102026（02. RF Phase 5 掛 24 個 Title；08. UF Phase 5 掛 5 個 Title；09. ACOUSTIC Phase 4 掛 6 個 Title）'
  },
  {
    id: 'qa_vars_validation',
    badge: '💾 變數 & 上下限',
    cardTitle: 'Ref 變數 ($ 全域) 與 Validation 上下限怎麼寫？',
    cardHint: '跨 Title 存變數一定要加 $；門檻寫 (變數,%f,下限,上限) 或讀 INI',
    theme: '#FCE7F3',
    accent: '#BE185D',
    chipText: '變數沒加 $ 會怎樣',
    keywords: '變數 ref $ 全域 區域 清空 validation 上下限 門檻 %f %d %s %len ini withinstring rpstring trim substring splitstring',
    directSteps: [
      { col: '存跨區塊變數必加 $', what: 'Ref 欄沒加 $ 的變數，只要進入下一個 Title 就會被系統清空！', ex: '存寫 $VCC_3V3（全域），後面取用一律寫 *(VCC_3V3)（括號內不加 $）' },
      { col: '用冒號接字串擷取函式', what: '一行把雜亂回覆洗乾淨再存起來', ex: '$VER:WithinString,"ver=","\\r","0":rpString," ","":Trim' },
      { col: 'Validation 寫門檻', what: '型別支援 %f (小數) / %d (整數) / %s (字串) / %len (長度)', ex: '(VCC_3V3,%f,3.15,3.45) 或讀 INI：(Temp,%f,*$(T_L),*$(T_H))' }
    ],
    previewCols: ['Title', 'Send', 'Ref', 'Validation', 'ExecMode'],
    highlightCols: ['Ref', 'Validation'],
    sampleRows: [
      { Title: '0,Check FW,3', Send: 'UART@cat /etc/ver\\r\\n', Ref: '$FW:WithinString,"ver=","\\r","0":Trim', Validation: '(FW,%s,*$(FW_VER),)', ExecMode: '1' },
      { Title: '0,Thermal', Send: 'UART@temp\\r\\n', Ref: '$T_VAL', Validation: '(T_VAL,%f,*$(Thermal_L),*$(Thermal_H))', ExecMode: '1' }
    ],
    tip: '⚠️ 站別表內的 *$(變數) 來自 Global.ini [Scripts]，而 DUTs / Instrument 分頁的 *$(變數) 來自 Global.ini [Settings]！',
    sourceRef: 'perter_SCRIPT_11102026（:Trim 2,526次 / :rpString 2,225次 / :WithinString 2,199次 / 單邊省略 (gHW,%s,*$(HWVer),)）'
  },
  {
    id: 'qa_speed_switch_end',
    badge: '⚡ 加速 & 結尾',
    cardTitle: '如何加快測試、多機接線與寫 Phase 97 / 98 / 99？',
    cardHint: 'EndPrompt="#" 秒回加速、Prompt="!" 串流等候、Phase 97 設 ExecMode=3',
    theme: '#F1F5F9',
    accent: '#334155',
    chipText: 'EndPrompt 與 Phase 97 怎麼寫',
    keywords: 'endprompt prompt ! 加速 waiting 超時 switch {1} duts 97 98 99 pwroff 收尾 斷電 utility rini conversion',
    directSteps: [
      { col: 'EndPrompt 填終止字元', what: '收到系統提示符號（如 #）立刻結束該步，不必傻等 5 秒超時', ex: 'Send 寫 UART@ls\\r\\n，EndPrompt 填 #，Cycle Time 直接大減' },
      { col: 'Prompt 寫 "!"', what: '長流程（如燒錄）分好幾段吐出完成字樣時逐段阻塞等待', ex: '搭配 Reply="@File download complete" 等關鍵字' },
      { col: 'Switch 多穴填 {1}', what: '配合 DUTs 欄位 Parameter，一份腳本控制 1~4 台機不同通道', ex: 'Switch 欄填 PPH1503-{1} 或 XelM8-{2},"1:{3}-{4}"' },
      { col: 'Phase 97 / 98 / 99 收尾', what: '98 寫 PASS、99 寫 FAIL，最後無論如何都會跑 97 斷電釋放', ex: 'Phase 97 Title 寫 1,Disconnection，所有收尾步驟 ExecMode=3' }
    ],
    previewCols: ['Phase', 'Title', 'Instrument', 'Send', 'EndPrompt', 'ExecMode'],
    highlightCols: ['Phase', 'EndPrompt', 'ExecMode'],
    sampleRows: [
      { Phase: '2', Title: '0,Read Boot', Instrument: '', Send: 'UART@cat /proc/ver\\r\\n', EndPrompt: '#', ExecMode: '1' },
      { Phase: '97', Title: '1,Disconnection', Instrument: 'OUTONOFF', Send: ':ObtainDevice', EndPrompt: '', ExecMode: '3' },
      { Phase: '', Title: '', Instrument: '', Send: ':Dev.OUTONOFF,"OFF"', EndPrompt: '', ExecMode: '3' },
      { Phase: '', Title: '', Instrument: '', Send: ':ReleaseDevice', EndPrompt: '', ExecMode: '3' }
    ],
    tip: '⚠️ 測試站新增的任何儀器／測項必須排在 Phase 97 之前，否則執行不到或斷電後才執行會誤判。',
    sourceRef: 'perter_SCRIPT_11102026（01. FWDL Prompt="!" 177 次 / 02. RF 97:PWROFF / 09. ACOUSTIC 97-98-99）'
  },
  {
    id: 'qa_taipei_vs_line',
    badge: '📍 台北 vs 產線共用',
    cardTitle: '台北座位（無硬體）與工廠產線怎麼用「同一包程式」切換？',
    cardHint: '用 Title *$(EN_xxx) 開關 + System.ini SFIS/DebugMode + 雙 Station 分頁分離 Mount',
    theme: '#ECFEFF',
    accent: '#0E7490',
    chipText: '台北 vs 產線同一包切換',
    keywords: '台北 產線 共用 一包 切換 座位 工廠 無硬體 沒儀器 除錯 debug sfis mount global.ini system.ini',
    directSteps: [
      { col: '層次①：INI 開關（有 DLL 時）', what: '在 Title 寫 *$(EN_xxx) ＋ ExecMode 寫 *$(AULAB)', ex: '台北：Global.ini 設 EN_LED=2, AULAB=6 / System.ini 設 SFIS_Enable=0, DebugMode=1' },
      { col: '層次②：同檔雙分頁（缺硬體/DLL時）', what: 'Centimani 開機會先讀 Instrument.Mount！在同一個 Excel 建 MB (產線) ＋ MB_TAIPEI (座位)', ex: '把大型機台 Mount 只填 MB 不填 MB_TAIPEI；台北跑 MB_TAIPEI 完全不會報 DLL/Init 錯！' },
      { col: '層次③：免 DLL 外部 Python 控制', what: '能走 CmdConsole@python.exe 呼叫的治具或量測，不必掛進 Instrument 表', ex: '搭配 Title *$(EN_PY)=2/0 直接由 Global.ini 決定台北要不要跑，一包通吃！' }
    ],
    previewCols: ['Phase', 'Title', 'Instrument', 'Send', 'ExecMode'],
    highlightCols: ['Title', 'ExecMode'],
    sampleRows: [
      { Phase: '1', Title: '*$(EN_LED_TEST),Check LED,3', Instrument: 'LED_Test', Send: ':ObtainDevice', ExecMode: '0' },
      { Phase: '98', Title: '1,PASS Upload', Instrument: '', Send: ':autLabs.UnitOut,"*(ISN)","1","PASS"', ExecMode: '*$(AULAB)' }
    ],
    tip: '💡 勾選匯出區的「加入 Global.ini 一鍵開關」即可自動產生 *$(EN_xxx) 並在輸出目錄附上 _編寫與使用說明.txt 供現場查閱！',
    sourceRef: 'perter_SCRIPT_11102026（01. FWDL / 08. UF 多工作表分流 + Global.ini AULAB/RL/TitleStatus 切換架構）'
  }
];

let QA_SELECTED_ID = '';

function qaEscapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function initScriptQaPanel() {
  const input = document.getElementById('qaSearchInput');
  if (input) input.value = '';
  QA_SELECTED_ID = '';
  qaRenderChips();
  qaRenderScenarioGrid();
  qaRenderResults('');
}

function qaSelectScenario(id) {
  QA_SELECTED_ID = id;
  const sc = QA_SCENARIOS.find(s => s.id === id);
  const input = document.getElementById('qaSearchInput');
  if (input && sc) input.value = sc.chipText;
  qaRenderResults(sc ? sc.chipText : '', id);
}

function qaAskQuick(queryText) {
  QA_SELECTED_ID = '';
  const input = document.getElementById('qaSearchInput');
  if (input) input.value = queryText;
  qaRenderResults(queryText);
}

function qaHandleSearchInput() {
  QA_SELECTED_ID = '';
  const input = document.getElementById('qaSearchInput');
  qaRenderResults(input ? input.value : '');
}

function qaRenderChips() {
  const box = document.getElementById('qaQuickChips');
  if (!box) return;
  const chipIds = ['qa_retry_where', 'qa_pause_skip', 'qa_instrument_once', 'qa_multi_title', 'qa_taipei_vs_line'];
  box.innerHTML = chipIds.map(id => QA_SCENARIOS.find(s => s.id === id)).filter(Boolean).map(s => `
    <button type="button" class="btn qa-chip-btn"
      onclick="qaSelectScenario('${s.id}')"
      style="padding:4px 10px; font-size:0.82rem; font-weight:700; border-radius:999px; background:#F8FAFC; border:1px solid #CBD5E1; color:#334155;">
      ${qaEscapeHtml(s.chipText)}
    </button>
  `).join('');
}

function qaRenderScenarioGrid() {
  const grid = document.getElementById('qaScenarioGrid');
  if (!grid) return;
  grid.innerHTML = QA_SCENARIOS.map(s => `
    <div onclick="qaSelectScenario('${s.id}')" class="qa-feature-tile"
      style="background:#FFFFFF; border:1.5px solid #CBD5E1; border-top:4px solid ${s.accent}; border-radius:10px; padding:12px 14px; cursor:pointer; display:flex; flex-direction:column; justify-content:space-between; gap:6px;">
      <div>
        <span style="display:inline-block; background:${s.theme}; color:${s.accent}; font-size:0.78rem; font-weight:800; padding:2px 8px; border-radius:999px; margin-bottom:6px;">${qaEscapeHtml(s.badge)}</span>
        <div style="font-weight:900; font-size:0.95rem; color:#0F172A; line-height:1.35;">${qaEscapeHtml(s.cardTitle)}</div>
      </div>
      <div style="font-size:0.83rem; color:#475569; line-height:1.45;">👉 ${qaEscapeHtml(s.cardHint)}</div>
    </div>
  `).join('');
}

function _qaScoreScenario(sc, rawQuery) {
  const q = (rawQuery || '').trim().toLowerCase();
  if (!q) return 0;

  const aliases = [
    ['retry', '重試', '重測', '次數', '幾次', '哪裡', '改', '跳轉', '退回', '回溯', '2:0', '4:', 'execmode'],
    ['暫停', '停用', '跳過', '略過', '關閉', '不測', '註解', 'pause', 'skip', '-1', 'disable', '6'],
    ['instrument', '留空', '重複', '連續', '寫一次', '寫幾次', 'obtaindevice', 'releasedevice', 'subdevice'],
    ['多個', '共用', '合併', '底下', '下面', 'phase', 'title'],
    ['變數', '全域', '區域', '清空', '$', 'validation', '上下限', '門檻', 'withinstring', 'rpstring', 'trim'],
    ['endprompt', 'prompt', '!', '加速', '超時', '97', '98', '99', 'pwroff', '收尾', '斷電', 'switch', '{1}'],
    ['台北', '產線', '共用', '一包', '切換', '無硬體', '沒儀器', '座位', '工廠', 'debug', 'sfis']
  ];

  const tokens = new Set(q.split(/[\s,，。？?、/]+/).filter(Boolean));
  aliases.forEach(grp => {
    if (grp.some(w => q.includes(w))) {
      grp.forEach(w => tokens.add(w));
    }
  });

  const hay = [
    sc.cardTitle, sc.cardHint, sc.chipText, sc.keywords,
    sc.directSteps.map(d => d.col + ' ' + d.what + ' ' + d.ex).join(' '),
    sc.tip
  ].join(' ').toLowerCase();

  let score = 0;
  if (hay.includes(q)) score += 80;
  tokens.forEach(tok => {
    if (sc.chipText.toLowerCase().includes(tok)) score += 30;
    if (sc.cardTitle.toLowerCase().includes(tok)) score += 25;
    if (sc.keywords.toLowerCase().includes(tok)) score += 18;
    if (hay.includes(tok)) score += 6;
  });
  return score;
}

function qaCopyTsv(id) {
  const sc = QA_SCENARIOS.find(s => s.id === id);
  if (!sc || !sc.sampleRows) return;
  const cols = ['Index', 'Phase', 'Title', 'Marco', 'Instrument', 'Switch', 'Send', 'Reply', 'EndPrompt', 'Ref', 'Validation', 'Prompt', 'Waiting', 'ExecMode', 'Description', 'TestID'];
  const lines = sc.sampleRows.map(r => cols.map(c => String(r[c] ?? '').replace(/\n/g, ' ')).join('\t'));
  const tsv = lines.join('\n');
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(tsv).then(() => {
      const btn = document.getElementById('qaCopyBtn_' + id);
      if (btn) {
        const old = btn.textContent;
        btn.textContent = '✅ 已複製（貼入 Excel 即對應欄位）';
        setTimeout(() => { btn.textContent = old; }, 2000);
      }
    }).catch(() => alert(tsv));
  } else {
    alert(tsv);
  }
}

function qaRenderResults(rawQuery, forcedId) {
  const gridWrap = document.getElementById('qaScenarioGridWrap');
  const resBox = document.getElementById('qaResultsList');
  if (!resBox) return;

  const q = (rawQuery || '').trim();
  if (!q && !forcedId) {
    if (gridWrap) gridWrap.style.display = 'block';
    resBox.innerHTML = '';
    return;
  }

  let matched = [];
  if (forcedId) {
    const sc = QA_SCENARIOS.find(s => s.id === forcedId);
    if (sc) matched = [sc];
  } else {
    matched = QA_SCENARIOS
      .map(sc => ({ sc, score: _qaScoreScenario(sc, q) }))
      .filter(x => x.score >= 12)
      .sort((a, b) => b.score - a.score)
      .map(x => x.sc);
  }

  if (gridWrap) gridWrap.style.display = 'none';

  if (!matched.length) {
    resBox.innerHTML = `
      <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:14px 16px; color:#92400E; font-size:0.9rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <span>找不到符合「<b>${qaEscapeHtml(q)}</b>」的條目，請試著輸入 <code>retry 哪裡改</code>、<code>暫停 Phase</code>、<code>Instrument</code>、<code>Title</code>、<code>$</code>，或點選下方「全部 6 大常見情境」。</span>
        <button type="button" onclick="qaAskQuick('')" class="btn" style="padding:6px 12px; font-size:0.84rem; background:#FFFFFF;">⬅ 回 6 大常見情境</button>
      </div>
    `;
    return;
  }

  resBox.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
      <span style="font-weight:900; font-size:0.93rem; color:#312E81;">🎯 直接解答：${qaEscapeHtml(q)}（共 ${matched.length} 筆最相關方案，越上面越符合）</span>
      <button type="button" onclick="qaAskQuick('')" class="btn" style="padding:5px 12px; font-size:0.83rem; font-weight:800; background:#F1F5F9; border:1px solid #CBD5E1;">⬅ 回 6 大常見情境</button>
    </div>
  ` + matched.map((sc, idx) => `
    <div style="background:#FFFFFF; border:${idx === 0 ? '2px solid ' + sc.accent : '1px solid #CBD5E1'}; border-radius:12px; padding:14px 16px; margin-bottom:12px; box-shadow:0 3px 10px rgba(15,23,42,0.06);">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="background:${sc.theme}; color:${sc.accent}; font-weight:800; font-size:0.8rem; padding:2px 9px; border-radius:999px;">${qaEscapeHtml(sc.badge)}</span>
          <span style="font-weight:900; font-size:1.05rem; color:#0F172A;">${qaEscapeHtml(sc.cardTitle)}</span>
        </div>
        <button id="qaCopyBtn_${sc.id}" type="button" class="btn" onclick="qaCopyTsv('${sc.id}')"
          style="padding:5px 11px; font-size:0.81rem; font-weight:800; background:#EEF2FF; color:#3730A3; border:1px solid #C7D2FE; border-radius:7px;">
          📋 複製整段範例到 Excel
        </button>
      </div>

      <!-- 一眼看懂：改哪一格 -> 怎麼填 -->
      <div style="display:flex; flex-direction:column; gap:7px; margin-bottom:12px;">
        ${sc.directSteps.map(st => `
          <div style="display:flex; align-items:flex-start; gap:10px; flex-wrap:wrap; background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid ${sc.accent}; border-radius:8px; padding:8px 12px;">
            <span style="background:${sc.theme}; color:${sc.accent}; font-weight:900; font-size:0.83rem; padding:2px 8px; border-radius:6px; white-space:nowrap;">${qaEscapeHtml(st.col)}</span>
            <div style="flex:1; min-width:220px; font-size:0.87rem; color:#1E293B; line-height:1.5;">
              <b>${qaEscapeHtml(st.what)}</b>
              <div style="font-family:Consolas, 'Microsoft JhengHei UI', monospace; font-size:0.83rem; color:#0F172A; margin-top:2px;">➔ ${qaEscapeHtml(st.ex)}</div>
            </div>
          </div>
        `).join('')}
      </div>

      <!-- 只顯示關鍵 3~5 欄的精簡 Excel 示範表 -->
      <div style="font-size:0.81rem; font-weight:800; color:#475569; margin-bottom:5px;">📊 Excel 對照位置（僅顯示有關的 ${sc.previewCols.length} 個欄位，黃底＝重點修改格）：</div>
      <div style="overflow-x:auto; border:1px solid #CBD5E1; border-radius:8px; margin-bottom:8px;">
        <table style="width:100%; border-collapse:collapse; font-size:0.82rem; font-family:Consolas, 'Microsoft JhengHei UI', monospace;">
          <thead>
            <tr style="background:#1E293B; color:#FFFFFF;">
              ${sc.previewCols.map(c => `<th style="padding:6px 9px; text-align:left; border-right:1px solid #334155; white-space:nowrap;">${qaEscapeHtml(c)}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${sc.sampleRows.map((row, rIdx) => `
              <tr style="background:${rIdx % 2 === 0 ? '#FFFFFF' : '#F8FAFC'}; border-top:1px solid #E2E8F0;">
                ${sc.previewCols.map(c => {
                  const val = String(row[c] ?? '');
                  const isHi = sc.highlightCols.includes(c) && val !== '';
                  return `<td style="padding:6px 9px; border-right:1px solid #E2E8F0; white-space:pre-wrap; ${isHi ? 'background:#FEF9C3; color:#92400E; font-weight:900;' : 'color:#334155;'}">${val === '' ? '<span style="color:#CBD5E1;">(留空)</span>' : qaEscapeHtml(val)}</td>`;
                }).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>

      <div style="font-size:0.82rem; color:#92400E; background:#FFFBEB; border:1px solid #FDE68A; border-radius:7px; padding:6px 10px; margin-bottom:4px;">${qaEscapeHtml(sc.tip)}</div>
      <div style="font-size:0.78rem; color:#64748B;">📂 來源依據：${qaEscapeHtml(sc.sourceRef)}</div>
    </div>
  `).join('');
}
