#!/bin/sh
set -eu
set -- /data/*.zim
EMPTY=/data/.dataark-reader/empty.xml
if [ ! -f "$1" ] && [ ! -f "$EMPTY" ]; then
    EMPTY=$(mktemp /tmp/dataark-empty-XXXXXX)
    printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?><library version="20110515"></library>' > "$EMPTY"
fi
if [ -f /data/.dataark-reader/catalogue-index.html ]; then
    if [ -f "$1" ]; then
        exec /usr/local/bin/kiwix-serve --port=8080 --customIndex=/data/.dataark-reader/catalogue-index.html "$@"
    fi
    exec /usr/local/bin/kiwix-serve --port=8080 --customIndex=/data/.dataark-reader/catalogue-index.html --library "$EMPTY"
fi
if [ -f "$1" ]; then
    exec /usr/local/bin/kiwix-serve --port=8080 "$@"
fi
exec /usr/local/bin/kiwix-serve --port=8080 --library "$EMPTY"
