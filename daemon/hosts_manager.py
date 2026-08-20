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
    "x.com": ["twitter.com", "mobile.twitter.com", "t.co", "twimg.com"],
    "twitter.com": ["x.com", "mobile.twitter.com", "t.co", "twimg.com"],
    "instagram.com": ["threads.net", "cdninstagram.com"],
    "facebook.com": ["fb.com", "messenger.com"],
    "youtube.com": ["youtu.be", "googlevideo.com", "music.youtube.com"],
    "reddit.com": ["old.reddit.com", "redd.it", "redditstatic.com"]
}


DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$")


def is_valid_domain(domain: str) -> bool:
    """Validates domain against RFC compliance and rejects CRLF / injection payloads."""
    if not isinstance(domain, str):
        return False
    if any(c in domain for c in ["\n", "\r", "\t", " ", "#", "/", "\\", ":", ";"]):
        return False
    clean = domain.strip().lower()
    if not clean or len(clean) > 253:
        return False
    return bool(DOMAIN_REGEX.match(clean))


class HostsManager:
    def __init__(self, hosts_path: str = "/etc/hosts", redirect_ipv4: str = "0.0.0.0", redirect_ipv6: str = "::1"):
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

    def _get_temp_dir(self) -> str:
        """
        Resolves safe temp directory on the same filesystem as hosts_path.
        Uses /etc/focus-guard when available to comply with systemd ProtectSystem=strict.
        """
        if self.hosts_path.startswith("/etc") and os.path.exists("/etc/focus-guard") and os.access("/etc/focus-guard", os.W_OK):
            return "/etc/focus-guard"
        dir_name = os.path.dirname(self.hosts_path)
        if dir_name and os.path.exists(dir_name) and os.access(dir_name, os.W_OK):
            return dir_name
        return "/tmp"

    def _expand_domains(self, domains: List[str]) -> List[str]:
        """Expands and strictly validates domains (subdomains, siblings, DoH canary)."""
        expanded: Set[str] = set()

        # Always include the DoH Canary domain if valid
        for canary in CANARY_DOH_DOMAINS:
            if is_valid_domain(canary):
                expanded.add(canary)

        for d in domains:
            if not is_valid_domain(d):
                logger.warning(f"Ignoring invalid or unsafe domain format: '{d}'")
                continue

            clean = d.strip().lower()
            expanded.add(clean)

            # Subdomain prefixes
            if not clean.startswith("www."):
                candidate = f"www.{clean}"
                if is_valid_domain(candidate):
                    expanded.add(candidate)
            if not clean.startswith("m."):
                candidate = f"m.{clean}"
                if is_valid_domain(candidate):
                    expanded.add(candidate)
            if not clean.startswith("l.") and "instagram" in clean:
                candidate = f"l.{clean}"
                if is_valid_domain(candidate):
                    expanded.add(candidate)

            # Sibling domains
            if clean in DOMAIN_SIBLINGS:
                for sib in DOMAIN_SIBLINGS[clean]:
                    if is_valid_domain(sib):
                        expanded.add(sib)
                        expanded.add(f"www.{sib}")
                        expanded.add(f"m.{sib}")

        return sorted([d for d in expanded if is_valid_domain(d)])

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

    def _write_hosts_content(self, new_content: str) -> bool:
        """
        Safely writes content to hosts file.
        Attempts atomic os.replace via tempfile first; if EXDEV (bind mount in systemd) occurs,
        falls back to direct in-place write with r+ and fsync.
        """
        temp_name = None
        try:
            temp_dir = self._get_temp_dir()
            with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tmp:
                tmp.write(new_content)
                temp_name = tmp.name

            if os.path.exists(self.hosts_path):
                os.chmod(temp_name, 0o644)

            os.replace(temp_name, self.hosts_path)
            return True
        except OSError as e:
            # Handle [Errno 18] EXDEV (Invalid cross-device link from systemd bind mounts) or Read-only FS
            if temp_name and os.path.exists(temp_name):
                try:
                    os.unlink(temp_name)
                except Exception:
                    pass

            # Fallback: In-place direct atomic write with fsync
            try:
                with open(self.hosts_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                    f.flush()
                    os.fsync(f.fileno())
                return True
            except Exception as direct_err:
                logger.error(f"In-place write to {self.hosts_path} failed: {direct_err}")
                return False
        except Exception as e:
            if temp_name and os.path.exists(temp_name):
                try:
                    os.unlink(temp_name)
                except Exception:
                    pass
            logger.error(f"Failed to write {self.hosts_path}: {e}")
            return False

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

            if self._write_hosts_content(new_content):
                logger.info(f"Successfully blocked {len(self._expand_domains(domains))} domain entries in {self.hosts_path}")
                return True
            return False

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

            if self._write_hosts_content(new_content):
                logger.info(f"Successfully removed Focus-Guard block from {self.hosts_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to remove block from {self.hosts_path}: {e}")
            return False
