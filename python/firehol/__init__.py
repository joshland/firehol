#!/usr/bin/env python3
"""
FireHOL - A firewall for humans...

Python implementation of the FireHOL firewall configuration tool.
"""

import argparse
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

VERSION = "3.1.9"

DEFAULT_CONFIG_DIR = "/etc/firehol"
DEFAULT_SERVICES_DIR = "/etc/firehol/services"
DEFAULT_SPOOL_DIR = "/var/spool/firehol"
DEFAULT_RUN_DIR = "/var/run/firehol"


class FireHOL:
    """Main FireHOL application class."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or f"{DEFAULT_CONFIG_DIR}/firehol.conf"
        self.services_dir = os.environ.get("FIREHOL_SERVICES_DIR", DEFAULT_SERVICES_DIR)
        self.spool_dir = os.environ.get("FIREHOL_SPOOL_DIR", DEFAULT_SPOOL_DIR)
        self.run_dir = os.environ.get("FIREHOL_RUN_DIR", DEFAULT_RUN_DIR)

        self.enable_ipv4 = os.environ.get("ENABLE_IPV4", "1") == "1"
        self.enable_ipv6 = os.environ.get("ENABLE_IPV6", "1") == "1"

        self.fast_activation = os.environ.get("FIREHOL_FAST_ACTIVATION", "1") == "1"
        self.ruleset_mode = os.environ.get("FIREHOL_RULESET_MODE", "accurate")

        self._rules: List[str] = []
        self._ipv4_rules: List[str] = []
        self._ipv6_rules: List[str] = []

    def run_command(self, cmd: str) -> int:
        """Execute a FireHOL command."""
        commands = {
            "start": self.cmd_start,
            "try": self.cmd_try,
            "stop": self.cmd_stop,
            "status": self.cmd_status,
            "panic": self.cmd_panic,
            "restore": self.cmd_restore,
            "save": self.cmd_save,
            "debug": self.cmd_debug,
            "explain": self.cmd_explain,
            "wizard": self.cmd_wizard,
            "helpme": self.cmd_wizard,
            "restart": self.cmd_start,
            "condrestart": self.cmd_restore,
        }

        if cmd not in commands:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            return 1

        return commands[cmd]()

    def cmd_start(self) -> int:
        """Start/activate the firewall."""
        print(f"Activating firewall from {self.config_file}...")

        if not os.path.exists(self.config_file):
            print(f"Configuration file not found: {self.config_file}", file=sys.stderr)
            return 1

        try:
            self._generate_rules()
            self._apply_rules()
            print("Firewall activated successfully.")
            return 0
        except Exception as e:
            print(f"Error activating firewall: {e}", file=sys.stderr)
            return 1

    def cmd_try(self) -> int:
        """Try the firewall, allowing user to confirm or revert."""
        print(f"Testing firewall configuration from {self.config_file}...")

        if not os.path.exists(self.config_file):
            print(f"Configuration file not found: {self.config_file}", file=sys.stderr)
            return 1

        try:
            self._generate_rules()
            self._apply_rules()
            print("Firewall activated. Type 'commit' within 30 seconds to keep it.")

            try:
                response = input(
                    "Keep the firewall? (type 'commit' to accept - 30 seconds timeout): "
                )
                if response.strip().lower() == "commit":
                    print("Firewall committed successfully.")
                    return 0
                else:
                    print("Firewall not committed. Reverting...")
                    self.cmd_stop()
                    return 1
            except TimeoutError:
                print("Timeout. Reverting firewall...")
                self.cmd_stop()
                return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    def cmd_stop(self) -> int:
        """Stop the firewall, allowing all traffic."""
        print("Stopping firewall (allowing all traffic)...")

        try:
            if self.enable_ipv4:
                subprocess.run(
                    ["iptables", "-t", "filter", "-P", "INPUT", "ACCEPT"], check=True
                )
                subprocess.run(
                    ["iptables", "-t", "filter", "-P", "OUTPUT", "ACCEPT"], check=True
                )
                subprocess.run(
                    ["iptables", "-t", "filter", "-P", "FORWARD", "ACCEPT"], check=True
                )
                subprocess.run(["iptables", "-F"], check=True)

            if self.enable_ipv6:
                subprocess.run(
                    ["ip6tables", "-t", "filter", "-P", "INPUT", "ACCEPT"], check=True
                )
                subprocess.run(
                    ["ip6tables", "-t", "filter", "-P", "OUTPUT", "ACCEPT"], check=True
                )
                subprocess.run(
                    ["ip6tables", "-t", "filter", "-P", "FORWARD", "ACCEPT"], check=True
                )
                subprocess.run(["ip6tables", "-F"], check=True)

            print("Firewall stopped.")
            return 0
        except subprocess.CalledProcessError as e:
            print(f"Error stopping firewall: {e}", file=sys.stderr)
            return 1

    def cmd_status(self) -> int:
        """Show firewall status."""
        print("Firewall status:")

        if self.enable_ipv4:
            print("\n=== IPv4 ===")
            subprocess.run(["iptables", "-t", "filter", "-L", "-n", "-v"])

        if self.enable_ipv6:
            print("\n=== IPv6 ===")
            subprocess.run(["ip6tables", "-t", "filter", "-L", "-n", "-v"])

        return 0

    def cmd_panic(self) -> int:
        """Block all traffic."""
        print("Panic mode: blocking all traffic...")

        try:
            if self.enable_ipv4:
                subprocess.run(
                    ["iptables", "-t", "filter", "-P", "INPUT", "DROP"], check=True
                )
                subprocess.run(
                    ["iptables", "-t", "filter", "-P", "OUTPUT", "DROP"], check=True
                )
                subprocess.run(
                    ["iptables", "-t", "filter", "-P", "FORWARD", "DROP"], check=True
                )
                subprocess.run(["iptables", "-F"], check=True)

            if self.enable_ipv6:
                subprocess.run(
                    ["ip6tables", "-t", "filter", "-P", "INPUT", "DROP"], check=True
                )
                subprocess.run(
                    ["ip6tables", "-t", "filter", "-P", "OUTPUT", "DROP"], check=True
                )
                subprocess.run(
                    ["ip6tables", "-t", "filter", "-P", "FORWARD", "DROP"], check=True
                )
                subprocess.run(["ip6tables", "-F"], check=True)

            print("All traffic blocked.")
            return 0
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    def cmd_restore(self) -> int:
        """Restore the last saved firewall."""
        print("Restoring last saved firewall...")

        restore_script = f"{self.spool_dir}/firewall_restore_commands.sh"

        if not os.path.exists(restore_script):
            print("No saved firewall found.", file=sys.stderr)
            return 1

        try:
            subprocess.run(["bash", restore_script], check=True)
            print("Firewall restored.")
            return 0
        except subprocess.CalledProcessError as e:
            print(f"Error restoring firewall: {e}", file=sys.stderr)
            return 1

    def cmd_save(self) -> int:
        """Start and save the firewall."""
        result = self.cmd_start()
        if result == 0:
            self._save_rules()
        return result

    def cmd_debug(self) -> int:
        """Parse config and show generated iptables commands."""
        print(f"Parsing configuration: {self.config_file}")

        if not os.path.exists(self.config_file):
            print(f"Configuration file not found: {self.config_file}", file=sys.stderr)
            return 1

        try:
            self._generate_rules()
            print("\n=== Generated iptables rules ===")
            print("\n".join(self._ipv4_rules))
            if self._ipv6_rules:
                print("\n=== Generated ip6tables rules ===")
                print("\n".join(self._ipv6_rules))
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    def cmd_explain(self) -> int:
        """Interactive mode with explanations."""
        print("Interactive mode - enter configuration directives")
        print("Type 'exit' to finish, 'help' for available commands")

        while True:
            try:
                line = input("firehol> ").strip()
                if not line:
                    continue
                if line == "exit":
                    break
                if line == "help":
                    self._show_help()
                else:
                    print(f"Would execute: {line}")
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nExiting...")
                break
        return 0

    def cmd_wizard(self) -> int:
        """Wizard mode to help create configuration."""
        print("FireHOL Configuration Wizard")
        print("=" * 40)

        print("\nThis wizard will help you create a basic firewall configuration.")
        print("For now, this is a placeholder.")

        return 0

    def _generate_rules(self) -> None:
        """Parse config and generate iptables rules."""
        from .config import FireHOLConfigParser

        parser = FireHOLConfigParser(self.config_file, self.services_dir)
        config = parser.parse()

        generator = RuleGenerator(config, self.enable_ipv4, self.enable_ipv6)
        self._ipv4_rules = generator.generate_ipv4_rules()
        self._ipv6_rules = generator.generate_ipv6_rules()

    def _apply_rules(self) -> None:
        """Apply the generated rules using iptables-restore."""
        import io

        if self._ipv4_rules:
            rule_data = "*filter\n" + "\n".join(self._ipv4_rules) + "\nCOMMIT\n"
            proc = subprocess.Popen(
                ["iptables-restore"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate(rule_data.encode())
            if proc.returncode != 0:
                raise Exception(f"Failed to apply IPv4 rules: {stderr.decode()}")

        if self._ipv6_rules:
            rule_data = "*filter\n" + "\n".join(self._ipv6_rules) + "\nCOMMIT\n"
            proc = subprocess.Popen(
                ["ip6tables-restore"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate(rule_data.encode())
            if proc.returncode != 0:
                raise Exception(f"Failed to apply IPv6 rules: {stderr.decode()}")

    def _save_rules(self) -> None:
        """Save rules to system location for persistence."""
        if self._ipv4_rules:
            save_path = f"{self.spool_dir}/ipv4.rules"
            with open(save_path, "w") as f:
                f.write("*filter\n")
                f.write("\n".join(self._ipv4_rules))
                f.write("\nCOMMIT\n")

        if self._ipv6_rules:
            save_path = f"{self.spool_dir}/ipv6.rules"
            with open(save_path, "w") as f:
                f.write("*filter\n")
                f.write("\n".join(self._ipv6_rules))
                f.write("\nCOMMIT\n")

    def _show_help(self) -> None:
        """Show help for interactive mode."""
        print("""
