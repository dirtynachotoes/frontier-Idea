"""NMS test bridge: bidirectional actuation reported runtime-verified by user.
Heartbeat repair itself still requires Windows runtime validation. TEST SAVE ONLY.
Requires NMSpy 180383.0 / pyMHF 0.2.4 and manual local binary validation.
A separate enable file explicitly unlocks the probe AFTER hooks have been checked.
"""
import ctypes
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import secrets
import time

def validate_binary_before_registering_hooks():
    if os.name != 'nt':
        raise RuntimeError('NMS probe requires Windows')
    record_path = os.environ.get('DESTINY_FRONTIER_PROBE_VALIDATION') or str(Path(__file__).with_name('runtime-validation.json'))
    if not record_path:
        raise RuntimeError('Refused to register hooks: local validation record is missing')
    record = json.loads(Path(record_path).read_text())
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    size = kernel.GetModuleFileNameW(None, buffer, len(buffer))
    if not size or size >= len(buffer):
        raise RuntimeError('Cannot identify host executable')
    executable = Path(buffer.value)
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if (executable.name.lower() != 'nms.exe' or record.get('nms_exe_sha256') != digest
            or record.get('nmspy_version') != '180383.0'
            or importlib.metadata.version('NMSpy') != '180383.0'
            or record.get('test_profile') is not True
            or record.get('runtime_hooks_validated') is not True):
        raise RuntimeError('Refused to register hooks: executable/framework/test validation differs')


validate_binary_before_registering_hooks()

from pymhf import Mod
import nmspy.data.types as nms
from nmspy.common import gameData
from nmspy.globals import globals
from frontier.ipc import Mapping

log = logging.getLogger('DestinyFrontier.NMS')


class DestinyFrontierNMSProbe(Mod):
    __version__ = '0.0.2-heartbeat'
    __description__ = 'TEST bridge: nanite/manual pulse read and walking speed control'

    def __init__(self):
        super().__init__()
        self.incarnation = secrets.randbits(63) or 1
        self.sequence = 0
        self.ack = 0
        self.detail = 0
        self.mapping = None
        self.last_poll = 0
        self.baseline = None
        self.enabled = False
        self.enabled = True  # binary validation ran before hook registration
        self.last_ipc_status = None
        self.manual_trigger = Path(__file__).with_name('frontier_pulse.trigger')

    @nms.cGcPlayerState.AwardNanites.after
    def nanites_awarded(self, this, liChange):
        if self.enabled and liChange > 0 and self.sequence < 1_000_000:
            self.sequence += 1
            self.detail = min(int(liChange), 0xFFFFFFFF)

    @nms.cGcApplication.Update.after
    def update(self, this):
        # This callback follows NMS.py's own singleton hook. Pointer ordering is still a runtime test gate.
        if not self.enabled or time.monotonic() - self.last_poll < .1:
            return
        self.last_poll = time.monotonic()
        if self.manual_trigger.exists():
            try:
                self.manual_trigger.unlink()
                if self.sequence < 1_000_000:
                    self.sequence += 1
                    self.detail = 1
                    log.info("Manual Frontier pulse triggered")
            except Exception:
                log.exception("Manual Frontier pulse failed")
        try:
            if self.mapping is None:
                self.mapping = Mapping()
            player = gameData.player_state
            ready = bool(player is not None and globals.GcPlayerGlobals is not None)
            result = self.mapping.exchange('nms', self.incarnation, self.sequence, ready, self.ack, self.detail)
            diagnostic = self.mapping.last_exchange
            if diagnostic.get('status') != self.last_ipc_status:
                log.info("Frontier IPC status=%s core_age_ms=%s peer_age_ms=%s",
                         diagnostic.get('status'), diagnostic.get('core_age_ms'), diagnostic.get('peer_age_ms'))
                self.last_ipc_status = diagnostic.get('status')
            if ready:
                if self.baseline is None:
                    self.baseline = float(globals.GcPlayerGlobals.GroundWalkSpeed)
                live = bool(result and result[2])
                target = result[1] if live else 0
                applied = self.baseline * (1.25 if live and target % 2 else 1.0)
                globals.GcPlayerGlobals.GroundWalkSpeed = applied
                if target != self.ack:
                    log.info("Frontier speed target=%s baseline=%s applied=%s", target, self.baseline, applied)
                self.ack = target
        except Exception:
            log.exception('Probe stopped after error; restart game before retrying')
            if self.baseline is not None:
                try:
                    globals.GcPlayerGlobals.GroundWalkSpeed = self.baseline
                except Exception:
                    log.exception('Unable to restore walking speed; restart NMS')
            self.enabled = False
