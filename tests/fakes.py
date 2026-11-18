"""
tests/fakes.py
In-memory stand-ins for every OS operation. Automated tests use these, so no
test ever changes the real DNS, hosts file or scheduled tasks of the machine.
"""
import copy
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
if APP not in sys.path:
    sys.path.insert(0, APP)

def inherited_copyright_holder():
    """Name in LICENSE's 'Inherited code' copyright line (read at runtime so
    tests don't repeat it). Returns '' if LICENSE has no such section."""
    import re
    with open(os.path.join(ROOT, "LICENSE"), encoding="utf-8") as f:
        text = f.read()
    section = text.split("Inherited code", 1)[-1]
    m = re.search(r"Copyright \(c\) ([^\r\n]+)", section)
    return m.group(1).strip() if m else ""


HOSTS = ("updates.discord.com", "discord.com", "gateway.discord.gg",
         "cdn.discordapp.com", "media.discordapp.net")


def dhcp_snapshot(guid="11111111-2222-3333-4444-555555555555"):
    return {"interface_guid": guid,
            "ipv4": {"dhcp": True, "servers": [], "primary": None, "secondary": None},
            "ipv6": {"dhcp": True, "servers": [], "primary": None, "secondary": None}}


def static_snapshot(servers, guid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"):
    return {"interface_guid": guid,
            "ipv4": {"dhcp": False, "servers": list(servers), "primary": servers[0],
                     "secondary": servers[1] if len(servers) > 1 else None},
            "ipv6": {"dhcp": True, "servers": [], "primary": None, "secondary": None}}


class FakeRelay:
    def __init__(self, ops):
        self.ops = ops
        self.running = False

    def preflight(self, host="discord.com"):
        self.ops.calls.append("preflight")
        if self.ops.fail.get("doh"):
            raise RuntimeError("doh down")
        return ["162.159.0.1"]

    def start(self):
        self.ops.calls.append("relay_start")
        if self.ops.fail.get("port"):
            return False
        self.running = True
        return True

    def stop(self):
        self.ops.calls.append("relay_stop")
        self.running = False

    def is_active(self):
        return self.running


class FakeOps:
    def __init__(self, adapters=None, dns=None):
        from core.dns_manager import normalize_snapshot
        self._normalize = normalize_snapshot
        self.calls = []
        self.fail = {}
        self.lock = threading.Lock()
        self.adapters = adapters if adapters is not None else [{"name": "Wi-Fi"}]
        self.dns = dns if dns is not None else {a["name"]: dhcp_snapshot() for a in self.adapters}
        self.original_dns = copy.deepcopy(self.dns)
        self.hosts_entries = []
        self.task = False
        self.store = {}
        self.store_writable = True
        self.relay = None
        self.verify_results = []
        self.admin = True

    # adapters / dns
    def active_adapters(self):
        return [dict(a) for a in self.adapters]

    def all_adapter_names(self):
        return {a["name"] for a in self.adapters}

    def get_dns(self, name):
        if self.fail.get("get_dns"):
            raise RuntimeError("cannot read")
        return copy.deepcopy(self.dns[name])

    def set_secure_dns(self, name):
        self.calls.append(f"set_dns:{name}")
        if self.fail.get("set_dns") == name or self.fail.get("set_dns") is True:
            return False, "netsh failed"
        guid = self.dns[name].get("interface_guid")
        self.dns[name] = static_snapshot(["1.1.1.1", "1.0.0.1"], guid=guid)
        return True, "OK"

    def restore_dns(self, name, snap):
        self.calls.append(f"restore_dns:{name}")
        if self.fail.get("restore_dns"):
            return False, "netsh failed"
        self.dns[name] = copy.deepcopy(snap)
        return True, "OK"

    def normalize_snapshot(self, snap):
        return self._normalize(snap)

    def flush_dns(self):
        self.calls.append("flush")

    # protected store
    def load_dns_backup(self):
        return copy.deepcopy(self.store)

    def save_dns_backup(self, backup):
        if not self.store_writable:
            return False
        self.store = copy.deepcopy(backup or {})
        return True

    # hosts
    def add_hosts(self):
        self.calls.append("add_hosts")
        if self.fail.get("hosts"):
            return False
        self.hosts_entries = list(HOSTS)
        return True

    def remove_hosts(self):
        self.calls.append("remove_hosts")
        if self.fail.get("remove_hosts"):
            return False
        self.hosts_entries = []
        return True

    def hosts_active(self):
        return bool(self.hosts_entries)

    def routed_hosts(self):
        return list(self.hosts_entries)

    def total_hosts(self):
        return len(HOSTS)

    def relay_port_free(self):
        return not self.fail.get("port_taken")

    def last_hosts_error(self):
        return "locked", self.fail.get("hosts_winerror")

    # failsafe
    def failsafe_target(self):
        return None if self.fail.get("no_target") else r"C:\Program Files\KJ Des\KJDes.exe"

    def install_failsafe(self):
        self.calls.append("install_task")
        if self.fail.get("task"):
            return False
        self.task = True
        return True

    def reconcile_failsafe(self, cleared):
        self.calls.append(f"reconcile:{cleared}")
        if cleared:
            self.task = False
        return not self.fail.get("reconcile")

    def failsafe_error(self):
        return ""

    def create_relay(self, log):
        self.relay = FakeRelay(self)
        return self.relay

    def verify_path(self, timeout=30.0):
        self.calls.append("verify")
        if self.verify_results:
            return self.verify_results.pop(0)
        if self.fail.get("verify"):
            return False, "timeout"
        return True, "tls=TLSv1.3"

    def is_admin(self):
        return self.admin


class MemoryLog:
    def __init__(self):
        self.lines = []
        self.enabled = True

    def write(self, message, *, level="INFO"):
        self.lines.append(message)

    def read_lines(self, last_n=200):
        return [line + "\n" for line in self.lines[-last_n:]]

    def clear(self):
        self.lines.clear()
