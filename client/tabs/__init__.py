"""Focus-Guard Modular Tabs Package."""

from client.tabs.domains_tab import DomainsTab
from client.tabs.selective_tab import SelectiveTab
from client.tabs.rules_tab import RulesTab
from client.tabs.dashboard_tab import DashboardTab

__all__ = [
    "DomainsTab",
    "SelectiveTab",
    "RulesTab",
    "DashboardTab",
]
