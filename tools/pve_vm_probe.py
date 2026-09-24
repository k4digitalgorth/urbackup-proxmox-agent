#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class VmDevice:
    key: str
    storage_ref: str
    path: Optional[str]
    kind: str
    include_payload: bool
    size_bytes: Optional[int]
    readable: Optional[bool]


def run(cmd: List[str]) -> str:
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def parse_qm_config(vmid: int):
    raw = run(["qm", "config", str(vmid)])
    cfg = {}
    for line in raw.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        cfg[key.strip()] = value.strip()
    return cfg


def classify_device(key: str, value: str):
    if "media=cdrom" in value:
        return "cdrom", False
    if key.startswith("efidisk"):
        return "efi", True
    if key.startswith("tpmstate"):
        return "tpm", True
    if re.match(r"^(scsi|sata|virtio|ide)\d+$", key):
        return "disk", True
    return None, False


def storage_ref_from_value(value: str) -> str:
    return value.split(",", 1)[0]


def resolve_path(storage_ref: str) -> Optional[str]:
    try:
        return run(["pvesm", "path", storage_ref]).strip()
    except RuntimeError:
        return None


def block_size_bytes(path: str) -> Optional[int]:
    try:
        out = run(["blockdev", "--getsize64", path]).strip()
        return int(out)
    except Exception:
        return None


def readable_probe(path: str) -> Optional[bool]:
    try:
        with open(path, "rb", buffering=0) as f:
            data = f.read(4096)
        return len(data) > 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Read-only Proxmox VM disk discovery probe")
    ap.add_argument("vmid", type=int)
    ap.add_argument("--read-probe", action="store_true", help="Read first 4096 bytes from each included block device")
    args = ap.parse_args()

    cfg = parse_qm_config(args.vmid)

    devices = []
    for key, value in cfg.items():
        kind, include_payload = classify_device(key, value)
        if kind is None:
            continue

        storage_ref = storage_ref_from_value(value)
        path = resolve_path(storage_ref)
        size = block_size_bytes(path) if path else None
        readable = readable_probe(path) if (path and args.read_probe and include_payload) else None

        devices.append(VmDevice(
            key=key,
            storage_ref=storage_ref,
            path=path,
            kind=kind,
            include_payload=include_payload,
            size_bytes=size,
            readable=readable,
        ))

    result = {
        "vmid": args.vmid,
        "name": cfg.get("name"),
        "status": run(["qm", "status", str(args.vmid)]).strip(),
        "bios": cfg.get("bios"),
        "machine": cfg.get("machine"),
        "ostype": cfg.get("ostype"),
        "devices": [asdict(d) for d in devices],
        "config": cfg,
    }

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
