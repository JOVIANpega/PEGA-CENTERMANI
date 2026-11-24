// Extracted Instrument Intro & Interactive HMI Module
const NI6_PRESETS = {
  '1.8V': { name: 'VCC_1V8', dl: '1.71', ul: '1.89', tag: '1.8V' },
  '3.3V': { name: 'VCC_3V3', dl: '3.15', ul: '3.45', tag: '3.3V' },
  '5V':   { name: 'VCC_5V',  dl: '4.75', ul: '5.25', tag: '5V' },
  '12V':  { name: 'VCC_12V', dl: '11.40', ul: '12.60', tag: '12V' },
  'custom': { name: 'VBAT_3V6', dl: '3.42', ul: '3.78', tag: '自訂' }
};
const INTRO_STATE = {
  targetMode: 'audit',
  instName: 'NI6008',
  editGenIdx: -1,
  fontSize: parseInt(localStorage.getItem('centimani_intro_font_size') || '15', 10) || 15
};
function resolveBaseInstName(instName) {
  const s = String(instName || '').trim();
  if (!s) return s;
  if (typeof INST_INTRO_PROFILES !== 'undefined' && INST_INTRO_PROFILES[s]) return s;
  const stem = s.replace(/-\d+$/, '');
  if (typeof INST_INTRO_PROFILES !== 'undefined') {
    if (INST_INTRO_PROFILES[stem]) return stem;
    if (INST_INTRO_PROFILES[`${stem}-1`]) return `${stem}-1`;
  }
  return s;
}
const INST_INTRO_PROFILES = {
  'NI6008': {
    title: 'NI USB-6009 / NI-6008 多功能資料擷取卡',
    dll: 'DaqUSBNi.dll',
    category: '量測電壓 / DAQ',
    img: '/images/51p+17SjMDL.jpg',
    hasInteractiveHmi: true,
    nextLabel: '下一步：開始設定接線與通道 ▶',
    highlights: [
      { label: '主要用途', value: '多通道電源軌電壓量測' },
      { label: '關鍵耐壓限制', value: '對 GND 耐壓 ±10V' },
      { label: 'Centimani 指令', value: ':Dev.VOLTAGE' }
    ],
    specs: [
      { k: '通訊介面', v: 'USB 隨插即用（無需外接電源）' },
      { k: '類比輸入', v: '8 路單端 (RSE, ±10V) / 4 路差動 (DIFF, ±20V)' },
      { k: '解析度', v: '14-bit ADC' },
      { k: '其他腳位', v: '2 路 AO (0~5V)、12 路 DIO、+5V / +2.5V' },
      { k: 'Global.ini', v: '[Settings] DAQ_1=Dev1' }
    ],
    features: [
      '適合同時多通道量測主機板各組電源軌（如 5V、3.3V、1.8V、1.2V）。',
      '透過 <code>:Dev.VOLTAGE</code> 一次讀取多通道數值後，由 <code>:CheckLimit</code> 逐項判定上下限，大幅縮短測試時間。'
    ],
    safety: [
      '任一類比接腳對 GND 絕對耐壓範圍為 <code>±10V</code>。',
      '量測 <code>12V</code> 等高於 10V 的電源軌時，請確認治具端有分壓電阻（如 10kΩ+10kΩ 分壓），或改採兩線差動接法。',
      'RSE 單端模式請將所有待測負極統一接至左側 GND 腳位（Pin 1/4/7/10/13/16）。'
    ],
    steps: [
      '選擇接線模式（RSE 單端或 DIFF 差動）',
      '在接線圖打勾或點選常用電壓（1.8V / 3.3V / 5V / 12V）',
      '確認上下限與名稱後加入測試流程'
    ],
    details: [
      'RSE 模式指令範例：<code>:Dev.VOLTAGE,"RSE,1000,0,1,2"</code>，回傳值依序寫入 Ref 欄變數（以分號換行分隔）。',
      'DIFF 模式成對腳位：AI0=(Pin2, Pin3)、AI1=(Pin5, Pin6)、AI2=(Pin8, Pin9)、AI3=(Pin11, Pin12)。'
    ]
  },
  'FeasaLED': {
    title: 'Feasa LED Analyser 光學色彩與亮度分析儀',
    dll: 'LED_analyser.dll',
    category: 'LED 色彩 / 波長 / 亮度檢測',
    img: '/images/FeasaLED.png',
    hasInteractiveHmi: true,
    hmiType: 'feasa',
    nextLabel: '下一步：開始設定光纖通道與色域 ▶',
    highlights: [
      { label: '主要用途', value: 'LED 色彩波長與亮度檢測' },
      { label: '量測光譜範圍', value: '450nm ~ 650nm（標準可見光）' },
      { label: 'Centimani 指令', value: ':Dev.CaptureAndRead' }
    ],
    specs: [
      { k: '通訊介面', v: 'USB / RS-232（預設鮑率 57600 bps）' },
      { k: '光纖通道數', v: '依機型提供 3 / 5 / 10 / 20 路 1mm 光纖頭' },
      { k: '量測項目', v: '主波長 (nm)、色座標 (xy / RGBI)、相對亮度 (Intensity)' },
      { k: '擷取速度', v: '全通道同步擷取約 102 ms（視 LED 亮度自動調整）' },
      { k: 'Global.ini', v: 'LED_AZ1=COM17, LED_Light1=02' }
    ],
    features: [
      '透過前端 1mm 可撓式光纖導管對準待測板上的指示燈（Power / Wi-Fi / Status LED），可同時平行擷取多顆 LED 的顏色與亮度。',
      '在 Centimani 中使用 <code>:Dev.CaptureAndRead,"01"</code> 擷取指定通道後，於 <code>Ref</code> 寫入 <code>$LED_Wave</code> 與 <code>$LED_Int</code>，並於 <code>Validation</code> 直接比對波長與亮度上下限。',
      '支援 RGBI、HSI（色相/飽和度/亮度）及 CIE xyY 等多種色彩格式輸出，適合區分綠燈、橘燈、藍燈與滅燈狀態。'
    ],
    safety: [
      '光纖探頭前端請對準 LED 正上方並維持固定距離（建議 2~5 mm），避免治具壓傷或折彎光纖導管（最小彎曲半徑限制）。',
      '周圍環境強光或鄰近 LED 漏光會干擾色座標與亮度讀值，建議在治具探頭處加裝遮光套筒。',
      '<code>Instrument</code> 分頁 Settings 格式為 <code>*$(LED_AZ1),57600,*$(LED_Light1)</code>，請確認 COM Port 與實體裝置管理員一致，且測試結束務必執行 <code>:ReleaseDevice</code> 釋放埠口。'
    ],
    steps: [
      '確認 Global.ini 的 LED_AZ1 (COM Port) 與通道編號 (01~20)',
      '在測試步驟設定目標波長範圍（例如綠燈 515 ~ 535 nm）',
      '設定亮度 (Intensity) 最低門檻（例如 1000 ~ 99999）防止 LED 未亮誤判'
    ],
    details: [
      '常見綠燈波長範圍參考：約 515 ~ 535 nm；紅燈：約 615 ~ 640 nm；藍燈：約 455 ~ 475 nm。',
      '若出現亮燈但亮度過低，請優先檢查光纖頭是否偏位、表面是否有髒污，或治具下壓後光纖是否被遮擋。',
      '可將實體外觀照片命名為 FeasaLED.png 放入程式目錄的 IMAGES 資料夾，左側即會自動顯示該照片。'
    ]
  },
  'IPOWER2401': {
    title: 'IPOWER2401 / IPRO800 網路程控電源開關',
    dll: 'iPower2401.dll / iPowerPro800.dll',
    category: '電源控制 (POWERSWITCH)',
    img: '/images/IPOWER2401.png',
    svgIcon: `<svg viewBox="0 0 260 95" style="width:100%;max-height:150px;"><rect x="6" y="15" width="248" height="65" rx="6" fill="#1E293B" stroke="#475569" stroke-width="2"/><rect x="18" y="30" width="38" height="34" rx="4" fill="#0F172A" stroke="#38BDF8"/><text x="37" y="51" fill="#38BDF8" font-size="10" text-anchor="middle" font-weight="bold">OUT 1</text><rect x="66" y="30" width="38" height="34" rx="4" fill="#0F172A" stroke="#38BDF8"/><text x="85" y="51" fill="#38BDF8" font-size="10" text-anchor="middle" font-weight="bold">OUT 2</text><rect x="114" y="30" width="38" height="34" rx="4" fill="#0F172A" stroke="#38BDF8"/><text x="133" y="51" fill="#38BDF8" font-size="10" text-anchor="middle" font-weight="bold">OUT 3</text><rect x="162" y="30" width="38" height="34" rx="4" fill="#0F172A" stroke="#38BDF8"/><text x="181" y="51" fill="#38BDF8" font-size="10" text-anchor="middle" font-weight="bold">OUT 4</text><rect x="212" y="34" width="28" height="26" rx="3" fill="#334155" stroke="#94A3B8"/><text x="226" y="50" fill="#E2E8F0" font-size="8" text-anchor="middle">LAN</text></svg>`,
    hasInteractiveHmi: true,
    hmiType: 'ipower',
    nextLabel: '下一步：設定插座編號與開關時序 ▶',
    highlights: [
      { label: '主要用途', value: 'AC 電源插座程控切換' },
      { label: '控制動作', value: 'SwitchON / SwitchOFF / Cycle' },
      { label: 'Centimani 指令', value: ':Dev.SwitchON / OFF' }
    ],
    specs: [
      { k: '通訊介面', v: 'Ethernet (TCP/IP) 或 RS-232 (IPRO800)' },
      { k: '控制迴路', v: '1 ~ 4 路獨立 AC 電源插座控制' },
      { k: '典型用途', v: 'DUT 上電開機、Reboot 斷電重啟、End Test 斷電' }
    ],
    features: [
      '可在測試腳本中自動控制待測物電源開關，實現全自動 Reboot 與異常斷電保護。',
      '搭配 <code>:Delay</code> 指令控制斷電放電等待時間（建議 500~2000ms），避免殘餘電容影響開機狀態。'
    ],
    safety: [
      '若多個工槽位共用同一台 IPOWER，請確認各槽位對應的 Outlet 插座編號 (1~4) 不可重複。',
      'Phase 97 收尾階段建議固定執行 <code>:Dev.SwitchOFF</code> 確保人員取放板時安全斷電。'
    ],
    steps: [
      '選擇要控制的插座編號 (Outlet 1 ~ 4)',
      '選擇控制動作（Power Cycle 斷電重啟 / ON / OFF）',
      '設定延遲等待時間 (ms) 後加入測試流程'
    ]
  },
  'MDA2700': {
    title: 'MDA2700 / 34401A 數位電表與資料擷取器',
    dll: 'MDA2700.dll / Agilent34401A.dll',
    category: '精密電壓 / 電流 / 電阻量測 (DMM / DAQ)',
    img: '/images/MDA2700.png',
    svgIcon: `<svg viewBox="0 0 260 95" style="width:100%;max-height:150px;"><rect x="8" y="12" width="244" height="72" rx="6" fill="#E2E8F0" stroke="#64748B" stroke-width="2"/><rect x="20" y="24" width="130" height="36" rx="4" fill="#0F172A"/><text x="85" y="47" fill="#4ADE80" font-size="14" font-family="Consolas,monospace" text-anchor="middle" font-weight="bold">+03.3021 VDC</text><circle cx="176" cy="42" r="8" fill="#DC2626"/><text x="176" y="62" fill="#334155" font-size="8" text-anchor="middle">HI</text><circle cx="204" cy="42" r="8" fill="#0F172A"/><text x="204" y="62" fill="#334155" font-size="8" text-anchor="middle">LO</text><circle cx="232" cy="42" r="8" fill="#2563EB"/><text x="232" y="62" fill="#334155" font-size="8" text-anchor="middle">AMPS</text></svg>`,
    hasInteractiveHmi: true,
    hmiType: 'dmm',
    nextLabel: '下一步：設定量測功能與上下限 ▶',
    highlights: [
      { label: '主要用途', value: '高精度電壓 / 電流 / 電阻量測' },
      { label: '量測精度', value: '6.5 位元高解析度' },
      { label: '通訊介面', v: 'GPIB / LAN / USB', value: 'GPIB / LAN' }
    ],
    specs: [
      { k: '支援功能', v: 'DCV 直流電壓、ACV 交流電壓、DCI 電流、RES 電阻' },
      { k: '通訊介面', v: 'GPIB (GPIB0::16::INSTR) / LAN' },
      { k: '適用場景', v: '靜態功耗電流 (uA/mA)、高壓電源軌、精密分壓點' }
    ],
    features: [
      '相較於 NI-6009，數位電表支援更高耐壓與微安培級電流（Sleep/Standby Current）量測。',
      '透過 <code>:Dev.Measure</code> 讀取數值並直接於 <code>Validation</code> 判定合格上下限。'
    ],
    safety: [
      '量測電流 (DCI) 時務必確認治具端測試點與電表串聯接線正確，避免電源直接對電流檔短路燒毀保險絲。'
    ],
    steps: [
      '選擇量測模式（DCV / ACV / DCI / RES）與通道',
      '設定變數名稱與合格上下限（Min ~ Max）',
      '確認後加入測試流程'
    ]
  },
  'DIO6509': {
    title: 'NI PCI-6509 96 通道工業數位 I/O 卡',
    dll: 'DigitIO6509.dll',
    category: '數位 I/O 控制與讀取 (DIO)',
    img: '/images/DIO6509.png',
    svgIcon: `<svg viewBox="0 0 260 95" style="width:100%;max-height:150px;"><rect x="14" y="14" width="232" height="66" rx="5" fill="#166534" stroke="#14532D" stroke-width="2"/><rect x="28" y="28" width="90" height="24" rx="3" fill="#CBD5E1" stroke="#475569"/><text x="73" y="44" fill="#0F172A" font-size="9" text-anchor="middle" font-weight="bold">100-Pin Port A</text><rect x="142" y="28" width="90" height="24" rx="3" fill="#CBD5E1" stroke="#475569"/><text x="187" y="44" fill="#0F172A" font-size="9" text-anchor="middle" font-weight="bold">100-Pin Port B</text><text x="130" y="70" fill="#DCFCE7" font-size="9" text-anchor="middle">NI PCI-6509 (P0.0 ~ P11.7)</text></svg>`,
    hasInteractiveHmi: true,
    hmiType: 'dio',
    nextLabel: '下一步：設定 DIO 腳位與電位 ▶',
    highlights: [
      { label: '主要用途', value: '治具繼電器切換 / 按鍵與 GPIO 檢測' },
      { label: '通道數', value: '96 路 TTL 數位 I/O' },
      { label: '通訊介面', value: 'PCI (Dev1 / Dev2)' }
    ],
    specs: [
      { k: '電氣準位', v: '5V TTL / CMOS 相容' },
      { k: '典型用途', v: '控制氣缸電磁閥、切換量測繼電器、讀取治具到位感測器' }
    ],
    features: [
      '可於腳本中精準切換個別數位輸出腳位的高/低電位 (High/Low)，或讀取感測器狀態並進行判斷。'
    ],
    safety: [
      '確認 DIO 腳位驅動外部繼電器時需經過光耦合或電晶體緩衝，勿直接驅動大電流線圈。'
    ],
    steps: [
      '點選目標 Port 與 Bit 腳位（P0.0 ~ P0.7）',
      '選擇動作（輸出 High / 輸出 Low / 讀取狀態）',
      '加入測試流程'
    ]
  },
  'InstIQApiA': {
    title: 'LitePoint IQxel / MT8870A 射頻綜合測試儀',
    dll: 'InstIQApi_A.dll / InstIQApi_B.dll',
    category: 'Wi-Fi / Bluetooth 射頻測試 (RF)',
    img: '/images/InstIQApiA.png',
    svgIcon: `<svg viewBox="0 0 260 95" style="width:100%;max-height:150px;"><rect x="8" y="14" width="244" height="68" rx="6" fill="#0F172A" stroke="#334155" stroke-width="2"/><rect x="20" y="24" width="84" height="46" rx="4" fill="#1E293B" stroke="#38BDF8"/><text x="62" y="45" fill="#38BDF8" font-size="11" text-anchor="middle" font-weight="bold">IQxel RF</text><text x="62" y="60" fill="#94A3B8" font-size="8" text-anchor="middle">2.4G / 5G / 6G</text><circle cx="136" cy="47" r="10" fill="#F59E0B" stroke="#FDE68A" stroke-width="2"/><text x="136" y="72" fill="#CBD5E1" font-size="8" text-anchor="middle">RF1</text><circle cx="172" cy="47" r="10" fill="#F59E0B" stroke="#FDE68A" stroke-width="2"/><text x="172" y="72" fill="#CBD5E1" font-size="8" text-anchor="middle">RF2</text><circle cx="208" cy="47" r="10" fill="#64748B" stroke="#CBD5E1" stroke-width="2"/><text x="208" y="72" fill="#CBD5E1" font-size="8" text-anchor="middle">RF3</text></svg>`,
    hasInteractiveHmi: true,
    hmiType: 'rf',
    nextLabel: '下一步：設定 RF 頻段與功率門檻 ▶',
    highlights: [
      { label: '主要用途', value: 'Wi-Fi / BT Tx 功率、EVM 與 Rx PER 測試' },
      { label: '支援頻段', value: '2.4GHz / 5GHz / 6GHz' },
      { label: '必備搭配', value: 'PathLoss.ini 線損補償' }
    ],
    specs: [
      { k: '通訊介面', v: 'Ethernet (192.168.100.254)' },
      { k: 'RF 連接線', v: 'SMA / IPEX 同軸測試線接至 IQxel RF1 / RF2 埠' },
      { k: '量測項目', v: 'Tx Power (dBm)、EVM (dB)、Freq Error (ppm)、Rx PER (%)' },
      { k: 'Settings', v: '192.168.100.254,1,2,1,60000,PathLoss.ini' }
    ],
    features: [
      '採用「主站呼叫列 ＋ Marco 子工作表」標準架構：主站僅放測試條件參數，實際下板子指令 (<code>LAN@wl</code>) 與儀器量測封裝在 <code>WIFI Tx MCS</code> (21 步) / <code>WIFI Rx MCS</code> (22 步)。',
      '可一次量測 Tx Power、Frequency Error (±20ppm)、EVM，以及 Rx 封包接收率 (PER / RxOK)。'
    ],
    safety: [
      'RF 接線路徑：DUT 天線座 (IPEX / SMA) →（視需要經 RFSwitch3001 或衰減器）→ IQxel 前面板 <code>RF1A / RF2A</code>，並於 <code>PathLoss.ini</code> 填寫各頻段線損補償 (dB)。',
      '控制接線：測試 PC 透過 RJ45 網路線連接 IQxel LAN 埠（預設 <code>192.168.100.254</code>），並另以 LAN / UART 控制待測板 (DUT) 發包與收包。',
      'RF 埠口最大輸入功率一般為 +30 dBm，直連大功率 PA 前請務必確認衰減器與 <code>PathLoss.ini</code> 設定。'
    ],
    steps: [
      '確認 RF 同軸線與 LAN 控制線 (192.168.100.254) 連接正確',
      '於右側設定 Tx (Power / EVM) 與 Rx (VSG 準位) 測項清單',
      '加入流程並自動補齊 WIFI Tx MCS (21 步) / Rx MCS (22 步) Marco'
    ],
    details: [
      'Settings 欄位格式 <code>IP,PortA,PortB,Mode,Timeout,PathLoss</code>：預設 <code>192.168.100.254,1,2,1,60000,PathLoss.ini</code>。',
      'Tx 量測核心指令：<code>:Dev.MeasWIFI,"{Chain}","11n_MCS{MCS}_{BW}","*(Channel)","{TargetPwr}","0",""</code>，回傳 <code>Power</code>、<code>FreqErrPPM</code>、<code>EVM</code>。',
      'Rx 發包核心指令：<code>:Dev.GenWIFI,"{Chain}","11n_MCS{MCS}_{BW}","*(Channel)","{RxLevel}","1000","0"</code>，搭配 <code>LAN@wl counters</code> 驗證 <code>RxOK</code>。'
    ]
  }
};
INST_INTRO_PROFILES['IPRO800'] = Object.assign({}, INST_INTRO_PROFILES['IPOWER2401'], { img: '/images/IPRO800.png' });
INST_INTRO_PROFILES['Agilent34401A'] = Object.assign({}, INST_INTRO_PROFILES['MDA2700'], { img: '/images/Agilent34401A.png' });
INST_INTRO_PROFILES['GDM906x'] = Object.assign({}, INST_INTRO_PROFILES['MDA2700'], { img: '/images/GDM906x.png' });
INST_INTRO_PROFILES['XelM8-B'] = Object.assign({}, INST_INTRO_PROFILES['InstIQApiA'], { img: '/images/XelM8-B.png' });
INST_INTRO_PROFILES['MT8870A'] = Object.assign({}, INST_INTRO_PROFILES['InstIQApiA'], { img: '/images/MT8870A.png' });

