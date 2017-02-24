import signal
from subprocess import *
import sys
import time
import urllib.request

import temper_exporter

from prometheus_client.parser import text_string_to_metric_families
import pytest

@pytest.fixture
def process():
    try:
        p = Popen([sys.executable, '-m', 'temper_exporter', '--bind-v6only=1'])
        time.sleep(1) # XXX wait for process readiness
        p.poll()
        assert p.returncode is None
        yield p
    finally:
        p.kill()

def test_main(process):
    r = urllib.request.urlopen('http://[::1]:9204/')
    for family in text_string_to_metric_families(r.read().decode('utf-8')):
        for sample in family.samples:
            print(sample)

    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=1) == 0

def test_bad_health_exits_with_nonzero_status(mocker):
    # Otherwise argparse will interpret pytest's arguments and will system.exit(2)
    mocker.patch('sys.argv', ['temper_exporter'])

    class Unhealth(temper_exporter.Health):
        def __init__(self, *args, **kwargs):
            super().__init__(interval=1, *args, **kwargs)
        def _Health__healthy(self):
            return False

    mocker.patch('temper_exporter.Health', Unhealth)

    with pytest.raises(SystemExit) as excinfo:
        temper_exporter.main()
    assert excinfo.value.code == 1
