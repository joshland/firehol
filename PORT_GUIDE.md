# FireHOL Python Port Guide

This document guides the port of FireHOL from bash to Python. It documents the codebase structure, external dependencies, code paths, and maps them to the emerging Python implementation.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [External Dependencies](#external-dependencies)
3. [Code Structure](#code-structure)
4. [Feature Mapping](#feature-mapping)
5. [Python Implementation Status](#python-implementation-status)
6. [Testing Infrastructure](#testing-infrastructure)

---

## Architecture Overview

FireHOL is a firewall configuration tool that generates iptables/ip6tables rules from a high-level configuration language. The bash implementation is ~12,000 lines across multiple components:

```
firehol      - Main firewall configuration tool (12332 lines)
fireqos     - Traffic shaping/QoS tool
link-balancer - Multi-WAN load balancer
update-ipsets - Dynamic IPset management
vnetbuild   - Virtual network builder
```

### Core Workflow

```
1. Parse config file (interface/router definitions)
2. Load service definitions
3. Generate iptables rules (two-pass: IPv4, IPv6)
4. Validate rules
5. Apply rules (fast mode: iptables-restore, or slow mode: direct iptables)
6. Save state for recovery
```

---

## External Dependencies

### Required System Commands

The bash implementation uses ~90 external commands, detected and validated at configure time:

| Category | Commands | Purpose |
|----------|----------|---------|
| **Core iptables** | `iptables`, `iptables-save`, `iptables-restore` | IPv4 firewall |
| **Core ip6tables** | `ip6tables`, `ip6tables-save`, `ip6tables-restore` | IPv6 firewall |
| **Networking** | `ip`, `ss` | Interface/IP address management |
| **Filesystem** | `cat`, `cp`, `mv`, `rm`, `mkdir`, `touch`, `chmod`, `chown` | File operations |
| **Text Processing** | `grep`, `sed`, `awk`, `cut`, `sort`, `uniq`, `head`, `tail`, `tr`, `wc`, `fold` | Config parsing |
| **System** | `readlink`, `basename`, `dirname` | Path manipulation |
| **Process** | `flock`, `sleep`, `date`, `expr`, `seq` | Runtime operations |
| **Logging** | `logger` | Syslog integration |
| **Kernel** | `lsmod`, `modprobe`, `sysctl` | Module loading |
| **Terminal** | `tput`, `stty` | Terminal capabilities |

### Optional Commands

| Command | Purpose | When Required |
|---------|---------|---------------|
| `ipset` | IP address sets | When using ipsets |
| `iprange` | IP range compression | Optimizing large ipsets |
| `ping`, `ping6` | Connectivity testing | Link-balancer |
| `traceroute` | Route tracing | Link-balancer |
| `whois` | IP lookup | Link-balancer |
| `curl`, `wget` | HTTP downloads | update-ipsets |
| `jq` | JSON parsing | Link-balancer, update-ipsets |
| `tcpdump` | Packet capture | FireQOS |
| `tc` | Traffic control | FireQOS |
| `bridge` | Bridge management | vnetbuild |
| `gawk` | Advanced awk | FireQOS |
| `screen` | Terminal multiplexing | Link-balancer |

### Kernel Requirements

FireHOL requires these kernel features (via netfilter):

```
Required:
- iptables (IPv4 packet filtering)
- ip6tables (IPv6 packet filtering)
- conntrack (connection tracking)
- nf_conntrack_* (connection tracking helpers)

Optional (for features):
- iptable_nat, ip6table_nat (NAT)
- iptable_mangle, ip6table_mangle (packet marking)
- iptable_raw, ip6table_raw (raw table)
- nfnetlink_conntrack (conntrack via netlink)
- ip_set (ipsets)
- xt_conntrack (conntrack matching)
- xt_state, xt_conntrack (state matching)
- xt_limit (rate limiting)
- xt_mac (MAC filtering)
- xt_*.ko (various match/target modules)
```

---

## Code Structure

### File Organization (bash)

```
sbin/
├── firehol              # Main firewall tool (12332 lines)
├── fireqos             # QoS tool
├── link-balancer       # Multi-WAN balancer
├── update-ipsets      # Dynamic ipsets
├── vnetbuild          # Virtual networks
├── functions.common   # Shared library (100 lines)
├── services.common    # Service definitions (308 lines)
├── services.firehol   # FireHOL-specific services
├── services.fireqos   # FireQOS-specific services
└── install.config.in.in  # Command definitions (90+ commands)
```

### Key Code Paths in firehol

#### 1. Entry Point (~line 5517)
```bash
case "$1" in
    start|try|stop|status|panic|restore|save|debug|explain|wizard|helpme)
```
Each command has a dedicated function handler.

#### 2. Config Parser
- Reads `firehol.conf` line by line
- Supports `interface`, `router`, `server`, `client`, `policy`, `protection`
- Variables via `${VAR}` expansion
- Multi-line statements via backslash continuation

#### 3. Rule Generation
- Two modes: `fast` (iptables-restore) and `slow` (direct iptables)
- Default chains: INPUT, OUTPUT, FORWARD
- Custom chains per interface/router
- NAT rules in nat table
- Mangle rules for marking

#### 4. Service System
- Simple services: single port (e.g., `server ssh accept`)
- Complex services: multiple ports/rules (e.g., `server ftp accept`)
- Helpers: kernel modules to load (e.g., `helper_ftp="ftp"`)

---

## Feature Mapping

### Current Python Implementation

The existing Python implementation (`python/firehol/`) covers basic functionality:

| Feature | Bash Lines | Python Status |
|---------|------------|---------------|
| CLI argument parsing | ~200 | ✅ Done |
| Config file parsing | ~500 | ✅ Basic |
| Interface definitions | ~1000 | ✅ Basic |
| Router definitions | ~1000 | ✅ Basic |
| Simple services | ~300 | ⚠️ Stub |
| Rule generation (IPv4) | ~3000 | ✅ Basic |
| Rule generation (IPv6) | ~3000 | ✅ Basic |
| iptables-restore | ~500 | ✅ Done |
| Commands (start/stop/etc) | ~500 | ✅ Done |
| NAT/Port forwarding | ~1500 | ❌ TODO |
| IPSets | ~1000 | ❌ TODO |
| SYNPROXY | ~1000 | ❌ TODO |
| Connection helpers | ~500 | ❌ TODO |
| Complex services | ~1000 | ❌ TODO |
| Protection/limits | ~500 | ❌ TODO |
| Wizard mode | ~500 | ⚠️ Stub |
| Interactive explain | ~500 | ❌ TODO |

### Detailed Feature Breakdown

#### Core Features (Priority 1)

1. **Interface Definitions**
   ```bash
   interface eth0 home
       policy accept
       server ssh accept
       client all accept
   ```
   - IPv4/IPv6 dual-stack
   - Custom policies (ACCEPT/DROP/REJECT)
   - Protection levels

2. **Router Definitions**
   ```bash
   router lan_to_wan inface eth0 outface eth1
       route all accept
   ```
   - NAT (masquerading)
   - Port forwarding (dnat)
   - Routing policies

3. **Services** (~100 services defined in `services.common`)
   - Simple: port-based (ssh, http, https, etc.)
   - Complex: multi-port with helpers (ftp, irc, etc.)

4. **Rule Generation**
   - Chain creation and policies
   - Match conditions (protocol, ports, IPs, states)
   - Actions (ACCEPT, DROP, REJECT, LOG, etc.)

#### Advanced Features (Priority 2)

1. **NAT (Network Address Translation)**
   - SNAT: `snat to 1.2.3.4`
   - DNAT: `dnat to 192.168.1.1:8080`
   - Masquerade: `masquerade`

2. **IPSets**
   - Dynamic IP sets
   - Blacklist/whitelist management
   - Country-based blocking

3. **SYNPROXY**
   - DDoS protection
   - SYN cookie acceleration

4. **Connection Tracking Helpers**
   - FTP, IRC, TFTP, etc.
   - NAT-aware helper assignment

#### Extended Features (Priority 3)

1. **Traffic Shaping** (handled by FireQOS)
2. **Multi-WAN Balancing** (handled by link-balancer)
3. **Virtual Networks** (handled by vnetbuild)

---

## Python Implementation Status

### Files Created

```
python/
├── firehol/
│   ├── __init__.py      # Main CLI, FireHOL class (300 lines)
│   ├── config.py        # Config parser (200 lines)
│   └── __main__.py      # Entry point
├── setup.py            # Package setup
└── example.conf        # Example config
```

### Class Structure (Current)

```python
class FireHOL:
    """Main application class"""
    def __init__(self, config_file: str = None)
    def run_command(self, cmd: str) -> int
    def cmd_start(self) -> int
    def cmd_try(self) -> int
    def cmd_stop(self) -> int
    def cmd_status(self) -> int
    def cmd_panic(self) -> int
    def cmd_restore(self) -> int
    def cmd_save(self) -> int
    def cmd_debug(self) -> int
    def cmd_explain(self) -> int
    def cmd_wizard(self) -> int

class RuleGenerator:
    """Generate iptables rules"""
    def generate_ipv4_rules(self) -> List[str]
    def generate_ipv6_rules(self) -> List[str]

class FireHOLConfigParser:
    """Parse configuration files"""
    def parse(self) -> Dict[str, Any]
```

### Required Python Dependencies

```python
# Minimal dependencies for core functionality
install_requires = [
    'ipaddress',  # Already in stdlib for Python 3.3+
]

# Optional for enhanced functionality
optional = [
    'ply',        # For config file parsing (alternative: re, pyparsing)
    'psutil',     # For system info
]
```

---

## Testing Infrastructure

### Test Framework

Located in `tests/`:

```
tests/
├── unittest              # Main test runner (bash script)
├── tools/
│   ├── clean-iptables   # Normalize iptables output
│   ├── clean-qdisc      # Normalize tc output
│   └── newns            # Create user namespace for tests
├── firehol/             # FireHOL tests
│   ├── basics/          # Basic functionality
│   ├── cmdline/         # CLI tests
│   └── not-both/       # IPv4/IPv6 disable tests
├── fireqos/            # FireQOS tests
├── link-balancer/      # Link balancer tests
└── update-ipsets/     # IPset update tests
```

### Test Execution

```bash
# Run single test
./tests/unittest tests/firehol/basics/empty.conf

# Run component tests
./tests/unittest tests/firehol

# Verbose mode
./tests/unittest -v tests/firehol/basics/empty.conf
```

### Test Requirements

- Must NOT run as root (uses user namespaces)
- Requires: `sysctl kernel.unprivileged_userns_clone=1`
- Requires kernel modules: iptable_mangle, ip6table_mangle, iptable_raw, ip6table_raw, iptable_nat, ip6table_nat, iptable_filter, ip6table_filter

### Test File Structure

Each test has:
- `testname.conf` - Configuration file
- `testname.pre.sh` - Pre-run setup (optional)
- `testname.run.sh` - Custom run script (optional)
- `testname.check.sh` - Custom verification (optional)
- `testname.aud4` - Expected IPv4 output
- `testname.aud6` - Expected IPv6 output

---

## Porting Checklist

### Phase 1: Core Functionality

- [x] CLI argument parsing
- [x] Config file parser
- [x] Interface definitions
- [x] Router definitions
- [x] Basic rule generation
- [x] Commands (start, stop, status, panic)

### Phase 2: Services & Rules

- [ ] Simple service definitions (~100 services)
- [ ] Complex service definitions
- [ ] Connection helpers (FTP, etc.)
- [ ] Protection/limit rules
- [ ] IPv4/IPv6 dual-stack

### Phase 3: Advanced Features

- [ ] NAT (snat, dnat, masquerade)
- [ ] IPSets integration
- [ ] SYNPROXY
- [ ] Connection tracking helpers

### Phase 4: Extended Features

- [ ] Interactive explain mode
- [ ] Wizard mode
- [ ] Auto-save/restore
- [ ] Test suite port to Python

---

## Recommendations

1. **Keep bash as fallback**: Maintain bash implementation until Python is feature-complete
2. **Use subprocess**: Wrap iptables/iptables-restore calls
3. **Consider nftables**: Future-proof by designing rule generation to support nftables output
4. **Type hints**: Add full type annotations for maintainability
5. **Config validation**: Use a proper parser (PLY or pyparsing) instead of regex
6. **Testing**: Port test infrastructure to Python pytest

---

## References

- Original bash implementation: `sbin/firehol` (12332 lines)
- Service definitions: `sbin/services.common` (308 lines)
- Common functions: `sbin/functions.common` (100 lines)
- Test infrastructure: `tests/` directory
- Existing Python stub: `python/firehol/`
