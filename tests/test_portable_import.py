"""Pure checks import without POSIX; bounded campaigns still require limits."""
from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class PortableImportTests(unittest.TestCase):
    def test_campaign_cli_collects_resource_usage_after_admission(self):
        from speculation import validate
        usage = SimpleNamespace(ru_maxrss=1234)
        resource = SimpleNamespace(RUSAGE_SELF=0, getrusage=lambda who: usage)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'results'
            arguments = ['validate', 'relations', '--output', str(output)]
            with patch.object(sys, 'argv', arguments), \
                 patch.dict(sys.modules, {'resource': resource}), \
                 patch.object(validate, 'resource_guard') as guard, \
                 patch.dict(validate.SUITES, {'relations': lambda: ([{'case': 'cli'}], {'cases': 1})}), \
                 redirect_stdout(io.StringIO()):
                validate.main()
            guard.assert_called_once_with()
            report = json.loads((output / 'relations.json').read_text())
            self.assertEqual(report['peak_rss_kib'], 1234)
            self.assertEqual(report['counts'], {'cases': 1})
            self.assertEqual(report['status'], 'finite checks passed')
            self.assertTrue((output / 'relations.csv').is_file())

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
