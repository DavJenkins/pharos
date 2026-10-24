$ErrorActionPreference = 'Stop'
$captureRoot = $PSScriptRoot
$pythonPath = (Get-Command python.exe).Source
$sshPath = (Get-Command ssh.exe).Source
$utf8 = New-Object System.Text.UTF8Encoding($false)
$configuration = @{
  ark_host = '192.168.40.123'
  ssh_executable = $sshPath
  ssh_key = "$env:USERPROFILE\.ssh\id_rsa"
  download_directories = @("$env:USERPROFILE\Downloads")
}
if (-not (Test-Path -LiteralPath (Join-Path $captureRoot 'config.json'))) {
  [System.IO.File]::WriteAllText((Join-Path $captureRoot 'config.json'), ($configuration | ConvertTo-Json), $utf8)
}
$launcher = Join-Path $captureRoot 'native-host.cmd'
('@echo off' + "`r`n" + '"' + $pythonPath + '" -B "' + (Join-Path $captureRoot 'native_host.py') + '"') | Set-Content -LiteralPath $launcher -Encoding ascii
$hostManifest = @{
 name='com.dejsoftware.dataark_capture'; description='Data Ark approved public PDF capture'; path=$launcher; type='stdio'
 allowed_origins=@('chrome-extension://gilcpcndoddadpkefaeecjemhhcahhig/')
}
$manifestPath=Join-Path $captureRoot 'native-host.json'
[System.IO.File]::WriteAllText($manifestPath, ($hostManifest | ConvertTo-Json), $utf8)
$registryPath='HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.dejsoftware.dataark_capture'
New-Item -Path $registryPath -Force | Out-Null
Set-Item -Path $registryPath -Value $manifestPath
Write-Output 'Native helper registered for Chrome. Load this folder as an unpacked extension in chrome://extensions.'
Write-Output $captureRoot