function setIntroFontSize(sz) {
  const valid = [13, 15, 17, 19].includes(sz) ? sz : 15;
  INTRO_STATE.fontSize = valid;
  localStorage.setItem('centimani_intro_font_size', String(valid));
  [13, 15, 17, 19].forEach(s => {
    ['introFs' + s, 'hmiFs' + s].forEach(bid => {
      const btn = document.getElementById(bid);
      if (!btn) return;
      if (s === valid) {
        btn.style.background = '#2563EB';
        btn.style.color = '#FFFFFF';
        btn.style.borderColor = '#1D4ED8';
        btn.style.fontWeight = '700';
      } else {
        btn.style.background = '#FFFFFF';
        btn.style.color = '#334155';
        btn.style.borderColor = '#CBD5E1';
        btn.style.fontWeight = '500';
      }
    });
  });
  document.body.style.fontSize = valid + 'px';
  document.documentElement.style.setProperty('--app-font-size', valid + 'px');
  document.querySelectorAll('.intro-scalable-text, .flow-guide-desc').forEach(el => {
    el.style.fontSize = valid + 'px';
  });
  document.querySelectorAll('.intro-spec-table').forEach(el => {
    el.style.fontSize = Math.max(12, valid - 1) + 'px';
  });
  const hmiL = document.getElementById('instHmiLeft');
  const hmiR = document.getElementById('instHmiRight');
  if (hmiL) hmiL.style.fontSize = valid + 'px';
  if (hmiR) hmiR.style.fontSize = valid + 'px';
}

