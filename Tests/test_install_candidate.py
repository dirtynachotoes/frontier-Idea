from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import install_candidate as installer
class InstallerTests(unittest.TestCase):
    def test_promotion_and_full_rollback_on_partial_install(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'source';source.write_bytes(b'new')
            old=root/'old';old.write_bytes(b'old');created=root/'created';fail=root/'fail'
            promote=installer.promote
            def reject(source,target):
                if target==fail:raise OSError('injected promotion failure')
                promote(source,target)
            with patch.object(installer,'promote',side_effect=reject):
                with self.assertRaisesRegex(OSError,'injected'):
                    installer.install([(source,old),(source,created),(source,fail)],root/'backups')
            self.assertEqual(old.read_bytes(),b'old');self.assertFalse(created.exists());self.assertFalse(fail.exists())
            self.assertEqual(len(list((root/'backups').rglob('targets.json'))),1)
            self.assertFalse(list(root.glob('.frontier-*')))
    def test_atomic_promotion_closes_staged_handle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'source';source.write_bytes(b'contents');target=root/'nested/dest'
            installer.promote(source,target);self.assertEqual(target.read_bytes(),b'contents');target.unlink()
