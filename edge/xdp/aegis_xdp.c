/*
 * Aegis.net — XDP Packet Filter
 * 
 * High-performance L3/L4 filtering using eBPF/XDP
 * Runs at driver level before kernel networking stack
 * 
 * Compile: clang -O2 -target bpf -c aegis_xdp.c -o aegis_xdp.o
 * Load: ip link set dev eth0 xdp obj aegis_xdp.o sec xdp
 */

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/ipv6.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

/* Configuration from control plane */
#define MAX_BLOCKED_IPS 10000
#define MAX_WHITELIST_IPS 1000
#define RATE_LIMIT_PPS 1000  /* Packets per second per IP */
#define RATE_LIMIT_WINDOW_NS 1000000000  /* 1 second in nanoseconds */

/* Protection levels */
#define LEVEL_OBSERVE 0
#define LEVEL_SOFT 1
#define LEVEL_MEDIUM 2
#define LEVEL_HARD 3
#define LEVEL_LOCKDOWN 4

/* Statistics */
struct stats {
    __u64 rx_packets;
    __u64 rx_bytes;
    __u64 dropped_blacklist;
    __u64 dropped_rate_limit;
    __u64 dropped_invalid;
    __u64 passed;
};

/* Rate limit entry */
struct rate_limit_entry {
    __u64 last_seen;
    __u32 packet_count;
    __u32 _pad;
};

/* Maps */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_BLOCKED_IPS);
    __type(key, __u32);    /* IPv4 address */
    __type(value, __u64);  /* Block timestamp */
} blacklist_ipv4 SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_WHITELIST_IPS);
    __type(key, __u32);
    __type(value, __u8);
} whitelist_ipv4 SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 100000);
    __type(key, __u32);    /* IPv4 address */
    __type(value, struct rate_limit_entry);
} rate_limit SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u32);  /* Protection level */
} config SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct stats);
} statistics SEC(".maps");


/* Helper: Update statistics */
static __always_inline void update_stats(int action, __u32 bytes) {
    __u32 key = 0;
    struct stats *s = bpf_map_lookup_elem(&statistics, &key);
    if (!s) return;
    
    s->rx_packets++;
    s->rx_bytes += bytes;
    
    switch (action) {
        case XDP_DROP:
            s->dropped_invalid++;
            break;
        case XDP_PASS:
            s->passed++;
            break;
    }
}

/* Helper: Check rate limit */
static __always_inline int check_rate_limit(__u32 src_ip) {
    __u64 now = bpf_ktime_get_ns();
    struct rate_limit_entry *entry;
    struct rate_limit_entry new_entry = {0};
    
    entry = bpf_map_lookup_elem(&rate_limit, &src_ip);
    
    if (entry) {
        /* Check if window expired */
        if (now - entry->last_seen > RATE_LIMIT_WINDOW_NS) {
            /* Reset counter */
            entry->last_seen = now;
            entry->packet_count = 1;
            return 1;  /* Allow */
        }
        
        /* Increment counter */
        entry->packet_count++;
        
        if (entry->packet_count > RATE_LIMIT_PPS) {
            return 0;  /* Rate limited */
        }
        
        return 1;  /* Allow */
    }
    
    /* New entry */
    new_entry.last_seen = now;
    new_entry.packet_count = 1;
    bpf_map_update_elem(&rate_limit, &src_ip, &new_entry, BPF_ANY);
    
    return 1;  /* Allow */
}

/* Helper: Validate TCP SYN (basic SYN cookie logic placeholder) */
static __always_inline int validate_tcp_syn(struct tcphdr *tcp, __u32 src_ip) {
    /* In real implementation, verify SYN cookie */
    /* For now, just check basic flags */
    if (tcp->syn && !tcp->ack) {
        /* New connection - check rate limit more strictly */
        /* Real implementation would use SYN cookies here */
        return 1;
    }
    return 1;
}

/* Main XDP program */
SEC("xdp")
int aegis_xdp_filter(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;
    
    __u32 key = 0;
    __u32 *protection_level;
    
    /* Get current protection level */
    protection_level = bpf_map_lookup_elem(&config, &key);
    __u32 level = protection_level ? *protection_level : LEVEL_OBSERVE;
    
    /* Parse Ethernet header */
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) {
        return XDP_DROP;
    }
    
    /* Only process IPv4 for now */
    if (eth->h_proto != bpf_htons(ETH_P_IP)) {
        return XDP_PASS;
    }
    
    /* Parse IP header */
    struct iphdr *ip = data + sizeof(*eth);
    if ((void *)(ip + 1) > data_end) {
        return XDP_DROP;
    }
    
    __u32 src_ip = ip->saddr;
    __u32 pkt_len = data_end - data;
    
    /* Level 4 (Lockdown): Only whitelist */
    if (level >= LEVEL_LOCKDOWN) {
        __u8 *whitelisted = bpf_map_lookup_elem(&whitelist_ipv4, &src_ip);
        if (!whitelisted) {
            update_stats(XDP_DROP, pkt_len);
            return XDP_DROP;
        }
    }
    
    /* Check whitelist (always pass) */
    __u8 *whitelisted = bpf_map_lookup_elem(&whitelist_ipv4, &src_ip);
    if (whitelisted) {
        update_stats(XDP_PASS, pkt_len);
        return XDP_PASS;
    }
    
    /* Check blacklist */
    __u64 *blocked = bpf_map_lookup_elem(&blacklist_ipv4, &src_ip);
    if (blocked) {
        update_stats(XDP_DROP, pkt_len);
        return XDP_DROP;
    }
    
    /* Rate limiting (Level 1+) */
    if (level >= LEVEL_SOFT) {
        if (!check_rate_limit(src_ip)) {
            /* Rate limited - mark for statistics */
            __u32 stats_key = 0;
            struct stats *s = bpf_map_lookup_elem(&statistics, &stats_key);
            if (s) s->dropped_rate_limit++;
            return XDP_DROP;
        }
    }
    
    /* Protocol-specific checks */
    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = (void *)ip + (ip->ihl * 4);
        if ((void *)(tcp + 1) > data_end) {
            return XDP_DROP;
        }
        
        /* SYN validation for Level 2+ */
        if (level >= LEVEL_MEDIUM && tcp->syn) {
            if (!validate_tcp_syn(tcp, src_ip)) {
                return XDP_DROP;
            }
        }
    }
    
    if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = (void *)ip + (ip->ihl * 4);
        if ((void *)(udp + 1) > data_end) {
            return XDP_DROP;
        }
        
        __u16 dst_port = bpf_ntohs(udp->dest);
        
        /* Game protocol ports - pass to userspace validator */
        /* RAGE MP: 22005, Minecraft: 25565, Source: 27015 */
        if (dst_port == 22005 || dst_port == 25565 || dst_port == 27015) {
            /* Let OpenResty/Rust handle game-specific validation */
            update_stats(XDP_PASS, pkt_len);
            return XDP_PASS;
        }
    }
    
    update_stats(XDP_PASS, pkt_len);
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
