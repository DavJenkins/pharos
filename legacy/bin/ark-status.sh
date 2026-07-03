#!/bin/bash

# Check for verbose mode
DEBUG_MODE=false
[[ -f /tmp/ark_debug_mode ]] && DEBUG_MODE=true

if [ "$DEBUG_MODE" = true ]; then
  echo "[ARK DEBUG] Generating status JSON at $(date)" >&2
fi

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

ip4() {
  ip -4 -o addr show dev "$1" 2>/dev/null |
    awk '{print $4}' | cut -d/ -f1 | head -n1
}

gateway4() {
  ip route show default dev "$1" 2>/dev/null |
    awk '/default/ {print $3; exit}'
}

bytes_human() {
  awk -v n="$1" 'BEGIN {
    split("B KiB MiB GiB TiB", u, " ");
    i=1;
    while (n >= 1024 && i < 5) { n/=1024; i++ }
    printf "%.1f %s", n, u[i]
  }'
}

# Ethernet
ETH_STATE=$(cat /sys/class/net/eth0/operstate 2>/dev/null || echo "down")
ETH_IP=$(ip4 eth0)
ETH_GW=$(gateway4 eth0)

# Upstream Wi-Fi
WIFI_LINK=$(iw dev wlan1 link 2>/dev/null)
WIFI_SSID=$(printf '%s\n' "$WIFI_LINK" | awk -F': ' '/SSID:/ {print $2; exit}')
WIFI_SIGNAL_DBM=$(printf '%s\n' "$WIFI_LINK" | awk '/signal:/ {print $2; exit}' | awk '{print $1}')
WIFI_RATE=$(printf '%s\n' "$WIFI_LINK" | awk -F': ' '/tx bitrate:/ {print $2; exit}')
WIFI_IP=$(ip4 wlan1)
WIFI_GW=$(gateway4 wlan1)

if [[ -n "$WIFI_SSID" ]]; then
  WIFI_STATE="connected"
  WIFI_SIGNAL_PCT=$(( (WIFI_SIGNAL_DBM + 90) * 100 / 60 ))
  (( WIFI_SIGNAL_PCT < 0 )) && WIFI_SIGNAL_PCT=0
  (( WIFI_SIGNAL_PCT > 100 )) && WIFI_SIGNAL_PCT=100
else
  WIFI_STATE="disconnected"
  WIFI_SSID="Disconnected"
  WIFI_SIGNAL_DBM=""
  WIFI_SIGNAL_PCT=0
  WIFI_RATE=""
fi

# AP setup
AP_SSID=$(nmcli -g 802-11-wireless.ssid connection show "DataArk" 2>/dev/null)
[[ -z "$AP_SSID" ]] && AP_SSID="DataArk"

# Clients
AP_CLIENTS_JSON=""
AP_CLIENT_COUNT=0
while read -r mac; do
  [[ -z "$mac" ]] && continue
  lease=$(awk -v mac="$mac" 'tolower($2) == tolower(mac) {print; exit}' /var/lib/misc/dnsmasq.leases 2>/dev/null)
  ip=$(printf '%s\n' "$lease" | awk '{print $3}')
  host=$(printf '%s\n' "$lease" | awk '{print $4}')
  [[ -z "$host" || "$host" == "*" ]] && host="Unknown device"
  [[ -z "$ip" ]] && ip="No DHCP lease"
  item="{\"hostname\":\"$(json_escape "$host")\",\"ip\":\"$(json_escape "$ip")\",\"mac\":\"$(json_escape "$mac")\"}"
  [[ -n "$AP_CLIENTS_JSON" ]] && AP_CLIENTS_JSON+=","
  AP_CLIENTS_JSON+="$item"
  AP_CLIENT_COUNT=$((AP_CLIENT_COUNT + 1))
done < <(iw dev wlan0 station dump 2>/dev/null | awk '/^Station / {print $2}')

