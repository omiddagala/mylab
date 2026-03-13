#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml


ROOT = Path(__file__).resolve().parent.parent
GENERATED_DIR = ROOT / "generated"

HOSTS_FILE = ROOT / "hosts.yaml"
GLOBALS_FILE = ROOT / "globals.yaml"


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def dump_yaml(data: Dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def ensure_generated_dir() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def fqdn_sort_key(item: Tuple[str, Dict[str, Any]]) -> Tuple[str, str]:
    hostname, meta = item
    dc = str(meta.get("dc", ""))
    role = str(meta.get("role", ""))
    return (dc, role + ":" + hostname)


def load_hosts() -> Dict[str, Dict[str, Any]]:
    raw = load_yaml(HOSTS_FILE)
    hosts = raw.get("hosts")
    if not isinstance(hosts, dict):
        raise ValueError("hosts.yaml must contain a top-level 'hosts' mapping")
    normalized: Dict[str, Dict[str, Any]] = {}
    for hostname, meta in hosts.items():
        if not isinstance(meta, dict):
            raise ValueError(f"Host entry for {hostname} must be a mapping")
        if "ip" not in meta:
            raise ValueError(f"Host {hostname} is missing required field 'ip'")
        normalized[hostname] = meta
    return normalized


def load_globals() -> Dict[str, Any]:
    return load_yaml(GLOBALS_FILE)


def role_matches(role: str, expected: str) -> bool:
    return role.strip().lower() == expected.strip().lower()


def get_hosts_by_role(
    hosts: Dict[str, Dict[str, Any]],
    *roles: str,
) -> List[Tuple[str, Dict[str, Any]]]:
    wanted = {r.lower() for r in roles}
    result = []
    for hostname, meta in hosts.items():
        role = str(meta.get("role", "")).lower()
        if role in wanted:
            result.append((hostname, meta))
    return sorted(result, key=fqdn_sort_key)


def get_hosts_by_cluster(
    hosts: Dict[str, Dict[str, Any]],
    cluster_name: str,
) -> List[Tuple[str, Dict[str, Any]]]:
    result = []
    for hostname, meta in hosts.items():
        if str(meta.get("cluster", "")) == cluster_name:
            result.append((hostname, meta))
    return sorted(result, key=fqdn_sort_key)


def unique_clusters(hosts: Dict[str, Dict[str, Any]]) -> List[str]:
    clusters = set()
    for meta in hosts.values():
        cluster = meta.get("cluster")
        if cluster:
            clusters.add(str(cluster))
    return sorted(clusters)


def build_ansible_inventory(hosts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    inventory: Dict[str, Any] = {
        "all": {
            "children": {
                "linux": {"hosts": {}},
                "bastion": {"hosts": {}},
                "routers": {"hosts": {}},
                "leafs": {"hosts": {}},
                "k8s_prod1": {"hosts": {}},
                "k8s_dev": {"hosts": {}},
                "k8s_prod2": {"hosts": {}},
                "k8s_control_plane": {"hosts": {}},
                "k8s_workers": {"hosts": {}},
                "dc1": {"hosts": {}},
                "dc2": {"hosts": {}},
            }
        }
    }

    children = inventory["all"]["children"]

    for hostname, meta in sorted(hosts.items(), key=fqdn_sort_key):
        ip = meta["ip"]
        role = str(meta.get("role", ""))
        dc = str(meta.get("dc", ""))

        hostvars: Dict[str, Any] = {
            "ansible_host": ip,
            "role": role,
        }

        if dc:
            hostvars["dc"] = dc
        if "cluster" in meta:
            hostvars["cluster"] = meta["cluster"]
        if "loopback" in meta:
            hostvars["loopback"] = meta["loopback"]
        if "vlan" in meta:
            hostvars["vlan"] = meta["vlan"]

        children["linux"]["hosts"][hostname] = hostvars

        if role_matches(role, "bastion"):
            children["bastion"]["hosts"][hostname] = {"ansible_host": ip}
        elif role_matches(role, "router"):
            children["routers"]["hosts"][hostname] = {"ansible_host": ip}
        elif role_matches(role, "leaf"):
            children["leafs"]["hosts"][hostname] = {"ansible_host": ip}
        elif role_matches(role, "k8s-master"):
            cluster = str(meta.get("cluster", ""))
            if cluster == "prod1":
                children["k8s_prod1"]["hosts"][hostname] = {"ansible_host": ip}
            elif cluster == "dev":
                children["k8s_dev"]["hosts"][hostname] = {"ansible_host": ip}
            elif cluster == "prod2":
                children["k8s_prod2"]["hosts"][hostname] = {"ansible_host": ip}
            children["k8s_control_plane"]["hosts"][hostname] = {"ansible_host": ip}
        elif role_matches(role, "k8s-worker"):
            cluster = str(meta.get("cluster", ""))
            if cluster == "prod1":
                children["k8s_prod1"]["hosts"][hostname] = {"ansible_host": ip}
            elif cluster == "dev":
                children["k8s_dev"]["hosts"][hostname] = {"ansible_host": ip}
            elif cluster == "prod2":
                children["k8s_prod2"]["hosts"][hostname] = {"ansible_host": ip}
            children["k8s_workers"]["hosts"][hostname] = {"ansible_host": ip}

        if dc == "dc1":
            children["dc1"]["hosts"][hostname] = {"ansible_host": ip}
        elif dc == "dc2":
            children["dc2"]["hosts"][hostname] = {"ansible_host": ip}

    return inventory


def build_kubespray_inventory(hosts: Dict[str, Dict[str, Any]]) -> str:
    cp_hosts: List[str] = []
    worker_hosts: List[str] = []
    cluster_map: Dict[str, List[str]] = {
        "prod1": [],
        "dev": [],
        "prod2": [],
    }

    lines: List[str] = []
    lines.append("[all]")
    lines.append("")

    for hostname, meta in sorted(hosts.items(), key=fqdn_sort_key):
        role = str(meta.get("role", ""))
        cluster = str(meta.get("cluster", ""))
        ip = str(meta["ip"])

        if role not in {"k8s-master", "k8s-worker"}:
            continue

        lines.append(f"{hostname} ansible_host={ip}")

        if role == "k8s-master":
            cp_hosts.append(hostname)
        if role == "k8s-worker":
            worker_hosts.append(hostname)

        if cluster in cluster_map:
            cluster_map[cluster].append(hostname)

    lines.append("")
    lines.append("[kube_control_plane]")
    for hostname in cp_hosts:
        lines.append(hostname)

    lines.append("")
    lines.append("[etcd]")
    for hostname in cp_hosts:
        lines.append(hostname)

    lines.append("")
    lines.append("[kube_node]")
    for hostname in worker_hosts:
        lines.append(hostname)

    lines.append("")
    lines.append("[calico_rr]")
    lines.append("")

    for cluster_name in ["prod1", "dev", "prod2"]:
        lines.append(f"[{cluster_name}]")
        for hostname in cluster_map[cluster_name]:
            lines.append(hostname)
        lines.append("")

    lines.append("[k8s_cluster:children]")
    lines.append("prod1")
    lines.append("dev")
    lines.append("prod2")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_dns_records(hosts: Dict[str, Dict[str, Any]], globals_cfg: Dict[str, Any]) -> Dict[str, Any]:
    domain = str(globals_cfg.get("lab_domain", "lab"))

    records: Dict[str, str] = {}
    ptr_records: Dict[str, str] = {}

    for hostname, meta in sorted(hosts.items(), key=fqdn_sort_key):
        ip = str(meta["ip"])
        records[hostname] = ip

        short = hostname.split(".")[0]
        fqdn_suffix = "." + domain
        if hostname.endswith(fqdn_suffix):
            records[short] = ip

        reversed_ip = ".".join(reversed(ip.split("."))) + ".in-addr.arpa"
        ptr_records[reversed_ip] = hostname

    return {
        "a_records": records,
        "ptr_records": ptr_records,
    }


def write_kubespray_inventory(content: str, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def main() -> int:
    try:
        ensure_generated_dir()

        hosts = load_hosts()
        globals_cfg = load_globals()

        ansible_inventory = build_ansible_inventory(hosts)
        kubespray_inventory = build_kubespray_inventory(hosts)
        dns_records = build_dns_records(hosts, globals_cfg)

        dump_yaml(ansible_inventory, GENERATED_DIR / "ansible_inventory.yaml")
        write_kubespray_inventory(kubespray_inventory, GENERATED_DIR / "kubespray_inventory.ini")
        dump_yaml(dns_records, GENERATED_DIR / "dns_records.yaml")

        print("Generated files:")
        print(f"  - {GENERATED_DIR / 'ansible_inventory.yaml'}")
        print(f"  - {GENERATED_DIR / 'kubespray_inventory.ini'}")
        print(f"  - {GENERATED_DIR / 'dns_records.yaml'}")
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())