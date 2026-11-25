// =========================================================================
// Centimani Studio - 0 -> 1 Visual Drag-and-Drop Block Builder + Q&A Stepper
// =========================================================================
(function () {
  const BUILDER_CATALOG = [
    {
      kind: 'comm_cmd',
      name: '💬 指令擷取',
      tier: 'common',
      exclusivePage: false,
      theme: '#EFF6FF',
      border: '#3B82F6',
      popTitle: '下指令與回傳字串擷取 (UART / ADB / SSH / CMD)',
      popDesc: '透過 UART / SSH / ADB / CMD / Telnet 對待測物下指令，可設定只檢查關鍵字（如 PASS），或直接貼上 Console 吐出的長字串、自動產生 WithinString / SplitString 擷取數值與上下限比對。',
      popExample: '例：UART@cat /etc/version ➔ 自動擷取版本號比對'
    },
    {
      kind: 'delay',
      name: '⏳ 延遲等待',
      tier: 'common',
      exclusivePage: false,
      theme: '#F0FDF4',
      border: '#22C55E',
      popTitle: '時間等待 (:Delay)',
      popDesc: '在兩個動作之間插入固定等待時間（輸入毫秒會自動換算為等幾秒），例如等待開機、放電或治具穩定，可依需要加入多塊。',
      popExample: '例：2000 ms（自動解讀為等 2 秒）'
    },
    {
      kind: 'inst',
      name: '🧪 儀器測試',
      tier: 'common',
      exclusivePage: true,
      theme: '#FEF2F2',
      border: '#EF4444',
      popTitle: '🔴 專屬設定頁｜外接儀器量測控制',
      popDesc: '整合全部 40+ 款實機儀器（電源供應器、NI-6008 電壓卡、萬用電表、IQxel RF、FeasaLED 等）。點入後進入專屬儀器選擇與 DL/UL 設定頁，可重複加入多台不同儀器。',
      popExample: '例：NI6008 量測多通道電壓 / Agilent34401A / PPH1503'
    },
    {
      kind: 'multi_sku',
      name: '🎯 品種分流',
      tier: 'common',
      exclusivePage: true,
      theme: '#FEF2F2',
      border: '#EF4444',
      popTitle: '🔴 專屬設定頁｜多 SKU / 衍生品分流 (4:P,F)',
      popDesc: '依 SFIS 欄位、工單名單 (69MO.txt) 或國別碼自動分流不同機種，決定哪些測項要跑或套用不同 DL/UL 上下限，並自動寫入 Global.ini 與雙色視覺底色。',
      popExample: '例：整機 / 無電池 / 無 WiFi 三分支分流＋測項閘門'
    },
    {
      kind: 'var_check',
      name: '🔍 數值檢查',
      tier: 'common',
      exclusivePage: false,
      theme: '#ECFEFF',
      border: '#06B6D4',
      popTitle: '變數運算與門檻檢查 (:GetVal / :CheckLimit)',
      popDesc: '拿前面步驟擷取下來的 $變數 做數值上下限判斷 (:CheckLimit) 或字串比對 (:GetVal)，常搭配儀器量測或字串擷取後進行 PASS / FAIL 驗算。',
      popExample: '例：:CheckLimit,"*(VCC_3V3)","3.15","3.45","%f"'
    },
    {
      kind: 'prompt_box',
      name: '🙋 人工確認',
      tier: 'common',
      exclusivePage: false,
      theme: '#FFFBEB',
      border: '#F59E0B',
      popTitle: '作業員提示視窗與 YES/NO 確認 (:ShowConfirmBox)',
      popDesc: '跳出視窗引導產線作業員動作（插拔線材、按 Reset 鍵、確認 LED 燈色）。支援「單顆 OK 確認」、「YES / NO 雙按鈕（選 No 判 FAIL 或跳分支）」以及「輸入框掃副條碼」。',
      popExample: '例：:ShowConfirmBox,"請確認藍燈是否亮起?","Yes;No"'
    },
    {
      kind: 'fixture',
      name: '🤖 治具控制',
      tier: 'common',
      exclusivePage: false,
      theme: '#F8FAFC',
      border: '#64748B',
      popTitle: '氣動治具下壓與電源控制',
      popDesc: '設定氣動治具 COM Port (UARTF) 下壓延遲，或使用 iPower 電源控制開關上電。如果本測試站沒有治具，選擇「無治具」或不加入此積木即可。',
      popExample: '例：UARTF@G 壓下治具並等待 3000ms 上電'
    },
    {
      kind: 'sfis_rw',
      name: '🔐 過站讀寫',
      tier: 'common',
      exclusivePage: false,
      theme: '#FDF2F8',
      border: '#EC4899',
      popTitle: 'SFIS 讀取欄位 / 寫回 LinkData / 刷副條碼',
      popDesc: '從 SFIS 讀取 MAC1 / 69PN / SNA (:SfGetVersion / :SfGetiMAC)、寫回測試值至 SFIS (:SfSaveLinkData)，或讓作業員掃描第二個條碼比對長度。',
      popExample: '例：:SfGetVersion,"*(ISN)","ISN_BASEINFO","2","MAC1",""'
    },
    {
      kind: 'python',
      name: '🐍 外部腳本',
      tier: 'common',
      exclusivePage: false,
      theme: '#F0FDF4',
      border: '#16A34A',
      popTitle: '呼叫外部 Python / Code 腳本 (.py)',
      popDesc: '透過 Windows CmdConsole 執行外部 python.exe 程式（免撰寫 C# DLL），並透過 WithinString 擷取終端機 print() 印出的數值進行上下限比對。',
      popExample: '例：python.exe my_test.py "*(ISN)" ➔ 抓 RESULT='
    },
    {
      kind: 'ping',
      name: '🌐 Ping測試',
      tier: 'common',
      exclusivePage: false,
      theme: '#EFF6FF',
      border: '#0EA5E9',
      popTitle: '網路連通性 Ping 測試 (:Utility.Ping)',
      popDesc: '呼叫 Centimani 內建 :Utility.Ping 指定待測物 IP (DUTIP) 與電腦網卡 IP (PCIP)，快速驗證 Ethernet / WiFi 連線通暢。',
      popExample: '例：:Utility.Ping,"192.168.11.143","5000","192.168.11.3"'
    },
    // Advanced blocks (hidden behind checkbox)
    {
      kind: 'ext_file',
      name: '📄 讀外部檔',
      tier: 'advanced',
      exclusivePage: false,
      theme: '#F8FAFC',
      border: '#64748B',
      popTitle: '讀取外部 INI / TXT (:Utility.Rini / Rtxt)',
      popDesc: '從本機外部設定檔或工單對照表讀取數值到變數中，適合需要讀取外部參考表或測試組態的進階站別。',
      popExample: '例：:Utility.Rini,".\\System\\config.ini","Scripts","Key"'
    },
    {
      kind: 'usb_fw',
      name: '🔌 升級抓埠',
      tier: 'advanced',
      exclusivePage: false,
      theme: '#F8FAFC',
      border: '#64748B',
      popTitle: 'USB 燒錄與動態抓 COM Port',
      popDesc: '使用 Utility.CMD 執行 USB 下載工具並搭配 GetChainCOM 自動取得動態分配的 COM Port 號碼。',
      popExample: '例：Download 站 USB 燒錄自動偵測 Port'
    },
    {
      kind: 'subdev_finalgo',
      name: '🔗 四槽同步',
      tier: 'advanced',
      exclusivePage: false,
      theme: '#F8FAFC',
      border: '#64748B',
      popTitle: '多槽共用治具與 FinalGo 同步柵欄',
      popDesc: '實戰 1 拖 4 站別使用 :ObtainSubDevice("DevUart") 搭配 :InitFinalGo / :CheckFinalGo 同步四個測試槽位進度。',
      popExample: '例：四槽同步觸發共享治具繼電器'
    },
    {
      kind: 'sfis_bypass',
      name: '🔀 雙模旁路',
      tier: 'advanced',
      exclusivePage: false,
      theme: '#F8FAFC',
      border: '#64748B',
      popTitle: ':SfEnabled 雙路線自動旁路',
      popDesc: '自動建立 :SfEnabled ExecMode=4:P,F 分支：產線連線跑 SFIS 取值，實驗室離線時自動改用預設值不擋測。',
      popExample: '例：:SfEnabled (Reply=1, EM=4:1,3) 自動切換離線預設值'
    },
    {
      kind: 'stream_flash',
      name: '📡 串流燒錄',
      tier: 'advanced',
      exclusivePage: false,
      theme: '#F8FAFC',
      border: '#64748B',
      popTitle: '長輸出串流燒錄範本 (Prompt="!")',
      popDesc: '針對會不斷吐出進度字元（如 ! 或進度條）的長耗時燒錄指令，使用 Prompt="!" 防止超時誤判與重試。',
      popExample: '例：大檔韌體燒錄長輸出監控'
    }
  ];

  const META_BY_KIND = {
    isn: {
      kind: 'isn',
      name: '🔢 條碼站名',
      fixed: true,
      exclusivePage: false,
      theme: '#EFF6FF',
      border: '#2563EB',
      popTitle: '專案名稱、測試站與 ISN 條碼規格（固定開頭）',
      popDesc: '設定此 Excel 測試包的 Project 名稱、Station 名稱、槽位數 (1/2/4 槽) 與條碼掃描位數（幾 Byte）和字元規則。',
    },
    sfis_route: {
      kind: 'sfis_route',
      name: '🛡️ 路由檢查',
      fixed: false,
      exclusivePage: false,
      theme: '#FDF2F8',
      border: '#DB2777',
      popTitle: '開局條碼顯示與 SFIS CheckRoute (Phase 0)',
      popDesc: '顯示掃入的 ISN、清空殘留 COM Port 並執行 :SfCheckRoute 確認路由。在問答頁可選擇「工程離線調試」或「產線實機過站」。',
    },
    teardown: {
      kind: 'teardown',
      name: '🛑 安全收尾',
      fixed: true,
      exclusivePage: false,
      theme: '#FFF1F2',
      border: '#E11D48',
      popTitle: 'Phase 97/98 安全斷電與資源釋放（固定壓底）',
      popDesc: '無論前方測項 PASS 或 FAIL 都必跑的安全保護區 (ExecMode=3)：自動斷電、治具復位、關閉所有 COM Port，並可加開 Phase 98 PASS / Phase 99 FAIL 分流。',
    }
  };
  BUILDER_CATALOG.forEach((b) => { META_BY_KIND[b.kind] = b; });

  function _esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _formatMsReadable(rawMs) {
    const n = Number(rawMs);
    if (!Number.isFinite(n) || n <= 0) return '請輸入正數毫秒';
    if (n >= 60000) {
      const mins = Math.floor(n / 60000);
      const remSec = Number(((n % 60000) / 1000).toFixed(2));
      return remSec > 0 ? `等 ${mins} 分 ${remSec} 秒` : `等 ${mins} 分鐘`;
    }
    const sec = Number((n / 1000).toFixed(3));
    return `等 ${sec} 秒`;
  }
  window.bbFormatMsReadable = _formatMsReadable;

  let _uidSeq = 1;
  function _newUid() { return 'blk_' + (_uidSeq++); }

  function _defaultConfigForKind(kind) {
    switch (kind) {
      case 'isn':
        return { project: 'PEGA_NEW', station: 'MB', dut_count: 1, isn_len: 3, isn_pattern: '[0-9A-Z]' };
      case 'sfis_route':
        return { sfis_mode: 'offline', tsp: 'PEGA,2', weblink: 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx', login_id: '', date_isn: '111111111111111' };
      case 'comm_cmd':
        return {
          protocol: 'uart', title: 'Check UART & FW Version', port: 'COM4', ssh_user: 'root', ssh_pass: '', dut_ip: '192.168.11.143',
          command: 'cat /etc/version', end_prompt: '#', waiting: '5000', retry: '3',
          extract_mode: 'within', reply_keyword: 'PASS',
          sample_log: 'root@DUT:~# cat /etc/version\nFW version=1.0.0_release\nroot@DUT:~#',
          left_delim: 'version=', right_delim: '\\n', split_sep: ':', split_idx: '1', sub_start: '0', sub_len: '8',
          var_name: 'DUT_FW', val_type: '%s', expect_min: '1.0.0_release', expect_max: '', use_ini_var: false
        };
      case 'delay':
        return { ms: '2000', note: '等待開機與供電穩定' };
      case 'prompt_box':
        return { prompt_mode: 'yes_no', title: 'Operator Confirm', message: '請確認待測物藍燈是否正常亮起？', ok_label: '好(OK)', yes_label: 'Yes', no_label: 'No', no_policy: 'fail', var_name: 'ScanSub', min_len: '1', max_len: '32' };
      case 'var_check':
        return { title: 'Check Limit', var_name: 'VCC_3V3', check_mode: 'limit', val_type: '%f', dl: '3.15', ul: '3.45', expect_str: 'PASS', use_ini_var: false };
      case 'inst':
        return {
          inst_mode: 'catalog', inst_name: 'NI6008', title_name: 'Measure Voltage Test', dl_val: '3.15', ul_val: '3.45',
          mode: 'RSE', sample_ms: '1000', dev_id: 'Dev1',
          channels: [{ ch: 0, name: 'VCC_5V', dl: '4.75', ul: '5.25' }, { ch: 1, name: 'VCC_3V3', dl: '3.15', ul: '3.45' }],
          settings_str: '192.168.100.254,1,2,1,60000,PathLoss.ini',
          tx_tests: [{ channel: '6', bw: '20', mcs: '7', antenna: '1', target_pwr: '15', pwr_min: '13', pwr_max: '17', evm_min: '-50', evm_max: '-28' }],
          rx_tests: [{ channel: '6', bw: '20', mcs: '7', antenna: '1', rx_level: '-59' }]
        };
      case 'multi_sku':
        return { sku_wizard: null };
      case 'fixture':
        return { fixture_type: 'none', com_port: 'COM8', delay_ms: '3000' };
      case 'sfis_rw':
        return { rw_mode: 'get_version', title: 'SFIS Get MAC', table_name: 'ISN_BASEINFO', field_name: 'MAC1', var_name: 'sfMAC', label_len: '12', save_value: '*(sfMAC)' };
      case 'python':
        return { python_path: 'D:\\PythonScript', script_name: 'my_test.py', result_prefix: 'RESULT=', min_val: '0.0', max_val: '100.0' };
      case 'ping':
        return { dut_ip: '192.168.11.143', pc_ip: '192.168.11.3', timeout_ms: '5000' };
      case 'ext_file':
        return { file_mode: 'rini', file_path: '.\\System\\config.ini', section: 'Scripts', key: 'TargetKey', var_name: 'gExtVal' };
      case 'teardown':
        return { teardown_mode: '97_only' };
      default:
        return {};
    }
  }

  const BB_STATE = {
    view: 'stack', // 'stack' | 'qa' | 'export'
    showAdvanced: false,
    fullscreen: false,
    splitLeftPx: 235,
    qaIdx: 0,
    dragSrcType: null, // 'palette' | 'stack'
    dragKind: null,
    dragStackIdx: -1,
    catalogInsts: null,
    stack: [
      { uid: _newUid(), kind: 'isn', configured: true, config: _defaultConfigForKind('isn') },
      { uid: _newUid(), kind: 'sfis_route', configured: false, config: _defaultConfigForKind('sfis_route') },
      { uid: _newUid(), kind: 'comm_cmd', configured: false, config: _defaultConfigForKind('comm_cmd') },
      { uid: _newUid(), kind: 'teardown', configured: false, config: _defaultConfigForKind('teardown') }
    ],
    exportOpts: {
      station_name_mode: 'fixed',
      no_hw_phase_pause: false
    }
  };
  window.BB_STATE = BB_STATE;

  function _summarizeBlock(item) {
    const c = item.config || {};
    switch (item.kind) {
      case 'isn':
        return `${c.project || 'PEGA_NEW'}/${c.station || 'MB'} · ${c.isn_len || 3}碼`;
      case 'sfis_route':
        return c.sfis_mode === 'online' ? `線上(${c.tsp || 'PEGA,2'})` : '工程離線';
      case 'comm_cmd':
        return `${String(c.protocol || 'uart').toUpperCase()}@${(c.command || '').slice(0, 16)}`;
      case 'delay':
        return `${c.ms || 2000}ms (${_formatMsReadable(c.ms || 2000)})`;
      case 'prompt_box':
        if (c.prompt_mode === 'yes_no') return `YES/NO (${c.no_policy === 'branch' ? '分支' : c.no_policy === 'retry' ? '重試' : 'No判FAIL'})`;
        if (c.prompt_mode === 'input') return `輸入 $${c.var_name || 'ScanSub'}`;
        return `單鈕確認`;
      case 'var_check':
        return c.check_mode === 'string' ? `$${c.var_name}=${c.expect_str}` : `$${c.var_name}(${c.dl}~${c.ul})`;
      case 'inst':
        if (c.inst_mode === 'ni6009') return `NI-6008 (${(c.channels || []).length}通道)`;
        if (c.inst_mode === 'rf') return `${c.inst_name || 'IQxel'} RF`;
        return `${c.inst_name || '未選儀器'}`;
      case 'multi_sku': {
        const sk = c.sku_wizard || (window.STATE && window.STATE.createSkuConfig);
        return (sk && sk.enabled) ? `${(sk.sku_branches || []).length} 支 SKU` : '待設定';
      }
      case 'fixture':
        return c.fixture_type === 'none' ? '無治具' : (c.fixture_type === 'ipower' ? `iPower ${c.delay_ms}ms` : `${c.com_port} ${c.delay_ms}ms`);
      case 'sfis_rw':
        return `${c.field_name || 'MAC1'}`;
      case 'python':
        return `${c.script_name || 'my_test.py'}`;
      case 'ping':
        return `${c.dut_ip || '192.168.11.143'}`;
      case 'ext_file':
        return `${c.key || c.file_path || ''}`;
      case 'teardown':
        return c.teardown_mode === '97_98_99' ? '97 + 98/99 分流' : 'Phase 97 斷電';
      default:
        return '標準模板';
    }
  }

  function _ensureStylesAndPop() {
    if (!document.getElementById('bbStyles')) {
      const st = document.createElement('style');
      st.id = 'bbStyles';
      st.textContent = `
        .bb-fullscreen-shell { position:fixed !important; inset:10px !important; z-index:950 !important; background:#F8FAFC !important; border:2px solid #2563EB !important; border-radius:12px !important; padding:14px !important; overflow-y:auto !important; box-shadow:0 24px 64px rgba(15,23,42,0.45) !important; }
        .bb-split-container { display:flex; align-items:stretch; gap:0; min-height:430px; }
        .bb-left-pane { flex:0 0 auto; background:#FFFFFF; border:1.5px solid #CBD5E1; border-radius:10px; padding:10px; box-sizing:border-box; overflow-y:auto; max-height:68vh; }
        .bb-splitter { flex:0 0 10px; cursor:col-resize; display:flex; align-items:center; justify-content:center; user-select:none; transition:background 0.12s; border-radius:6px; margin:0 2px; }
        .bb-splitter:hover, .bb-splitter.dragging { background:#BAE6FD; }
        .bb-splitter-bar { width:3px; height:44px; border-radius:999px; background:#94A3B8; }
        .bb-right-pane { flex:1 1 0%; min-width:260px; background:#F8FAFC; border:1.5px solid #93C5FD; border-radius:10px; padding:10px 12px; box-sizing:border-box; display:flex; flex-direction:column; justify-content:space-between; }
        .bb-palette-list { display:flex; flex-direction:column; gap:5px; }
        /* 統一積木尺寸：左欄與右欄積木維持一致緊湊高度 */
        .bb-uniform-brick { height:38px; min-height:38px; box-sizing:border-box; border-radius:7px; padding:0 8px; border:1.5px solid #CBD5E1; background:#FFFFFF; display:flex; align-items:center; justify-content:space-between; gap:6px; transition:all 0.14s ease; user-select:none; }
        .bb-uniform-brick.palette-item { cursor:grab; }
        .bb-uniform-brick:hover { background:#E0F2FE; border-color:#38BDF8; }
        .bb-uniform-brick.is-red { background:#FEF2F2; border-color:#EF4444; }
        .bb-uniform-brick.is-red:hover { background:#FEE2E2; border-color:#DC2626; }
        .bb-uniform-brick.is-fixed { background:#F1F5F9; border-style:dashed; }
        .bb-plus-btn { width:26px; height:24px; padding:0; border-radius:5px; border:1px solid #94A3B8; background:#F8FAFC; color:#0F172A; font-weight:900; font-size:0.95rem; line-height:1; cursor:pointer; flex-shrink:0; transition:all 0.12s; }
        .bb-plus-btn:hover { background:#2563EB; border-color:#1D4ED8; color:#FFFFFF; }
        .bb-uniform-brick.is-red .bb-plus-btn { border-color:#FCA5A5; color:#991B1B; background:#FFFFFF; }
        .bb-uniform-brick.is-red .bb-plus-btn:hover { background:#DC2626; border-color:#991B1B; color:#FFFFFF; }
        .bb-drop-slot { height:6px; border-radius:5px; transition:all 0.14s ease; border:1.5px dashed transparent; }
        .bb-drop-slot.drag-over { height:24px; background:#DBEAFE; border-color:#2563EB; }
        .bb-bottom-dock { margin-top:14px; padding-top:12px; border-top:1.5px solid #CBD5E1; display:flex; flex-direction:column; gap:10px; }
        .bb-progress-strip { display:flex; align-items:stretch; gap:6px; overflow-x:auto; padding:8px 10px; background:#F1F5F9; border:1.5px solid #CBD5E1; border-radius:10px; }
        .bb-step-pill { min-width:94px; max-width:140px; flex:1 0 auto; border-radius:8px; padding:6px 8px; border:1.5px solid #94A3B8; background:#FFFFFF; cursor:pointer; transition:all 0.18s ease; text-align:left; filter:grayscale(100%); opacity:0.65; }
        .bb-step-pill:hover { opacity:0.92; filter:grayscale(35%); background:#E2E8F0; }
        .bb-step-pill.active { filter:none !important; opacity:1 !important; transform:translateY(-2px); border:2px solid #2563EB; background:#DBEAFE; box-shadow:0 4px 12px rgba(37,99,235,0.22); }
        .bb-step-pill.active.is-red { border-color:#DC2626; background:#FEE2E2; box-shadow:0 4px 12px rgba(220,38,38,0.22); }
        #bbPopWindow { position:fixed; z-index:1200; max-width:320px; background:#0F172A; color:#F8FAFC; border:1.5px solid #38BDF8; border-radius:10px; padding:10px 12px; box-shadow:0 12px 32px rgba(15,23,42,0.45); pointer-events:none; display:none; font-size:0.82rem; line-height:1.5; }
      `;
      document.head.appendChild(st);
    }
    if (!document.getElementById('bbPopWindow')) {
      const pop = document.createElement('div');
      pop.id = 'bbPopWindow';
      document.body.appendChild(pop);
    }
  }

  window.bbStartSplitDrag = function (ev) {
    ev.preventDefault();
    const splitter = ev.currentTarget;
    if (splitter) splitter.classList.add('dragging');
    const leftPane = document.getElementById('bbLeftPane');
    const container = document.getElementById('bbSplitContainer');
    const startX = ev.clientX;
    const startW = leftPane ? leftPane.getBoundingClientRect().width : BB_STATE.splitLeftPx;
    const maxW = container ? Math.max(260, container.getBoundingClientRect().width - 280) : 520;

    const onMove = (me) => {
      const nextW = Math.max(175, Math.min(maxW, Math.round(startW + (me.clientX - startX))));
      BB_STATE.splitLeftPx = nextW;
      if (leftPane) leftPane.style.width = nextW + 'px';
    };
    const onUp = () => {
      if (splitter) splitter.classList.remove('dragging');
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  window.bbShowPop = function (evt, kind) {
    _ensureStylesAndPop();
    const meta = META_BY_KIND[kind];
    const pop = document.getElementById('bbPopWindow');
    if (!meta || !pop) return;
    pop.innerHTML = `
      <div style="font-weight:900; font-size:0.88rem; color:${meta.exclusivePage ? '#FCA5A5' : '#7DD3FC'}; margin-bottom:4px;">${_esc(meta.popTitle || meta.name)}</div>
      <div style="color:#E2E8F0; margin-bottom:5px;">${_esc(meta.popDesc || '')}</div>
      ${meta.popExample ? `<div class="mono" style="background:#1E293B; color:#FDE047; padding:4px 7px; border-radius:5px; font-size:0.76rem;">${_esc(meta.popExample)}</div>` : ''}
    `;
    pop.style.display = 'block';
    const x = Math.min((evt.clientX || 200) + 14, window.innerWidth - 340);
    const y = Math.min((evt.clientY || 200) + 14, window.innerHeight - 160);
    pop.style.left = Math.max(10, x) + 'px';
    pop.style.top = Math.max(10, y) + 'px';
  };

  window.bbHidePop = function () {
    const pop = document.getElementById('bbPopWindow');
    if (pop) pop.style.display = 'none';
  };

  async function _ensureCatalogLoaded() {
    if (BB_STATE.catalogInsts) return;
    try {
      const res = await fetch('/api/instrument_catalog');
      const d = await res.json();
      if (d && Array.isArray(d.instruments)) BB_STATE.catalogInsts = d.instruments;
    } catch (_e) {
      BB_STATE.catalogInsts = [];
    }
  }

  function _syncCompatInputsFromIsnBlock() {
    const isnBlk = BB_STATE.stack.find(b => b.kind === 'isn');
    if (!isnBlk) return;
    const c = isnBlk.config || {};
    const elProj = document.getElementById('genProj');
    const elSt = document.getElementById('genStation');
    const elDut = document.getElementById('genDutCount');
    const elLen = document.getElementById('genIsnLen');
    const elPat = document.getElementById('genIsnPattern');
    if (elProj) elProj.value = c.project || 'PEGA_NEW';
    if (elSt) elSt.value = c.station || 'MB';
    if (elDut) elDut.value = String(c.dut_count || 1);
    if (elLen) elLen.value = String(c.isn_len || 3);
    if (elPat) elPat.value = c.isn_pattern || '[0-9A-Z]';
    if (typeof window.updateIsnRulePreview === 'function') window.updateIsnRulePreview();
  }

  function _insertBlockAt(kind, insertPos) {
    const cfg = _defaultConfigForKind(kind);
    const newItem = { uid: _newUid(), kind, configured: false, config: cfg };
    const maxPos = Math.max(1, BB_STATE.stack.length - 1);
    const safePos = Math.max(1, Math.min(insertPos, maxPos));
    BB_STATE.stack.splice(safePos, 0, newItem);
    bbRender();
  }

  window.bbAddBlock = function (kind) {
    _insertBlockAt(kind, BB_STATE.stack.length - 1);
  };

  window.bbRemoveStackIdx = function (idx) {
    const item = BB_STATE.stack[idx];
    if (!item) return;
    const meta = META_BY_KIND[item.kind];
    if (meta && meta.fixed) return;
    BB_STATE.stack.splice(idx, 1);
    if (BB_STATE.qaIdx >= BB_STATE.stack.length) BB_STATE.qaIdx = Math.max(0, BB_STATE.stack.length - 1);
    bbRender();
  };

  window.bbMoveStackIdx = function (idx, delta) {
    const target = idx + delta;
    if (target < 1 || target >= BB_STATE.stack.length - 1) return;
    const item = BB_STATE.stack[idx];
    if (!item || (META_BY_KIND[item.kind] && META_BY_KIND[item.kind].fixed)) return;
    BB_STATE.stack.splice(idx, 1);
    BB_STATE.stack.splice(target, 0, item);
    bbRender();
  };

  window.bbDragStartPalette = function (ev, kind) {
    BB_STATE.dragSrcType = 'palette';
    BB_STATE.dragKind = kind;
    BB_STATE.dragStackIdx = -1;
    if (ev.dataTransfer) {
      ev.dataTransfer.effectAllowed = 'copy';
      ev.dataTransfer.setData('text/plain', kind);
    }
    bbHidePop();
  };

  window.bbDragStartStack = function (ev, idx) {
    const item = BB_STATE.stack[idx];
    if (!item || (META_BY_KIND[item.kind] && META_BY_KIND[item.kind].fixed)) {
      ev.preventDefault();
      return;
    }
    BB_STATE.dragSrcType = 'stack';
    BB_STATE.dragStackIdx = idx;
    BB_STATE.dragKind = item.kind;
    if (ev.dataTransfer) {
      ev.dataTransfer.effectAllowed = 'move';
      ev.dataTransfer.setData('text/plain', String(idx));
    }
  };

  window.bbDropAtSlot = function (ev, slotIdx) {
    ev.preventDefault();
    document.querySelectorAll('.bb-drop-slot.drag-over').forEach(el => el.classList.remove('drag-over'));
    if (BB_STATE.dragSrcType === 'palette' && BB_STATE.dragKind) {
      _insertBlockAt(BB_STATE.dragKind, slotIdx);
    } else if (BB_STATE.dragSrcType === 'stack' && BB_STATE.dragStackIdx >= 1) {
      const from = BB_STATE.dragStackIdx;
      const item = BB_STATE.stack[from];
      if (!item) return;
      BB_STATE.stack.splice(from, 1);
      let ins = slotIdx > from ? slotIdx - 1 : slotIdx;
      ins = Math.max(1, Math.min(ins, BB_STATE.stack.length - 1));
      BB_STATE.stack.splice(ins, 0, item);
      bbRender();
    }
    BB_STATE.dragSrcType = null;
    BB_STATE.dragKind = null;
    BB_STATE.dragStackIdx = -1;
  };

  window.bbToggleFullscreen = function () {
    BB_STATE.fullscreen = !BB_STATE.fullscreen;
    bbRender();
  };

  window.bbToggleAdvanced = function (checked) {
    BB_STATE.showAdvanced = !!checked;
    bbRender();
  };

  window.bbStartQa = async function (startIdx = 0) {
    await _ensureCatalogLoaded();
    BB_STATE.view = 'qa';
    BB_STATE.qaIdx = Math.max(0, Math.min(startIdx, BB_STATE.stack.length - 1));
    if (BB_STATE.stack[BB_STATE.qaIdx]) BB_STATE.stack[BB_STATE.qaIdx].configured = true;
    bbRender();
  };

  window.bbGoView = function (viewName) {
    BB_STATE.view = viewName;
    if (viewName === 'qa' && BB_STATE.stack[BB_STATE.qaIdx]) {
      BB_STATE.stack[BB_STATE.qaIdx].configured = true;
    }
    bbRender();
  };

  window.bbQaStep = function (delta) {
    const nxt = BB_STATE.qaIdx + delta;
    if (nxt < 0) {
      BB_STATE.view = 'stack';
    } else if (nxt >= BB_STATE.stack.length) {
      if (BB_STATE.stack[BB_STATE.qaIdx]) BB_STATE.stack[BB_STATE.qaIdx].configured = true;
      BB_STATE.view = 'export';
    } else {
      if (BB_STATE.stack[BB_STATE.qaIdx]) BB_STATE.stack[BB_STATE.qaIdx].configured = true;
      BB_STATE.qaIdx = nxt;
      if (BB_STATE.stack[nxt]) BB_STATE.stack[nxt].configured = true;
    }
    bbRender();
  };

  window.bbJumpQa = async function (idx) {
    await _ensureCatalogLoaded();
    if (BB_STATE.stack[BB_STATE.qaIdx]) BB_STATE.stack[BB_STATE.qaIdx].configured = true;
    BB_STATE.view = 'qa';
    BB_STATE.qaIdx = Math.max(0, Math.min(idx, BB_STATE.stack.length - 1));
    if (BB_STATE.stack[BB_STATE.qaIdx]) BB_STATE.stack[BB_STATE.qaIdx].configured = true;
    bbRender();
  };

  window.bbUpdateField = function (idx, key, val, rerender = false) {
    const it = BB_STATE.stack[idx];
    if (!it) return;
    it.config = it.config || {};
    it.config[key] = val;
    it.configured = true;
    if (it.kind === 'isn') _syncCompatInputsFromIsnBlock();
    if (it.kind === 'delay' && key === 'ms') {
      const hint = document.getElementById('bbDelayReadableHint');
      if (hint) hint.textContent = _formatMsReadable(val);
    }
    if (rerender) bbRender();
  };

  function _simulateExtract(cfg) {
    const raw = String(cfg.sample_log || '');
    const m = String(cfg.extract_mode || 'within').toLowerCase();
    if (m === 'reply_only') {
      const kw = String(cfg.reply_keyword || 'PASS');
      return { ok: raw.includes(kw), text: raw.includes(kw) ? `命中關鍵字 "${kw}" (PASS)` : `未發現關鍵字 "${kw}"`, expr: `Reply: @${kw}` };
    }
    if (m === 'split') {
      const sep = String(cfg.split_sep || ':');
      const idx = parseInt(cfg.split_idx || '1', 10) || 0;
      const parts = sep ? raw.split(sep) : [raw];
      const hit = (idx >= 0 && idx < parts.length) ? parts[idx].trim() : '(超出索引)';
      return { ok: idx >= 0 && idx < parts.length, text: hit, expr: `$${cfg.var_name || 'gOut'}:SplitString,"${sep}","${idx}"` };
    }
    if (m === 'sub') {
      const s = parseInt(cfg.sub_start || '0', 10) || 0;
      const l = parseInt(cfg.sub_len || '8', 10) || 0;
      return { ok: true, text: raw.substr(s, l), expr: `$${cfg.var_name || 'gOut'}:SubString,"${s}","${l}"` };
    }
    const lRaw = String(cfg.left_delim ?? '').replace(/\\r/g, '\r').replace(/\\n/g, '\n');
    const rRaw = String(cfg.right_delim ?? '').replace(/\\r/g, '\r').replace(/\\n/g, '\n');
    let out = '(未找到左邊界)';
    let ok = false;
    const i1 = lRaw ? raw.indexOf(lRaw) : 0;
    if (i1 >= 0) {
      const start = i1 + lRaw.length;
      const i2 = rRaw ? raw.indexOf(rRaw, start) : raw.length;
      out = (i2 >= 0 ? raw.slice(start, i2) : raw.slice(start)).trim();
      ok = true;
    }
    return {
      ok,
      text: out,
      expr: `$${cfg.var_name || 'gOut'}:WithinString,"${cfg.left_delim || ''}","${cfg.right_delim || '\\n'}",""`
    };
  }

  window.bbRefreshExtractPreview = function (idx) {
    const it = BB_STATE.stack[idx];
    const box = document.getElementById('bbExtractSimBox');
    if (!it || !box) return;
    const res = _simulateExtract(it.config || {});
    box.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
        <span>🔍 試算擷取結果：<b class="mono" style="background:#FEF08A; color:#854D0E; padding:1px 7px; border-radius:4px;">${_esc(res.text)}</b></span>
        <span class="mono" style="font-size:0.78rem; color:#1E40AF;">產生語法：${_esc(res.expr)}</span>
      </div>
    `;
  };

  window.bbOpenMultiSkuForBlock = function (idx) {
    const it = BB_STATE.stack[idx];
    if (it && it.config && it.config.sku_wizard) {
      window.STATE = window.STATE || {};
      window.STATE.createSkuConfig = JSON.parse(JSON.stringify(it.config.sku_wizard));
    }
    if (typeof window.openTemplateSkuWizard === 'function') {
      window.STATE = window.STATE || {};
      window.STATE._builderSectionsOverride = BB_STATE.stack
        .filter(b => !['isn', 'sfis_route', 'multi_sku', 'teardown'].includes(b.kind))
        .map(b => ({ section_title: b.config?.title || b.config?.title_name || META_BY_KIND[b.kind]?.name || b.kind, badge: '目前流程積木' }));
      window.openTemplateSkuWizard('create');
      const origApply = window.tswApplyToTarget;
      if (!origApply.__bbWrapped) {
        const wrapped = async function () {
          await origApply.apply(this, arguments);
          const cur = BB_STATE.stack.find(b => b.kind === 'multi_sku');
          if (cur && window.STATE && window.STATE.createSkuConfig) {
            cur.config.sku_wizard = JSON.parse(JSON.stringify(window.STATE.createSkuConfig));
            cur.configured = true;
          }
          bbRender();
        };
        wrapped.__bbWrapped = true;
        window.tswApplyToTarget = wrapped;
      }
    }
  };

  function _renderStackView() {
    const commonCards = BUILDER_CATALOG.filter(b => b.tier === 'common');
    const advCards = BUILDER_CATALOG.filter(b => b.tier === 'advanced');

    // 垂直小條積木，只留圖示與精簡中文（<=4字）及「+」按鈕
    const mkPaletteCard = (b) => `
      <div class="bb-uniform-brick palette-item ${b.exclusivePage ? 'is-red' : ''}"
        draggable="true"
        ondragstart="bbDragStartPalette(event, '${b.kind}')"
        onmousemove="bbShowPop(event, '${b.kind}')"
        onmouseleave="bbHidePop()">
        <span style="font-weight:800; font-size:0.84rem; color:${b.exclusivePage ? '#991B1B' : '#0F172A'}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${_esc(b.name)}</span>
        <button type="button" class="bb-plus-btn" title="加入此積木" onclick="event.stopPropagation(); bbAddBlock('${b.kind}');">+</button>
      </div>
    `;

    // 右欄積木採用與左欄一致的 38px 緊湊單行高度與外觀
    const stackHtml = BB_STATE.stack.map((item, idx) => {
      const meta = META_BY_KIND[item.kind] || {};
      const isFixed = !!meta.fixed;
      const isRed = !!meta.exclusivePage;
      const slotBefore = idx > 0 ? `
        <div class="bb-drop-slot"
          ondragover="event.preventDefault(); this.classList.add('drag-over');"
          ondragleave="this.classList.remove('drag-over');"
          ondrop="bbDropAtSlot(event, ${idx})"></div>
      ` : '';
      return `
        ${slotBefore}
        <div class="bb-uniform-brick ${isRed ? 'is-red' : ''} ${isFixed ? 'is-fixed' : ''}"
          style="cursor:pointer;"
          draggable="${isFixed ? 'false' : 'true'}"
          ondragstart="bbDragStartStack(event, ${idx})"
          onmousemove="bbShowPop(event, '${item.kind}')"
          onmouseleave="bbHidePop()"
          onclick="bbJumpQa(${idx})">
          <div style="display:flex; align-items:center; gap:7px; min-width:0; flex:1;">
            <span class="mono" style="font-weight:900; font-size:0.75rem; padding:1px 5px; border-radius:4px; background:${isRed ? '#FEE2E2' : '#E2E8F0'}; color:${isRed ? '#991B1B' : '#334155'}; flex-shrink:0;">#${idx + 1}</span>
            <span style="font-weight:800; font-size:0.84rem; color:${isRed ? '#991B1B' : '#0F172A'}; white-space:nowrap; flex-shrink:0;">${_esc(meta.name || item.kind)}</span>
            <span style="font-size:0.75rem; color:#64748B; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${_esc(_summarizeBlock(item))}</span>
            ${item.configured ? `<span style="font-size:0.72rem; color:#15803D; font-weight:900; flex-shrink:0;">✓</span>` : ''}
          </div>
          <div style="display:flex; align-items:center; gap:3px; flex-shrink:0;" onclick="event.stopPropagation();">
            ${!isFixed ? `
              <button type="button" class="btn" style="padding:1px 6px; font-size:0.74rem;" title="上移" onclick="bbMoveStackIdx(${idx}, -1)">▲</button>
              <button type="button" class="btn" style="padding:1px 6px; font-size:0.74rem;" title="下移" onclick="bbMoveStackIdx(${idx}, 1)">▼</button>
              <button type="button" class="btn" style="padding:1px 6px; font-size:0.74rem; color:#B91C1C; border-color:#FCA5A5;" title="移除" onclick="bbRemoveStackIdx(${idx})">✕</button>
            ` : `<span style="font-size:0.72rem; color:#64748B; padding:0 4px;">固定</span>`}
          </div>
        </div>
      `;
    }).join('');

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px; background:#FFFFFF; border:1px solid #CBD5E1; border-radius:9px; padding:9px 14px;">
        <div>
          <div style="font-weight:900; font-size:1rem; color:#0F172A;">🧱 拖曳積木堆疊測試流程（移過積木看說明，中間線可左右拖曳調寬）</div>
        </div>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <button type="button" class="btn" style="padding:5px 12px; font-size:0.83rem; background:${BB_STATE.fullscreen ? '#1E293B' : '#F8FAFC'}; color:${BB_STATE.fullscreen ? '#FFFFFF' : '#0F172A'}; border:1.5px solid #94A3B8; font-weight:800;" onclick="bbToggleFullscreen()">
            ${BB_STATE.fullscreen ? '🗗 退出全螢幕' : '⛶ 全螢幕編排'}
          </button>
          <button type="button" class="btn btn-primary-blue" style="padding:6px 15px; font-size:0.88rem; font-weight:900;" onclick="bbStartQa(0)">
            🚀 開始逐塊設定 (${BB_STATE.stack.length} 塊) ▶
          </button>
        </div>
      </div>

      <div id="bbSplitContainer" class="bb-split-container">
        <!-- 左欄：垂直單排精簡小積木 -->
        <div id="bbLeftPane" class="bb-left-pane" style="width:${Number(BB_STATE.splitLeftPx || 235)}px;">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin-bottom:8px;">
            <span style="font-weight:900; font-size:0.86rem; color:#0F172A;">📦 積木庫</span>
            <label style="display:inline-flex; align-items:center; gap:4px; cursor:pointer; font-size:0.77rem; font-weight:700; color:#334155;">
              <input type="checkbox" ${BB_STATE.showAdvanced ? 'checked' : ''} onchange="bbToggleAdvanced(this.checked)" style="cursor:pointer;">
              <span>進階 (${advCards.length})</span>
            </label>
          </div>
          <div class="bb-palette-list">
            ${commonCards.map(mkPaletteCard).join('')}
          </div>
          ${BB_STATE.showAdvanced ? `
            <div style="margin-top:8px; padding-top:8px; border-top:1px dashed #CBD5E1;">
              <div style="font-size:0.75rem; font-weight:800; color:#64748B; margin-bottom:5px;">進階積木</div>
              <div class="bb-palette-list">
                ${advCards.map(mkPaletteCard).join('')}
              </div>
            </div>
          ` : ''}
        </div>

        <!-- 中間可左右拖曳調整視窗大小的分割桿 -->
        <div id="bbSplitter" class="bb-splitter" title="按住左右拖曳調整兩欄寬度" onmousedown="bbStartSplitDrag(event)">
          <div class="bb-splitter-bar"></div>
        </div>

        <!-- 右欄：已堆疊測試流程 -->
        <div id="bbRightPane" class="bb-right-pane"
          ondragover="event.preventDefault();"
          ondrop="if(!event.target.classList.contains('bb-drop-slot') && BB_STATE.dragSrcType==='palette' && BB_STATE.dragKind){ bbAddBlock(BB_STATE.dragKind); BB_STATE.dragSrcType=null; }">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:8px;">
              <span style="font-weight:900; font-size:0.88rem; color:#1E3A8A;">🧱 已排定執行順序（共 ${BB_STATE.stack.length} 塊）</span>
              <span style="font-size:0.76rem; color:#64748B;">點擊積木可直接跳進問答</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:3px;">
              ${stackHtml}
            </div>
          </div>
          <div style="margin-top:12px; display:flex; justify-content:flex-end;">
            <button type="button" class="btn btn-primary-green" style="padding:8px 18px; font-weight:900;" onclick="bbStartQa(0)">
              🚀 排好了，開始逐塊設定 ▶
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function _renderQaBody(item, idx) {
    const c = item.config || {};
    switch (item.kind) {
      case 'isn':
        return `
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
            <label style="font-weight:700; font-size:0.86rem;">專案名稱 (Project)
              <input value="${_esc(c.project || 'PEGA_NEW')}" oninput="bbUpdateField(${idx},'project',this.value)" style="width:100%; margin-top:4px; padding:7px 10px; border:1.5px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <label style="font-weight:700; font-size:0.86rem;">測試站別 (Station)
              <input value="${_esc(c.station || 'MB')}" oninput="bbUpdateField(${idx},'station',this.value)" style="width:100%; margin-top:4px; padding:7px 10px; border:1.5px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <label style="font-weight:700; font-size:0.86rem;">幾槽並行測試 (DUTs)
              <select onchange="bbUpdateField(${idx},'dut_count',parseInt(this.value,10)||1,true)" style="width:100%; margin-top:4px; padding:7px 10px; border:1.5px solid #94A3B8; border-radius:6px;">
                <option value="1" ${Number(c.dut_count || 1) === 1 ? 'selected' : ''}>1 槽 (單板 LOAD_1=true)</option>
                <option value="2" ${Number(c.dut_count) === 2 ? 'selected' : ''}>2 槽 (雙板同步)</option>
                <option value="4" ${Number(c.dut_count) === 4 ? 'selected' : ''}>4 槽 (四板同步)</option>
              </select>
            </label>
            <label style="font-weight:700; font-size:0.86rem;">ISN 條碼位數 (幾個 Byte / 碼)
              <input type="number" min="1" max="32" value="${_esc(c.isn_len || 3)}" oninput="bbUpdateField(${idx},'isn_len',parseInt(this.value,10)||3,true)" style="width:100%; margin-top:4px; padding:7px 10px; border:1.5px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <label style="font-weight:700; font-size:0.86rem;">條碼字元規則
              <select onchange="bbUpdateField(${idx},'isn_pattern',this.value,true)" style="width:100%; margin-top:4px; padding:7px 10px; border:1.5px solid #94A3B8; border-radius:6px;">
                <option value="[0-9A-Z]" ${c.isn_pattern === '[0-9A-Z]' ? 'selected' : ''}>[0-9A-Z] 大寫英數字</option>
                <option value="[0-9]" ${c.isn_pattern === '[0-9]' ? 'selected' : ''}>[0-9] 純數字</option>
                <option value="[0-9A-Za-z]" ${c.isn_pattern === '[0-9A-Za-z]' ? 'selected' : ''}>[0-9A-Za-z] 大小寫英數</option>
              </select>
            </label>
            <div style="display:flex; flex-direction:column; justify-content:flex-end;">
              <div style="font-weight:700; font-size:0.86rem; margin-bottom:4px;">ScanBarcode 預覽</div>
              <div class="mono" style="background:#EFF6FF; border:1.5px solid #3B82F6; color:#1E3A8A; font-weight:800; padding:7px 10px; border-radius:6px;">{ISN,${c.isn_len || 3},${c.isn_pattern || '[0-9A-Z]'}}</div>
            </div>
          </div>
        `;

      case 'sfis_route':
        return `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
              <label style="flex:1; min-width:220px; cursor:pointer; padding:10px 14px; border-radius:8px; border:1.5px solid ${c.sfis_mode !== 'online' ? '#2563EB' : '#CBD5E1'}; background:${c.sfis_mode !== 'online' ? '#EFF6FF' : '#F8FAFC'}; font-weight:800;">
                <input type="radio" name="bbSfisMode_${idx}" ${c.sfis_mode !== 'online' ? 'checked' : ''} onchange="bbUpdateField(${idx},'sfis_mode','offline',true)"> 🛠️ 工程調試離線模式 (SFIS_Enable=0 / DebugMode=1)
              </label>
              <label style="flex:1; min-width:220px; cursor:pointer; padding:10px 14px; border-radius:8px; border:1.5px solid ${c.sfis_mode === 'online' ? '#16A34A' : '#CBD5E1'}; background:${c.sfis_mode === 'online' ? '#F0FDF4' : '#F8FAFC'}; font-weight:800;">
                <input type="radio" name="bbSfisMode_${idx}" ${c.sfis_mode === 'online' ? 'checked' : ''} onchange="bbUpdateField(${idx},'sfis_mode','online',true)"> 🌐 產線正式過站模式 (SFIS_Enable=1)
              </label>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:10px;">
              <label style="font-weight:700; font-size:0.84rem;">SFIS_TSP 路由代碼
                <input value="${_esc(c.tsp || 'PEGA,2')}" oninput="bbUpdateField(${idx},'tsp',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
              <label style="font-weight:700; font-size:0.84rem;">SFIS_WebLink 網址
                <input value="${_esc(c.weblink || '')}" oninput="bbUpdateField(${idx},'weblink',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
            </div>
          </div>
        `;

      case 'comm_cmd': {
        const sim = _simulateExtract(c);
        return `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div>
              <div style="font-weight:800; font-size:0.87rem; margin-bottom:6px;">Q1. 選擇通訊方式：</div>
              <div style="display:flex; gap:8px; flex-wrap:wrap;">
                ${[
                  ['uart', '🔌 UART 串口'],
                  ['adb', '🤖 ADB 指令'],
                  ['ssh', '🔐 SSH 連線'],
                  ['cmd', '💻 Windows CMD'],
                  ['telnet', '📡 Telnet']
                ].map(([val, lbl]) => `
                  <button type="button" class="btn" onclick="bbUpdateField(${idx},'protocol','${val}',true)"
                    style="padding:6px 13px; font-weight:800; font-size:0.84rem; ${c.protocol === val ? 'background:#2563EB; color:#FFFFFF; border-color:#1D4ED8;' : 'background:#F8FAFC; color:#1E293B;'}">
                    ${lbl}
                  </button>
                `).join('')}
              </div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:10px;">
              <label style="font-weight:700; font-size:0.84rem;">測項名稱 (Title)
                <input value="${_esc(c.title || '')}" oninput="bbUpdateField(${idx},'title',this.value)" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
              <label style="font-weight:700; font-size:0.84rem;">下達指令 (Send)
                <input value="${_esc(c.command || '')}" oninput="bbUpdateField(${idx},'command',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
              ${c.protocol === 'uart' ? `
                <label style="font-weight:700; font-size:0.84rem;">COM Port (DUT_UR1)
                  <input value="${_esc(c.port || 'COM4')}" oninput="bbUpdateField(${idx},'port',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
                </label>
              ` : (c.protocol === 'ssh' || c.protocol === 'telnet') ? `
                <label style="font-weight:700; font-size:0.84rem;">DUT IP / 帳號
                  <div style="display:flex; gap:4px; margin-top:3px;">
                    <input value="${_esc(c.dut_ip || '192.168.11.143')}" oninput="bbUpdateField(${idx},'dut_ip',this.value)" class="mono" style="flex:1.4; padding:6px; border:1px solid #94A3B8; border-radius:6px; min-width:0;">
                    <input value="${_esc(c.ssh_user || 'root')}" oninput="bbUpdateField(${idx},'ssh_user',this.value)" class="mono" style="flex:0.8; padding:6px; border:1px solid #94A3B8; border-radius:6px; min-width:0;">
                  </div>
                </label>
              ` : ''}
              <label style="font-weight:700; font-size:0.84rem;">結尾提示符 (EndPrompt / 等待 ms)
                <div style="display:flex; gap:5px; margin-top:3px;">
                  <input value="${_esc(c.end_prompt ?? '#')}" oninput="bbUpdateField(${idx},'end_prompt',this.value)" class="mono" style="width:65px; padding:6px; border:1px solid #94A3B8; border-radius:6px;" title="如 # 或 >">
                  <input value="${_esc(c.waiting || '5000')}" oninput="bbUpdateField(${idx},'waiting',this.value)" class="mono" style="flex:1; padding:6px; border:1px solid #94A3B8; border-radius:6px;" title="Waiting ms">
                </div>
              </label>
            </div>

            <div style="background:#EFF6FF; border:1.5px solid #60A5FA; border-radius:9px; padding:11px 13px;">
              <div style="font-weight:900; font-size:0.89rem; color:#1E3A8A; margin-bottom:7px;">Q2. 怎麼檢查回傳內容？（直接貼上 Console 吐出的字，幫你自動撈字串）</div>
              <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
                ${[
                  ['within', '✂️ 頭尾夾字串 (WithinString)'],
                  ['split', '🪓 符號分段取第N欄 (SplitString)'],
                  ['sub', '📐 固定位置切字 (SubString)'],
                  ['reply_only', '🔎 只比對關鍵字 (PASS/OK)']
                ].map(([em, lbl]) => `
                  <label style="cursor:pointer; padding:4px 10px; border-radius:6px; border:1px solid ${c.extract_mode === em ? '#2563EB' : '#CBD5E1'}; background:${c.extract_mode === em ? '#DBEAFE' : '#FFFFFF'}; font-weight:800; font-size:0.81rem;">
                    <input type="radio" name="bbExtMode_${idx}" ${c.extract_mode === em ? 'checked' : ''} onchange="bbUpdateField(${idx},'extract_mode','${em}',true)"> ${lbl}
                  </label>
                `).join('')}
              </div>

              ${c.extract_mode === 'reply_only' ? `
                <label style="font-weight:700; font-size:0.84rem;">期待回傳要包含哪個字 (寫進 Reply)：
                  <input value="${_esc(c.reply_keyword || 'PASS')}" oninput="bbUpdateField(${idx},'reply_keyword',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:180px; margin-left:6px; padding:5px 8px; border:1px solid #94A3B8; border-radius:5px;">
                </label>
              ` : `
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:8px; margin-bottom:8px;">
                  ${c.extract_mode === 'split' ? `
                    <label style="font-size:0.8rem; font-weight:700;">分隔符號 (例 : 或 =)
                      <input value="${_esc(c.split_sep || ':')}" oninput="bbUpdateField(${idx},'split_sep',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                    </label>
                    <label style="font-size:0.8rem; font-weight:700;">取第幾段 (0起算)
                      <input type="number" value="${_esc(c.split_idx || '1')}" oninput="bbUpdateField(${idx},'split_idx',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                    </label>
                  ` : c.extract_mode === 'sub' ? `
                    <label style="font-size:0.8rem; font-weight:700;">起始索引 (0起算)
                      <input type="number" value="${_esc(c.sub_start || '0')}" oninput="bbUpdateField(${idx},'sub_start',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                    </label>
                    <label style="font-size:0.8rem; font-weight:700;">截取長度
                      <input type="number" value="${_esc(c.sub_len || '8')}" oninput="bbUpdateField(${idx},'sub_len',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                    </label>
                  ` : `
                    <label style="font-size:0.8rem; font-weight:700;">左邊界關鍵字
                      <input value="${_esc(c.left_delim ?? '')}" oninput="bbUpdateField(${idx},'left_delim',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                    </label>
                    <label style="font-size:0.8rem; font-weight:700;">右邊界關鍵字 (例 \\n 或空白)
                      <input value="${_esc(c.right_delim ?? '\\n')}" oninput="bbUpdateField(${idx},'right_delim',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                    </label>
                  `}
                  <label style="font-size:0.8rem; font-weight:700;">存成變數名稱 ($)
                    <input value="${_esc(c.var_name || 'DUT_FW')}" oninput="bbUpdateField(${idx},'var_name',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                  </label>
                  <label style="font-size:0.8rem; font-weight:700;">比對型態與標準值/上下限
                    <div style="display:flex; gap:4px; margin-top:2px;">
                      <select onchange="bbUpdateField(${idx},'val_type',this.value,true)" class="mono" style="padding:5px; border:1px solid #94A3B8; border-radius:5px;">
                        <option value="%s" ${c.val_type === '%s' ? 'selected' : ''}>字串</option>
                        <option value="%f" ${c.val_type === '%f' ? 'selected' : ''}>小數</option>
                        <option value="%d" ${c.val_type === '%d' ? 'selected' : ''}>整數</option>
                      </select>
                      <input value="${_esc(c.expect_min ?? '')}" placeholder="下限/目標字" oninput="bbUpdateField(${idx},'expect_min',this.value)" class="mono" style="flex:1; min-width:0; padding:5px; border:1px solid #94A3B8; border-radius:5px;">
                      ${c.val_type !== '%s' ? `<input value="${_esc(c.expect_max ?? '')}" placeholder="上限" oninput="bbUpdateField(${idx},'expect_max',this.value)" class="mono" style="flex:1; min-width:0; padding:5px; border:1px solid #94A3B8; border-radius:5px;">` : ''}
                    </div>
                  </label>
                </div>
                <label style="display:block; font-size:0.8rem; font-weight:700; margin-bottom:6px;">📋 貼上你 Console 實際吐出的範例文字（即時驗證有沒有撈準）：
                  <textarea rows="2" oninput="bbUpdateField(${idx},'sample_log',this.value); bbRefreshExtractPreview(${idx});" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box; font-size:0.8rem;">${_esc(c.sample_log || '')}</textarea>
                </label>
                <div id="bbExtractSimBox" style="background:#FFFFFF; border:1px solid #93C5FD; border-radius:6px; padding:6px 10px; font-size:0.82rem;">
                  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
                    <span>🔍 試算擷取結果：<b class="mono" style="background:#FEF08A; color:#854D0E; padding:1px 7px; border-radius:4px;">${_esc(sim.text)}</b></span>
                    <span class="mono" style="font-size:0.78rem; color:#1E40AF;">產生語法：${_esc(sim.expr)}</span>
                  </div>
                </div>
                <label style="display:inline-flex; align-items:center; gap:6px; margin-top:6px; font-size:0.8rem; font-weight:700; cursor:pointer;">
                  <input type="checkbox" ${c.use_ini_var ? 'checked' : ''} onchange="bbUpdateField(${idx},'use_ini_var',this.checked)"> 將目標值/上下限同時抽出到 Global.ini [Scripts]（日後免改 Excel）
                </label>
              `}
            </div>
          </div>
        `;
      }

      case 'delay':
        return `
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
              <span style="font-weight:800; font-size:0.85rem;">快選時間：</span>
              ${['500', '1000', '2000', '3000', '5000', '10000'].map(v => `
                <button type="button" class="btn" style="padding:4px 10px; font-size:0.82rem; ${String(c.ms) === v ? 'background:#16A34A;color:#FFF;' : ''}" onclick="bbUpdateField(${idx},'ms','${v}',true)">${v} 毫秒</button>
              `).join('')}
            </div>
            <div style="display:flex; align-items:flex-end; gap:12px; flex-wrap:wrap;">
              <label style="font-weight:700; font-size:0.84rem; width:170px;">等待毫秒 (ms)
                <input type="number" min="1" value="${_esc(c.ms || '2000')}" oninput="bbUpdateField(${idx},'ms',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
              <div style="background:#DCFCE7; border:1.5px solid #4ADE80; color:#14532D; font-weight:900; font-size:0.88rem; padding:6px 12px; border-radius:6px;">
                💡 自動解讀：<span id="bbDelayReadableHint">${_esc(_formatMsReadable(c.ms || '2000'))}</span>
              </div>
              <label style="font-weight:700; font-size:0.84rem; flex:1; min-width:200px;">步驟用途說明
                <input value="${_esc(c.note || '')}" oninput="bbUpdateField(${idx},'note',this.value)" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
            </div>
          </div>
        `;

      case 'prompt_box':
        return `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              ${[
                ['yes_no', '✅❌ YES / NO 雙按鈕判斷（點 No 判 Fail 或分支）'],
                ['ok_only', '👍 單顆「好(OK)」提示確認'],
                ['input', '⌨️ 彈出輸入框讓作業員刷子條碼']
              ].map(([m, lbl]) => `
                <label style="cursor:pointer; padding:7px 12px; border-radius:8px; border:1.5px solid ${c.prompt_mode === m ? '#D97706' : '#CBD5E1'}; background:${c.prompt_mode === m ? '#FEF3C7' : '#F8FAFC'}; font-weight:800; font-size:0.84rem;">
                  <input type="radio" name="bbPromptM_${idx}" ${c.prompt_mode === m ? 'checked' : ''} onchange="bbUpdateField(${idx},'prompt_mode','${m}',true)"> ${lbl}
                </label>
              `).join('')}
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
              <label style="font-weight:700; font-size:0.84rem;">測項名稱 (Title)
                <input value="${_esc(c.title || 'Operator Check')}" oninput="bbUpdateField(${idx},'title',this.value)" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
              <label style="font-weight:700; font-size:0.84rem;">視窗上要顯示給作業員看的提示文字
                <input value="${_esc(c.message || '')}" oninput="bbUpdateField(${idx},'message',this.value)" style="width:100%; margin-top:3px; padding:6px 9px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
            </div>
            ${c.prompt_mode === 'yes_no' ? `
              <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:10px 12px; display:grid; grid-template-columns:120px 120px 1fr; gap:10px; align-items:end;">
                <label style="font-size:0.81rem; font-weight:700;">過關按鈕文字
                  <input value="${_esc(c.yes_label || 'Yes')}" oninput="bbUpdateField(${idx},'yes_label',this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
                <label style="font-size:0.81rem; font-weight:700;">失敗按鈕文字
                  <input value="${_esc(c.no_label || 'No')}" oninput="bbUpdateField(${idx},'no_label',this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
                <label style="font-size:0.81rem; font-weight:700;">如果作業員點「No」怎麼辦？
                  <select onchange="bbUpdateField(${idx},'no_policy',this.value,true)" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px;">
                    <option value="fail" ${c.no_policy === 'fail' ? 'selected' : ''}>直接判定此測項 FAIL (ExecMode=0，產線最標準)</option>
                    <option value="retry" ${c.no_policy === 'retry' ? 'selected' : ''}>再重試 3 次確認，仍按 No 才 FAIL (ExecMode=1)</option>
                    <option value="branch" ${c.no_policy === 'branch' ? 'selected' : ''}>走 4:P,F 分支紀錄 PASS / FAIL 標記列</option>
                  </select>
                </label>
              </div>
            ` : c.prompt_mode === 'input' ? `
              <div style="display:grid; grid-template-columns:1fr 110px 110px; gap:10px;">
                <label style="font-size:0.81rem; font-weight:700;">輸入存進變數名 ($)
                  <input value="${_esc(c.var_name || 'ScanSub')}" oninput="bbUpdateField(${idx},'var_name',this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
                <label style="font-size:0.81rem; font-weight:700;">最短碼數
                  <input type="number" value="${_esc(c.min_len || '1')}" oninput="bbUpdateField(${idx},'min_len',this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
                <label style="font-size:0.81rem; font-weight:700;">最長碼數
                  <input type="number" value="${_esc(c.max_len || '32')}" oninput="bbUpdateField(${idx},'max_len',this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
              </div>
            ` : ''}
          </div>
        `;

      case 'var_check':
        return `
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
              <label style="font-weight:700; font-size:0.84rem;">要檢查的變數名稱 (免打 $)
                <input value="${_esc(c.var_name || 'VCC_3V3')}" oninput="bbUpdateField(${idx},'var_name',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
              <label style="font-weight:700; font-size:0.84rem;">判斷方式
                <select onchange="bbUpdateField(${idx},'check_mode',this.value,true)" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                  <option value="limit" ${c.check_mode !== 'string' ? 'selected' : ''}>數值範圍 (:CheckLimit DL ~ UL)</option>
                  <option value="string" ${c.check_mode === 'string' ? 'selected' : ''}>字串比對 (:GetVal Reply=@字)</option>
                </select>
              </label>
              <label style="font-weight:700; font-size:0.84rem;">測項標題 (Title)
                <input value="${_esc(c.title || 'Check Limit')}" oninput="bbUpdateField(${idx},'title',this.value)" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
            </div>
            ${c.check_mode === 'string' ? `
              <label style="font-weight:700; font-size:0.84rem;">預期相等字串
                <input value="${_esc(c.expect_str || 'PASS')}" oninput="bbUpdateField(${idx},'expect_str',this.value)" class="mono" style="width:220px; margin-left:6px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
              </label>
            ` : `
              <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:flex-end;">
                <label style="font-weight:700; font-size:0.84rem;">格式
                  <select onchange="bbUpdateField(${idx},'val_type',this.value,true)" class="mono" style="display:block; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                    <option value="%f" ${c.val_type !== '%d' ? 'selected' : ''}>%f (浮點數)</option>
                    <option value="%d" ${c.val_type === '%d' ? 'selected' : ''}>%d (整數)</option>
                  </select>
                </label>
                <label style="font-weight:700; font-size:0.84rem;">下限 DL
                  <input value="${_esc(c.dl ?? '3.15')}" oninput="bbUpdateField(${idx},'dl',this.value)" class="mono" style="display:block; width:120px; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                </label>
                <label style="font-weight:700; font-size:0.84rem;">上限 UL
                  <input value="${_esc(c.ul ?? '3.45')}" oninput="bbUpdateField(${idx},'ul',this.value)" class="mono" style="display:block; width:120px; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                </label>
              </div>
            `}
            <label style="display:inline-flex; align-items:center; gap:6px; font-size:0.82rem; font-weight:700; cursor:pointer;">
              <input type="checkbox" ${c.use_ini_var ? 'checked' : ''} onchange="bbUpdateField(${idx},'use_ini_var',this.checked)"> 抽出門檻至 Global.ini [Scripts]
            </label>
          </div>
        `;

      case 'inst': {
        const insts = BB_STATE.catalogInsts || [];
        const usable = insts.filter(i => i.dll_exists !== false);
        const allList = usable.length ? usable : insts;
        return `
          <div style="background:#FEF2F2; border:1.5px solid #EF4444; border-radius:10px; padding:12px;">
            <div style="font-weight:900; color:#991B1B; margin-bottom:8px;">🔴 專屬設定頁｜挑選這一步要使用的儀器類型與參數：</div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
              ${[
                ['ni6009', '⚡ NI-6008 / NI-6009 多通道電壓卡'],
                ['rf', '📶 LitePoint IQxel WiFi RF'],
                ['catalog', '🧪 挑選其他全部儀器 (電源/電表/LED/34+款)']
              ].map(([m, lbl]) => `
                <button type="button" class="btn" onclick="bbUpdateField(${idx},'inst_mode','${m}',true)"
                  style="padding:6px 12px; font-weight:800; font-size:0.83rem; ${c.inst_mode === m ? 'background:#DC2626;color:#FFF;border-color:#991B1B;' : 'background:#FFF;color:#7F1D1D;border-color:#FCA5A5;'}">${lbl}</button>
              `).join('')}
            </div>
            ${c.inst_mode === 'ni6009' ? `
              <div style="display:grid; grid-template-columns:1fr 140px 140px; gap:10px; margin-bottom:8px;">
                <label style="font-size:0.82rem; font-weight:700;">測項標題
                  <input value="${_esc(c.title_name || 'Measure Voltage Test')}" oninput="bbUpdateField(${idx},'title_name',this.value)" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
                <label style="font-size:0.82rem; font-weight:700;">量測模式
                  <select onchange="bbUpdateField(${idx},'mode',this.value)" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px;">
                    <option value="RSE" ${c.mode !== 'DIFF' ? 'selected' : ''}>RSE (單端)</option>
                    <option value="DIFF" ${c.mode === 'DIFF' ? 'selected' : ''}>DIFF (差動)</option>
                  </select>
                </label>
                <label style="font-size:0.82rem; font-weight:700;">DAQ 裝置 ID
                  <input value="${_esc(c.dev_id || 'Dev1')}" oninput="bbUpdateField(${idx},'dev_id',this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
              </div>
              <div style="font-size:0.81rem; font-weight:800; margin-bottom:4px;">通道腳位與 DL/UL 上下限：</div>
              ${(c.channels || []).map((ch, ci) => `
                <div style="display:flex; gap:6px; align-items:center; margin-bottom:5px; flex-wrap:wrap;">
                  <span class="mono" style="font-weight:800;">AI</span>
                  <input type="number" value="${_esc(ch.ch)}" oninput="BB_STATE.stack[${idx}].config.channels[${ci}].ch=parseInt(this.value,10)||0" class="mono" style="width:55px; padding:4px; border:1px solid #94A3B8; border-radius:4px;">
                  <input value="${_esc(ch.name)}" placeholder="名稱如 VCC_3V3" oninput="BB_STATE.stack[${idx}].config.channels[${ci}].name=this.value" class="mono" style="width:110px; padding:4px; border:1px solid #94A3B8; border-radius:4px;">
                  <span>DL:</span>
                  <input value="${_esc(ch.dl)}" oninput="BB_STATE.stack[${idx}].config.channels[${ci}].dl=this.value" class="mono" style="width:75px; padding:4px; border:1px solid #94A3B8; border-radius:4px;">
                  <span>UL:</span>
                  <input value="${_esc(ch.ul)}" oninput="BB_STATE.stack[${idx}].config.channels[${ci}].ul=this.value" class="mono" style="width:75px; padding:4px; border:1px solid #94A3B8; border-radius:4px;">
                  <button type="button" class="btn" style="padding:2px 7px; font-size:0.75rem;" onclick="BB_STATE.stack[${idx}].config.channels.splice(${ci},1); bbRender();">✕</button>
                </div>
              `).join('')}
              <button type="button" class="btn" style="padding:4px 10px; font-size:0.8rem;" onclick="BB_STATE.stack[${idx}].config.channels.push({ch:BB_STATE.stack[${idx}].config.channels.length,name:'V_CH',dl:'3.15',ul:'3.45'}); bbRender();">+ 新增一個 AI 通道</button>
            ` : c.inst_mode === 'rf' ? `
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <label style="font-size:0.82rem; font-weight:700;">RF 儀器名稱
                  <input value="${_esc(c.inst_name || 'InstIQApiA')}" oninput="bbUpdateField(${idx},'inst_name',this.value)" class="mono" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
                <label style="font-size:0.82rem; font-weight:700;">測項標題
                  <input value="${_esc(c.title_name || 'WIFI RF Test')}" oninput="bbUpdateField(${idx},'title_name',this.value)" style="width:100%; margin-top:2px; padding:5px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
              </div>
              <div style="font-size:0.81rem; color:#7F1D1D; margin-top:6px;">預設附帶標準 CH6 MCS7 Tx Power (13~17dBm) &amp; EVM + Rx 驗測與 Marco 子工作表。</div>
            ` : `
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:10px;">
                <label style="font-size:0.82rem; font-weight:700;">選擇儀器型號
                  <select onchange="bbUpdateField(${idx},'inst_name',this.value,true)" class="mono" style="width:100%; margin-top:2px; padding:6px; border:1px solid #94A3B8; border-radius:5px;">
                    ${allList.map(i => `<option value="${_esc(i.Name)}" ${c.inst_name === i.Name ? 'selected' : ''}>${_esc(i.Name)} — ${_esc(i.Desc || i.Functions || '')}</option>`).join('')}
                  </select>
                </label>
                <label style="font-size:0.82rem; font-weight:700;">測項名稱
                  <input value="${_esc(c.title_name || '')}" oninput="bbUpdateField(${idx},'title_name',this.value)" style="width:100%; margin-top:2px; padding:6px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
                <label style="font-size:0.82rem; font-weight:700;">下限 DL
                  <input value="${_esc(c.dl_val || '')}" oninput="bbUpdateField(${idx},'dl_val',this.value)" class="mono" style="width:100%; margin-top:2px; padding:6px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
                <label style="font-size:0.82rem; font-weight:700;">上限 UL
                  <input value="${_esc(c.ul_val || '')}" oninput="bbUpdateField(${idx},'ul_val',this.value)" class="mono" style="width:100%; margin-top:2px; padding:6px; border:1px solid #94A3B8; border-radius:5px; box-sizing:border-box;">
                </label>
              </div>
            `}
          </div>
        `;
      }

      case 'multi_sku': {
        const sk = c.sku_wizard || (window.STATE && window.STATE.createSkuConfig);
        return `
          <div style="background:#FEF2F2; border:1.5px solid #EF4444; border-radius:10px; padding:14px;">
            <div style="font-weight:900; color:#991B1B; font-size:0.96rem; margin-bottom:6px;">🔴 專屬設定頁｜多 SKU 分流與衍生品閘門設定</div>
            <div style="font-size:0.84rem; color:#7F1D1D; margin-bottom:10px;">
              點擊下方按鈕進入多 SKU 一頁式設定精靈（可挑 3 SKU / 工單名單 / 國別碼、設定個別 DL/UL 與「哪個 SKU 跑哪些積木」），套用後會自動回來並顯示於本積木。
            </div>
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
              <button type="button" class="btn" style="background:#DC2626; color:#FFFFFF; border:none; padding:8px 18px; font-weight:900; font-size:0.92rem;" onclick="bbOpenMultiSkuForBlock(${idx})">
                🎯 開啟多 SKU 分流精靈設定
              </button>
              ${(sk && sk.enabled) ? `<span style="background:#DCFCE7; color:#15803D; border:1px solid #4ADE80; padding:5px 10px; border-radius:6px; font-weight:800; font-size:0.83rem;">✓ 已設定 ${(sk.sku_branches || []).length} 支 SKU（來源：${_esc(sk.source_mode)}）</span>` : `<span style="color:#991B1B; font-weight:700; font-size:0.82rem;">（尚未設定 SKU 規則）</span>`}
            </div>
          </div>
        `;
      }

      case 'fixture':
        return `
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              ${[
                ['none', '🚫 此站沒有治具（略過不產生治具步驟）'],
                ['pneumatic', '🤖 氣動治具 COM Port (UARTF)'],
                ['ipower', '🔌 iPower 電源控制上電']
              ].map(([m, lbl]) => `
                <label style="cursor:pointer; padding:7px 12px; border-radius:8px; border:1.5px solid ${c.fixture_type === m ? '#2563EB' : '#CBD5E1'}; background:${c.fixture_type === m ? '#EFF6FF' : '#F8FAFC'}; font-weight:800; font-size:0.84rem;">
                  <input type="radio" name="bbFx_${idx}" ${c.fixture_type === m ? 'checked' : ''} onchange="bbUpdateField(${idx},'fixture_type','${m}',true)"> ${lbl}
                </label>
              `).join('')}
            </div>
            ${c.fixture_type !== 'none' ? `
              <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:flex-end;">
                ${c.fixture_type === 'pneumatic' ? `
                  <label style="font-size:0.83rem; font-weight:700;">治具 COM Port (PCUART_fixture_1)
                    <input value="${_esc(c.com_port || 'COM8')}" oninput="bbUpdateField(${idx},'com_port',this.value)" class="mono" style="display:block; width:130px; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                  </label>
                ` : ''}
                <label style="font-size:0.83rem; font-weight:700;">動作後等待毫秒 (ms)
                  <input type="number" value="${_esc(c.delay_ms || '3000')}" oninput="bbUpdateField(${idx},'delay_ms',this.value,true)" class="mono" style="display:block; width:140px; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                </label>
                <span style="font-size:0.82rem; font-weight:800; color:#15803D;">(${_esc(_formatMsReadable(c.delay_ms || '3000'))})</span>
              </div>
            ` : ''}
          </div>
        `;

      case 'sfis_rw':
        return `
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
            <label style="font-weight:700; font-size:0.84rem;">動作類型
              <select onchange="bbUpdateField(${idx},'rw_mode',this.value,true)" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                <option value="get_version" ${c.rw_mode === 'get_version' ? 'selected' : ''}>讀取 SFIS 欄位 (:SfGetVersion)</option>
                <option value="get_imac" ${c.rw_mode === 'get_imac' ? 'selected' : ''}>讀取 SFIS MAC (:SfGetiMAC)</option>
                <option value="save_link" ${c.rw_mode === 'save_link' ? 'selected' : ''}>寫回資料至 SFIS (:SfSaveLinkData)</option>
                <option value="scan_label" ${c.rw_mode === 'scan_label' ? 'selected' : ''}>作業員額外掃描副條碼 (ScanLabel)</option>
              </select>
            </label>
            <label style="font-weight:700; font-size:0.84rem;">欄位 / 標籤名稱
              <input value="${_esc(c.field_name || 'MAC1')}" oninput="bbUpdateField(${idx},'field_name',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <label style="font-weight:700; font-size:0.84rem;">存進變數 ($) / 寫回值
              <input value="${_esc(c.rw_mode === 'save_link' ? (c.save_value || '*(sfMAC)') : (c.var_name || 'sfMAC'))}" oninput="bbUpdateField(${idx},'${c.rw_mode === 'save_link' ? 'save_value' : 'var_name'}',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
          </div>
        `;

      case 'python':
        return `
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
            <label style="font-weight:700; font-size:0.84rem;">Python 資料夾路徑 (PythonPath)
              <input value="${_esc(c.python_path || 'D:\\PythonScript')}" oninput="bbUpdateField(${idx},'python_path',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <label style="font-weight:700; font-size:0.84rem;">腳本檔名 (.py)
              <input value="${_esc(c.script_name || 'my_test.py')}" oninput="bbUpdateField(${idx},'script_name',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <label style="font-weight:700; font-size:0.84rem;">輸出前綴字 (擷取用)
              <input value="${_esc(c.result_prefix || 'RESULT=')}" oninput="bbUpdateField(${idx},'result_prefix',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <div style="display:flex; gap:6px;">
              <label style="flex:1; font-weight:700; font-size:0.84rem;">下限
                <input value="${_esc(c.min_val ?? '0.0')}" oninput="bbUpdateField(${idx},'min_val',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
              <label style="flex:1; font-weight:700; font-size:0.84rem;">上限
                <input value="${_esc(c.max_val ?? '100.0')}" oninput="bbUpdateField(${idx},'max_val',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
              </label>
            </div>
          </div>
        `;

      case 'ping':
        return `
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
            <label style="font-weight:700; font-size:0.84rem;">待測物 IP (DUTIP_1)
              <input value="${_esc(c.dut_ip || '192.168.11.143')}" oninput="bbUpdateField(${idx},'dut_ip',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <label style="font-weight:700; font-size:0.84rem;">電腦網卡 IP (PCIP_1)
              <input value="${_esc(c.pc_ip || '192.168.11.3')}" oninput="bbUpdateField(${idx},'pc_ip',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            <label style="font-weight:700; font-size:0.84rem;">超時 (ms)
              <input type="number" value="${_esc(c.timeout_ms || '5000')}" oninput="bbUpdateField(${idx},'timeout_ms',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
          </div>
        `;

      case 'ext_file':
        return `
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
            <label style="font-weight:700; font-size:0.84rem;">檔案類型
              <select onchange="bbUpdateField(${idx},'file_mode',this.value,true)" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                <option value="rini" ${c.file_mode !== 'rtxt' ? 'selected' : ''}>讀取 .ini 欄位 (:Utility.Rini)</option>
                <option value="rtxt" ${c.file_mode === 'rtxt' ? 'selected' : ''}>讀取 .txt 文字 (:Utility.Rtxt)</option>
              </select>
            </label>
            <label style="font-weight:700; font-size:0.84rem;">檔案路徑
              <input value="${_esc(c.file_path || '.\\\\System\\\\config.ini')}" oninput="bbUpdateField(${idx},'file_path',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
            ${c.file_mode !== 'rtxt' ? `
              <label style="font-weight:700; font-size:0.84rem;">INI Section / Key
                <div style="display:flex; gap:4px; margin-top:3px;">
                  <input value="${_esc(c.section || 'Scripts')}" oninput="bbUpdateField(${idx},'section',this.value)" class="mono" style="flex:1; min-width:0; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                  <input value="${_esc(c.key || 'TargetKey')}" oninput="bbUpdateField(${idx},'key',this.value)" class="mono" style="flex:1; min-width:0; padding:6px; border:1px solid #94A3B8; border-radius:6px;">
                </div>
              </label>
            ` : ''}
            <label style="font-weight:700; font-size:0.84rem;">存進變數 ($)
              <input value="${_esc(c.var_name || 'gExtVal')}" oninput="bbUpdateField(${idx},'var_name',this.value)" class="mono" style="width:100%; margin-top:3px; padding:6px; border:1px solid #94A3B8; border-radius:6px; box-sizing:border-box;">
            </label>
          </div>
        `;

      case 'teardown':
        return `
          <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <label style="flex:1; min-width:240px; cursor:pointer; padding:12px; border-radius:8px; border:1.5px solid ${c.teardown_mode !== '97_98_99' ? '#E11D48' : '#CBD5E1'}; background:${c.teardown_mode !== '97_98_99' ? '#FFF1F2' : '#F8FAFC'}; font-weight:800;">
              <input type="radio" name="bbTd_${idx}" ${c.teardown_mode !== '97_98_99' ? 'checked' : ''} onchange="bbUpdateField(${idx},'teardown_mode','97_only',true)">
              🛑 標準 Phase 97 強制收尾（無論 PASS/FAIL 都斷電＋關所有 COM Port）
            </label>
            <label style="flex:1; min-width:240px; cursor:pointer; padding:12px; border-radius:8px; border:1.5px solid ${c.teardown_mode === '97_98_99' ? '#E11D48' : '#CBD5E1'}; background:${c.teardown_mode === '97_98_99' ? '#FFF1F2' : '#F8FAFC'}; font-weight:800;">
              <input type="radio" name="bbTd_${idx}" ${c.teardown_mode === '97_98_99' ? 'checked' : ''} onchange="bbUpdateField(${idx},'teardown_mode','97_98_99',true)">
              🔀 加開 Phase 98 (PASS 綠燈) ＋ Phase 99 (FAIL 紅燈) 雙分流收尾
            </label>
          </div>
        `;

      default:
        return `
          <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:12px; font-size:0.86rem; color:#334155;">
            <b>${_esc(META_BY_KIND[item.kind]?.popTitle || item.kind)}</b>：此積木將套用官方實戰標準模板生成，無需額外填寫，可直接按「下一塊 ▶」。
          </div>
        `;
    }
  }

  function _renderProgressStrip(activeIdx) {
    return `
      <div class="bb-progress-strip">
        ${BB_STATE.stack.map((it, i) => {
          const meta = META_BY_KIND[it.kind] || {};
          const isAct = (i === activeIdx);
          const isRed = !!meta.exclusivePage;
          return `
            <button type="button" onclick="bbJumpQa(${i})" class="bb-step-pill ${isAct ? 'active' : ''} ${isRed ? 'is-red' : ''}">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:4px; margin-bottom:2px;">
                <span class="mono" style="font-weight:900; font-size:0.74rem; color:${isAct ? (isRed ? '#991B1B' : '#1E3A8A') : '#475569'};">#${i + 1}</span>
                ${isAct ? `<span style="font-size:0.68rem; font-weight:900; color:${isRed ? '#DC2626' : '#2563EB'};">● 設定中</span>` : (it.configured ? `<span style="font-size:0.72rem; color:#15803D;">✓</span>` : '')}
              </div>
              <div style="font-weight:800; font-size:0.78rem; color:#0F172A; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${_esc(meta.name || it.kind)}</div>
            </button>
          `;
        }).join('')}
      </div>
    `;
  }

  function _renderQaView() {
    const idx = Math.max(0, Math.min(BB_STATE.qaIdx, BB_STATE.stack.length - 1));
    const item = BB_STATE.stack[idx];
    const meta = META_BY_KIND[item.kind] || {};
    const isLast = (idx === BB_STATE.stack.length - 1);

    return `
      <div style="background:#FFFFFF; border:2px solid ${meta.exclusivePage ? '#EF4444' : '#3B82F6'}; border-radius:11px; padding:16px;">
        <!-- 上方純問題填寫區 -->
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
          <span style="font-weight:900; font-size:1.1rem; color:${meta.exclusivePage ? '#991B1B' : '#0F172A'};">${_esc(meta.name || item.kind)}</span>
        </div>
        <div style="font-size:0.84rem; color:#475569; margin-bottom:14px;">💡 ${_esc(meta.popDesc || '')}</div>
        <div style="min-height:175px;">
          ${_renderQaBody(item, idx)}
        </div>

        <!-- 最底部：固定整排彩/灰積木進度條 ＋ 導覽操作列 -->
        <div class="bb-bottom-dock">
          ${_renderProgressStrip(idx)}
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <button type="button" class="btn" style="padding:6px 13px; font-size:0.84rem; font-weight:800;" onclick="bbGoView('stack')">◀ 回積木編排</button>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="mono" style="background:${meta.exclusivePage ? '#FEE2E2' : '#DBEAFE'}; color:${meta.exclusivePage ? '#991B1B' : '#1E3A8A'}; padding:3px 10px; border-radius:999px; font-weight:900; font-size:0.83rem;">第 ${idx + 1} / ${BB_STATE.stack.length} 塊</span>
              <span style="font-weight:800; font-size:0.9rem; color:#334155;">${_esc(meta.name || item.kind)}</span>
            </div>
            <div style="display:flex; gap:8px;">
              <button type="button" class="btn" style="padding:6px 14px; font-size:0.85rem; font-weight:800;" onclick="bbQaStep(-1)">${idx === 0 ? '◀ 回排順序' : '◀ 上一塊'}</button>
              <button type="button" class="btn ${isLast ? 'btn-primary-green' : 'btn-primary-blue'}" style="padding:6px 18px; font-size:0.88rem; font-weight:900;" onclick="bbQaStep(1)">${isLast ? '✅ 完成設定，看總覽匯出 ▶' : '下一塊 ▶'}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function _renderExportView() {
    const isnCfg = (BB_STATE.stack.find(b => b.kind === 'isn') || {}).config || {};
    return `
      <div style="background:#FFFFFF; border:2px solid #16A34A; border-radius:11px; padding:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
          <div>
            <div style="font-weight:900; font-size:1.08rem; color:#14532D;">🎉 總覽確認與產出 Excel 測試包</div>
            <div style="font-size:0.83rem; color:#475569;">專案 <code>${_esc(isnCfg.project || 'PEGA_NEW')}</code> ｜ 站別 <code>${_esc(isnCfg.station || 'MB')}</code> ｜ 共 ${BB_STATE.stack.length} 塊流程</div>
          </div>
          <button type="button" class="btn" style="padding:6px 12px; font-weight:800;" onclick="bbGoView('stack')">◀ 回積木堆疊微調</button>
        </div>

        <div style="display:flex; flex-direction:column; gap:5px; margin-bottom:14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 12px;">
          ${BB_STATE.stack.map((it, i) => {
            const meta = META_BY_KIND[it.kind] || {};
            return `
              <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; padding:4px 8px; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px;">
                <div style="font-size:0.84rem;">
                  <b class="mono" style="color:#1E40AF;">#${i + 1}</b> <b>${_esc(meta.name || it.kind)}</b>
                  <span style="color:#475569; margin-left:6px;">${_esc(_summarizeBlock(it))}</span>
                </div>
                <button type="button" class="btn" style="padding:2px 8px; font-size:0.76rem;" onclick="bbJumpQa(${i})">修改</button>
              </div>
            `;
          }).join('')}
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:8px; margin-bottom:14px;">
          <div style="display:flex; align-items:center; gap:8px; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px; padding:7px 12px; font-size:0.83rem; color:#1E3A8A; font-weight:700;">
            <span>🎯 啟動站別 (StationName)：</span>
            <select onchange="BB_STATE.exportOpts.station_name_mode=this.value" style="flex:1; padding:4px 6px; border:1px solid #93C5FD; border-radius:5px; font-weight:700;">
              <option value="fixed" ${BB_STATE.exportOpts.station_name_mode !== 'ask' ? 'selected' : ''}>指定站別直接啟動 (寫入站名)</option>
              <option value="ask" ${BB_STATE.exportOpts.station_name_mode === 'ask' ? 'selected' : ''}>留空 (執行時彈窗選擇站別)</option>
            </select>
          </div>
          <label style="display:flex; align-items:center; gap:8px; background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:7px 12px; font-size:0.83rem; color:#92400E; font-weight:700; cursor:pointer;">
            <input type="checkbox" ${BB_STATE.exportOpts.no_hw_phase_pause ? 'checked' : ''} onchange="BB_STATE.exportOpts.no_hw_phase_pause=this.checked" style="width:16px; height:16px;">
            <span>⏸️ 無儀器時將儀器測項先寫為 <code>Phase = -1</code></span>
          </label>
        </div>

        <div style="display:flex; gap:12px; flex-wrap:wrap;">
          <button type="button" class="btn btn-dry" style="padding:10px 18px; font-size:0.95rem; font-weight:900;" onclick="bbExportExcel(true)">🧪 產生「無硬體試跑版」</button>
          <button type="button" class="btn btn-primary-green" style="padding:10px 20px; font-size:0.95rem; font-weight:900;" onclick="bbExportExcel(false)">💾 匯出 16 欄正式測試包 + Checksum</button>
        </div>
        <div class="bb-bottom-dock">
          ${_renderProgressStrip(-1)}
        </div>
      </div>
    `;
  }

  window.bbExportExcel = async function (dryRun) {
    const isnCfg = (BB_STATE.stack.find(b => b.kind === 'isn') || {}).config || {};
    const skuBlk = BB_STATE.stack.find(b => b.kind === 'multi_sku');
    const skuCfg = (skuBlk && skuBlk.config && skuBlk.config.sku_wizard) || (window.STATE && window.STATE.createSkuConfig) || null;
    const body = {
      project_name: (isnCfg.project || 'PEGA_NEW').trim() || 'PEGA_NEW',
      station_name: (isnCfg.station || 'MB').trim() || 'MB',
      dut_count: Number(isnCfg.dut_count || 1),
      dry_run: !!dryRun,
      no_hw_phase_pause: !!BB_STATE.exportOpts.no_hw_phase_pause,
      station_name_mode: BB_STATE.exportOpts.station_name_mode || 'fixed',
      open_excel: false,
      wizard_config: {
        isn_length: Number(isnCfg.isn_len || 3),
        isn_pattern: isnCfg.isn_pattern || '[0-9A-Z]',
      },
      builder_sequence: BB_STATE.stack.map(it => ({ uid: it.uid, kind: it.kind, config: it.config || {} })),
    };
    if (skuCfg && skuCfg.enabled) body.sku_wizard = skuCfg;

    const data = await window.withLoadingTimer(
      dryRun ? '正在依積木順序產生「無硬體試跑版」' : '正在依積木順序產出 16 欄正式測試包與 INI',
      async () => {
        const res = await fetch('/api/generate_new_standalone', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        return await res.json();
      },
      900
    );
    if (!data || data.status !== 'ok') {
      alert('產出失敗：' + ((data && data.message) || ''));
      return;
    }
    const alertBox = document.getElementById('genAlertBox');
    if (alertBox) {
      alertBox.style.display = 'block';
      alertBox.innerHTML = `
        ✅ <strong>測試包產出完成</strong>（已自動寫入 Checksum 並開啟資料夾）<br>
        📂 <span class="mono">${_esc(data.output_dir)}</span><br>
        📄 <span class="mono">${_esc(data.excel_path)}</span><br>
        ${typeof window.formatIsnHtml === 'function' ? window.formatIsnHtml(data.isn_info) : ''}
      `;
    }
    if (typeof window.showExportCompleteModal === 'function') {
      window.showExportCompleteModal({
        title: '🎉 積木組裝 Excel 測試包匯出完成',
        excelPath: data.excel_path,
        guideTxtPath: data.guide_txt_path || '',
        missingDlls: data.missing_dlls || [],
      });
    }
  };

  window.bbRender = function () {
    _ensureStylesAndPop();
    const host = document.getElementById('createBlockBuilderRoot');
    if (!host) return;
    host.classList.toggle('bb-fullscreen-shell', !!BB_STATE.fullscreen);
    if (BB_STATE.view === 'qa') {
      host.innerHTML = _renderQaView();
    } else if (BB_STATE.view === 'export') {
      host.innerHTML = _renderExportView();
    } else {
      host.innerHTML = _renderStackView();
    }
  };

  window.initCreateBlockBuilder = function () {
    _syncCompatInputsFromIsnBlock();
    bbRender();
  };
})();
