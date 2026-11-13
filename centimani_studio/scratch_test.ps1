$dll = "D:\PYTHON\自動化編寫EXCEL\Centimani_1.5.3_sample\CentimaniSystem.exe"
$asm = [System.Reflection.Assembly]::LoadFrom($dll)
$asm.GetTypes() | Where-Object { $_.Name -like "*Script*" -or $_.Name -like "*Load*" -or $_.Name -like "*DUT*" } | ForEach-Object {
    $t = $_
    $t.GetMethods([System.Reflection.BindingFlags]'Public,NonPublic,Instance,Static') | Where-Object { $_.Name -like "*NewFormat*" -or $_.Name -like "*DUT*" -or $_.Name -like "*Script*" } | ForEach-Object {
        [PSCustomObject]@{
            Type = $t.FullName
            Method = $_.Name
        }
    }
} | Format-Table -AutoSize | Out-String -Width 200
