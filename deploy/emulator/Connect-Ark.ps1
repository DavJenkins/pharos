param([string]$VmRoot = 'F:\DataArk-Emulator')
& ssh -o UserKnownHostsFile="$VmRoot/seed/known_hosts" -i "$VmRoot/seed/admin-ed25519" -p 22222 admin@127.0.0.1
