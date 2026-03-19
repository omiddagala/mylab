# mylab IPAM

This repository remains the source of truth for addressing, but now also generates the **hypervisor-facing VM matrix** used by the KVM/QEMU host.

## New generated artifact

- `generated/hypervisor-vms.yaml`
  - drives CPU, RAM, disk, bridge attachments, static IPs, MAC addresses, and router WAN uplinks for the KVM host

## Consumers

- `hypervisor-ansible`
- `infra-ansible`
- future Kubespray inventory generation
