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
        normalized[hostname] = dict(meta)
        normalized[hostname]["hostname"] = hostname
    return normalized


def load_globals() -> Dict[str, Any]:
    return load_yaml(GLOBALS_FILE)


def role_matches(role: str, expected: str) -> bool:
    left = role.strip().lower().replace("_", "-")
    right = expected.strip().lower().replace("_", "-")
    return left == right


def nameservers() -> List[str]:
    return ["1.1.1.1", "8.8.8.8"]


def mac_for_ip(ip: str) -> str:
    a, b, c, d = ip.split(".")
    return f"52:54:{int(a):02x}:{int(b):02x}:{int(c):02x}:{int(d):02x}"


def mgmt_ip_for_host(meta: Dict[str, Any]) -> str:
    hostname = str(meta.get("hostname", "")).strip()

    mgmt_map = {
        "bastion1.dc1.lab": "192.168.50.10/24",
        "r1-dc1.lab": "192.168.50.1/24",
        "r2-dc1.lab": "192.168.50.2/24",
        "leaf1-dc1.lab": "192.168.50.11/24",
        "leaf2-dc1.lab": "192.168.50.12/24",
        "prod1-cp1.dc1.lab": "192.168.50.21/24",
        "prod1-w1.dc1.lab": "192.168.50.31/24",
        "prod1-w2.dc1.lab": "192.168.50.32/24",
        "r1-dc2.lab": "192.168.50.41/24",
        "r2-dc2.lab": "192.168.50.42/24",
        "leaf1-dc2.lab": "192.168.50.51/24",
        "leaf2-dc2.lab": "192.168.50.52/24",
        "prod2-cp1.dc2.lab": "192.168.50.61/24",
        "prod2-w1.dc2.lab": "192.168.50.71/24",
        "prod2-w2.dc2.lab": "192.168.50.72/24",
    }

    if hostname not in mgmt_map:
        raise ValueError(f"No management IP mapping defined for host: {hostname}")

    return mgmt_map[hostname]


def mgmt_ip_plain(meta: Dict[str, Any]) -> str:
    return mgmt_ip_for_host(meta).split("/")[0]


def gateway_for_vlan(meta: Dict[str, Any]) -> str:
    dc = str(meta.get("dc", ""))
    vlan = str(meta.get("vlan", ""))

    if dc == "dc1" and vlan == "management":
        return "192.168.50.254"
    if dc == "dc1" and vlan == "infra":
        return "10.10.50.254"
    if dc == "dc1" and vlan == "prod1":
        return "10.10.20.254"
    if dc == "dc2" and vlan == "infra":
        return "10.20.50.254"
    if dc == "dc2" and vlan == "prod2":
        return "10.20.20.254"

    raise ValueError(f"Cannot derive gateway for host metadata: {meta}")


def wan_ip_for_router(meta: Dict[str, Any]) -> str:
    hostname = str(meta.get("hostname", ""))
    dc = str(meta.get("dc", ""))
    ip = str(meta["ip"])

    if dc == "dc1" and ip.endswith(".1"):
        return "172.16.255.11/24"
    if dc == "dc1" and ip.endswith(".2"):
        return "172.16.255.12/24"
    if dc == "dc2" and ip.endswith(".1"):
        return "172.16.255.21/24"
    if dc == "dc2" and ip.endswith(".2"):
        return "172.16.255.22/24"

    raise ValueError(f"Cannot derive WAN IP for router {hostname or meta}")


def role_vm_size(role: str) -> Dict[str, int]:
    if role_matches(role, "bastion"):
        return {"vcpu": 2, "memory_mb": 2048, "disk_gb": 20}
    if role_matches(role, "router"):
        return {"vcpu": 2, "memory_mb": 2048, "disk_gb": 16}
    if role_matches(role, "leaf"):
        return {"vcpu": 2, "memory_mb": 1536, "disk_gb": 12}
    if role_matches(role, "k8s-control-plane"):
        return {"vcpu": 2, "memory_mb": 4096, "disk_gb": 32}
    if role_matches(role, "k8s-worker"):
        return {"vcpu": 2, "memory_mb": 4096, "disk_gb": 40}
    return {"vcpu": 2, "memory_mb": 2048, "disk_gb": 20}


