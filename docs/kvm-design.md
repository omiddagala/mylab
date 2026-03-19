# mylab KVM hypervisor design

## Host model

- Host OS: Debian 12
- Virtualization: QEMU + KVM directly
- Networking: Linux bridges controlled by the host
- Bootstrap: cloud-init NoCloud seed image per VM
- Lifecycle: systemd unit per VM

## Bridges

- `br-mgmt`: host access, bastion access, out-of-band operator plane
- `br-wan`: outside segment used by edge routers for north-south internet access
- `br-dc1`: DC1 isolated fabric
- `br-dc2`: DC2 isolated fabric

## Provisioning flow

1. IPAM generates `ipam/generated/hypervisor-vms.yaml`
2. `hypervisor-ansible` reads the generated data
3. base cloud image is cached on the host
4. qcow2 overlay is created for every VM
5. cloud-init user-data/meta-data/network-config are rendered
6. launch script + systemd unit are rendered
7. systemd starts each VM
8. `infra-ansible` configures the guests afterward

## Operational model

- bastion and selected nodes keep management NICs on `br-mgmt`
- only edge routers attach to `br-wan`
- the Debian host provides forwarding/NAT to the real upstream when `mylab_upstream_mode: routed`
- router configuration later determines how DC workloads actually egress through the edge

## Why this replaces libvirt

The design is intentionally explicit:

- no default NAT network
- no `virbr0`
- no hidden DHCP or network XML
- no state split between libvirt and Ansible

Everything is represented in files rendered by Ansible.
