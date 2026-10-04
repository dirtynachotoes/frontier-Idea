"""Destiny Frontier read-only NMS spatial telemetry probe.

Separate from frontier_nms_probe.py. It does not write movement globals or game state.
It publishes live player position/orientation to Local\\DestinyFrontier_Spatial_v2.
Requires the same validated NMSpy 180383.0 / pyMHF 0.2.4 test environment.
"""
import ctypes
import hashlib
import importlib.metadata
import json
import logging
import math
import os
from pathlib import Path
import struct
import time
import secrets

def validate_binary_before_registering_hooks():
    if os.name != "nt":
        raise RuntimeError("NMS spatial probe requires Windows")
    record_path = os.environ.get("DESTINY_FRONTIER_PROBE_VALIDATION") or str(
        Path(__file__).with_name("runtime-validation.json")
    )
    record = json.loads(Path(record_path).read_text())
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    size = kernel.GetModuleFileNameW(None, buffer, len(buffer))
    if not size or size >= len(buffer):
        raise RuntimeError("Cannot identify host executable")
    executable = Path(buffer.value)
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if (
        executable.name.lower() != "nms.exe"
        or record.get("nms_exe_sha256") != digest
        or record.get("nmspy_version") != "180383.0"
        or importlib.metadata.version("NMSpy") != "180383.0"
        or record.get("test_profile") is not True
        or record.get("runtime_hooks_validated") is not True
    ):
        raise RuntimeError("Refused to register hooks: executable/framework/test validation differs")

validate_binary_before_registering_hooks()

from pymhf import Mod
import nmspy.data.types as nms
from nmspy.common import gameData
from frontier.spatial import SpatialMapping
from frontier.control import ControlMapping
from frontier.host_input import HostKey

log = logging.getLogger("DestinyFrontier.NMS.Spatial")

class DestinyFrontierNMSSpatialProbe(Mod):
    __version__='0.1.0-spatial-v2'
    __description__='Read-only host pose/context delivery to native Guardian guest'
    def __init__(self):
        super().__init__();self.mapping=None;self.last_poll=0;self.incarnation=secrets.randbits(63) or 1;self.sequence=0;self.enabled=True;self.control=None;self.key=HostKey();self.pulse_pending=False
    @nms.cGcApplication.Update.after
    def update(self,this):
        now=time.monotonic()
        if not self.enabled:return
        try:
            self.pulse_pending = self.key.pressed() or self.pulse_pending
            if now-self.last_poll<0.1:return
            self.last_poll=now
            if self.mapping is None:self.mapping=SpatialMapping()
            player=gameData.player
            pos=forward=up=right=None
            if player is not None:
                pos=(player.mPosition.x,player.mPosition.y,player.mPosition.z)
                matrix=player.mGraphicsMatrix
                forward=(-matrix.at.x,-matrix.at.y,-matrix.at.z)
                up=(matrix.up.x,matrix.up.y,matrix.up.z)
                right=(matrix.right.x,matrix.right.y,matrix.right.z)
            if self.control is None:self.control=ControlMapping()
            status=self.control.status()
            pressed=self.pulse_pending;self.pulse_pending=False
            if pressed and status and status['core_valid'] and status['scout_link']:
                Path(__file__).with_name('frontier_pulse.trigger').touch()
                log.info('Host F8 pulse requested native Guardian guest mode toggle')
            self.sequence=(self.sequence+1)&0xffffffff
            self.mapping.publish('nms',self.incarnation,self.sequence,player=pos,forward=forward,up=up,right=right)
        except Exception:
            self.enabled=False
            log.exception('Spatial V2 stopped; event bridge remains independent')
            if self.mapping is not None:self.mapping.close();self.mapping=None
            if self.control is not None:self.control.close();self.control=None
