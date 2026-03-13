# mylab infra-ansible

Production-ready Ansible repository for the **mylab** dual-datacenter lab.

This repository configures the operating system and infrastructure baseline for:
- bastion host
- routers
- leaf/L3 switch nodes
- Kubernetes nodes for **prod only**
  - `prod1` in `dc1`: `1 control-plane + 2 workers`
  - `prod2` in `dc2`: `1 control-plane + 2 workers`

It intentionally does **not** create a dev environment.

## Scope

This repo handles:
- OS baseline
- package baseline
- admin users and SSH hardening
- journald, sysctl, nftables baseline
- time sync
- node exporter
- containerd and Kubernetes prerequisites on cluster nodes
- FRR configuration on router nodes
- VLAN / bridge / SVI style L3 leaf configuration on leaf nodes
- bastion host baseline

This repo does **not** replace:
- hypervisor VM provisioning
- IPAM source-of-truth generation
- Kubespray cluster deployment
- GitOps platform deployment

Those belong to other mylab repos.

## Repository layout

```text
inventories/prod/
playbooks/
roles/
```

## Inventory model

The inventory uses these major groups:
- `bastion`
- `routers`
- `leafs`
- `k8s_control_plane`
- `k8s_workers`
- `k8s_cluster`
- `dc1`
- `dc2`

## Run order

Recommended order:

```bash
ansible-playbook -i inventories/prod/hosts.yml playbooks/site.yml
```

Or stage-by-stage:

```bash
ansible-playbook -i inventories/prod/hosts.yml playbooks/bootstrap.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/network.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/kubernetes-prereqs.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/observability.yml
```

## Requirements

- Ansible Core >= 2.16
- Debian 12 on managed nodes
- root or sudo access from bastion/control host
- internet access or internal mirror for packages

## Notes

- Firewall defaults are conservative and intended for a lab with controlled east-west access.
- Kubernetes ports are opened only on Kubernetes groups.
- FRR templates are intentionally structured so you can later extend toward inter-DC routing or WireGuard underlay.
