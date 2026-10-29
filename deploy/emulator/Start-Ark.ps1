param([string]$VmRoot = 'F:\DataArk-Emulator')
$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $VmRoot 'vm.pid'
if (Test-Path $pidFile) {
    $running = Get-Process -Id ([int](Get-Content $pidFile)) -ErrorAction SilentlyContinue
    if ($running -and $running.ProcessName -eq 'qemu-system-aarch64') { Write-Output 'The Ark emulator is already running.'; exit 0 }
}
$arguments = Get-Content (Join-Path $VmRoot 'qemu-arguments.json') | ConvertFrom-Json
$process = Start-Process -FilePath (Join-Path $VmRoot 'qemu/qemu-system-aarch64.exe') -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardError (Join-Path $VmRoot 'logs/qemu-error.log') -RedirectStandardOutput (Join-Path $VmRoot 'logs/qemu-output.log') -PassThru
$process.Id | Set-Content $pidFile
Write-Output 'Starting ARM64 Ark emulator. Dashboard: http://127.0.0.1:18080/ (allow time to boot)'