# System health
HOSTNAME=$(hostname)
PLATFORM=$(tr -d '\0' </proc/device-tree/model 2>/dev/null)
CPU_TEMP_RAW=$(vcgencmd measure_temp 2>/dev/null | sed -n "s/temp=\([0-9.]*\).*/\1/p")
CPU_TEMP_RAW=${CPU_TEMP_RAW:-0}
read -r LOAD_1 LOAD_5 LOAD_15 _ < /proc/loadavg
MEM_TOTAL=$(awk '/MemTotal:/ {print $2 * 1024}' /proc/meminfo)
MEM_AVAILABLE=$(awk '/MemAvailable:/ {print $2 * 1024}' /proc/meminfo)
MEM_USED=$((MEM_TOTAL - MEM_AVAILABLE))
SWAP_TOTAL=$(awk '/SwapTotal:/ {print $2 * 1024}' /proc/meminfo)
SWAP_FREE=$(awk '/SwapFree:/ {print $2 * 1024}' /proc/meminfo)
SWAP_USED=$((SWAP_TOTAL - SWAP_FREE))
DISK_LINE=$(df -B1 / | tail -1)
DISK_USED=$(printf '%s\n' "$DISK_LINE" | awk '{print $3}')
DISK_FREE=$(printf '%s\n' "$DISK_LINE" | awk '{print $4}')
DISK_PCT=$(printf '%s\n' "$DISK_LINE" | awk '{gsub("%","",$5); print $5}')
SSD_LINE=$(df -B1 /mnt/storage 2>/dev/null | tail -1)
SSD_USED=$(printf '%s\n' "$SSD_LINE" | awk '{print $3}')
SSD_FREE=$(printf '%s\n' "$SSD_LINE" | awk '{print $4}')
SSD_PCT=$(printf '%s\n' "$SSD_LINE" | awk '{gsub("%","",$5); print $5}')
UPTIME=$(uptime -p | sed 's/^up //')
SYSTEM_STATE="ok"
if (( ${DISK_PCT:-0} >= 90 )) || (( $(awk "BEGIN {print ($CPU_TEMP_RAW >= 80)}") )); then SYSTEM_STATE="critical"
elif (( ${DISK_PCT:-0} >= 80 )) || (( $(awk "BEGIN {print ($CPU_TEMP_RAW >= 70)}") )); then SYSTEM_STATE="warning"; fi
SYNC=$(pgrep -x "rsync" >/dev/null && echo "Syncing" || echo "Idle")

# Determine debug status
DEBUG_STATUS="OFF"
[ -f "/var/lib/ark/debug_status" ] && DEBUG_STATUS="ON"

if [ "$DEBUG_MODE" = true ]; then
  echo "[ARK DEBUG] Values: Eth:$ETH_STATE, WiFi:$WIFI_STATE, Sys:$SYSTEM_STATE, Debug:$DEBUG_STATUS" >&2
fi

cat <<EOF_JSON > /var/www/html/status.json
{
  "eth_state": "$(json_escape "$ETH_STATE")",
  "eth_ip": "$(json_escape "$ETH_IP")",
  "eth_gateway": "$(json_escape "$ETH_GW")",
  "wifi_state": "$(json_escape "$WIFI_STATE")",
  "wifi_ssid": "$(json_escape "$WIFI_SSID")",
  "wifi_signal_dbm": "$(json_escape "$WIFI_SIGNAL_DBM")",
  "wifi_signal_pct": $WIFI_SIGNAL_PCT,
  "wifi_rate": "$(json_escape "$WIFI_RATE")",
  "wifi_ip": "$(json_escape "$WIFI_IP")",
  "wifi_gateway": "$(json_escape "$WIFI_GW")",
  "ap_ssid": "$(json_escape "$AP_SSID")",
  "ap_client_count": $AP_CLIENT_COUNT,
  "ap_clients": [$AP_CLIENTS_JSON],
  "system_state": "$(json_escape "$SYSTEM_STATE")",
  "hostname": "$(json_escape "$HOSTNAME")",
  "platform": "$(json_escape "$PLATFORM")",
  "cpu_temp_c": $CPU_TEMP_RAW,
  "load_1": "$LOAD_1",
  "load_5": "$LOAD_5",
  "load_15": "$LOAD_15",
  "mem_used": "$(bytes_human "$MEM_USED")",
  "mem_available": "$(bytes_human "$MEM_AVAILABLE")",
  "swap_used": "$(bytes_human "$SWAP_USED")",
  "sd_used": "$(bytes_human "$DISK_USED")",
  "sd_free": "$(bytes_human "$DISK_FREE")",
  "sd_pct": $DISK_PCT,
  "ssd_used": "$(bytes_human "$SSD_USED")",
  "ssd_free": "$(bytes_human "$SSD_FREE")",
  "ssd_pct": $SSD_PCT,
  "uptime": "$(json_escape "$UPTIME")",
  "sync": "$(json_escape "$SYNC")",
  "debug_mode": "$DEBUG_STATUS",
  "updated": "$(date +%T)"
}
EOF_JSON