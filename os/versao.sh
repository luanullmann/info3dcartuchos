#!/bin/sh
# Rode antes de publicar: força os navegadores a baixarem a versão nova.
cd "$(dirname "$0")"
V=$(date +%s)
sed -i "s#\(app\|config\|dados\|pix\|qrcode\)\.js?v=[0-9]*#\1.js?v=$V#g; s#estilo\.css?v=[0-9]*#estilo.css?v=$V#g" index.html cliente.html app.js
echo "versão $V"
