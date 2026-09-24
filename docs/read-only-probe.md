# Read-only VM probe

The first prototype is intentionally narrow and safe. It does not create snapshots, write to block devices, or modify VM configuration.

It:

1. reads `qm config <vmid>`,
2. classifies VM devices,
3. resolves Proxmox storage references using `pvesm path`,
4. reads block-device size using `blockdev --getsize64`,
5. optionally reads the first 4096 bytes from included devices.

## Usage

Copy `tools/pve_vm_probe.py` to the Proxmox host and run:

```bash
python3 pve_vm_probe.py 150
```

Optional read test:

```bash
python3 pve_vm_probe.py 150 --read-probe
```

The `--read-probe` option only opens the device read-only and reads 4096 bytes. It does not write anything.

For VM 150 we expect:
- `scsi0` => payload
- `efidisk0` => payload/boot state
- `tpmstate0` => payload/security state
- `ide0` with `media=cdrom` => metadata only, excluded from payload
