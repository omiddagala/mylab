# mylab infra-ansible

Integrated **infra-ansible** repository for the current **mylab** topology.

Aligned to the current mylab contract:

- **prod-only**
- **two datacenters**
- **one control-plane and two worker nodes in each cluster**
- **same current FQDN set across infra/IPAM/hypervisor/kubespray**
- **bastion-only administration**
- **Debian baseline + network + FRR + Kubernetes node prep**

## Current topology

### DC1
- bastion1.dc1.lab
- r1-dc1.lab
- r2-dc1.lab
- leaf1-dc1.lab
- leaf2-dc1.lab
- prod1-cp1.dc1.lab
- prod1-w1.dc1.lab
- prod1-w2.dc1.lab

### DC2
- r1-dc2.lab
- r2-dc2.lab
- leaf1-dc2.lab
- leaf2-dc2.lab
- prod2-cp1.dc2.lab
- prod2-w1.dc2.lab
- prod2-w2.dc2.lab

## Run

```bash
ansible-galaxy collection install -r requirements.yml
ansible-inventory -i inventories/prod/hosts.yml --graph
ansible-playbook -i inventories/prod/hosts.yml playbooks/site.yml
```

## Staged runs

```bash
ansible-playbook -i inventories/prod/hosts.yml playbooks/bootstrap.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/network.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/kubernetes.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/observability.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/validate.yml
```

## Important notes

- `inventories/prod/generated/` contains bridge artifacts aligned with the current mylab state.
- SSH keys in `inventories/prod/group_vars/all/main.yml` are placeholders and must be replaced.
- Interface names are written as `ens18`, `ens19`, ... based on a typical VM layout. Adjust if your hypervisor uses different names.
- This repo **prepares** Kubernetes nodes; deploy the cluster in the next mylab stage.
