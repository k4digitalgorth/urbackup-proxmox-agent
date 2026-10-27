"""Isolated regression tests; no Proxmox or UrBackup connection required."""
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "integration/urbackup/build_vm_backup_plan.py"
# Import safely without loading the real discovery implementation or calling qm/pvesm.
sys.modules.setdefault("discover_vm_backup_set", types.ModuleType("discover_vm_backup_set"))
sys.modules["discover_vm_backup_set"].discover = lambda vmid: None
spec = importlib.util.spec_from_file_location("build_vm_backup_plan", SCRIPT)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


def device(key, role="disk", supported=True):
    return {
        "key": key,
        "role": role,
        "supported_v1": supported,
        "path": f"/dev/zvol/tank/vm-150-{key}" if supported else None,
        "storage_ref": f"tank:vm-150-{key}",
        **({} if supported else {"error": "cannot resolve storage"}),
    }


def discovery(devices, supported=None, skipped=None, config=None):
    unsupported = [d for d in devices if not d["supported_v1"]]
    return {
        "devices": devices,
        "supported_v1": bool(devices) and not unsupported if supported is None else supported,
        "storage_scope": "zfs-only",
        "vm_config": config if config is not None else "name: vm150\nparent: snap1\nlock: backup\ncores: 2\n",
        "skipped": skipped if skipped is not None else [{"key": "ide2", "reason": "cdrom", "config": "none,media=cdrom"}],
        "unsupported_devices": unsupported,
    }


class PlanTests(unittest.TestCase):
    def make_plan(self, result):
        with patch.object(planner, "discover", return_value=result) as mocked:
            plan = planner.build_plan(150)
            mocked.assert_called_once_with(150)
            return plan

    def test_supported_vm_jobs_order_and_exact_fields(self):
        devices = [device("tpmstate0", "tpm"), device("scsi1"),
                   device("efidisk0", "efi"), device("scsi0")]
        plan = self.make_plan(discovery(devices))
        self.assertTrue(plan["supported_v1"])
        self.assertEqual([j["device_key"] for j in plan["image_jobs"]],
                         ["scsi0", "scsi1", "efidisk0", "tpmstate0"])
        for job in plan["image_jobs"]:
            self.assertEqual(job["source"], job["urbackup_image_source"])
            self.assertEqual(set(job), {"device_key", "role", "source", "storage_ref", "urbackup_image_source"})
        self.assertEqual(plan["metadata"]["vm_config"], "name: vm150\ncores: 2\n")
        self.assertEqual(plan["storage_scope"], "zfs-only")
        self.assertEqual(plan["vmid"], 150)
        self.assertEqual(plan["version"], 1)
        self.assertEqual(plan["unsupported_devices"], [])
        self.assertEqual(plan["skipped"][0]["reason"], "cdrom")

    def test_unsupported_efi_blocks_supported_system_disk(self):
        result = discovery([device("scsi0"), device("efidisk0", "efi", False)])
        plan = self.make_plan(result)
        self.assertFalse(plan["supported_v1"])
        self.assertEqual(plan["image_jobs"], [])
        self.assertEqual(plan["unsupported_devices"], result["unsupported_devices"])
        self.assertEqual(plan["skipped"], result["skipped"])
        self.assertEqual(plan["metadata"]["vm_config"], "name: vm150\ncores: 2\n")

    def test_unsupported_tpm_blocks_supported_system_disk(self):
        plan = self.make_plan(discovery([device("scsi0"), device("tpmstate0", "tpm", False)]))
        self.assertFalse(plan["supported_v1"])
        self.assertEqual(plan["image_jobs"], [])
        self.assertEqual(plan["unsupported_devices"][0]["key"], "tpmstate0")

    def test_failed_storage_resolution_blocks_all_jobs(self):
        plan = self.make_plan(discovery([device("scsi0"), device("scsi1", supported=False)]))
        self.assertEqual(plan["image_jobs"], [])
        self.assertFalse(plan["supported_v1"])
        self.assertEqual(plan["unsupported_devices"][0]["error"], "cannot resolve storage")

    def test_no_payload_devices_blocks_plan(self):
        plan = self.make_plan(discovery([]))
        self.assertFalse(plan["supported_v1"])
        self.assertEqual(plan["image_jobs"], [])
        self.assertEqual(plan["skipped"][0]["key"], "ide2")

    def test_top_level_unsupported_is_authoritative_even_if_every_device_supported(self):
        plan = self.make_plan(discovery([device("scsi0")], supported=False))
        self.assertFalse(plan["supported_v1"])
        self.assertEqual(plan["image_jobs"], [])

    def test_cli_failure_exit_code_and_json_are_safe(self):
        result = discovery([device("scsi0"), device("efidisk0", "efi", False)])
        output = io.StringIO()
        with patch.object(planner, "discover", return_value=result), \
             patch.object(sys, "argv", [str(SCRIPT), "150", "--compact"]), \
             patch.object(sys, "stdout", output):
            status = planner.main()
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["image_jobs"], [])

    def test_cli_supported_exit_code(self):
        output = io.StringIO()
        with patch.object(planner, "discover", return_value=discovery([device("scsi0")])), \
             patch.object(sys, "argv", [str(SCRIPT), "150"]), \
             patch.object(sys, "stdout", output):
            status = planner.main()
        self.assertEqual(status, 0)
        self.assertEqual(len(json.loads(output.getvalue())["image_jobs"]), 1)


if __name__ == "__main__":
    unittest.main()
