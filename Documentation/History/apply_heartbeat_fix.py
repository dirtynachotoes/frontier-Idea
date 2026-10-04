"""Apply three guarded Python files only. No DLL/build/hook-loader/game launching."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import uuid

EXPECTED = {
    'Core/frontier/ipc.py': '891970ed6c3d88c1f986bfa2f1d8bf7ffb8ae68a89a61ee8f7f88106371e553b',
    'Core/frontier/probe.py': '0faa7b6ac9c96b7a362a5d9e1a0edd71121c88f6655d0b77d13e602d4f81cb62',
    'Adapters/NMS/frontier_nms_probe.py': 'a6c61ef7dd579e9e69d66c3f45427617b7a833ccd9f75d62fae6836258590a61',
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-root', required=True, type=Path, help='Existing DestinyFrontier project root (containing Core)')
    parser.add_argument('--nms-adapter', required=True, type=Path, help='Exact actually loaded NMS mod .py file')
    parser.add_argument('--apply', action='store_true', help='Write only after games/core are fully closed; default is read-only validation')
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[1]
    root = args.core_root.resolve()
    targets = {name: (args.nms_adapter.resolve() if name.startswith('Adapters/') else root / name) for name in EXPECTED}
    # Validate ALL targets before ANY write. A reconstructed file mismatch needs
    # actual source review, not an unsafe --force option.
    for name, target in targets.items():
        if not target.is_file() or digest(target) != EXPECTED[name]:
            parser.exit(1, 'REFUSED: source differs from supplied handoff: ' + str(target) + '\nAttach the actual file for review; nothing was changed.\n')
        if target.resolve() == (package / name).resolve():
            parser.exit(1, 'REFUSED: source package cannot also be the installed destination.\n')
    print('All three destination files match the handoff SHA-256 values.')
    if not args.apply:
        print('Read-only check complete. Close NMS, offline Destiny, and Core before using --apply.')
        return
    backup = root / 'Backups' / ('heartbeat-source-' + uuid.uuid4().hex)
    # Back up EVERY original before promoting the first changed source file.
    for name, target in targets.items():
        saved = backup / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, saved)
        if digest(saved) != EXPECTED[name]:
            raise RuntimeError('Backup verification failed: ' + name)
    (backup / 'targets.json').write_text(json.dumps({name: str(path) for name, path in targets.items()}, indent=2), encoding='utf-8')
    print('Original source backups: ' + str(backup), flush=True)
    staged = []
    try:
        for name, target in targets.items():
            # Stage beside destination for same-filesystem replacement. A
            # regular file context closes before promotion on Windows.
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='frontier-source-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                staged.append(temporary)
                stream.write((package / name).read_bytes())
            temporary.replace(target)
            print('Updated ' + str(target))
    finally:
        for temporary in staged:
            temporary.unlink(missing_ok=True)
    print('Original source backups: ' + str(backup))
    print('All three replacements are required. Restart all Python processes; do not hot-reload the NMS mod.')


if __name__ == '__main__':
    main()
