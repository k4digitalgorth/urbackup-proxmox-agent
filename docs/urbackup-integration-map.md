# UrBackup integration map

This note records the first concrete source-level integration points identified in the upstream UrBackup client.

## Relevant request handlers

In `urbackupclient/ClientServiceCMD.cpp`:

- `ClientConnector::CMD_FULL_IMAGE(...)`
- `ClientConnector::CMD_INCR_IMAGE(...)`

Both handlers parse image-backup parameters, including:

- `letter`
- `shadowdrive`
- `clientsubname`
- image status/checksum/bitmap parameters

On non-Windows systems, the requested image target is passed through `mapLinuxDev(...)`.

If no existing shadow copy is supplied, the client asks `IndexThread` to create one. Once a usable source is available, the normal image path continues into `sendFullImage()` / `sendIncrImage()` and ultimately `ImageThread`.

## Proposed Proxmox hook

Do not replace UrBackup transport or block hashing.

Instead, add a Proxmox-aware source resolver in the client-side image-start path:

```text
UrBackup server requests image backup
        |
        v
CMD_FULL_IMAGE / CMD_INCR_IMAGE
        |
        +-- ordinary volume -> existing behavior
        |
        +-- proxmox VM target
                |
                +-- resolve VM + virtual disk
                +-- create Proxmox-managed VM snapshot
                +-- expose ZVOL snapshot via snapdev=visible
                +-- return /dev/zvol/...@snapshot as shadowdrive
                |
                v
        existing ImageThread
```

## V1 target syntax

A small explicit namespace is preferable to overloading normal Linux device names.

Provisional examples:

```text
PVE:150:scsi0
PVE:150:efidisk0
PVE:150:tpmstate0
```

The resolver can translate this to a snapshot block device such as:

```text
/dev/zvol/rpool/data/vm-150-disk-1@urbackup_<backup-id>
```

The exact public naming convention is not yet fixed.

## Lifecycle requirement

A Proxmox-backed image source is not just a path. It has a lifecycle:

1. create a VM-level Proxmox snapshot,
2. expose all required ZVOL snapshot devices,
3. feed one of those devices to UrBackup,
4. keep the snapshot alive while UrBackup reads it,
5. after every required component has completed, restore `snapdev` and delete the VM snapshot.

This means the integration needs a small backup-session manager rather than a stateless path mapper.

## Multi-device VM backup

UrBackup image backup requests operate on individual image sources. A complete Proxmox VM consists of several components.

For VM 150:

- scsi0
- efidisk0
- tpmstate0
- VM configuration metadata

V1 therefore needs a grouping/session layer so all component backups reference the same Proxmox snapshot and are treated as one VM backup generation.

## Open design question

Virtual sub-client support appears in the image request path through `clientsubname`, but the exact server-side scheduling/UI semantics for multiple image sources under one virtual client still need a proof-of-concept.

Fallback if necessary:

- expose each VM as a distinct UrBackup client identity,
- represent each VM component as a separately named image source tied to one shared Proxmox snapshot session.

The source-level image path itself does not require a custom transport protocol.
