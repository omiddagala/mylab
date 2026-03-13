# mylab / hypervisor-ansible

Production-style Ansible repo for the mylab hypervisor layer.

## Scope

This repo is responsible for:

1. Preparing Linux hypervisor hosts
2. Applying security and OS baseline hardening
3. Defining and provisioning VMs declaratively
4. Preparing guest operating systems with consistent access, firewall, logging, and kernel settings

## Target model

- Debian 12 hypervisor hosts
- Debian 12 cloud image based guests
- libvirt/KVM on Linux hypervisors
- Bastion-only SSH model
- Dual datacenter layout:
    - DC1
    - DC2

## Main playbooks

- `playbooks/hypervisors.yml`
    - harden and prepare hypervisor hosts
- `playbooks/hypervisor-vms.yml`
    - create or update VMs on hypervisors
- `playbooks/guests.yml`
    - harden guest VMs after first bootstrap
- `playbooks/site.yml`
    - all of the above in order

## Usage

### 1. Install collections
```bash
ansible-galaxy collection install -r collections/requirements.yml