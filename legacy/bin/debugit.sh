#!/bin/bash
# /usr/local/bin/debugit.sh
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

DEBUG_FILE="/var/lib/ark/debug_status"
mkdir -p /var/lib/ark/
chown www-data:www-data /var/lib/ark/
chmod 775 /var/lib/ark/

ACTION=$1
case "$ACTION" in
    "on")
        touch "$DEBUG_FILE"
        chmod 664 "$DEBUG_FILE"
        chown www-data:www-data "$DEBUG_FILE"
        echo "ON"
        ;;
    "off")
        rm -f "$DEBUG_FILE"
        echo "OFF"
        ;;
    *)
        [ -f "$DEBUG_FILE" ] && echo "ON" || echo "OFF"
        ;;
esac