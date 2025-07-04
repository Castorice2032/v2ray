
# run xray
./xray run -config ./config/vless-cloudflare.json

# check handsack (other terminal)
curl -x socks5h://127.0.0.1:10808 https://www.gstatic.com/generate_204 -I
