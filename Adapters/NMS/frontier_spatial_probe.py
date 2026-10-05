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
    # Guardian displacement drives NMS through its own character controller velocity, never by
    # teleporting: NMS keeps its gravity, floors and collision, so a Guardian walking downhill in its
    # own activity can no longer push the NMS player through the floor (seen 2026-10-04).
    MOTION_WINDOW_S=0.15
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
            samples=getattr(self,'motion_samples',None)
            if samples is None:samples=self.motion_samples=[]
            if delta is None or not player.mbSpawned or player.mbIsTransitioning or player.mbIsDying:
                samples.clear();return
            now=time.monotonic()
            if any(delta):samples.append((now,tuple(delta)))
            samples[:]=[s for s in samples if now-s[0]<=self.MOTION_WINDOW_S]
            up=(player.mGraphicsMatrix.up.x,player.mGraphicsMatrix.up.y,player.mGraphicsMatrix.up.z)
            length=math.sqrt(sum(v*v for v in up))
            if not math.isfinite(length) or length<=0:return
            up=tuple(v/length for v in up)
            velocity=[sum(s[1][lane] for s in samples)/self.MOTION_WINDOW_S for lane in range(3)]
            along=sum(a*b for a,b in zip(velocity,up))
            horizontal=tuple(velocity[lane]-along*up[lane] for lane in range(3))
            if not all(math.isfinite(v) for v in horizontal):return
            self.motion_base=(horizontal,up,self.motion_host.valid_until)
            if any(delta) and time.monotonic()-self.last_motion_log>=1:
                self.last_motion_log=time.monotonic()
                log.info('Guardian velocity queued horizontal=%s input_scan_reads=%s',horizontal,self.motion_host.last_result[8])
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
            horizontal,up,expiry=target
            if ticks()>=expiry or not self.motion_host.keys.focused() or not player.mbSpawned or player.mbIsTransitioning or player.mbIsDying:return
            controller=player.mPhysicsController
            if not controller:return
            wanted=controller.contents.mTargetVelocity
            # Keep NMS's own vertical (gravity, jump, slopes); replace only the horizontal intent.
            own=wanted.x*up[0]+wanted.y*up[1]+wanted.z*up[2]
            wanted.x=horizontal[0]+own*up[0];wanted.y=horizontal[1]+own*up[1];wanted.z=horizontal[2]+own*up[2]
            self.motion_trace(player,horizontal,own)
        except Exception:
            if self.motion_host:self.motion_host.close()
            self.motion_host=None
            log.exception('NMS result actuation failed; locomotion disarmed, normal input resumes')
    def motion_trace(self,player,horizontal,own):
        now=time.monotonic()
        if now-getattr(self,'last_trace',0)<0.25:return
        self.last_trace=now
        try:
            import frontier
            path=Path(frontier.__file__).resolve().parents[2]/'Saves'/'Guardian_Test'/'Logs'/'nms-motion.jsonl'
            p=player.mPosition
            with open(path,'a',encoding='utf-8') as f:
                f.write(json.dumps(dict(utc=time.time(),horizontal=[round(v,3) for v in horizontal],own_vertical=round(own,3),position=[round(p.x,3),round(p.y,3),round(p.z,3)]))+'\n')
        except Exception:
            pass
