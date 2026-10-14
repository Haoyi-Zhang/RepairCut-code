"""Pure checks import without POSIX; bounded campaigns still require limits."""
from pathlib import Path
import subprocess
import sys
import unittest


class PortableImportTests(unittest.TestCase):
    def test_finite_imports_and_fail_closed_campaign_without_resource(self):
        script = r'''
import builtins
original_import = builtins.__import__
def without_resource(name, *args, **kwargs):
    if name == "resource":
        raise ModuleNotFoundError("resource intentionally unavailable")
    return original_import(name, *args, **kwargs)
builtins.__import__ = without_resource
from speculation import validate
from speculation.builders import gap_graph
from speculation.bitcheck import analyze
from speculation.replay import certificate, verify
g = gap_graph(2)
a = analyze(g)
if (a.adaptive_min, a.uniform_min) != (1, 2):
    raise AssertionError("portable semantic result changed")
if not verify(g, certificate(g, 2, "uniform", [a.uniform_mask])):
    raise AssertionError("portable certificate replay failed")
try:
    validate.resource_guard()
except RuntimeError as error:
    if "requires POSIX resource limits" not in str(error):
        raise AssertionError("unexpected admission error") from error
else:
    raise AssertionError("bounded campaign silently omitted required limits")
print("portable checks passed; unbounded campaign refused")
'''
        run = subprocess.run(
            [sys.executable, '-B', '-c', script],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('portable checks passed', run.stdout)


if __name__ == '__main__':
    unittest.main()
