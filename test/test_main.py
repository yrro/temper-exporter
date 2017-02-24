import signal
from subprocess import *
import sys
import time
from unittest import mock
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

def test_main_exits_with_nonzero_status_on_bad_health(mocker):
    # Otherwise argparse will interpret pytest's arguments and will system.exit(2)
    mocker.patch('sys.argv', ['temper_exporter'])

    class Unhealth(temper_exporter.Health):
        def __init__(self, components, interval):
            super().__init__(components, interval=1)
        def _Health__healthy(self):
            return False

    mocker.patch('temper_exporter.Health', Unhealth)

    with pytest.raises(SystemExit) as excinfo:
        temper_exporter.main()
    assert excinfo.value.code == 1

def test_health_good():
    c1 = mock.MagicMock()
    c1.healthy.return_value = True
    c2 = mock.MagicMock()
    c2.healthy.return_value = True
    assert temper_exporter.Health([c1, c2], 1)._Health__healthy()

def test_health_bad_if_any_component_bad():
    c1 = mock.MagicMock()
    c1.healthy.return_value = True
    c2 = mock.MagicMock()
    c2.healthy.return_value = False
    assert not temper_exporter.Health([c1, c2], 1)._Health__healthy()

def test_health_bad_if_any_component_health_raises():
    c1 = mock.MagicMock()
    c1.healthy.return_value = True
    c2 = mock.MagicMock()
    c2.healthy.side_effect = Exception
    assert not temper_exporter.Health([c1, c2], 1)._Health__healthy()
