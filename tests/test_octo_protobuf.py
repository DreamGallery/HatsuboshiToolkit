"""Offline regression tests for encrypted Octo manifests and protobuf JSON."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import ParseDict

from proto.octodb_pb2 import Database, Data
from src import config, octo_manager


def database(revision=123):
    db = Database(revision=revision)
    db.assetBundleList.add(name="asset-defaults")
    db.resourceList.add(
        name="resource", state=Data.ADD, generation=2**63 + 1,
        tagid=[0, 2], dependencie=[3],
    )
    return db


class OctoProtobufTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        previous = Path.cwd()
        os.chdir(self.directory.name)
        self.addCleanup(os.chdir, previous)
        Path("cache").mkdir()

    def read_json(self, name):
        return json.loads(Path("cache", name).read_text(encoding="utf8"))

    def assert_manifest(self, actual, expected):
        # Downstream downloads rely on empty/default fields being present.
        self.assertEqual(actual["tagname"], [])
        self.assertEqual(actual["urlFormat"], "")
        asset = actual["assetBundleList"][0]
        self.assertEqual(asset["state"], 0)
        self.assertEqual(asset["size"], 0)
        self.assertEqual(asset["tagid"], [])
        self.assertEqual(asset["dependencie"], [])
        self.assertEqual(actual["resourceList"][0]["state"], 1)
        self.assertEqual(actual["resourceList"][0]["generation"], str(2**63 + 1))
        self.assertEqual(ParseDict(actual, Database()), expected)

    def encrypt(self, db):
        iv = bytes(range(16))
        cipher = AES.new(config.API_KEY, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(pad(db.SerializeToString(), 16))

    def test_encrypted_manifest_preserves_defaults_and_roundtrips(self):
        db = database()
        manager = octo_manager.DataManger()
        with patch.object(octo_manager, "request_update", return_value=self.encrypt(db)) as request:
            manager.start_db_update()
        request.assert_called_once_with(0)
        self.assert_manifest(self.read_json("OctoManifest.json"), db)
        self.assertEqual(manager.get_diff_and_check_legal(init=True), db)
        self.assertEqual(manager.revision, 123)
        self.assertTrue(manager.get_status())
        self.assertFalse(Path("cache/OctoDiff.json").exists())

    def test_incremental_update_saves_diff_and_refreshes_full_manifest(self):
        manager = octo_manager.DataManger()
        manager.update_db(self.encrypt(database()), reset=True)
        diff = Database(revision=124)
        diff.resourceList.add(name="resource", size=4096, state=Data.UPDATE)
        full = database(124)
        full.resourceList[0].size = 4096
        with patch.object(octo_manager, "request_update", side_effect=[
            self.encrypt(diff), self.encrypt(full),
        ]) as request:
            manager.start_db_update()
        self.assertEqual([call.args for call in request.call_args_list], [(123,), (0,)])
        self.assert_manifest(self.read_json("OctoManifest.json"), full)
        self.assertEqual(self.read_json("OctoDiff.json")["assetBundleList"], [])
        self.assertEqual(manager.get_diff_and_check_legal(), diff)
        self.assertEqual(manager.get_diff_and_check_legal(init=True), full)

    def test_unchanged_manifest_is_not_rewritten(self):
        manager = octo_manager.DataManger()
        payload = self.encrypt(database())
        manager.update_db(payload, reset=True)
        before = Path("cache/OctoManifest.json").read_bytes()
        manager.update_db(payload, reset=False)
        self.assertFalse(manager.get_status())
        self.assertIsNone(manager.get_diff_and_check_legal())
        self.assertEqual(Path("cache/OctoManifest.json").read_bytes(), before)

    def test_reset_replaces_existing_manifest_at_same_revision(self):
        manager = octo_manager.DataManger()
        manager.update_db(self.encrypt(database()), reset=True)
        replacement = database()
        replacement.resourceList[0].size = 8192
        manager.update_db(self.encrypt(replacement), reset=True)
        self.assert_manifest(self.read_json("OctoManifest.json"), replacement)

    def test_empty_manifest_retains_lists(self):
        manager = octo_manager.DataManger()
        manager.update_db(self.encrypt(Database()), reset=True)
        self.assertEqual(self.read_json("OctoManifest.json"), {
            "revision": 0, "assetBundleList": [], "resourceList": [],
            "tagname": [], "urlFormat": "",
        })
        self.assertEqual(manager.get_diff_and_check_legal(init=True), Database())
