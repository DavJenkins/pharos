#!/bin/sh
set -eu
set -- /data/*.zim
if [ -f /data/.dataark-reader/catalogue-index.html ]; then
    if [ -f "$1" ]; then
        exec /usr/local/bin/kiwix-serve --port=8080 --customIndex=/data/.dataark-reader/catalogue-index.html "$@"
    fi
    exec /usr/local/bin/kiwix-serve --port=8080 --customIndex=/data/.dataark-reader/catalogue-index.html --library /data/.dataark-reader/empty.xml
fi
if [ -f "$1" ]; then
    exec /usr/local/bin/kiwix-serve --port=8080 "$@"
fi
exec /usr/local/bin/kiwix-serve --port=8080 --library /data/.dataark-reader/empty.xml