function buildGenericProfile(instName) {
  const meta = (STATE.instrumentCatalog || []).find(i => i.Name === instName) || {};
  return {
    title: `${instName}${meta.Desc ? ' — ' + meta.Desc : ''}`,
    dll: meta.ControlDLL || 'Standard.dll',
    category: meta.Functions || '通用儀器',
    img: `/images/${encodeURIComponent(instName)}.png`,
    hasInteractiveHmi: false,
    nextLabel: '返回繼續設定 ▶',
    highlights: [
      { label: '儀器名稱', value: instName },
      { label: '控制函式庫', value: meta.ControlDLL || '-' },
      { label: '支援功能', value: meta.Functions || '-' }
    ],
    specs: [
      { k: 'Instrument 名稱', v: instName },
      { k: 'ControlDLL', v: meta.ControlDLL || '-' },
      { k: 'Settings 預設', v: meta.Settings || '-' },
      { k: 'Functions', v: meta.Functions || '-' },
      { k: '建議版本', v: meta.Version || '1.0.0.0' }
    ],
    features: [
      `此儀器透過 <code>${meta.ControlDLL || 'ControlDLL'}</code> 與 Centimani 溝通，對應功能欄位為 <code>${meta.Functions || '-'}</code>。`,
      '建議依標準流程包夾 <code>:ObtainDevice</code> 與 <code>:ReleaseDevice</code>，確保多工槽位平行測試時不發生資源搶佔。'
    ],
    safety: [
      '請確認 Instrument 分頁的 Mount 欄位已正確掛載到目標測試站位，且 Settings 內的 IP / COM Port / GPIB 位址與 Global.ini 一致。',
      '尚未為此儀器建立專屬圖解介紹時，將自動套用共用公版規格卡。'
    ],
    steps: [
      '確認 Global.ini 內的連線位址設定',
      '確認 Instrument 分頁的 DLL 版本與 Mount 站別',
      '設定測項上下限並加入測試流程'
    ],
    details: [
      `可將 ${instName}.png 放入 IMAGES 資料夾，左側卡片即會自動載入實體儀器照片。`
    ]
  };
}

