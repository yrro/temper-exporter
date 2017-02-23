import signal
from subprocess import *
import sys
import time
import urllib.request

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
