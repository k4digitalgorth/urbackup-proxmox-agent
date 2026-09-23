# Version 1 Scope

## Supported

- Proxmox VE 9.x
- QEMU/KVM VMs
- ZFS-backed VM storage
- Whole-VM backup
- Running VM snapshot workflow
- VM configuration capture
- Regular virtual disks
- OVMF EFI disk
- TPM state disk
- UrBackup full image backup
- UrBackup incremental image backup
- UrBackup Internet client/server connectivity

## Explicitly not supported in V1

- LXC containers
- File-level restore from the VM image
- QEMU dirty bitmap / CBT optimization
- Ceph-specific integration
- LVM-thin-specific integration
- NFS-specific snapshot logic
- HA/failover orchestration
- Cross-node migration during an active backup
- Application-aware guest quiescing beyond what Proxmox/QEMU already provides

## Acceptance criteria

V1 is considered successful when the following sequence works reproducibly on the test environment:

1. VM 150 remains running.
2. The agent creates a consistent backup view.
3. UrBackup performs a full image backup of the VM disks.
4. A later incremental image backup transfers only changed image data.
5. Snapshot resources are cleaned up after success and after failure.
6. VM configuration, EFI state and TPM state are captured.
7. The resulting backup can be used to reconstruct a bootable clone of VM 150.
