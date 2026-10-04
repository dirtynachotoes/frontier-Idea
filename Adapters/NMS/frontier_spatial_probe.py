"""Destiny Frontier spatial host with explicit opt-in Guardian locomotion.

Spatial delivery and F8 behavior remain unchanged. F9 movement is enabled only by the opt-in Core motion mode.
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
import nmspy.data.basic_types as basic
from nmspy.common import gameData
from frontier.spatial import SpatialMapping
from frontier.control import ControlMapping
from frontier.host_input import HostKey
from frontier.motion_host import HostMotion
from frontier.ipc import ticks

log = logging.getLogger("DestinyFrontier.NMS.Spatial")

class DestinyFrontierNMSSpatialProbe(Mod):
    __version__='0.2.0-guardian-motion'
    __description__='Spatial V2 host and opt-in native Guardian locomotion'
    def __init__(self):
        super().__init__();self.mapping=None;self.last_poll=0;self.incarnation=secrets.randbits(63) or 1;self.sequence=0;self.enabled=True;self.control=None;self.key=HostKey();self.pulse_pending=False;self.motion_host=None;self.motion_base=None;self.last_motion_armed=False;self.last_motion_log=0
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

    @nms.cGcPlayer.SetToPosition.before
    def motion_position_seam(self,this,lPos,lDir,lVel):
        # Registers the maintained typed method; no raw function addresses or offsets.
        pass
    @nms.cGcPlayer.Update.before
    def motion_before(self,this,lfStep):
        self.motion_base=None
        if not self.enabled:return
        player=gameData.player
        if player is None or ctypes.addressof(player)!=ctypes.addressof(this.contents):return
        try:
            if self.control is None:self.control=ControlMapping()
            status=self.control.status()
            if self.motion_host is None:self.motion_host=HostMotion()
            delta=self.motion_host.exchange(self.incarnation,status)
            if self.motion_host.armed!=self.last_motion_armed:
                log.info('Guardian locomotion armed=%s (F9); native displacement only',self.motion_host.armed)
                self.last_motion_armed=self.motion_host.armed
            if delta is None or not player.mbSpawned or player.mbIsTransitioning or player.mbIsDying:return
            # Preserve the engine's explicit local/offset representation; never treat a plain
            # player-position vector as an absolute cTkBigPos.
            base=basic.cTkBigPos.from_buffer_copy(player.mGraphicsMatrix.pos)
            for lane,change in zip(('x','y','z'),delta):setattr(base.local,lane,getattr(base.local,lane)+change)
            direction=basic.cTkVector3(-player.mGraphicsMatrix.at.x,-player.mGraphicsMatrix.at.y,-player.mGraphicsMatrix.at.z)
            self.motion_base=(base,direction,self.motion_host.valid_until)
            if any(delta) and time.monotonic()-self.last_motion_log>=1:
                self.last_motion_log=time.monotonic()
                log.info('Guardian result queued delta=%s input_scan_reads=%s',delta,self.motion_host.last_result[8])
        except Exception:
            if self.motion_host:self.motion_host.close()
            self.motion_host=None;self.motion_base=None
            log.exception('Locomotion disabled; normal NMS input resumes, legacy bridge unchanged')
    @nms.cGcPlayer.Update.after
    def motion_after(self,this,lfStep):
        target=self.motion_base;self.motion_base=None
        if target is None:return
        player=gameData.player
        if player is None or ctypes.addressof(player)!=ctypes.addressof(this.contents):return
        try:
            position,direction,expiry=target
            if ticks()>=expiry or not self.motion_host.keys.focused() or not player.mbSpawned or player.mbIsTransitioning or player.mbIsDying:return
            velocity=basic.cTkVector3(0,0,0)
            player.SetToPosition(ctypes.byref(position),ctypes.byref(direction),ctypes.byref(velocity))
        except Exception:
            if self.motion_host:self.motion_host.close()
            self.motion_host=None
            log.exception('NMS result actuation failed; locomotion disarmed, normal input resumes')
