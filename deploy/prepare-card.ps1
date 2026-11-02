#Requires -RunAsAdministrator
param([string]$ImagePath,[Nullable[int]]$DiskNumber)
$ErrorActionPreference='Stop'
$package=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'card-package.json') -Raw | ConvertFrom-Json
$imager=Join-Path $env:ProgramFiles 'Raspberry Pi Ltd/Imager/rpi-imager.exe'
if(-not(Test-Path -LiteralPath $imager)){throw 'Install Raspberry Pi Imager 2.0.12 or newer from raspberrypi.com/software, then run again.'}
function Get-EligibleCards {
 foreach($item in Get-Disk){
  if($item.IsBoot -or $item.IsSystem -or $item.Size -eq 0 -or $item.BusType -notin @('USB','SD')){continue}
  $protected=$false
  foreach($partition in @(Get-Partition -DiskNumber $item.Number -ErrorAction SilentlyContinue)){
   if($partition.DriveLetter){
    $volumeRoot=([string]$partition.DriveLetter)+':\'
    if((Test-Path -LiteralPath (Join-Path $volumeRoot 'DATA-ARK-CONFIG')) -or (Test-Path -LiteralPath (Join-Path $volumeRoot 'DATA-ARK-RECOVERY'))){$protected=$true}
   }
  }
  if(-not $protected){$item}
 }
}
$cards=@(Get-EligibleCards)
$cards | Select-Object Number,FriendlyName,SerialNumber,@{n='GiB';e={[math]::Round($_.Size/1GB,1)}} | Format-Table
if($null -eq $DiskNumber){$DiskNumber=[int](Read-Host 'Destination disk NUMBER (Ctrl+C cancels)')}
$selected=$cards | Where-Object Number -eq $DiskNumber
if(-not $selected){throw 'Choose a listed removable disk. System disks and recognized Ark libraries are excluded.'}
if(-not $ImagePath){$ImagePath=Read-Host ('Path to '+$package.image.filename)}
$ImagePath=(Resolve-Path -LiteralPath $ImagePath).Path
foreach($inputFile in @($ImagePath,$PSScriptRoot)){
 $volume=[IO.Path]::GetPathRoot($inputFile)
 if($volume -match '^([A-Za-z]):[\\/]$'){
  $inputDisk=Get-Partition -DriveLetter $Matches[1] | Get-Disk
  if($inputDisk.Number -eq $selected.Number){throw 'The input image or preparation package is on the selected destination.'}
 }
}
if((Get-Item -LiteralPath $ImagePath).Length -ne $package.image.download_bytes -or (Get-FileHash -LiteralPath $ImagePath -Algorithm SHA256).Hash.ToLower() -ne $package.image.download_sha256){throw 'Image does not match the reviewed Raspberry Pi OS reference. Nothing written.'}
if($selected.Size -lt ($package.library_gib+$package.image.image_allowance_gib+$package.image.os_reserve_gib)*1GB){throw 'Card is too small for the selected library and Linux reserve.'}
if((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'kit.tar.gz') -Algorithm SHA256).Hash.ToLower() -ne $package.kit_sha256){throw 'Kit checksum differs.'}
$serial=([string]$selected.SerialNumber).Trim();if(-not $serial){$serial='NO-SERIAL'}
$confirmation='ERASE '+$selected.Number+' '+$serial
Write-Host ('ALL contents of Disk '+$selected.Number+' ('+$selected.FriendlyName+', '+$serial+') will be replaced.')
if((Read-Host ('Type exactly: '+$confirmation)) -cne $confirmation){throw 'Confirmation did not match. Nothing written.'}
$current=Get-Disk -Number $selected.Number
if($current.IsBoot -or $current.IsSystem -or $current.Size -ne $selected.Size -or ([string]$current.SerialNumber).Trim() -cne ([string]$selected.SerialNumber).Trim()){throw 'Destination identity changed.'}
$random=New-Object byte[] 4;$rng=[Security.Cryptography.RandomNumberGenerator]::Create();try{$rng.GetBytes($random)}finally{$rng.Dispose()}
$code=([BitConverter]::ToUInt32($random,0)%10000).ToString('D4')
$hostname='dataark-'+[guid]::NewGuid().ToString('N').Substring(0,12)
$seed=@{pairing_code=$code;hostname=$hostname;library_gib=[int]$package.library_gib;country=$package.country;kit_sha256=$package.kit_sha256}
$driver=[Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'first-boot.py')))
$unit="[Unit]`nDescription=Build a recipient-ready Data Ark card`nAfter=network-online.target`nWants=network-online.target`nConditionPathExists=!/var/lib/dataark/card-build/ready`n[Service]`nType=oneshot`nExecStart=/usr/bin/python3 /usr/local/libexec/dataark-card-build`nTimeoutStartSec=infinity`n[Install]`nWantedBy=multi-user.target`n"
$cloud=@{hostname=$hostname;manage_etc_hosts=$true;ssh_pwauth=$false;disable_root=$true;package_update=$false;package_upgrade=$false;
 users=@(@{name='admin';uid=1000;groups=@('adm','sudo','audio','video','plugdev','netdev','gpio','i2c','spi');shell='/bin/bash';lock_passwd=$true;sudo='ALL=(ALL) NOPASSWD:ALL'});
 write_files=@(@{path='/usr/local/libexec/dataark-card-build';permissions='0700';encoding='b64';content=$driver},@{path='/etc/systemd/system/dataark-card-build.service';permissions='0644';content=$unit});
 runcmd=@(@('systemctl','daemon-reload'),@('systemctl','enable','--now','dataark-card-build.service'))}
