# Snapshot lifecycle probe

This probe validates the Proxmox-managed snapshot path before it is connected to UrBackup.

## Safety model

The script is a dry-run by default:

```bash
python3 tools/pve_snapshot_probe.py 150
```

No VM or storage state is changed.

To perform the actual lifecycle test:

```bash
python3 tools/pve_snapshot_probe.py 150 --execute
```

The script then:

1. calls `qm snapshot` without VM RAM state,
2. lists Proxmox snapshots,
3. lists matching ZFS snapshots,
4. deletes the probe snapshot in a `finally` cleanup path.

The snapshot can intentionally be retained only with:

```bash
python3 tools/pve_snapshot_probe.py 150 --execute --keep-snapshot
```

Do not use `--keep-snapshot` for routine tests.

## Why use qm snapshot?

The integration should let Proxmox/QEMU coordinate VM consistency rather than creating storage snapshots directly behind Proxmox's back. This is particularly important for running VMs, multiple virtual disks, EFI/TPM state, and QEMU Guest Agent coordination.

## V1 test sequence

1. Validate the script in dry-run mode.
2. Start the disposable test VM.
3. Verify QEMU Guest Agent responds.
4. Run one execute lifecycle test.
5. Confirm the VM remains operational.
6. Inspect the actual ZFS snapshot naming/path while the snapshot exists.
7. Only then build the read-only UrBackup block-source adapter.
