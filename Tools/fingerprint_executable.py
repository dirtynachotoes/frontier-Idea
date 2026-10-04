"""Read-only binary fingerprint. Does not certify runtime compatibility."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

parser = argparse.ArgumentParser()
parser.add_argument('executable', type=Path)
args = parser.parse_args()
data = args.executable.read_bytes()
if data[:2] != b'MZ' or len(data) < 64:
    raise SystemExit('Not a PE executable')
pe = struct.unpack_from('<I',data,0x3c)[0]
if data[pe:pe+4] != b'PE\0\0' or len(data) < pe+24:
    raise SystemExit('Invalid PE header')
machine = struct.unpack_from('<H',data,pe+4)[0]
print(json.dumps(dict(name=args.executable.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),machine=hex(machine),is_x64=machine==0x8664,runtime_verified=False),indent=2))
