#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time


def run(cmd, check=True):
    p = subprocess.run(cmd, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(
            f"Command failed ({p.returncode}): {' '.join(cmd)}\n"
            f"stdout: {p.stdout.strip()}\n"
            f"stderr: {p.stderr.strip()}"
        )
    return p


def get_prop(dataset, prop):
    p = run(["zfs", "get", "-H", "-o", "value,source", prop, dataset])
    value, source = p.stdout.rstrip("\n").split("\t", 1)
    return value, source


def restore_snapdev(dataset, value, source):
    if source == "local":
        run(["zfs", "set", f"snapdev={value}", dataset])
    else:
        run(["zfs", "inherit", "snapdev", dataset])


def wait_for(path, seconds=10):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if os.path.exists(path):
            return True
        time.sleep(0.2)
    return False


def main():
    ap = argparse.ArgumentParser(
        description="Create a Proxmox VM snapshot and validate ZVOL snapshot devices read-only."
    )
    ap.add_argument("vmid", type=int)
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Actually create snapshot and temporarily set snapdev=visible",
    )
    args = ap.parse_args()

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    snap = f"urbackup_block_probe_{stamp}"

    cfg = run(["qm", "config", str(args.vmid)]).stdout
    refs = []
    for line in cfg.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if "media=cdrom" in value:
            continue
        if key.startswith(("scsi", "sata", "virtio", "efidisk", "tpmstate")):
            ref = value.split(",", 1)[0]
            path = run(["pvesm", "path", ref], check=False)
            if path.returncode == 0:
                dev = path.stdout.strip()
                prefix = "/dev/zvol/"
                if dev.startswith(prefix):
                    refs.append({
                        "key": key,
                        "storage_ref": ref,
                        "live_path": dev,
                        "dataset": dev[len(prefix):],
                    })

    plan = {
        "vmid": args.vmid,
        "snapshot": snap,
        "devices": refs,
        "execute": args.execute,
    }
    print(json.dumps(plan, indent=2))

    if not args.execute:
        print("\nDRY RUN ONLY. No properties or snapshots changed.", file=sys.stderr)
        return 0

    originals = {}
    created = False
    try:
        run([
            "qm", "snapshot", str(args.vmid), snap,
            "--description", "urbackup-proxmox-agent block-source probe"
        ])
        created = True

        for item in refs:
            ds = item["dataset"]
            originals[ds] = get_prop(ds, "snapdev")
            run(["zfs", "set", "snapdev=visible", ds])

        results = []
        for item in refs:
            spath = f'{item["live_path"]}@{snap}'
            visible = wait_for(spath)
            entry = dict(item)
            entry["snapshot_path"] = spath
            entry["visible"] = visible
            entry["size_bytes"] = None
            entry["readable"] = False

            if visible:
                size = run(["blockdev", "--getsize64", spath], check=False)
                if size.returncode == 0:
                    try:
                        entry["size_bytes"] = int(size.stdout.strip())
                    except ValueError:
                        pass
                try:
                    with open(spath, "rb", buffering=0) as f:
                        entry["readable"] = len(f.read(4096)) == 4096
                except OSError as exc:
                    entry["read_error"] = str(exc)

            results.append(entry)

        print("\nRESULT:")
        print(json.dumps(results, indent=2))
        return 0 if all(x["visible"] and x["readable"] for x in results) else 2

    finally:
        for ds, (value, source) in reversed(list(originals.items())):
            try:
                restore_snapdev(ds, value, source)
            except Exception as exc:
                print(f"WARNING: failed to restore snapdev on {ds}: {exc}", file=sys.stderr)

        if created:
            delete = run(["qm", "delsnapshot", str(args.vmid), snap], check=False)
            if delete.returncode != 0:
                print(
                    f"WARNING: snapshot cleanup failed. Run manually: "
                    f"qm delsnapshot {args.vmid} {snap}",
                    file=sys.stderr,
                )
                print(delete.stderr, file=sys.stderr)
            else:
                print("\nSnapshot cleanup completed.", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
