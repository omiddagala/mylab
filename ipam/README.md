# mylab IPAM

This repository acts as the **Source of Truth** for all network addressing
in the mylab dual-datacenter environment.

It contains:

- VLAN definitions
- Subnet allocations
- Host addressing
- Loopbacks
- BGP AS numbers
- Infrastructure addressing

Other infrastructure repositories must **consume this repo**.

This prevents configuration drift.

---

## Datacenters

DC1
DC2

---

## Clusters

prod1 -> DC1  
prod2 -> DC2  
dev -> DC1

---

## Usage

Repositories consuming this IPAM:

infra-ansible  
kubespray-inventory  
network-automation