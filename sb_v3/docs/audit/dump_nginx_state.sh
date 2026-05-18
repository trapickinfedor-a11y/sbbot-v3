#!/usr/bin/env bash
set -euo pipefail

echo '== LS ==' 
ls -l /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

echo '== GREP AVAILABLE =='
grep -n 'proxy_pass http://127.0.0.1:' /etc/nginx/sites-available/default || true

echo '== GREP ENABLED =='
grep -n 'proxy_pass http://127.0.0.1:' /etc/nginx/sites-enabled/default || true

echo '== AVAILABLE SNIP =='
sed -n '185,375p' /etc/nginx/sites-available/default || true

echo '== ENABLED SNIP =='
sed -n '185,375p' /etc/nginx/sites-enabled/default || true

echo '== NGINX -T FILTER =='
nginx -T 2>/dev/null | grep -n 'proxy_pass http://127.0.0.1:' || true
