# urbackup-proxmox-agent

Prototype integration between Proxmox VE and UrBackup for whole-VM image backups.

## Goal

Expose Proxmox QEMU/KVM virtual machines to an UrBackup server as image-backup targets, while keeping file-level backup inside guest VMs as a separate concern.

Version 1 deliberately focuses on a small, testable scope:

- Proxmox VE 9.x
- QEMU/KVM virtual machines
- ZFS-backed VM disks
- Complete VM backup, not file-level restore
- VM configuration plus boot-relevant auxiliary disks (EFI/TPM)
- UrBackup full and incremental image transport
- Existing UrBackup Internet client/server connection model
- No QEMU dirty bitmap/CBT optimization yet

## Initial test environment

- Proxmox VE 9.2
- Test node: `pve1`
- Test VM: `150` (`Lansweeper-On-Prem`)
- VM storage: `local-zfs`
- VM firmware: OVMF
- TPM: 2.0
- Primary VM disk: `scsi0`, 64 GiB
- UrBackup server: 2.5.37

## Design principle

Do not invent a new backup format.

The prototype should reuse UrBackup's existing image-backup pipeline. The Proxmox-specific layer is responsible for discovering VMs, obtaining a consistent read-only view of their disks, preserving VM metadata, and later recreating a VM during restore.

See [docs/architecture.md](docs/architecture.md) and [docs/v1-scope.md](docs/v1-scope.md).

## Safety

Development and builds should not happen directly on a production Proxmox host. The host should only receive tested artifacts or narrowly scoped probe scripts.

## License

This project is licensed under the GNU Affero General Public License, version 3 or (at your option) any later version (AGPL-3.0-or-later).

The project is intended to integrate with and may modify/derive from UrBackup client code, which is distributed under the same license. See [LICENSE](LICENSE).
