"""
FireHOL configuration file parser.

Parses FireHOL configuration files which have a bash-like syntax.
"""

import re
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class FireHOLConfigParser:
    """Parser for FireHOL configuration files."""

    def __init__(self, config_file: str, services_dir: str):
        self.config_file = config_file
        self.services_dir = services_dir
        self.config: Dict[str, Any] = {
            "interfaces": [],
            "routers": [],
            "variables": {},
            "defaults": {},
        }
        self._current_context: Optional[str] = None
        self._current_item: Optional[Dict[str, Any]] = None
        self._services: Dict[str, Dict[str, Any]] = {}

    def parse(self) -> Dict[str, Any]:
        """Parse the configuration file."""
        self._load_services()
        self._parse_config_file()
        return self.config

    def _load_services(self) -> None:
        """Load service definitions from services directory."""
        if not os.path.isdir(self.services_dir):
            return

        for service_file in Path(self.services_dir).glob("*.conf"):
            try:
                self._parse_service_file(service_file)
            except Exception:
                pass

    def _parse_service_file(self, path: Path) -> None:
        """Parse a service definition file."""
        content = path.read_text()
        service_name = path.stem

        self._services[service_name] = {
            "name": service_name,
            "ports": [],
            "protocol": "tcp",
        }

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if "port" in key.lower():
                    self._services[service_name]["ports"] = [
                        int(p.strip()) for p in value.split(",")
                    ]
                elif "protocol" in key.lower():
                    self._services[service_name]["protocol"] = value

    def _parse_config_file(self) -> None:
        """Parse the main configuration file."""
        content = Path(self.config_file).read_text()

        lines = self._preprocess_lines(content)

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            try:
                self._parse_line(line, line_num)
            except Exception as e:
                print(f"Warning: Error parsing line {line_num}: {e}")

    def _preprocess_lines(self, content: str) -> List[str]:
        """Preprocess configuration lines."""
        lines = []

        for line in content.splitlines():
            line = line.rstrip()

            line = self._expand_variables(line)

            if line.endswith("\\"):
                lines.append(line[:-1].rstrip())
            else:
                lines.append(line)

        return lines

    def _expand_variables(self, line: str) -> str:
        """Expand ${VAR} and $VAR variables."""
        line = re.sub(r"\$\{([^}]+)\}", lambda m: os.environ.get(m.group(1), ""), line)
        line = re.sub(
            r"\$([A-Za-z_][A-Za-z0-9_]*)",
            lambda m: os.environ.get(m.group(1), ""),
            line,
        )
        return line

    def _parse_line(self, line: str, line_num: int) -> None:
        """Parse a single configuration line."""
        if line.startswith("interface "):
            self._parse_interface(line)
        elif line.startswith("router "):
            self._parse_router(line)
        elif line.startswith("server "):
            self._parse_server(line)
        elif line.startswith("client "):
            self._parse_client(line)
        elif line.startswith("policy "):
            self._parse_policy(line)
        elif line.startswith("protection "):
            self._parse_protection(line)
        elif line.startswith("iptables "):
            self._parse_iptables(line)
        elif (
            "=" in line
            and not line.startswith("server_")
            and not line.startswith("client_")
        ):
            key, value = line.split("=", 1)
            self.config["variables"][key.strip()] = value.strip().strip('"').strip("'")

    def _parse_interface(self, line: str) -> None:
        """Parse interface definition."""
        parts = line.split(None, 2)

        name = parts[1] if len(parts) > 1 else "default"
        policy = parts[2].strip('"').strip("'") if len(parts) > 2 else "DROP"

        self._current_context = "interface"
        self._current_item = {
            "name": name,
            "policy": policy,
            "rules": [],
            "type": "interface",
        }
        self.config["interfaces"].append(self._current_item)

    def _parse_router(self, line: str) -> None:
        """Parse router definition."""
        parts = line.split(None, 2)

        name = parts[1] if len(parts) > 1 else "default"
        policy = parts[2].strip('"').strip("'") if len(parts) > 2 else "DROP"

        self._current_context = "router"
        self._current_item = {
            "name": name,
            "policy": policy,
            "rules": [],
            "type": "router",
        }
        self.config["routers"].append(self._current_item)

    def _parse_server(self, line: str) -> None:
        """Parse server definition."""
        parts = line.split(None, 2)

        if len(parts) < 2:
            return

        service = parts[1]
        action = "ACCEPT"

        if len(parts) > 2:
            action = parts[2].upper()

        rule = {
            "type": "server",
            "service": service,
            "action": action,
        }

        if self._current_item is not None:
            self._current_item["rules"].append(rule)

    def _parse_client(self, line: str) -> None:
        """Parse client definition."""
        parts = line.split(None, 2)

        if len(parts) < 2:
            return

        service = parts[1]
        action = "ACCEPT"

        if len(parts) > 2:
            action = parts[2].upper()

        rule = {
            "type": "client",
            "service": service,
            "action": action,
        }

        if self._current_item is not None:
            self._current_item["rules"].append(rule)

    def _parse_policy(self, line: str) -> None:
        """Parse policy definition."""
        parts = line.split(None, 1)

        if len(parts) < 2:
            return

        policy = parts[1].upper()

        if self._current_item is not None:
            self._current_item["policy"] = policy
        else:
            self.config["defaults"]["policy"] = policy

    def _parse_protection(self, line: str) -> None:
        """Parse protection definition."""
        parts = line.split(None, 1)

        if len(parts) < 2:
            return

        level = parts[1]

        if self._current_item is not None:
            self._current_item["protection"] = level

    def _parse_iptables(self, line: str) -> None:
        """Parse raw iptables command."""
        if self._current_item is not None:
            self._current_item["rules"].append(
                {
                    "type": "raw",
                    "command": line[9:].strip(),
                }
            )


def parse_config_file(
    config_file: str, services_dir: str = "/etc/firehol/services"
) -> Dict[str, Any]:
    """Convenience function to parse a FireHOL configuration file."""
    parser = FireHOLConfigParser(config_file, services_dir)
    return parser.parse()