function openInstIntroPage(targetMode, instName = 'NI6008', editGenIdx = -1) {
  INTRO_STATE.targetMode = targetMode || 'audit';
  INTRO_STATE.instName = instName || 'NI6008';
  INTRO_STATE.editGenIdx = editGenIdx;
  const baseInst = resolveBaseInstName(INTRO_STATE.instName);
  const prof = INST_INTRO_PROFILES[baseInst] || buildGenericProfile(INTRO_STATE.instName);
  const fs = INTRO_STATE.fontSize || 15;

  document.getElementById('introPageTitle').textContent = `📖 儀器介紹：${prof.title} (${prof.dll})`;
  const nextBtn = document.getElementById('introNextBtn');
  if (nextBtn) nextBtn.textContent = prof.nextLabel || '下一步：開始設定 ▶';

  const specsHtml = (prof.specs || []).map(sp => `
    <tr>
      <td style="padding:5px 6px; font-weight:700; color:#475569; width:96px; border-bottom:1px solid #E2E8F0; vertical-align:top;">${sp.k}</td>
      <td style="padding:5px 6px; color:#0F172A; border-bottom:1px solid #E2E8F0;">${sp.v}</td>
    </tr>
  `).join('');

  const highlightsHtml = (prof.highlights || []).map(h => `
    <div style="flex:1; min-width:150px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:8px 10px;">
      <div style="font-size:0.77rem; color:#64748B; font-weight:700;">${h.label}</div>
      <div class="mono" style="font-size:0.9rem; color:#0F172A; font-weight:700; margin-top:2px;">${h.value}</div>
    </div>
  `).join('');

  const stepsHtml = (prof.steps || []).map((st, idx) => `
    <div style="flex:1; min-width:160px; display:flex; align-items:flex-start; gap:8px; background:#F0F9FF; border:1px solid #BAE6FD; border-radius:6px; padding:8px 10px;">
      <span style="flex-shrink:0; width:22px; height:22px; border-radius:999px; background:#0284C7; color:#FFFFFF; font-weight:700; font-size:0.8rem; display:inline-flex; align-items:center; justify-content:center;">${idx + 1}</span>
      <span class="intro-scalable-text" style="font-size:${fs}px; color:#0C4A6E; line-height:1.45;">${st}</span>
    </div>
  `).join('');

  const detailsHtml = (prof.details && prof.details.length) ? `
    <details style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:10px 14px;">
      <summary style="cursor:pointer; font-weight:700; color:#334155; font-size:0.9rem;">📚 進階指令與參數補充說明（點擊展開）</summary>
      <ul class="intro-scalable-text" style="margin:8px 0 0 18px; padding:0; font-size:${fs}px; color:#334155; line-height:1.65;">
        ${prof.details.map(d => `<li style="margin-bottom:4px;">${d}</li>`).join('')}
      </ul>
    </details>
  ` : '';

  document.getElementById('introPageBody').innerHTML = `
    <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:14px;">
      <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px; text-align:center; margin-bottom:10px; min-height:175px; display:flex; flex-direction:column; align-items:center; justify-content:center;">
        <img src="${prof.img}" alt="${prof.title}"
             style="max-height:185px; max-width:100%; border-radius:6px; object-fit:contain;"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
        <div style="display:none; flex-direction:column; align-items:center; justify-content:center; color:#64748B; padding:12px 10px; gap:6px; width:100%;">
          ${prof.svgIcon || '<div style="font-size:2.4rem;">📷</div>'}
          <div style="font-weight:700; font-size:0.87rem; color:#334155;">${prof.title}</div>
          <div style="font-size:0.77rem; color:#64748B;">可放置實體照片至 <code class="mono">IMAGES/${instName}.png</code></div>
        </div>
      </div>
      <div style="font-weight:700; font-size:0.9rem; color:#0F172A; margin-bottom:6px;">📋 硬體規格摘要</div>
      <table class="intro-spec-table" style="width:100%; border-collapse:collapse; font-size:${Math.max(12, fs - 1)}px;">
        <tbody>${specsHtml}</tbody>
      </table>
    </div>
    <div style="display:flex; flex-direction:column; gap:12px;">
      <div style="display:flex; gap:8px; flex-wrap:wrap;">${highlightsHtml}</div>
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:14px 16px;">
        <div style="font-weight:700; font-size:1rem; color:#0F172A; margin-bottom:6px;">📌 主要特色與 Centimani 應用方式</div>
        <ul class="intro-scalable-text" style="margin:0 0 0 18px; padding:0; font-size:${fs}px; color:#334155; line-height:1.65;">
          ${prof.features.map(f => `<li style="margin-bottom:4px;">${f}</li>`).join('')}
        </ul>
      </div>
      <div style="background:#FFFBEB; border:1.5px solid #F59E0B; border-radius:8px; padding:14px 16px;">
        <div style="font-weight:700; font-size:1rem; color:#92400E; margin-bottom:6px;">⚠️ 硬體安全與接線須知</div>
        <ul class="intro-scalable-text" style="margin:0 0 0 18px; padding:0; font-size:${fs}px; color:#78350F; line-height:1.65;">
          ${prof.safety.map(s => `<li style="margin-bottom:4px;">${s}</li>`).join('')}
        </ul>
      </div>
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px 14px;">
        <div style="font-weight:700; font-size:0.93rem; color:#0F172A; margin-bottom:8px;">🧭 設定流程預覽</div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">${stepsHtml}</div>
      </div>
      ${detailsHtml}
      <div style="display:flex; justify-content:flex-end;">
        <button onclick="proceedFromIntroToConfig()" class="btn btn-primary-green" style="padding:9px 20px; font-size:0.97rem;">
          ${prof.nextLabel || '下一步：開始設定 ▶'}
        </button>
      </div>
    </div>
  `;

  setIntroFontSize(fs);
  ['panelHome', 'panelAudit', 'panelGen', 'panelDiagnose', 'panelTic', 'panelFlowGuide', 'panelSettings', 'panelNi6009', 'panelInstHmi'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
  document.getElementById('panelInstIntro').style.display = 'block';
}

function closeInstIntroPage() {
  document.getElementById('panelInstIntro').style.display = 'none';
  document.getElementById('panelGen').style.display = 'block';
  if (typeof switchGenSubMode === 'function') {
    if (INTRO_STATE.targetMode === 'gen' || INTRO_STATE.targetMode === 'wiz_volt') {
      switchGenSubMode('create');
    } else if (INTRO_STATE.targetMode === 'tab3') {
      switchGenSubMode('inst');
    } else {
      switchGenSubMode('edit');
    }
  }
}

function proceedFromIntroToConfig() {
  document.getElementById('panelInstIntro').style.display = 'none';
  const baseInst = resolveBaseInstName(INTRO_STATE.instName);
  const prof = INST_INTRO_PROFILES[baseInst];
  if (prof && prof.hasInteractiveHmi) {
    if (baseInst === 'NI6008') {
      openNi6009Hmi(INTRO_STATE.targetMode, INTRO_STATE.editGenIdx, INTRO_STATE.instName);
    } else {
      openInstHmi(INTRO_STATE.targetMode, INTRO_STATE.instName);
    }
  } else {
    closeInstIntroPage();
  }
}

const INST_HMI_STATE = {
  targetMode: 'audit',
  instName: 'FeasaLED',
  hmiType: 'feasa',
  // FeasaLED (支援多顆 RGB / 多通道批次設定)
  feasaCh: '01',
  feasaColor: 'green',
  feasaCom: 'COM17',
  feasaWaveMin: '515',
  feasaWaveMax: '535',
  feasaIntMin: '1000',
  feasaIntMax: '99999',
  feasaItems: [
    { ch: '01', color: 'green', label: 'Green LED', waveMin: '515', waveMax: '535', intMin: '1000', intMax: '99999' }
  ],
  // IPOWER
  pwrOutlet: '1',
  pwrAction: 'cycle',
  pwrDelay: '1000',
  // DMM
  dmmFunc: 'DCV',
  dmmCh: '1',
  dmmVar: 'DMM_VAL',
  dmmMin: '3.15',
  dmmMax: '3.45',
  // DIO
  dioPin: 'P0.0',
  dioMode: 'high',
  // RF (IQxel / MT8870A)
  rfSettings: '192.168.100.254,1,2,1,60000,PathLoss.ini',
  rfTxTests: [
    { channel: '3', bw: '20', mcs: '7', antenna: '1', target_pwr: '15', pwr_min: '13', pwr_max: '17', evm_min: '-50', evm_max: '-28' }
  ],
  rfRxTests: [
    { channel: '5', bw: '40', mcs: '7', antenna: '1', rx_level: '-59' }
  ],
  titleName: ''
};

function openInstHmi(targetMode, instName) {
  const baseInst = resolveBaseInstName(instName);
  const prof = INST_INTRO_PROFILES[baseInst] || buildGenericProfile(instName);
  INST_HMI_STATE.targetMode = targetMode || 'audit';
  INST_HMI_STATE.instName = instName;
  INST_HMI_STATE.hmiType = prof.hmiType || 'feasa';

  if (INST_HMI_STATE.hmiType === 'feasa') INST_HMI_STATE.titleName = 'Check LED Color & Intensity';
  else if (INST_HMI_STATE.hmiType === 'ipower') INST_HMI_STATE.titleName = `${instName} Power Control`;
  else if (INST_HMI_STATE.hmiType === 'dmm') INST_HMI_STATE.titleName = `${instName} Precision Measure`;
  else if (INST_HMI_STATE.hmiType === 'dio') INST_HMI_STATE.titleName = `${instName} Digital IO Control`;
  else if (INST_HMI_STATE.hmiType === 'rf') INST_HMI_STATE.titleName = `${instName} WiFi RF Test`;

  document.getElementById('instHmiTitle').textContent = `🎛️ ${prof.title} — 互動式人機設定`;

  const tBar = document.getElementById('instHmiTargetBar');
  if (INST_HMI_STATE.targetMode === 'audit' && STATE.workspace) {
    tBar.style.display = 'flex';
    const stNames = Object.keys(STATE.workspace.stations || {});
    const sSel = document.getElementById('instHmiSheetSel');
    sSel.innerHTML = stNames.map(n => `<option value="${n}">${n}</option>`).join('');
    const modalSheet = document.getElementById('iiSheetSel') ? document.getElementById('iiSheetSel').value : '';
    if (modalSheet && STATE.workspace.stations[modalSheet]) sSel.value = modalSheet;
    else if (STATE.activeSheetFilter && STATE.activeSheetFilter !== 'ALL' && STATE.workspace.stations[STATE.activeSheetFilter]) sSel.value = STATE.activeSheetFilter;
    onInstHmiSheetChange();
  } else {
    tBar.style.display = 'none';
  }

  renderInstHmi();
  setIntroFontSize(INTRO_STATE.fontSize || 15);
  ['panelHome', 'panelAudit', 'panelGen', 'panelDiagnose', 'panelTic', 'panelFlowGuide', 'panelSettings', 'panelInstIntro', 'panelNi6009'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
  document.getElementById('panelInstHmi').style.display = 'block';
}

function closeInstHmi() {
  document.getElementById('panelInstHmi').style.display = 'none';
  document.getElementById('panelGen').style.display = 'block';
  if (typeof switchGenSubMode === 'function') {
    if (INST_HMI_STATE.targetMode === 'gen' || INST_HMI_STATE.targetMode === 'wiz_volt') {
      switchGenSubMode('create');
    } else if (INST_HMI_STATE.targetMode === 'tab3') {
      switchGenSubMode('inst');
    } else {
      switchGenSubMode('edit');
    }
  }
}

function onInstHmiSheetChange() {
  const stName = document.getElementById('instHmiSheetSel').value;
  const blks = _jeBuildTitleBlocks((STATE.workspace.stations || {})[stName] || []);
  const aSel = document.getElementById('instHmiAfterSel');
  let opts = '<option value="-1">（插在 Phase 97 之前 / 最後一個測項之後）</option>';
  blks.forEach((b, i) => {
    opts += `<option value="${i}">插在 [${i + 1}] ${b.title} 之後</option>`;
  });
  aSel.innerHTML = opts;
}

const FEASA_COLOR_PRESETS = {
  green:  { label: 'Green LED', wmin: '515', wmax: '535', imin: '1000', imax: '99999', title: 'Check Green LED' },
  red:    { label: 'Red LED',   wmin: '615', wmax: '640', imin: '1000', imax: '99999', title: 'Check Red LED' },
  blue:   { label: 'Blue LED',  wmin: '455', wmax: '475', imin: '1000', imax: '99999', title: 'Check Blue LED' },
  yellow: { label: 'Amber LED', wmin: '580', wmax: '600', imin: '1000', imax: '99999', title: 'Check Amber LED' },
  white:  { label: 'White LED', wmin: '400', wmax: '700', imin: '1500', imax: '99999', title: 'Check White LED Intensity' }
};

function setFeasaColorPreset(colorKey) {
  INST_HMI_STATE.feasaColor = colorKey;
  const p = FEASA_COLOR_PRESETS[colorKey] || FEASA_COLOR_PRESETS.green;
  INST_HMI_STATE.feasaWaveMin = p.wmin;
  INST_HMI_STATE.feasaWaveMax = p.wmax;
  INST_HMI_STATE.feasaIntMin = p.imin;
  INST_HMI_STATE.feasaIntMax = p.imax;
  if (!INST_HMI_STATE.feasaItems || INST_HMI_STATE.feasaItems.length === 0) {
    INST_HMI_STATE.feasaItems = [{ ch: INST_HMI_STATE.feasaCh || '01', color: colorKey, label: p.label, waveMin: p.wmin, waveMax: p.wmax, intMin: p.imin, intMax: p.imax }];
  } else {
    const target = INST_HMI_STATE.feasaItems[0];
    target.color = colorKey;
    target.label = p.label;
    target.waveMin = p.wmin;
    target.waveMax = p.wmax;
    target.intMin = p.imin;
    target.intMax = p.imax;
  }
  INST_HMI_STATE.titleName = INST_HMI_STATE.feasaItems.length > 1 ? 'Check Multi-Color LEDs' : p.title;
  renderInstHmi();
}

function addFeasaColorItem(colorKey) {
  const p = FEASA_COLOR_PRESETS[colorKey] || FEASA_COLOR_PRESETS.green;
  INST_HMI_STATE.feasaItems = INST_HMI_STATE.feasaItems || [];
  // Find next unused channel starting from selected feasaCh or 01..10
  const used = new Set(INST_HMI_STATE.feasaItems.map(x => x.ch));
  let ch = String(INST_HMI_STATE.feasaCh || '01').padStart(2, '0');
  if (used.has(ch)) {
    for (let i = 1; i <= 10; i++) {
      const cand = String(i).padStart(2, '0');
      if (!used.has(cand)) { ch = cand; break; }
    }
  }
  INST_HMI_STATE.feasaItems.push({
    ch, color: colorKey, label: p.label,
    waveMin: p.wmin, waveMax: p.wmax, intMin: p.imin, intMax: p.imax
  });
  INST_HMI_STATE.titleName = INST_HMI_STATE.feasaItems.length > 1 ? 'Check Multi-Color LEDs' : p.title;
  renderInstHmi();
}

function addFeasaRgbPreset() {
  INST_HMI_STATE.feasaItems = [
    { ch: '01', color: 'red',   label: 'Red LED',   waveMin: '615', waveMax: '640', intMin: '1000', intMax: '99999' },
    { ch: '02', color: 'green', label: 'Green LED', waveMin: '515', waveMax: '535', intMin: '1000', intMax: '99999' },
    { ch: '03', color: 'blue',  label: 'Blue LED',  waveMin: '455', waveMax: '475', intMin: '1000', intMax: '99999' }
  ];
  INST_HMI_STATE.titleName = 'Check RGB LEDs (Ch01~03)';
  renderInstHmi();
}

function buildInstHmiPayload() {
  const s = INST_HMI_STATE;
  const t = s.hmiType;
  let steps = [];
  let globalsPatch = null;
  let dl = '';
  let ul = '';

  if (t === 'feasa') {
    const items = (s.feasaItems && s.feasaItems.length > 0)
      ? s.feasaItems
      : [{ ch: String(s.feasaCh || '01').padStart(2, '0'), label: 'LED', waveMin: s.feasaWaveMin, waveMax: s.feasaWaveMax, intMin: s.feasaIntMin, intMax: s.feasaIntMax }];
    const first = items[0];
    dl = first.waveMin;
    ul = first.waveMax;
    globalsPatch = { Settings: { LED_AZ1: s.feasaCom || 'COM17', LED_Light1: String(first.ch).padStart(2, '0') } };
    steps.push({ Instrument: 'LED_Test', Send: ':ObtainDevice', ExecMode: '0', Description: 'LED#-#Obtain Feasa LED Lock', TestID: 'BRME027' });
    items.forEach(it => {
      const ch = String(it.ch).padStart(2, '0');
      steps.push({
        Instrument: 'LED_Test',
        Send: `:Dev.CaptureAndRead,"${ch}"`,
        Ref: '$LED_Wave;\n$LED_Int',
        Validation: `(LED_Wave,%f,${it.waveMin},${it.waveMax});\n(LED_Int,%f,${it.intMin},${it.intMax})`,
        ExecMode: '2:0',
        Description: `LED#-#Ch${ch} ${it.label || 'LED'} (${it.waveMin}~${it.waveMax}nm) & Intensity`,
        TestID: 'IOLE015'
      });
    });
    steps.push({ Instrument: 'LED_Test', Send: ':ReleaseDevice', ExecMode: '3', Description: 'LED#-#Release Feasa LED Lock', TestID: 'BRME027' });
  } else if (t === 'ipower') {
    const out = s.pwrOutlet || '1';
    steps.push({ Instrument: s.instName, Send: ':ObtainDevice', ExecMode: '1', Description: `PC#-#Obtain ${s.instName}`, TestID: 'B7PL025' });
    if (s.pwrAction === 'cycle') {
      steps.push({ Instrument: s.instName, Send: `:Dev.SwitchOFF,"${out}"`, ExecMode: '1', Description: `PC#-#${s.instName} Outlet ${out} OFF`, TestID: 'B7PL025' });
      steps.push({ Instrument: '', Send: `:Delay,"${s.pwrDelay || '1000'}"`, ExecMode: '0', Description: 'PC#-#Wait Power Discharge', TestID: 'B7PL025' });
      steps.push({ Instrument: s.instName, Send: `:Dev.SwitchON,"${out}"`, ExecMode: '1', Description: `PC#-#${s.instName} Outlet ${out} ON`, TestID: 'B7PL025' });
    } else if (s.pwrAction === 'on') {
      steps.push({ Instrument: s.instName, Send: `:Dev.SwitchON,"${out}"`, ExecMode: '1', Description: `PC#-#${s.instName} Outlet ${out} ON`, TestID: 'B7PL025' });
    } else {
      steps.push({ Instrument: s.instName, Send: `:Dev.SwitchOFF,"${out}"`, ExecMode: '1', Description: `PC#-#${s.instName} Outlet ${out} OFF`, TestID: 'B7PL025' });
    }
    steps.push({ Instrument: s.instName, Send: ':ReleaseDevice', ExecMode: '3', Description: `PC#-#Release ${s.instName}`, TestID: 'B7PL025' });
  } else if (t === 'dmm') {
    dl = s.dmmMin; ul = s.dmmMax;
    const vname = (s.dmmVar || 'DMM_VAL').trim();
    steps = [
      { Instrument: s.instName, Send: ':ObtainDevice', ExecMode: '0', Description: `INST#-#Obtain ${s.instName}`, TestID: 'B7PL025' },
      { Instrument: s.instName, Send: `:Dev.${s.dmmFunc},"${s.dmmCh || '1'}"`, Ref: `$${vname}`, Validation: `(${vname},%f,${s.dmmMin},${s.dmmMax})`, ExecMode: '2:0', Description: `DUT#-#${s.dmmFunc} Ch${s.dmmCh} (${s.dmmMin}~${s.dmmMax})`, TestID: 'BRPW024' },
      { Instrument: s.instName, Send: ':ReleaseDevice', ExecMode: '3', Description: `INST#-#Release ${s.instName}`, TestID: 'B7PL025' }
    ];
  } else if (t === 'dio') {
    const cmd = s.dioMode === 'high' ? `:Dev.SetHigh,"${s.dioPin}"` : (s.dioMode === 'low' ? `:Dev.SetLow,"${s.dioPin}"` : `:Dev.ReadBit,"${s.dioPin}"`);
    const val = s.dioMode === 'read' ? `(DIO_${s.dioPin.replace('.','_')},%d,1,1)` : '';
    steps = [
      { Instrument: s.instName, Send: ':ObtainDevice', ExecMode: '0', Description: `INST#-#Obtain ${s.instName}`, TestID: 'B7PL025' },
      { Instrument: s.instName, Send: cmd, Validation: val, ExecMode: s.dioMode === 'read' ? '2:0' : '1', Description: `FIX#-#DIO ${s.dioPin} ${s.dioMode.toUpperCase()}`, TestID: 'B7PL025' },
      { Instrument: s.instName, Send: ':ReleaseDevice', ExecMode: '3', Description: `INST#-#Release ${s.instName}`, TestID: 'B7PL025' }
    ];
  } else if (t === 'rf') {
    (s.rfTxTests || []).forEach(tx => {
      const lbl = `WIFI TX_CH${tx.channel} MCS${tx.mcs}_BW${tx.bw}`;
      steps.push({ Instrument: 'MeasWIFI', Send: `${tx.channel},${tx.bw},${tx.mcs},${tx.antenna},${tx.target_pwr},${tx.pwr_min},${tx.pwr_max},${tx.evm_min},${tx.evm_max},${lbl}`, Ref: 'Marco: WIFI Tx MCS', Validation: `Pwr ${tx.pwr_min}~${tx.pwr_max}, EVM<=${tx.evm_max}`, ExecMode: '1' });
    });
    (s.rfRxTests || []).forEach(rx => {
      const lbl = `WIFI RX_CH${rx.channel} MCS${rx.mcs}_BW${rx.bw}`;
      steps.push({ Instrument: 'GenWIFI', Send: `${rx.channel},${rx.bw},${rx.mcs},${rx.antenna},${rx.rx_level},${lbl}`, Ref: 'Marco: WIFI Rx MCS', Validation: 'RxOK 900~1000', ExecMode: '1' });
    });
  }
  return { steps, globalsPatch, dl, ul };
}

function renderInstHmi() {
  const s = INST_HMI_STATE;
  const prof = INST_INTRO_PROFILES[resolveBaseInstName(s.instName)] || buildGenericProfile(s.instName);
  const left = document.getElementById('instHmiLeft');
  const right = document.getElementById('instHmiRight');

  let leftPicker = '';
  let rightControls = '';

  if (s.hmiType === 'feasa') {
    const items = s.feasaItems || [];
    const usedSet = new Set(items.map(x => String(x.ch).padStart(2, '0')));
    const chButtons = Array.from({length: 10}, (_, i) => {
      const ch = String(i + 1).padStart(2, '0');
      const active = s.feasaCh === ch;
      const inList = usedSet.has(ch);
      return `<button onclick="INST_HMI_STATE.feasaCh='${ch}';renderInstHmi();" class="btn" style="padding:5px 9px; font-size:0.8rem; ${active ? 'background:#2563EB;color:#fff;border-color:#1D4ED8;font-weight:700;' : (inList ? 'background:#DCFCE7;color:#166534;border-color:#22C55E;font-weight:700;' : 'background:#F8FAFC;color:#334155;')}">Ch ${ch}${inList ? ' ✓' : ''}</button>`;
    }).join('');
    leftPicker = `
      <div style="font-weight:700; font-size:0.87rem; color:#0F172A; margin:8px 0 6px;">💡 點選光纖測試通道（Ch 01 ~ 10，綠底 ✓ 代表已加入清單）：</div>
      <div style="display:grid; grid-template-columns:repeat(5, 1fr); gap:6px;">${chButtons}</div>
    `;
    const ledRowsHtml = items.map((it, idx) => `
      <tr>
        <td><input value="${it.ch}" onchange="INST_HMI_STATE.feasaItems[${idx}].ch=this.value.padStart(2,'0');renderInstHmi();" class="mono" style="width:44px;padding:3px;"></td>
        <td><input value="${it.label}" onchange="INST_HMI_STATE.feasaItems[${idx}].label=this.value;renderInstHmi();" style="width:96px;padding:3px;"></td>
        <td><input value="${it.waveMin}" onchange="INST_HMI_STATE.feasaItems[${idx}].waveMin=this.value;renderInstHmi();" class="mono" style="width:52px;padding:3px;"></td>
        <td><input value="${it.waveMax}" onchange="INST_HMI_STATE.feasaItems[${idx}].waveMax=this.value;renderInstHmi();" class="mono" style="width:52px;padding:3px;"></td>
        <td><input value="${it.intMin}" onchange="INST_HMI_STATE.feasaItems[${idx}].intMin=this.value;renderInstHmi();" class="mono" style="width:62px;padding:3px;"></td>
        <td><input value="${it.intMax}" onchange="INST_HMI_STATE.feasaItems[${idx}].intMax=this.value;renderInstHmi();" class="mono" style="width:68px;padding:3px;"></td>
        <td><button class="btn" style="padding:2px 6px;" onclick="INST_HMI_STATE.feasaItems.splice(${idx},1);renderInstHmi();">✕</button></td>
      </tr>
    `).join('');

    rightControls = `
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px;">
        <div style="font-weight:700; font-size:0.93rem; color:#0F172A; margin-bottom:8px;">① 一鍵加入單色 / RGB 多顆燈號（支援同站一次寫入多組燈號）</div>
        <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px;">
          <button onclick="addFeasaRgbPreset()" class="btn" style="background:#FEF08A; color:#0F172A; border-color:#CA8A04; font-weight:700;">🌈 一鍵加入 RGB 三色 (Ch01紅+02綠+03藍)</button>
          <button onclick="addFeasaColorItem('green')" class="btn" style="background:#DCFCE7; color:#166534; border-color:#86EFAC;">➕ 綠燈 (515~535nm)</button>
          <button onclick="addFeasaColorItem('red')" class="btn" style="background:#FEE2E2; color:#991B1B; border-color:#FCA5A5;">➕ 紅燈 (615~640nm)</button>
          <button onclick="addFeasaColorItem('blue')" class="btn" style="background:#DBEAFE; color:#1E40AF; border-color:#93C5FD;">➕ 藍燈 (455~475nm)</button>
          <button onclick="addFeasaColorItem('yellow')" class="btn" style="background:#FEF3C7; color:#92400E; border-color:#FCD34D;">➕ 黃燈 (580~600nm)</button>
          <button onclick="addFeasaColorItem('white')" class="btn" style="background:#F1F5F9; color:#334155; border-color:#CBD5E1;">➕ 白燈 / 純亮度</button>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
          <label style="font-size:0.83rem; font-weight:700;">Title 測項名稱
            <input value="${s.titleName}" onchange="INST_HMI_STATE.titleName=this.value;renderInstHmi();" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;">
          </label>
          <label style="font-size:0.83rem; font-weight:700;">COM Port (Global.ini)
            <input value="${s.feasaCom}" onchange="INST_HMI_STATE.feasaCom=this.value;renderInstHmi();" class="mono" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;">
          </label>
        </div>
      </div>
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px;">
        <div style="font-weight:700; font-size:0.93rem; color:#0F172A; margin-bottom:8px;">② 已加入的 LED 測試清單（共 ${items.length} 顆燈號，送出時一次寫入）</div>
        <table class="meas-table">
          <thead><tr><th>Ch</th><th>燈號名稱</th><th>波長下限(nm)</th><th>波長上限(nm)</th><th>亮度下限</th><th>亮度上限</th><th>刪</th></tr></thead>
          <tbody>${ledRowsHtml || '<tr><td colspan="7" style="text-align:center;color:#64748B;">尚未加入 LED 測項，請點上方「➕」或「🌈 RGB 三色」</td></tr>'}</tbody>
        </table>
      </div>
    `;
  } else if (s.hmiType === 'ipower') {
    const outBtns = ['1','2','3','4'].map(o => `<button onclick="INST_HMI_STATE.pwrOutlet='${o}';renderInstHmi();" class="btn" style="padding:8px 12px; font-weight:700; ${s.pwrOutlet===o?'background:#2563EB;color:#fff;border-color:#1D4ED8;':'background:#F8FAFC;color:#334155;'}">Outlet ${o}</button>`).join('');
    leftPicker = `<div style="font-weight:700; font-size:0.87rem; color:#0F172A; margin:8px 0 6px;">🔌 點選電源插座迴路：</div><div style="display:grid; grid-template-columns:repeat(4,1fr); gap:6px;">${outBtns}</div>`;
    rightControls = `
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px;">
        <div style="font-weight:700; font-size:0.93rem; color:#0F172A; margin-bottom:8px;">電源開關動作與等待時間</div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
          <button onclick="INST_HMI_STATE.pwrAction='cycle';renderInstHmi();" class="btn" style="${s.pwrAction==='cycle'?'background:#DBEAFE;border-color:#2563EB;color:#1E3A8A;font-weight:700;':''}">🔄 斷電後重啟 (Power Cycle)</button>
          <button onclick="INST_HMI_STATE.pwrAction='on';renderInstHmi();" class="btn" style="${s.pwrAction==='on'?'background:#DCFCE7;border-color:#16A34A;color:#166534;font-weight:700;':''}">⚡ 單純開啟 (Power ON)</button>
          <button onclick="INST_HMI_STATE.pwrAction='off';renderInstHmi();" class="btn" style="${s.pwrAction==='off'?'background:#FEE2E2;border-color:#DC2626;color:#991B1B;font-weight:700;':''}">🛑 單純關閉 (Power OFF)</button>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
          <label style="font-size:0.83rem; font-weight:700;">Title 測項名稱<input value="${s.titleName}" onchange="INST_HMI_STATE.titleName=this.value;renderInstHmi();" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
          <label style="font-size:0.83rem; font-weight:700;">斷電放電延遲 (ms)<input value="${s.pwrDelay}" onchange="INST_HMI_STATE.pwrDelay=this.value;renderInstHmi();" class="mono" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
        </div>
      </div>
    `;
  } else if (s.hmiType === 'dmm') {
    const fnBtns = ['DCV','ACV','DCI','RES'].map(f => `<button onclick="INST_HMI_STATE.dmmFunc='${f}';renderInstHmi();" class="btn" style="padding:7px 10px; font-weight:700; ${s.dmmFunc===f?'background:#2563EB;color:#fff;border-color:#1D4ED8;':'background:#F8FAFC;color:#334155;'}">${f}</button>`).join('');
    leftPicker = `<div style="font-weight:700; font-size:0.87rem; color:#0F172A; margin:8px 0 6px;">📏 點選量測檔位：</div><div style="display:grid; grid-template-columns:repeat(4,1fr); gap:6px;">${fnBtns}</div>`;
    rightControls = `
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px;">
        <div style="font-weight:700; font-size:0.93rem; color:#0F172A; margin-bottom:8px;">量測通道與合格上下限</div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:10px;">
          <label style="font-size:0.83rem; font-weight:700;">Title 測項名稱<input value="${s.titleName}" onchange="INST_HMI_STATE.titleName=this.value;renderInstHmi();" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
          <label style="font-size:0.83rem; font-weight:700;">通道編號 (Ch)<input value="${s.dmmCh}" onchange="INST_HMI_STATE.dmmCh=this.value;renderInstHmi();" class="mono" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
          <label style="font-size:0.83rem; font-weight:700;">變數名稱<input value="${s.dmmVar}" onchange="INST_HMI_STATE.dmmVar=this.value;renderInstHmi();" class="mono" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
          <label style="font-size:0.83rem; font-weight:700;">下限 Min<input value="${s.dmmMin}" onchange="INST_HMI_STATE.dmmMin=this.value;renderInstHmi();" class="mono" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
          <label style="font-size:0.83rem; font-weight:700;">上限 Max<input value="${s.dmmMax}" onchange="INST_HMI_STATE.dmmMax=this.value;renderInstHmi();" class="mono" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
        </div>
      </div>
    `;
  } else if (s.hmiType === 'dio') {
    const pinBtns = Array.from({length: 8}, (_, i) => `P0.${i}`).map(p => `<button onclick="INST_HMI_STATE.dioPin='${p}';renderInstHmi();" class="btn mono" style="padding:6px 8px; font-size:0.8rem; ${s.dioPin===p?'background:#2563EB;color:#fff;border-color:#1D4ED8;font-weight:700;':'background:#F8FAFC;color:#334155;'}">${p}</button>`).join('');
    leftPicker = `<div style="font-weight:700; font-size:0.87rem; color:#0F172A; margin:8px 0 6px;">🎛️ 點選數位 I/O 腳位：</div><div style="display:grid; grid-template-columns:repeat(4,1fr); gap:6px;">${pinBtns}</div>`;
    rightControls = `
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px;">
        <div style="font-weight:700; font-size:0.93rem; color:#0F172A; margin-bottom:8px;">DIO 動作設定</div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
          <button onclick="INST_HMI_STATE.dioMode='high';renderInstHmi();" class="btn" style="${s.dioMode==='high'?'background:#DCFCE7;border-color:#16A34A;color:#166534;font-weight:700;':''}">▲ 輸出 High (1)</button>
          <button onclick="INST_HMI_STATE.dioMode='low';renderInstHmi();" class="btn" style="${s.dioMode==='low'?'background:#FEE2E2;border-color:#DC2626;color:#991B1B;font-weight:700;':''}">▼ 輸出 Low (0)</button>
          <button onclick="INST_HMI_STATE.dioMode='read';renderInstHmi();" class="btn" style="${s.dioMode==='read'?'background:#DBEAFE;border-color:#2563EB;color:#1E3A8A;font-weight:700;':''}">👁️ 讀取輸入狀態</button>
        </div>
        <label style="font-size:0.83rem; font-weight:700; display:block;">Title 測項名稱<input value="${s.titleName}" onchange="INST_HMI_STATE.titleName=this.value;renderInstHmi();" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box;"></label>
      </div>
    `;
  } else if (s.hmiType === 'rf') {
    leftPicker = `
      <div style="margin-top:10px; background:#F0F9FF; border:1px solid #BAE6FD; border-radius:6px; padding:10px;">
        <div style="font-weight:700; font-size:0.87rem; color:#0369A1; margin-bottom:6px;">🔌 RF 實體接線方式圖解</div>
        <svg viewBox="0 0 340 128" style="width:100%; background:#FFFFFF; border:1px solid #CBD5E1; border-radius:4px;">
          <rect x="8" y="14" width="76" height="42" rx="5" fill="#1E293B"/>
          <text x="46" y="33" fill="#FFFFFF" font-size="10" text-anchor="middle" font-weight="bold">測試 PC</text>
          <text x="46" y="47" fill="#93C5FD" font-size="8" text-anchor="middle">Centimani</text>
          <line x1="84" y1="35" x2="128" y2="35" stroke="#2563EB" stroke-width="2.5"/>
          <text x="106" y="28" fill="#1D4ED8" font-size="8" text-anchor="middle" font-weight="bold">LAN 控制</text>
          <rect x="128" y="14" width="90" height="42" rx="5" fill="#0F172A" stroke="#38BDF8" stroke-width="1.5"/>
          <text x="173" y="33" fill="#38BDF8" font-size="10" text-anchor="middle" font-weight="bold">IQxel / RF</text>
          <text x="173" y="47" fill="#CBD5E1" font-size="8" text-anchor="middle">RF1 / RF2</text>
          <line x1="218" y1="35" x2="262" y2="35" stroke="#D97706" stroke-width="2.5"/>
          <text x="240" y="28" fill="#B45309" font-size="8" text-anchor="middle" font-weight="bold">RF 同軸線</text>
          <rect x="262" y="14" width="70" height="42" rx="5" fill="#ECFDF5" stroke="#10B981" stroke-width="1.5"/>
          <text x="297" y="33" fill="#065F46" font-size="10" text-anchor="middle" font-weight="bold">DUT 待測板</text>
          <text x="297" y="47" fill="#047857" font-size="8" text-anchor="middle">IPEX / SMA</text>
          <path d="M 46 56 L 46 92 L 297 92 L 297 56" fill="none" stroke="#16A34A" stroke-width="2" stroke-dasharray="4 3"/>
          <text x="172" y="108" fill="#166534" font-size="8.5" text-anchor="middle" font-weight="bold">PC ⇄ DUT 控板線 (LAN@wl / UART)：下達發包與收包指令</text>
          <text x="240" y="52" fill="#B45309" font-size="7.5" text-anchor="middle">(PathLoss.ini)</text>
        </svg>
        <ul style="margin:8px 0 0 16px; padding:0; font-size:0.8rem; color:#334155; line-height:1.5;">
          <li><b>RF 同軸線</b>：DUT 天線座 (SMA/IPEX) →（選配 <code>RFSwitch3001</code>）→ IQxel <b>RF1A/RF2A</b>。</li>
          <li><b>儀器控制線</b>：PC RJ45 網口 → IQxel LAN（預設 <code>192.168.100.254</code>）。</li>
          <li><b>控板線</b>：PC → DUT（<code>LAN@wl</code> 下達切換通道、功率與發包）。</li>
        </ul>
      </div>
      <div style="margin-top:8px;">
        <label style="font-size:0.8rem; font-weight:700; color:#334155; display:block;">Instrument Settings（寫入 Instrument 分頁）：
          <input value="${s.rfSettings}" onchange="INST_HMI_STATE.rfSettings=this.value;renderInstHmi();" class="mono" style="width:100%; margin-top:3px; padding:5px 8px; border:1px solid #94A3B8; border-radius:4px; box-sizing:border-box; font-size:0.8rem;">
        </label>
      </div>
      <details style="margin-top:8px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:8px 10px;">
        <summary style="cursor:pointer; font-weight:700; font-size:0.83rem; color:#1E3A8A;">📖 相關操作儀器資料（指令與 Marco 21/22 步）</summary>
        <div style="margin-top:6px; font-size:0.8rem; color:#334155; line-height:1.55;">
          <div><b>1. Tx 量測流程 (WIFI Tx MCS · 21 步)：</b></div>
          <div>計算 BW 偏移 → <code>LAN@wl chanspec / nrate / txchain / txpwr1 / pkteng_start</code> → <code>:ObtainDevice</code> → <code>:Dev.MeasWIFI</code> 取 <code>Power / FreqErrPPM / EVM</code> → <code>:ReleaseDevice</code></div>
          <div style="margin-top:5px;"><b>2. Rx 靈敏度流程 (WIFI Rx MCS · 22 步)：</b></div>
          <div><code>LAN@wl rxwithack / reset_cnts</code> → <code>:ObtainDevice</code> → <code>:Dev.GenWIFI</code> 送 1000 封包 → <code>:ReleaseDevice</code> → <code>LAN@wl counters</code> 檢核 <code>RxOK (900~1000)</code></div>
        </div>
      </details>
    `;

    const txRowsHtml = (s.rfTxTests || []).map((t, i) => `
      <tr>
        <td><input value="${t.channel}" onchange="INST_HMI_STATE.rfTxTests[${i}].channel=this.value;renderInstHmi();" class="mono" style="width:42px;padding:3px;"></td>
        <td><select onchange="INST_HMI_STATE.rfTxTests[${i}].bw=this.value;renderInstHmi();" style="padding:3px;"><option value="20" ${t.bw==='20'?'selected':''}>20</option><option value="40" ${t.bw==='40'?'selected':''}>40</option><option value="80" ${t.bw==='80'?'selected':''}>80</option></select></td>
        <td><input value="${t.mcs}" onchange="INST_HMI_STATE.rfTxTests[${i}].mcs=this.value;renderInstHmi();" class="mono" style="width:36px;padding:3px;"></td>
        <td><input value="${t.antenna}" onchange="INST_HMI_STATE.rfTxTests[${i}].antenna=this.value;renderInstHmi();" class="mono" style="width:36px;padding:3px;"></td>
        <td><input value="${t.target_pwr}" onchange="INST_HMI_STATE.rfTxTests[${i}].target_pwr=this.value;renderInstHmi();" class="mono" style="width:46px;padding:3px;"></td>
        <td><input value="${t.pwr_min}" onchange="INST_HMI_STATE.rfTxTests[${i}].pwr_min=this.value;renderInstHmi();" class="mono" style="width:46px;padding:3px;"></td>
        <td><input value="${t.pwr_max}" onchange="INST_HMI_STATE.rfTxTests[${i}].pwr_max=this.value;renderInstHmi();" class="mono" style="width:46px;padding:3px;"></td>
        <td><input value="${t.evm_max}" onchange="INST_HMI_STATE.rfTxTests[${i}].evm_max=this.value;renderInstHmi();" class="mono" style="width:48px;padding:3px;"></td>
        <td><button class="btn" style="padding:2px 6px;" onclick="INST_HMI_STATE.rfTxTests.splice(${i},1);renderInstHmi();">✕</button></td>
      </tr>
    `).join('');

    const rxRowsHtml = (s.rfRxTests || []).map((r, i) => `
      <tr>
        <td><input value="${r.channel}" onchange="INST_HMI_STATE.rfRxTests[${i}].channel=this.value;renderInstHmi();" class="mono" style="width:48px;padding:3px;"></td>
        <td><select onchange="INST_HMI_STATE.rfRxTests[${i}].bw=this.value;renderInstHmi();" style="padding:3px;"><option value="20" ${r.bw==='20'?'selected':''}>20</option><option value="40" ${r.bw==='40'?'selected':''}>40</option><option value="80" ${r.bw==='80'?'selected':''}>80</option></select></td>
        <td><input value="${r.mcs}" onchange="INST_HMI_STATE.rfRxTests[${i}].mcs=this.value;renderInstHmi();" class="mono" style="width:42px;padding:3px;"></td>
        <td><input value="${r.antenna}" onchange="INST_HMI_STATE.rfRxTests[${i}].antenna=this.value;renderInstHmi();" class="mono" style="width:42px;padding:3px;"></td>
        <td><input value="${r.rx_level}" onchange="INST_HMI_STATE.rfRxTests[${i}].rx_level=this.value;renderInstHmi();" class="mono" style="width:58px;padding:3px;"></td>
        <td><button class="btn" style="padding:2px 6px;" onclick="INST_HMI_STATE.rfRxTests.splice(${i},1);renderInstHmi();">✕</button></td>
      </tr>
    `).join('');

    rightControls = `
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:8px;">
          <span style="font-weight:700; font-size:0.93rem; color:#0F172A;">① Tx 射頻發射測試（Marco：WIFI Tx MCS）</span>
          <div style="display:flex; gap:5px; flex-wrap:wrap;">
            <button onclick="rfAddPreset('24g_tx')" class="btn" style="padding:3px 9px; font-size:0.8rem; background:#DBEAFE; color:#1E40AF;">+ 2.4G CH1/6/11</button>
            <button onclick="rfAddPreset('5g_tx')" class="btn" style="padding:3px 9px; font-size:0.8rem; background:#EDE9FE; color:#5B21B6;">+ 5G CH36/100/149</button>
            <button onclick="INST_HMI_STATE.rfTxTests.push({channel:'6',bw:'20',mcs:'7',antenna:'1',target_pwr:'15',pwr_min:'13',pwr_max:'17',evm_min:'-50',evm_max:'-28'});renderInstHmi();" class="btn btn-primary-green" style="padding:3px 9px; font-size:0.8rem;">+ 新增 Tx</button>
          </div>
        </div>
        <table class="meas-table">
          <thead><tr><th>Ch</th><th>BW</th><th>MCS</th><th>Chain</th><th>Target</th><th>PwrMin</th><th>PwrMax</th><th>EVMMax</th><th>刪</th></tr></thead>
          <tbody>${txRowsHtml || '<tr><td colspan="9" style="text-align:center;color:#64748B;">尚未加入 Tx 測項</td></tr>'}</tbody>
        </table>
      </div>
      <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:8px;">
          <span style="font-weight:700; font-size:0.93rem; color:#0F172A;">② Rx 射頻接收靈敏度測試（Marco：WIFI Rx MCS）</span>
          <div style="display:flex; gap:5px; flex-wrap:wrap;">
            <button onclick="INST_HMI_STATE.rfRxTests.push({channel:'6',bw:'20',mcs:'7',antenna:'1',rx_level:'-59'});renderInstHmi();" class="btn" style="padding:3px 9px; font-size:0.8rem; background:#DBEAFE; color:#1E40AF;">+ 2.4G CH6 Rx</button>
            <button onclick="INST_HMI_STATE.rfRxTests.push({channel:'36',bw:'40',mcs:'7',antenna:'1',rx_level:'-59'});renderInstHmi();" class="btn" style="padding:3px 9px; font-size:0.8rem; background:#EDE9FE; color:#5B21B6;">+ 5G CH36 Rx</button>
          </div>
        </div>
        <table class="meas-table">
          <thead><tr><th>Ch</th><th>BW</th><th>MCS</th><th>Chain</th><th>VSG Level (dBm)</th><th>刪</th></tr></thead>
          <tbody>${rxRowsHtml || '<tr><td colspan="6" style="text-align:center;color:#64748B;">尚未加入 Rx 測項</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }

  left.innerHTML = `
    <div style="display:flex; flex-wrap:wrap; gap:16px; align-items:flex-start;">
      <div style="width:240px; flex-shrink:0; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:8px; text-align:center;">
        <img src="${prof.img}" alt="${prof.title}" style="max-height:150px; max-width:100%; object-fit:contain;"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <div style="display:none;">${prof.svgIcon || ''}</div>
      </div>
      <div style="flex:1; min-width:280px;">
        ${leftPicker}
      </div>
    </div>
  `;

  const previewPayload = buildInstHmiPayload();
  const previewRows = previewPayload.steps.map(st => `
    <tr>
      <td class="mono">${st.Instrument || '-'}</td>
      <td class="mono">${st.Send}</td>
      <td class="mono" style="white-space:pre-wrap;">${st.Ref || '-'}</td>
      <td class="mono" style="white-space:pre-wrap;">${st.Validation || '-'}</td>
      <td class="mono">${st.ExecMode}</td>
    </tr>
  `).join('');

  right.innerHTML = `
    ${rightControls}
    <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:12px;">
      <div style="font-weight:700; font-size:0.9rem; color:#0F172A; margin-bottom:6px;">📄 將產生的 Centimani 腳本預覽</div>
      <table class="meas-table">
        <thead><tr><th>Instrument</th><th>Send</th><th>Ref</th><th>Validation</th><th>ExecMode</th></tr></thead>
        <tbody>${previewRows}</tbody>
      </table>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:12px;">
        <button onclick="closeInstHmi()" class="btn" style="background:#E2E8F0; color:#334155;">取消</button>
        <button onclick="confirmInstHmi()" class="btn btn-primary-green" style="padding:8px 18px; font-size:0.93rem;">✨ 確認加入測試流程</button>
      </div>
    </div>
  `;
}

function rfAddPreset(kind) {
  if (kind === '24g_tx') {
    ['1', '6', '11'].forEach(ch => {
      INST_HMI_STATE.rfTxTests.push({ channel: ch, bw: '20', mcs: '7', antenna: '1', target_pwr: '15', pwr_min: '13', pwr_max: '17', evm_min: '-50', evm_max: '-28' });
    });
  } else if (kind === '5g_tx') {
    ['36', '100', '149'].forEach(ch => {
      INST_HMI_STATE.rfTxTests.push({ channel: ch, bw: '40', mcs: '7', antenna: '1', target_pwr: '14', pwr_min: '12', pwr_max: '16', evm_min: '-50', evm_max: '-28' });
    });
  }
  renderInstHmi();
}

async function confirmInstHmi() {
  const s = INST_HMI_STATE;
  if (s.hmiType === 'rf') {
    if ((!s.rfTxTests || s.rfTxTests.length === 0) && (!s.rfRxTests || s.rfRxTests.length === 0)) {
      alert('請至少保留一筆 Tx 或 Rx 射頻測項。');
      return;
    }
    const rfPayload = {
      inst_name: s.instName,
      title_name: s.titleName || 'WIFI RF Test',
      settings_str: s.rfSettings || '192.168.100.254,1,2,1,60000,PathLoss.ini',
      tx_tests: s.rfTxTests.map(x => Object.assign({}, x)),
      rx_tests: s.rfRxTests.map(x => Object.assign({}, x))
    };
    if (s.targetMode === 'tab3') {
      closeInstHmi();
      if (typeof tab3SaveHmiItemFromModal === 'function') {
        await tab3SaveHmiItemFromModal({
          inst_name: s.instName,
          title_name: rfPayload.title_name,
          rf_block: rfPayload
        });
      }
      return;
    }

    if (s.targetMode === 'gen') {
      STATE.genRfBlocks = STATE.genRfBlocks || [];
      STATE.genRfBlocks.push(rfPayload);
      closeInstHmi();
      renderGenCustomInstList();
      return;
    }
    const res = await fetch('/api/insert_rf_iqxel_block', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        workspace: STATE.workspace,
        sheet_name: document.getElementById('instHmiSheetSel').value,
        after_block_idx: parseInt(document.getElementById('instHmiAfterSel').value || '-1', 10),
        ...rfPayload
      })
    });
    const data = await res.json();
    if (data.status !== 'ok') {
      alert(data.message || 'RF 區塊插入失敗');
      return;
    }
    STATE.workspace = data.workspace;
    STATE.report = data.report;
    STATE.pendingInserts = STATE.pendingInserts || [];
    STATE.pendingInserts.push({
      sheet: document.getElementById('instHmiSheetSel').value,
      inst: s.instName,
      summary: `Tx ${rfPayload.tx_tests.length} 筆 / Rx ${rfPayload.rx_tests.length} 筆（含 WIFI Tx/Rx MCS Marco）`
    });
    closeInstHmi();
    renderAuditResults();
    alert(`已插入 ${data.added_rows} 列 RF 主站呼叫列，並自動補齊 WIFI Tx MCS (21 步) / WIFI Rx MCS (22 步) Marco 子工作表！請點擊「💾 立即匯出並驗證」寫入 *_FIXED.xlsx。`);
    return;
  }

  const { steps, globalsPatch, dl, ul } = buildInstHmiPayload();
  const cleanTitle = (s.titleName || `${s.instName} Test`).trim();

  if (s.targetMode === 'tab3') {
    closeInstHmi();
    if (typeof tab3SaveHmiItemFromModal === 'function') {
      await tab3SaveHmiItemFromModal({
        inst_name: s.instName,
        title_name: cleanTitle,
        dl_val: dl,
        ul_val: ul,
        custom_steps: steps,
        globals_patch: globalsPatch
      });
    }
    return;
  }

  if (s.targetMode === 'gen') {
    STATE.genCustomInsts = STATE.genCustomInsts || [];
    STATE.genCustomInsts.push({
      inst_name: s.instName,
      title_name: cleanTitle,
      dl_val: dl,
      ul_val: ul,
      custom_steps: steps,
      globals_patch: globalsPatch
    });
    closeInstHmi();
    renderGenCustomInstList();
    return;
  }

  const res = await fetch('/api/insert_instrument_block', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      workspace: STATE.workspace,
      sheet_name: document.getElementById('instHmiSheetSel').value,
      after_block_idx: parseInt(document.getElementById('instHmiAfterSel').value || '-1', 10),
      inst_name: s.instName,
      title_name: cleanTitle,
      dl_val: dl,
      ul_val: ul,
      custom_steps: steps,
      globals_patch: globalsPatch,
      no_hw_phase_pause: !!(document.getElementById('instHmiNoHwPhaseChk') && document.getElementById('instHmiNoHwPhaseChk').checked)
    })
  });
  const data = await res.json();
  if (data.status !== 'ok') {
    alert(data.message || '儀器區塊插入失敗');
    return;
  }
  STATE.workspace = data.workspace;
  STATE.report = data.report;
  STATE.pendingInserts = STATE.pendingInserts || [];
  STATE.pendingInserts.push({
    sheet: document.getElementById('instHmiSheetSel').value,
    inst: s.instName,
    summary: cleanTitle
  });
  closeInstHmi();
  renderAuditResults();
  alert(`已透過 ${s.instName} 人機介面插入 ${data.added_rows} 列獨立 Title 區塊（整塊已亮黃底標記，請點擊「💾 立即匯出並驗證」寫入 *_FIXED.xlsx）。`);
}

const NI6_STATE = { targetMode: 'audit', editGenIdx: -1, mode: 'RSE', channels: [] };

