# Test Environment Notes

## Proxmox node

- Host: `pve1`
- Proxmox VE: 9.2.0
- Kernel: 7.0.14-12-pve

## Storage

Known storage classes in the environment:

- PBS
- PBS-OBS
- local
- local-zfs

V1 targets `local-zfs` only.

## Test VM 150

Name: `Lansweeper-On-Prem`

Relevant configuration:

```text
agent: 1
bios: ovmf
cores: 4
cpu: host
efidisk0: local-zfs:vm-150-disk-0,efitype=4m,size=1M
machine: pc-q35-10.1
memory: 8192
net0: virtio=...,bridge=vmbrLAN,queues=8,tag=40
ostype: win11
scsi0: local-zfs:vm-150-disk-1,discard=on,iothread=1,size=64G
scsihw: virtio-scsi-single
tpmstate0: local-zfs:vm-150-disk-2,size=4M,version=v2.0
```

The attached VirtIO ISO is not part of the VM payload backup.

## UrBackup

- Server version: 2.5.37
- Server is on the same management network as the Proxmox node.
- Client connectivity should follow UrBackup's Internet-client model.
