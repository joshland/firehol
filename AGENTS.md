# AGENTS.md - FireHOL Development Guide

This file provides guidance for AI agents working on the FireHOL codebase.

## Project Overview

FireHOL is a bash-based firewall configuration suite (firehol, fireqos, link-balancer, update-ipsets, vnetbuild). The codebase consists primarily of shell scripts using GNU autotools for building.

## Build Commands

### Initial Setup (from git repository)
```bash
./autogen.sh
./configure --enable-maintainer-mode
```

### Building Without Documentation
If pandoc is not available:
```bash
./autogen.sh
./configure --disable-doc --disable-man
make
make install
```

### Standard Build Commands
- `make` - Build all components
- `make check` - Run tests (requires unprivileged user namespaces and kernel modules)
- `make install` - Install built files
- `make dist` - Create distribution tarball

### Running a Single Test
```bash
# Run specific test directory or config file
./tests/unittest tests/firehol/basics/empty.conf

# Run all tests for a component
./tests/unittest tests/firehol
./tests/unittest tests/fireqos
./tests/unittest tests/link-balancer

# Run with verbose output
./tests/unittest -v tests/firehol/basics/empty.conf
```

Test Requirements:
- Must NOT run as root (uses user namespaces)
- Requires unprivileged user namespaces enabled: `sysctl kernel.unprivileged_userns_clone=1`
- Requires kernel modules: iptable_mangle, ip6table_mangle, iptable_raw, ip6table_raw, iptable_nat, ip6table_nat, iptable_filter, ip6table_filter

## Code Style Guidelines

### Shell Script Conventions
- Use `#!/bin/bash` shebang
- Use `set -e` for strict error handling where appropriate
- Use `local` for all variables inside functions
- Always quote variables: `"${var}"` not `$var`

### Naming Conventions
- Command variables: `*_CMD` suffix (e.g., `CAT_CMD`, `IP_CMD`, `IPTABLES_CMD`)
- Configuration files: `install.config.in.in`
- Functions in libraries: prefix with component name (e.g., `common_*`, `int_*`)
  - `common_*` - public functions
  - `int_*` - internal helper functions

### Error Handling
- Use `exit 1` for fatal errors in scripts
- Use `return 1` for recoverable errors in functions
- Include `${FUNCNAME}` in error messages: `echo >&2 "ERROR in ${FUNCNAME}: ..."`
- Check command results: `cmd || return 1`

### Command Variable Pattern
All external commands must be defined as variables at the top of scripts:
```bash
CAT_CMD=${CAT_CMD:-cat}
IP_CMD=${IP_CMD:-ip}
```
This allows the configure script to detect and validate required commands.

### Indentation
- Use consistent indentation (varies by file - follow existing style)
- Use tabs for Makefiles
- Comment heavily for complex logic

### Comments
- Use `#` for single-line comments
- Add descriptive comments for complex firewall rules
- Document the "why" not the "what"

## Test File Conventions

Test files use these naming patterns:
- `testname.conf` - Configuration file to test
- `testname.pre.sh` - Setup script (optional)
- `testname.run.sh` - Custom run script (optional, for non-standard execution)
- `testname.check.sh` - Custom verification (optional)
- `testname.aud4` - Expected iptables output
- `testname.aud6` - Expected ip6tables output (for IPv6 tests)

## Git Hooks

Install hooks by copying from `hooks/` directory:
```bash
cp hooks/* .git/hooks
```

- `pre-commit` - Runs `packaging/check-files` for style validation
- `post-commit` - Runs `packaging/update-tags` for tagging

## Key Files and Locations

- Main scripts: `sbin/firehol`, `sbin/fireqos`, `sbin/link-balancer`, `sbin/update-ipsets`, `sbin/vnetbuild`
- Common functions: `sbin/functions.common`
- Service definitions: `sbin/services.common`, `sbin/services.firehol`, `sbin/services.fireqos`
- Configuration: `configure.ac`, `sbin/install.config.in.in`
- Test framework: `tests/unittest`

## Version Management

- Version defined in `configure.ac` using `VERSION_MAJOR`, `VERSION_MINOR`, `VERSION_FIX`, `VERSION_SUFFIX`
- ChangeLog must have matching version
- Use semantic versioning patterns: x.y.z, x.y.z-rc.N, x.y.z_preN

## Important Notes

- This is a firewall configuration tool - changes can lock you out of systems
- Always test in isolated environments (the unittest framework uses user namespaces)
- The project requires bash 4.0+ and iprange 1.0.2+
- Scripts use both IPv4 and IPv6 - test both when modifying firewall rules
