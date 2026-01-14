# Aegis.net XDP Filter

High-performance L3/L4 packet filtering using eBPF/XDP.

## Features

- **Blacklist/Whitelist**: IP-based blocking and bypassing
- **Rate Limiting**: Per-IP packet rate limiting
- **SYN Flood Protection**: SYN cookie validation
- **Game Protocol Detection**: Special handling for game ports

## Requirements

- Linux kernel 5.4+
- clang/LLVM 11+
- libbpf

## Compilation

```bash
# Install dependencies (Ubuntu/Debian)
apt-get install clang llvm libbpf-dev linux-headers-$(uname -r)

# Compile
clang -O2 -g -target bpf -c aegis_xdp.c -o aegis_xdp.o

# Load on interface
ip link set dev eth0 xdp obj aegis_xdp.o sec xdp

# Unload
ip link set dev eth0 xdp off
```

## Maps

| Map | Type | Description |
|-----|------|-------------|
| `blacklist_ipv4` | Hash | Blocked IP addresses |
| `whitelist_ipv4` | Hash | Always-allowed IPs |
| `rate_limit` | LRU Hash | Per-IP rate limit state |
| `config` | Array | Protection level setting |
| `statistics` | PerCPU Array | Traffic counters |

## Protection Levels

- **0 (Observe)**: Pass-through, logging only
- **1 (Soft)**: Rate limiting enabled
- **2 (Medium)**: SYN validation, stricter limits
- **3 (Hard)**: Full validation
- **4 (Lockdown)**: Whitelist only
