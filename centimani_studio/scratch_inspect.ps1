$p = 'D:\PYTHON\自動化編寫EXCEL\Centimani_1.5.3_sample\LoadScript.dll'
$asm = [System.Reflection.Assembly]::LoadFrom($p)
$t = $asm.GetType('LoadScript.MainScript')
$inst = [System.Activator]::CreateInstance($t)
$excelFile = 'D:\PYTHON\自動化編寫EXCEL\centimani_studio\output_system\PEGA_NEW_MB\System\PEGA_NEW_TestFlow_MB.xlsx'
$sysIni = 'D:\PYTHON\自動化編寫EXCEL\centimani_studio\output_system\PEGA_NEW_MB\System\System.ini'
$checksum = $inst.GetChecksum($excelFile, $sysIni, '')
Write-Host "CALCULATED INSTANCE CHECKSUM: $checksum"