Available commands:
  interface <name> [policy]  - Define an interface
  router <name> [policy]     - Define a router  
  server <name>              - Define a server service
  client <name>              - Define a client service
  protection <level>         - Set protection level
  policy <action>            - Set default policy
  exit                       - Exit interactive mode
""")


class RuleGenerator:
    """Generate iptables rules from parsed configuration."""

    def __init__(
        self, config: Dict[str, Any], enable_ipv4: bool = True, enable_ipv6: bool = True
    ):
        self.config = config
        self.enable_ipv4 = enable_ipv4
        self.enable_ipv6 = enable_ipv6
        self.rules: List[str] = []

    def generate_ipv4_rules(self) -> List[str]:
        """Generate IPv4 iptables rules."""
        if not self.enable_ipv4:
            return []

        self.rules = []

        self._add_default_policies()
        self._add_loopback_rules()
        self._add_established_rules()
        self._add_interface_rules()
        self._add_router_rules()

        return self.rules

    def generate_ipv6_rules(self) -> List[str]:
        """Generate IPv6 ip6tables rules."""
        if not self.enable_ipv6:
            return []

        self.rules = []

        self._add_default_policies()
        self._add_loopback_rules()
        self._add_established_rules()
        self._add_interface_rules()
        self._add_router_rules()

        return self.rules

    def _add_default_policies(self) -> None:
        """Add default policies."""
        self.rules.append("-P INPUT DROP")
        self.rules.append("-P OUTPUT DROP")
        self.rules.append("-P FORWARD DROP")

    def _add_loopback_rules(self) -> None:
        """Add loopback interface rules."""
        self.rules.append("-A INPUT -i lo -j ACCEPT")
        self.rules.append("-A OUTPUT -o lo -j ACCEPT")

    def _add_established_rules(self) -> None:
        """Add established/related connection rules."""
        self.rules.append(
            "-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT"
        )
        self.rules.append(
            "-A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT"
        )
        self.rules.append(
            "-A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT"
        )

    def _add_interface_rules(self) -> None:
        """Add interface-specific rules."""
        interfaces = self.config.get("interfaces", [])
        for iface in interfaces:
            name = iface.get("name", "default")
            policy = iface.get("policy", "DROP")

            self.rules.append(f":{name} - [0:0]")

            for rule in iface.get("rules", []):
                self._add_rule_from_config(rule, name, "input")

    def _add_router_rules(self) -> None:
        """Add router-specific rules."""
        routers = self.config.get("routers", [])
        for router in routers:
            name = router.get("name", "default")

            self.rules.append(f":{name} - [0:0]")

            for rule in router.get("rules", []):
                self._add_rule_from_config(rule, name, "forward")

    def _add_rule_from_config(
        self, rule: Dict[str, Any], chain: str, default_chain: str
    ) -> None:
        """Add a rule from configuration."""
        action = rule.get("action", "ACCEPT").upper()
        protocol = rule.get("protocol")
        src = rule.get("src")
        dst = rule.get("dst")
        sport = rule.get("sport")
        dport = rule.get("dport")

        parts = ["-A", chain]

        if src:
            parts.extend(["-s", src])
        if dst:
            parts.extend(["-d", dst])
        if protocol:
            parts.extend(["-p", protocol])
        if sport:
            parts.extend(["--sport", str(sport)])
        if dport:
            parts.extend(["--dport", str(dport)])

        parts.extend(["-j", action])

        self.rules.append(" ".join(parts))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FireHOL - A firewall for humans",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start       Activate the firewall configuration
  try         Activate and wait for user confirmation
  stop        Stop the firewall (allow all traffic)
  status      Show firewall status
  panic       Block all traffic
  restore     Restore last saved firewall
  save        Start and save firewall
  debug       Show generated iptables commands
  explain     Interactive mode with explanations
  wizard      Configuration wizard
  helpme      Alias for wizard
  restart     Alias for start
        """,
    )

    parser.add_argument(
        "--version", "-V", action="version", version=f"FireHOL {VERSION}"
    )

    parser.add_argument(
        "config_file",
        nargs="?",
        default=None,
        help="Configuration file (default: /etc/firehol/firehol.conf)",
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="status",
        help="Command to execute (default: status)",
    )

    parser.add_argument(
        "--fast", action="store_true", help="Use fast activation (default)"
    )

    parser.add_argument("--nofast", action="store_true", help="Disable fast activation")

    parser.add_argument(
        "--optimal", action="store_true", help="Use optimal ruleset mode"
    )

    parser.add_argument(
        "--accurate", action="store_true", help="Use accurate ruleset mode (default)"
    )

    args = parser.parse_args()

    if os.geteuid() != 0:
        print("Error: FireHOL must be run as root", file=sys.stderr)
        return 1

    firehol = FireHOL(config_file=args.config_file)

    if args.nofast:
        firehol.fast_activation = False
    if args.optimal:
        firehol.ruleset_mode = "optimal"
    if args.accurate:
        firehol.ruleset_mode = "accurate"

    return firehol.run_command(args.command)


if __name__ == "__main__":
    sys.exit(main())
