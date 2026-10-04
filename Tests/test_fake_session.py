from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from fake_session import run_session
class FakeSessionTests(unittest.TestCase):
    def test_real_core_with_fake_host_guest(self):run_session()
