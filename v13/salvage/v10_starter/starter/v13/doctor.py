"""Read-only local hardware inventory, no network or unique device identifiers."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

def getprop(key):
    if not shutil.which('getprop'):
        return None
    try:
        return subprocess.run(['getprop', key], capture_output=True, text=True,
                              timeout=2, check=True).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None

def inventory():
    memory = {}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            key, value = line.split(':', 1)
            if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
                memory[key + '_KiB'] = int(value.strip().split()[0])
    except (OSError, ValueError):
        pass
    disk = shutil.disk_usage(Path.cwd())
    return {
        'status': 'inventory_only_no_model_benchmark',
        'system': platform.system(), 'machine': platform.machine(),
        'python': platform.python_version(), 'cpu_count': os.cpu_count(),
        'android_manufacturer': getprop('ro.product.manufacturer'),
        'android_model': getprop('ro.product.model'),
        'android_abi': getprop('ro.product.cpu.abi'),
        'android_version': getprop('ro.build.version.release'),
        'memory': memory, 'storage_free_bytes': disk.free,
        'monotonic_clock': time.get_clock_info('monotonic').monotonic,
        'native_models_installed_by_this_package': False,
        'temperature': 'not measured; requires device-specific access',
    }

if __name__ == '__main__':
    if sys.version_info < (3, 8):
        raise SystemExit('Python 3.8 or newer required')
    print(json.dumps(inventory(), ensure_ascii=False, indent=2))

