#!/bin/bash
# Строгий режим: остановка должна быть предсказуемой, а ошибки — видны.
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

if pidof /opt/zapret/nfqws > /dev/null 2>&1; then
    killall nfqws || true
fi

if [ -f /opt/zapret/FWTYPE ]; then
    content=$(cat /opt/zapret/FWTYPE)
    if [ "$content" = "iptables" ]; then
        FWTYPE=iptables
    elif [ "$content" = "nftables" ]; then
        FWTYPE=nftables
    else
        echo "Error: invalid value in file FWTYPE."
        exit 1
    fi
    echo "FWTYPE=$FWTYPE" 2>/dev/null
else
    echo "Error: File /opt/zapret/FWTYPE not found."
    exit 1
fi

if [ "$FWTYPE" = "iptables" ]; then
    # Убираем только свою цепочку и её jump'ы, включая ip6tables.
    for tool in iptables ip6tables; do
        "$tool" -t mangle -D PREROUTING -j ZAPRET 2>/dev/null || true
        "$tool" -t mangle -D POSTROUTING -j ZAPRET 2>/dev/null || true
        "$tool" -t mangle -F ZAPRET 2>/dev/null || true
        "$tool" -t mangle -X ZAPRET 2>/dev/null || true
    done
elif [ "$FWTYPE" = "nftables" ]; then
    nft flush table inet zapret 2>/dev/null || true
    nft delete table inet zapret 2>/dev/null || true
fi

# Возвращаем прежнее значение sysctl, сохранённое starter.sh.
SYSCTL_KEY="net.netfilter.nf_conntrack_tcp_be_liberal"
SYSCTL_STATE_FILE="/run/zapret/be_liberal.before"
if [ -f "$SYSCTL_STATE_FILE" ]; then
    BEFORE=$(cat "$SYSCTL_STATE_FILE" 2>/dev/null || true)
    if [ -n "${BEFORE:-}" ]; then
        sysctl -q "$SYSCTL_KEY=$BEFORE" || true
    fi
    rm -f "$SYSCTL_STATE_FILE" || true
fi