def build_ansible_inventory(hosts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    inventory: Dict[str, Any] = {
        "all": {
            "children": {
                "linux": {"hosts": {}},
                "bastion": {"hosts": {}},
                "routers": {"hosts": {}},
                "leafs": {"hosts": {}},
                "kubernetes": {
                    "children": {
                        "kube_control_plane": {"hosts": {}},
                        "kube_workers": {"hosts": {}},
                    }
                },
                "dc1": {"hosts": {}},
                "dc2": {"hosts": {}},
            }
        }
    }

    children = inventory["all"]["children"]

    for hostname, meta in sorted(hosts.items(), key=fqdn_sort_key):
        role = str(meta.get("role", ""))
        dc = str(meta.get("dc", ""))
        mgmt_ip = mgmt_ip_plain(meta)

        host_vars = {
            "ansible_host": mgmt_ip,
            "mylab_mgmt_ip": mgmt_ip,
            "mylab_primary_ip": str(meta["ip"]),
        }

        children["linux"]["hosts"][hostname] = dict(host_vars)

        if role_matches(role, "bastion"):
            children["bastion"]["hosts"][hostname] = dict(host_vars)
        elif role_matches(role, "router"):
            children["routers"]["hosts"][hostname] = dict(host_vars)
        elif role_matches(role, "leaf"):
            children["leafs"]["hosts"][hostname] = dict(host_vars)
        elif role_matches(role, "k8s-control-plane"):
            children["kubernetes"]["children"]["kube_control_plane"]["hosts"][hostname] = dict(host_vars)
        elif role_matches(role, "k8s-worker"):
            children["kubernetes"]["children"]["kube_workers"]["hosts"][hostname] = dict(host_vars)

        if dc == "dc1":
            children["dc1"]["hosts"][hostname] = dict(host_vars)
        elif dc == "dc2":
            children["dc2"]["hosts"][hostname] = dict(host_vars)

    return inventory


def build_kubespray_inventory(hosts: Dict[str, Dict[str, Any]]) -> str:
    cp_hosts: List[str] = []
    worker_hosts: List[str] = []

    lines: List[str] = ["[all]"]
    for hostname, meta in sorted(hosts.items(), key=fqdn_sort_key):
        role = str(meta.get("role", ""))
        workload_ip = str(meta["ip"])
        mgmt_ip = mgmt_ip_plain(meta)

        if role_matches(role, "k8s-control-plane") or role_matches(role, "k8s-worker"):
            lines.append(
                f"{hostname} ansible_host={mgmt_ip} ip={workload_ip} access_ip={workload_ip}"
            )
            if role_matches(role, "k8s-control-plane"):
                cp_hosts.append(hostname)
            else:
                worker_hosts.append(hostname)

    lines += ["", "[kube_control_plane]"] + cp_hosts
    lines += ["", "[etcd]"] + cp_hosts
    lines += ["", "[kube_node]"] + worker_hosts
    lines += ["", "[calico_rr]", "", "[k8s_cluster:children]", "kube_control_plane", "kube_node", ""]
    return "\n".join(lines)


def build_dns_records(hosts: Dict[str, Dict[str, Any]], globals_cfg: Dict[str, Any]) -> Dict[str, Any]:
    domain = str(globals_cfg.get("lab_domain", "lab"))
    records: Dict[str, str] = {}
    ptr_records: Dict[str, str] = {}

    for hostname, meta in sorted(hosts.items(), key=fqdn_sort_key):
        ip = str(meta["ip"])
        records[hostname] = ip
        short = hostname.split(".")[0]
        if hostname.endswith("." + domain):
            records[short] = ip
        ptr_records[".".join(reversed(ip.split("."))) + ".in-addr.arpa"] = hostname

    return {"a_records": records, "ptr_records": ptr_records}


def build_hypervisor_vms(hosts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    vms: List[Dict[str, Any]] = []

    for hostname, meta in sorted(hosts.items(), key=fqdn_sort_key):
        role = str(meta.get("role", ""))
        dc = str(meta.get("dc", ""))
        host_ip = str(meta["ip"])
        size = role_vm_size(role)

        vm: Dict[str, Any] = {
            "name": hostname,
            "role": role.replace("-", "_"),
            "dc": dc,
            "vcpu": size["vcpu"],
            "memory_mb": size["memory_mb"],
            "disk_gb": size["disk_gb"],
            "networks": [],
        }

        if role_matches(role, "bastion"):
            vm["networks"].append(
                {
                    "bridge": "br-mgmt",
                    "ip": mgmt_ip_for_host(meta),
                    "gateway": gateway_for_vlan({"dc": "dc1", "vlan": "management"}),
                    "nameservers": nameservers(),
                    "mac": "52:54:00:10:50:10",
                }
            )

        elif role_matches(role, "router"):
            vm["networks"].append(
                {
                    "bridge": "br-dc1" if dc == "dc1" else "br-dc2",
                    "ip": f"{host_ip}/24",
                    "mac": mac_for_ip(host_ip),
                }
            )
            vm["networks"].append(
                {
                    "bridge": "br-mgmt",
                    "ip": mgmt_ip_for_host(meta),
                    "gateway": gateway_for_vlan({"dc": "dc1", "vlan": "management"}),
                    "nameservers": nameservers(),
                    "mac": mac_for_ip(mgmt_ip_plain(meta)),
                }
            )
            vm["networks"].append(
                {
                    "bridge": "br-wan",
                    "ip": wan_ip_for_router({"dc": dc, "ip": host_ip, "hostname": hostname}),
                    "gateway": "172.16.255.1",
                    "nameservers": nameservers(),
                    "mac": mac_for_ip(
                        wan_ip_for_router({"dc": dc, "ip": host_ip, "hostname": hostname}).split("/")[0]
                    ),
                }
            )

        elif role_matches(role, "leaf"):
            vm["networks"].append(
                {
                    "bridge": "br-dc1" if dc == "dc1" else "br-dc2",
                    "ip": f"{host_ip}/24",
                    "gateway": gateway_for_vlan(meta),
                    "nameservers": nameservers(),
                    "mac": mac_for_ip(host_ip),
                }
            )
            vm["networks"].append(
                {
                    "bridge": "br-mgmt",
                    "ip": mgmt_ip_for_host(meta),
                    "gateway": gateway_for_vlan({"dc": "dc1", "vlan": "management"}),
                    "nameservers": nameservers(),
                    "mac": mac_for_ip(mgmt_ip_plain(meta)),
                }
            )

        elif role_matches(role, "k8s-control-plane") or role_matches(role, "k8s-worker"):
            vm["networks"].append(
                {
                    "bridge": "br-dc1" if dc == "dc1" else "br-dc2",
                    "ip": f"{host_ip}/24",
                    "gateway": gateway_for_vlan(meta),
                    "nameservers": nameservers(),
                    "mac": mac_for_ip(host_ip),
                }
            )
            vm["networks"].append(
                {
                    "bridge": "br-mgmt",
                    "ip": mgmt_ip_for_host(meta),
                    "gateway": gateway_for_vlan({"dc": "dc1", "vlan": "management"}),
                    "nameservers": nameservers(),
                    "mac": mac_for_ip(mgmt_ip_plain(meta)),
                }
            )

        else:
            raise ValueError(f"Unsupported role for hypervisor VM generation: {role}")

        vms.append(vm)

    return {"vms": vms}


def write_kubespray_inventory(content: str, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def main() -> int:
    try:
        ensure_generated_dir()
        hosts = load_hosts()
        globals_cfg = load_globals()

        dump_yaml(build_ansible_inventory(hosts), GENERATED_DIR / "ansible_inventory.yaml")
        write_kubespray_inventory(build_kubespray_inventory(hosts), GENERATED_DIR / "kubespray_inventory.ini")
        dump_yaml(build_dns_records(hosts, globals_cfg), GENERATED_DIR / "dns_records.yaml")
        dump_yaml(build_hypervisor_vms(hosts), GENERATED_DIR / "hypervisor-vms.yaml")

        print("Generated files:")
        print(f" - {GENERATED_DIR / 'ansible_inventory.yaml'}")
        print(f" - {GENERATED_DIR / 'kubespray_inventory.ini'}")
        print(f" - {GENERATED_DIR / 'dns_records.yaml'}")
        print(f" - {GENERATED_DIR / 'hypervisor-vms.yaml'}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())