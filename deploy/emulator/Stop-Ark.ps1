param([string]$VmRoot = 'F:\DataArk-Emulator')
$ErrorActionPreference = 'Stop'
& ssh -o BatchMode=yes -o ConnectTimeout=5 -o UserKnownHostsFile="$VmRoot/seed/known_hosts" -i "$VmRoot/seed/admin-ed25519" -p 22222 admin@127.0.0.1 'sudo systemctl poweroff'
if ($LASTEXITCODE -ne 0) { throw 'Guest shutdown request failed; inspect the VM before retrying.' }
Write-Output 'Clean guest shutdown requested. The physical Ark is unaffected.'
