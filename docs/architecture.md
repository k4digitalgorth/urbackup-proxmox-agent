# Architecture

## Objective

The agent bridges Proxmox VE VM storage and UrBackup's existing image-backup mechanism.

The core idea is to keep responsibilities separated:

```text
UrBackup Server
      |
      | existing Internet client protocol
      v
UrBackup client core
      |
      | image backup request
      v
Proxmox integration layer
      |
      +-- VM discovery
      +-- VM configuration capture
      +-- snapshot orchestration
      +-- read-only block source
      +-- restore orchestration
      |
      v
Proxmox/QEMU/ZFS
```

## V1 data model

A Proxmox VM backup consists of:

- VM configuration
- Primary and secondary virtual disks that are part of the VM
- EFI disk, when present
- TPM state disk, when present

CD/DVD ISO media is metadata only and is not copied as VM payload.

For test VM 150 this means:

```text
VM 150
+-- config
+-- scsi0
+-- efidisk0
+-- tpmstate0
```

## UrBackup integration

UrBackup already has an image pipeline that:

- supports full and incremental image requests,
- reads a device through an `IFilesystem` abstraction,
- falls back to a raw/unknown filesystem implementation when needed,
- transfers only blocks required by the image protocol.

V1 should reuse this mechanism and inject a consistent Proxmox block source instead of implementing a new image format.

## Snapshot strategy

V1 must not call `zfs snapshot` blindly behind Proxmox's back.

Preferred order:

1. Ask Proxmox/QEMU to create or coordinate a consistent VM snapshot state.
2. Resolve the backing ZFS volumes belonging to that VM state.
3. Expose those volumes read-only to the UrBackup image reader.
4. Release the snapshot state only after the backup has completed or failed cleanly.

The exact Proxmox 9.2 mechanism will be selected after probing the test VM.

## Incremental behavior in V1

V1 does not use QEMU dirty bitmaps.

Therefore UrBackup may need to scan/read a large portion of the virtual disk to decide which blocks changed. Network transfer can still be incremental, but host storage I/O will not yet be optimized.

Dirty bitmap/CBT support is a later optimization.

## Restore

A restore must recreate a complete bootable VM, not only a disk image.

The restore workflow will eventually:

1. create a new VM shell,
2. restore the VM configuration,
3. recreate target volumes,
4. write disk image data,
5. restore EFI/TPM state,
6. attach networking and boot configuration,
7. validate the VM before start.

V1 implementation work begins with backup first, but restore metadata requirements are designed in from the beginning.
