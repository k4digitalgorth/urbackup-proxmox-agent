# ZVOL snapshot block-source probe

This probe validates the exact storage path needed by the UrBackup image reader.

OpenZFS hides ZVOL snapshot devices by default when `snapdev=hidden`. When
`snapdev=visible`, snapshot block devices are exposed below `/dev/zvol/`.

The tool is a dry-run unless `--execute` is supplied.

## Dry run

```bash
python3 tools/pve_zvol_snapshot_probe.py 150
```

## Execute

```bash
python3 tools/pve_zvol_snapshot_probe.py 150 --execute
```

The execute path:

1. Creates one Proxmox-managed VM snapshot.
2. Records each ZVOL's current `snapdev` value and property source.
3. Temporarily sets `snapdev=visible`.
4. Waits for `/dev/zvol/<dataset>@<snapshot>`.
5. Reads the snapshot device size.
6. Opens the snapshot device read-only and reads 4096 bytes.
7. Restores the original `snapdev` property semantics.
8. Deletes the Proxmox snapshot.

If the original property was inherited or default, the cleanup uses
`zfs inherit snapdev` instead of leaving a new local property behind.

This probe does not write to the snapshot block device.
