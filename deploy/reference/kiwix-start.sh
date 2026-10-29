#!/bin/sh
set -eu
set -- /data/*.zim
if [ -f "$1" ]; then
    exec /usr/local/bin/kiwix-serve --port=8080 "$@"
fi
exec /usr/local/bin/kiwix-serve --port=8080 --library /data/.dataark-reader/empty.xml