$temporaryFile=Join-Path ([IO.Path]::GetTempPath()) ('dataark-card-'+[guid]::NewGuid().ToString('N')+'.json')
try {
 [IO.File]::WriteAllText($temporaryFile,"#cloud-config`n"+($cloud|ConvertTo-Json -Depth 20)+"`n",(New-Object Text.UTF8Encoding($false)))
 $arguments=@('--cli','--disable-eject','--sha256',$package.image.uncompressed_sha256,'--cloudinit-userdata',('"'+$temporaryFile+'"'),('"'+$ImagePath+'"'),('\\.\PhysicalDrive'+$selected.Number))
 $process=Start-Process -FilePath $imager -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
 if($process.ExitCode -ne 0){throw ('Imager stopped with code '+$process.ExitCode)}
 $partition=Get-Partition -DiskNumber $selected.Number | Where-Object PartitionNumber -eq 1
 if(-not $partition.DriveLetter){$partition | Add-PartitionAccessPath -AssignDriveLetter; $partition=Get-Partition -DiskNumber $selected.Number -PartitionNumber 1}
 $boot=([string]$partition.DriveLetter)+':\'
 $folder=Join-Path $boot 'dataark-card';New-Item -ItemType Directory -Path $folder | Out-Null
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'kit.tar.gz') -Destination (Join-Path $folder 'kit.tar.gz')
 [IO.File]::WriteAllText((Join-Path $folder 'provision.json'),($seed|ConvertTo-Json)+"`n",(New-Object Text.UTF8Encoding($false)))
 if((Get-FileHash -LiteralPath (Join-Path $folder 'kit.tar.gz') -Algorithm SHA256).Hash.ToLower() -ne $package.kit_sha256){throw 'Copied kit verification failed.'}
 foreach($name in @('kit.tar.gz','provision.json')){$stream=[IO.File]::Open((Join-Path $folder $name),'Open','ReadWrite','Read');try{$stream.Flush($true)}finally{$stream.Dispose()}}
 $sheet=Join-Path $PSScriptRoot ($hostname+'-PRIVATE-welcome.html')
 $html='<!doctype html><html lang="en"><meta charset="utf-8"><title>Private Data Ark welcome</title><style>body{font:18px/1.6 system-ui;max-width:750px;margin:40px auto;padding:24px;color:#203e54}h1{background:#172d40;color:#e0bd68;padding:20px}.code{font:700 36px monospace;letter-spacing:8px}@media print{button{display:none}}</style><h1>Your Pharos Data Ark</h1><p>Keep this sheet private. The sender first boots the card with Ethernet/internet and waits for its successful build to power off. It is then ready for its recipient.</p><p>The recipient joins DataArk Wi-Fi and opens <strong>http://192.168.4.1/setup.html</strong>.</p><p>One-time code:</p><p class="code">'+$code+'</p><p>Choose separate caretaker and Linux admin passwords (12+ characters). No shared root password or online activation. Complete HTTP setup privately. Installed content and enrollment work offline after the build.</p><p>Device: '+$hostname+'</p><button onclick="print()">Print / Save as PDF</button></html>'
 [IO.File]::WriteAllText($sheet,$html,(New-Object Text.UTF8Encoding($false)))
 Write-Host ('Installer card verified. PRIVATE welcome sheet: '+$sheet)
 Write-Host 'Safely eject, then boot with Ethernet/internet. Only a successful build followed by automatic power-off makes it ready to give away.'
} finally {if(Test-Path -LiteralPath $temporaryFile){Remove-Item -LiteralPath $temporaryFile}}
