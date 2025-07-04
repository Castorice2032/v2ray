#!/bin/bash

set -e

BASE_DIR="$HOME/server"

echo "📁 در حال ایجاد ساختار دایرکتوری در: $BASE_DIR"
mkdir -p "$BASE_DIR"/{shadowsocks,vmess,vless,trojan,hysteria,tuic}

cd "$BASE_DIR"

echo "🔍 در حال بروزرسانی پکیج‌ها..."
sudo apt update -y

echo "🔧 نصب ابزار shadowsocks-libev..."
sudo apt install -y shadowsocks-libev

echo "📦 نصب xray-core (برای vmess و vless)..."
mkdir -p xray && cd xray
XRAY_VER=$(curl -s https://api.github.com/repos/XTLS/Xray-core/releases/latest | grep tag_name | cut -d '"' -f 4)
wget https://github.com/XTLS/Xray-core/releases/download/${XRAY_VER}/Xray-linux-64.zip
unzip Xray-linux-64.zip && chmod +x xray
mv xray ../vmess/xray && cp ../vmess/xray ../vless/xray
cd ..

echo "🔧 نصب Trojan-Go..."
mkdir -p trojan && cd trojan
TROJAN_VER=$(curl -s https://api.github.com/repos/p4gefau1t/trojan-go/releases/latest | grep tag_name | cut -d '"' -f 4)
wget https://github.com/p4gefau1t/trojan-go/releases/download/${TROJAN_VER}/trojan-go-linux-amd64.zip
unzip trojan-go-linux-amd64.zip && chmod +x trojan-go
mv trojan-go ../trojan/
cd ..

echo "⚡ نصب Hysteria (v2)..."
mkdir -p hysteria && cd hysteria
HYS_VER=$(curl -s https://api.github.com/repos/apernet/hysteria/releases/latest | grep tag_name | cut -d '"' -f 4)
wget https://github.com/apernet/hysteria/releases/download/${HYS_VER}/hysteria-linux-amd64 -O hysteria
chmod +x hysteria && mv hysteria ../hysteria/
cd ..

echo "🚀 نصب TUIC..."
mkdir -p tuic && cd tuic
TUIC_VER=$(curl -s https://api.github.com/repos/EAimTY/tuic/releases/latest | grep tag_name | cut -d '"' -f 4)
wget https://github.com/EAimTY/tuic/releases/download/${TUIC_VER}/tuic-client-linux-amd64 -O tuic-client
chmod +x tuic-client && mv tuic-client ../tuic/
cd ..

echo "✅ همه ابزارها نصب شدند. آماده استفاده هستند."

