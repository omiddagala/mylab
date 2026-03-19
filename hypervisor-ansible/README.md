Edit:

hypervisor-ansible/inventories/prod/hosts.yml

Change this host to your real laptop:

all:
children:
hypervisors:
hosts:
mylab-host:
ansible_host: <your-laptop-ip>
ansible_user: <your-linux-user>

Example:

ansible_host: 192.168.1.23
ansible_user: omid
3. Update the host variables

Edit:

hypervisor-ansible/inventories/prod/group_vars/all.yml

These are the important ones you must change:

Replace your SSH public key
mylab_ssh_public_key: "ssh-ed25519 REPLACE_ME"

Put your real public key there.

You can get it with:

cat ~/.ssh/id_ed25519.pub
Set the real uplink interface
mylab_uplink_interface: enp0s31f6

Change this to your actual interface.

Check with:

ip link

If you are on Wi-Fi, it may be something like wlp0s20f3.

Keep or change routed mode

Right now it is:

mylab_upstream_mode: routed

For a laptop, especially on Wi-Fi, keep it as routed.

Do not switch to bridged unless you really have a wired interface and you want br-wan to absorb that NIC.

Optionally adjust bridge CIDRs

These can stay as they are unless they conflict with your home network:

mylab_mgmt_bridge_cidr: 192.168.50.1/24
mylab_wan_bridge_cidr: 172.16.255.1/24
mylab_dc1_bridge_cidr: 10.10.10.1/24
mylab_dc2_bridge_cidr: 10.20.20.1/24

If your real LAN already uses one of those ranges, change the conflicting one.

4. Make sure the IPAM-generated VM file exists and matches the design

This file is the source of truth for VM creation:

ipam/generated/hypervisor-vms.yaml

It must exist, and the VMs in it must have the right NIC layout.

At minimum, check that:

bastion has br-mgmt

edge routers have br-mgmt, br-wan, and their DC bridge

Kubernetes nodes have br-mgmt and their DC bridge

all NICs have IPs and MACs

If that file is missing or stale, the VM playbook will fail or create the wrong topology.

5. Make sure your Ansible user can become root

The playbook installs packages, creates bridges, writes under /etc, enables services, and edits nftables.

So your ansible_user must be able to sudo.

Test it:

ssh <your-user>@<your-laptop-ip>
sudo -v

If sudo asks for a password, that is fine, but you should run the playbook with become enabled. If your repo/playbooks do not already set become: true, run with:

ansible-playbook -i inventories/prod/hosts.yml playbooks/site.yml -K

The -K asks for the sudo password.

6. Install Ansible and the required collection on the host you will run Ansible from

From inside hypervisor-ansible:

ansible-galaxy collection install -r collections/requirements.yml

Also make sure Ansible itself is installed on the machine where you launch the playbook.

7. Make sure virtualization is available on the laptop

Check:

egrep -c '(vmx|svm)' /proc/cpuinfo
lsmod | grep kvm

The first command should return a number greater than 0.

If not, enable virtualization in BIOS/UEFI.

8. Be aware of what the playbook will change on your laptop

This playbook will:

install QEMU/KVM packages

create br-mgmt, br-wan, br-dc1, br-dc2

enable IP forwarding

replace /etc/nftables.conf

enable and start nftables

download the Debian cloud image

create and start systemd-managed VMs

That means the most sensitive file in your current setup is effectively:

hypervisor-ansible/roles/hypervisor_host/templates/nftables-mylab.conf.j2

If you already have custom nftables rules on your laptop, this playbook will overwrite them.

9. Then run the playbook

From:

mylab/hypervisor-ansible

Run:

ansible-galaxy collection install -r collections/requirements.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/site.yml -K
The only files you most likely need to edit right now

In practice, before first run, I would edit only these three:

hypervisor-ansible/inventories/prod/hosts.yml
hypervisor-ansible/inventories/prod/group_vars/all.yml
ipam/generated/hypervisor-vms.yaml

That is the minimum real set.