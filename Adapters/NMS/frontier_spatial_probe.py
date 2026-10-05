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
    # Guardian horizontal displacement drives NMS with a closed-loop position anchor.
    # Runtime 2026-10-04: re-basing every frame on the pre-update graphics position drifted the player
    # through the Space Anomaly floor even with zero Guardian motion (SetToPosition and the graphics
    # position differ by an unknown offset); writing the controller target velocity had no effect.
    # Now: anchor (in mPosition space) = Guardian horizontal steps + NMS's own vertical (gravity/ground),
    # and the SetToPosition offset is measured from the observed result each frame, so no error builds up.
    MOTION_WINDOW_S=0.15
    MOTION_RESET_M=5.0
    def motion_reset(self):
        self.motion_anchor=None;self.motion_offset=None;self.motion_last_target=None
        samples=getattr(self,'motion_samples',None)
        if samples is not None:samples.clear()
    @staticmethod
    def vec(v):return (float(v.x),float(v.y),float(v.z))
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
            if getattr(self,'motion_samples',None) is None:self.motion_samples=[]
            if delta is None or not player.mbSpawned or player.mbIsTransitioning or player.mbIsDying:
                self.motion_reset();return
            up=self.vec(player.mGraphicsMatrix.up)
            length=math.sqrt(sum(v*v for v in up))
            if not math.isfinite(length) or length<=0:self.motion_reset();return
            up=tuple(v/length for v in up)
            along=sum(a*b for a,b in zip(delta,up))
            step=tuple(delta[i]-along*up[i] for i in range(3))
            now=time.monotonic()
            if any(step):self.motion_samples.append((now,step))
            self.motion_samples[:]=[s for s in self.motion_samples if now-s[0]<=self.MOTION_WINDOW_S]
            velocity=tuple(sum(s[1][i] for s in self.motion_samples)/self.MOTION_WINDOW_S for i in range(3))
            before=self.vec(player.mPosition)
            graphics=basic.cTkBigPos.from_buffer_copy(player.mGraphicsMatrix.pos)
            if not all(math.isfinite(v) for v in step+velocity+before):self.motion_reset();return
            self.motion_base=(step,velocity,up,before,graphics,self.motion_host.valid_until)
            if any(step) and time.monotonic()-self.last_motion_log>=1:
                self.last_motion_log=time.monotonic()
                log.info('Guardian step queued step=%s input_scan_reads=%s',step,self.motion_host.last_result[8])
        except Exception:
            if self.motion_host:self.motion_host.close()
            self.motion_host=None;self.motion_base=None;self.motion_reset()
            log.exception('Locomotion disabled; normal NMS input resumes, legacy bridge unchanged')
    @nms.cGcPlayer.Update.after
    def motion_after(self,this,lfStep):
        target=self.motion_base;self.motion_base=None
        if target is None:return
        player=gameData.player
        if player is None or ctypes.addressof(player)!=ctypes.addressof(this.contents):return
        try:
            step,velocity,up,before,graphics,expiry=target
            if ticks()>=expiry or not self.motion_host.keys.focused() or not player.mbSpawned or player.mbIsTransitioning or player.mbIsDying:
                self.motion_reset();return
            after=self.vec(player.mPosition)
            sub=lambda a,b:tuple(x-y for x,y in zip(a,b))
            add=lambda a,b:tuple(x+y for x,y in zip(a,b))
            dot=lambda a,b:sum(x*y for x,y in zip(a,b))
            scale=lambda a,k:tuple(x*k for x in a)
            anchor=getattr(self,'motion_anchor',None);offset=getattr(self,'motion_offset',None)
            last=getattr(self,'motion_last_target',None)
            error=None
            if anchor is not None and last is not None:
                # Where our last command actually landed versus where we asked: measure, never guess.
                error=sub(before,last)
                if math.sqrt(dot(error,error))>self.MOTION_RESET_M:
                    # A large jump is a teleport/respawn or an offset we cannot trust: stop, never chase it.
                    self.motion_host.close();self.motion_host=None;self.motion_reset()
                    log.warning('Guardian locomotion disarmed: host position jumped %.2f m',math.sqrt(dot(error,error)))
                    return
            if anchor is None:
                anchor=before
                offset=sub((graphics.local.x,graphics.local.y,graphics.local.z),before)
            elif error is not None:
                offset=sub(offset,error)
            # Guardian supplies horizontal motion; NMS keeps its own vertical (gravity, ground, slopes).
            anchor=add(anchor,step)
            anchor=add(anchor,scale(up,dot(sub(after,before),up)))  # NMS's own vertical change this frame only
            command=add(anchor,offset)
            if not all(math.isfinite(v) for v in command):self.motion_reset();return
            position=basic.cTkBigPos.from_buffer_copy(graphics)
            position.local.x,position.local.y,position.local.z=command
            # Horizontal Guardian velocity only. Feeding NMS's own vertical speed back in was a positive
            # feedback loop (runtime 2026-10-04: player launched upward ~20 m/s through the ceiling).
            vel=velocity
            direction=basic.cTkVector3(-player.mGraphicsMatrix.at.x,-player.mGraphicsMatrix.at.y,-player.mGraphicsMatrix.at.z)
            speed=basic.cTkVector3(*vel)
            player.SetToPosition(ctypes.byref(position),ctypes.byref(direction),ctypes.byref(speed))
            self.motion_anchor=anchor;self.motion_offset=offset;self.motion_last_target=anchor
            self.motion_trace(step,velocity,before,after,anchor,offset,error)
        except Exception:
            if self.motion_host:self.motion_host.close()
            self.motion_host=None;self.motion_reset()
            log.exception('NMS result actuation failed; locomotion disarmed, normal input resumes')
    def motion_trace(self,step,velocity,before,after,anchor,offset,error):
        now=time.monotonic()
        if now-getattr(self,'last_trace',0)<0.2:return
        self.last_trace=now
        try:
            import frontier
            path=Path(frontier.__file__).resolve().parents[2]/'Saves'/'Guardian_Test'/'Logs'/'nms-motion.jsonl'
            r=lambda v:None if v is None else [round(x,3) for x in v]
            with open(path,'a',encoding='utf-8') as f:
                f.write(json.dumps(dict(utc=time.time(),mode='anchor',step=r(step),velocity=r(velocity),before=r(before),after=r(after),anchor=r(anchor),offset=r(offset),error=r(error)))+'\n')
        except Exception:
            pass
