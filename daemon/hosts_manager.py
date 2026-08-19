"""
Safe hosts file manager with atomic writes and delimited blocks.
"""
import os
import re
import tempfile
import logging
from typing import List, Set

logger = logging.getLogger("focus-guard.hosts")

HEADER_MARKER = "### FOCUS-GUARD-BLOCK-START - DO NOT EDIT MANUALLY ###"
FOOTER_MARKER = "### FOCUS-GUARD-BLOCK-END ###"


class HostsManager:
    def __init__(self, hosts_path: str = "/etc/hosts"):
        self.hosts_path = hosts_path

    def _expand_domains(self, domains: List[str]) -> Set[str]:
        """Expands domain list to include common subdomains (www, m)."""
        expanded = set()
        for d in domains:
            d = d.strip().lower()
            if not d or d.startswith("#"):
                continue
            expanded.add(d)
            if not d.startswith("www."):
                expanded.add(f"www.{d}")
            if not d.startswith("m."):
                expanded.add(f"m.{d}")
        return sorted(expanded)

    def _read_hosts_clean(self) -> str:
        """Reads hosts file and strips any existing Focus-Guard block."""
        if not os.path.exists(self.hosts_path):
            return ""

        with open(self.hosts_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Regex to match the block including markers
        pattern = re.compile(
            rf"\n?{re.escape(HEADER_MARKER)}.*?{re.escape(FOOTER_MARKER)}\n?",
            re.DOTALL
        )
        clean_content = re.sub(pattern, "", content).rstrip()
        return clean_content

    def _write_atomic(self, content: str) -> bool:
        """Writes content atomically to the hosts file to avoid race conditions."""
        hosts_dir = os.path.dirname(os.path.abspath(self.hosts_path))
        temp_file = None
        try:
            # Create temp file in the same directory to allow atomic os.replace across filesystems
            with tempfile.NamedTemporaryFile("w", dir=hosts_dir, delete=False, encoding="utf-8") as tf:
                temp_file = tf.name
                tf.write(content.rstrip() + "\n")
                tf.flush()
                os.fsync(tf.fileno())

            # Preserve original permissions if possible, else 0644
            try:
                if os.path.exists(self.hosts_path):
                    st = os.stat(self.hosts_path)
                    os.chmod(temp_file, st.st_mode)
                    os.chown(temp_file, st.st_uid, st.st_gid)
                else:
                    os.chmod(temp_file, 0o644)
            except Exception as e:
                logger.warning(f"Could not copy permissions for hosts file: {e}")

            os.replace(temp_file, self.hosts_path)
            return True
        except Exception as e:
            logger.error(f"Failed to write atomically to {self.hosts_path}: {e}")
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
            raise
        return False

    def is_blocked(self) -> bool:
        """Returns True if the Focus-Guard block currently exists in the hosts file."""
        if not os.path.exists(self.hosts_path):
            return False
        try:
            with open(self.hosts_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return HEADER_MARKER in content and FOOTER_MARKER in content
        except Exception as e:
            logger.error(f"Error checking block status: {e}")
            return False

    def apply_block(self, domains: List[str], ipv4: str = "127.0.0.1", ipv6: str = "::1") -> bool:
        """Adds or updates the blocked domains inside the Focus-Guard block."""
        try:
            clean_base = self._read_hosts_clean()
            expanded_domains = self._expand_domains(domains)

            if not expanded_domains:
                logger.info("No domains to block. Removing block if present.")
                return self.remove_block()

            block_lines = [HEADER_MARKER]
            for domain in expanded_domains:
                block_lines.append(f"{ipv4} {domain}")
                block_lines.append(f"{ipv6} {domain}")
            block_lines.append(FOOTER_MARKER)

            new_block = "\n".join(block_lines)
            new_content = f"{clean_base}\n\n{new_block}\n" if clean_base else f"{new_block}\n"

            self._write_atomic(new_content)
            logger.info(f"Successfully blocked {len(expanded_domains)} domain entries in {self.hosts_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply block: {e}")
            return False

    def remove_block(self) -> bool:
        """Removes the Focus-Guard block completely, restoring clean hosts."""
        try:
            if not self.is_blocked():
                return True
            clean_base = self._read_hosts_clean()
            self._write_atomic(clean_base)
            logger.info(f"Successfully removed Focus-Guard block from {self.hosts_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove block: {e}")
            return False
