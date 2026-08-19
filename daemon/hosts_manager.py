"""
Focus-Guard Hosts Manager.
Atomically manages /etc/hosts entries with strict delimiters, DoH Canary protection, and subdomain expansion.
"""
import os
import re
import tempfile
import logging
from typing import List, Set, Optional

logger = logging.getLogger("focus-guard.hosts")

BLOCK_START_DELIMITER = "### FOCUS-GUARD-BLOCK-START - DO NOT EDIT MANUALLY ###"
BLOCK_END_DELIMITER = "### FOCUS-GUARD-BLOCK-END ###"

# Backward compatibility aliases
HEADER_MARKER = BLOCK_START_DELIMITER
FOOTER_MARKER = BLOCK_END_DELIMITER

# Mozilla DoH Canary Domain to force browsers (Firefox/Chromium) to respect local /etc/hosts
CANARY_DOH_DOMAINS = [
    "use-application-dns.net"
]

# Sibling domain expansions for complete coverage
DOMAIN_SIBLINGS = {
    "x.com": ["twitter.com", "t.co", "twimg.com"],
    "twitter.com": ["x.com", "t.co", "twimg.com"],
    "instagram.com": ["threads.net", "cdninstagram.com"],
    "facebook.com": ["fb.com", "messenger.com"],
    "youtube.com": ["youtu.be", "googlevideo.com"]
}


class HostsManager:
    def __init__(self, hosts_path: str = "/etc/hosts", redirect_ipv4: str = "127.0.0.1", redirect_ipv6: str = "::1"):
        self.hosts_path = hosts_path
        self.redirect_ipv4 = redirect_ipv4
        self.redirect_ipv6 = redirect_ipv6

    def is_blocked(self) -> bool:
        """Checks if the Focus-Guard block is currently present in the hosts file."""
        if not os.path.exists(self.hosts_path):
            return False
        try:
            with open(self.hosts_path, "r", encoding="utf-8") as f:
                return BLOCK_START_DELIMITER in f.read()
        except Exception:
            return False

    def _expand_domains(self, domains: List[str]) -> List[str]:
        """Expands domains to include www, m., l., siblings, and DoH canaries."""
        expanded: Set[str] = set()

        # Always include the DoH Canary domain
        for canary in CANARY_DOH_DOMAINS:
            expanded.add(canary)

        for d in domains:
            clean = d.strip().lower()
            if not clean:
                continue

            expanded.add(clean)

            # Subdomain prefixes
            if not clean.startswith("www."):
                expanded.add(f"www.{clean}")
            if not clean.startswith("m."):
                expanded.add(f"m.{clean}")
            if not clean.startswith("l.") and "instagram" in clean:
                expanded.add(f"l.{clean}")

            # Sibling domains
            if clean in DOMAIN_SIBLINGS:
                for sib in DOMAIN_SIBLINGS[clean]:
                    expanded.add(sib)
                    expanded.add(f"www.{sib}")
                    expanded.add(f"m.{sib}")

        return sorted(list(expanded))

    def _generate_block_content(self, domains: List[str], redirect_ipv4: Optional[str] = None, redirect_ipv6: Optional[str] = None) -> str:
        """Generates the block section for the hosts file."""
        expanded_domains = self._expand_domains(domains)
        if not expanded_domains:
            return ""

        ipv4 = redirect_ipv4 or self.redirect_ipv4
        ipv6 = redirect_ipv6 or self.redirect_ipv6

        lines = [BLOCK_START_DELIMITER]
        for d in expanded_domains:
            lines.append(f"{ipv4} {d}")
            if ipv6:
                lines.append(f"{ipv6} {d}")
        lines.append(BLOCK_END_DELIMITER)
        return "\n".join(lines) + "\n"

    def apply_block(self, domains: List[str], redirect_ipv4: Optional[str] = None, redirect_ipv6: Optional[str] = None) -> bool:
        """Atomically inserts or updates the Focus-Guard block in the hosts file."""
        try:
            current_content = ""
            if os.path.exists(self.hosts_path):
                with open(self.hosts_path, "r", encoding="utf-8") as f:
                    current_content = f.read()

            # Clean out any previous Focus-Guard block
            pattern = re.compile(
                rf"{re.escape(BLOCK_START_DELIMITER)}.*?{re.escape(BLOCK_END_DELIMITER)}\n?",
                re.DOTALL
            )
            cleaned_content = pattern.sub("", current_content).rstrip()

            block_str = self._generate_block_content(domains, redirect_ipv4, redirect_ipv6)
            new_content = cleaned_content + "\n\n" + block_str if cleaned_content else block_str

            # Atomic write via temporary file in the same directory
            dir_name = os.path.dirname(self.hosts_path) or "/tmp"
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp:
                tmp.write(new_content)
                temp_name = tmp.name

            # Preserve permissions
            if os.path.exists(self.hosts_path):
                os.chmod(temp_name, 0o644)

            os.replace(temp_name, self.hosts_path)
            logger.info(f"Successfully blocked {len(self._expand_domains(domains))} domain entries in {self.hosts_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply block to {self.hosts_path}: {e}")
            return False

    def remove_block(self) -> bool:
        """Atomically removes the Focus-Guard block from the hosts file."""
        try:
            if not os.path.exists(self.hosts_path):
                return True

            with open(self.hosts_path, "r", encoding="utf-8") as f:
                current_content = f.read()

            if BLOCK_START_DELIMITER not in current_content:
                return True

            pattern = re.compile(
                rf"{re.escape(BLOCK_START_DELIMITER)}.*?{re.escape(BLOCK_END_DELIMITER)}\n?",
                re.DOTALL
            )
            new_content = pattern.sub("", current_content).rstrip() + "\n"

            dir_name = os.path.dirname(self.hosts_path) or "/tmp"
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp:
                tmp.write(new_content)
                temp_name = tmp.name

            os.chmod(temp_name, 0o644)
            os.replace(temp_name, self.hosts_path)
            logger.info(f"Successfully removed Focus-Guard block from {self.hosts_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove block from {self.hosts_path}: {e}")
            return False
