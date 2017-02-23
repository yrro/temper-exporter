import types
from unittest import mock

import pytest
import pyudev

from temper_exporter import exporter, temper

def test_empty_collector():
    c = exporter.Collector()

    c.coldplug_scan([])
    assert c.healthy

    for fam in c.collect():
        assert fam.samples == []
    assert c.healthy

def test_populated_collector():
    d = mock.create_autospec(pyudev.Device)
    d.action = None

    t = mock.create_autospec(temper.usb_temper)
    t.phy.return_value = ':phy:'
    t.version = 'VERSIONSTRING___'
    t.read_sensor.return_value = [
        ('temp', 'foo', 22),
        ('humid', 'bar', 45),
    ]

    class MyCollector(exporter.Collector):
        def class_for_device(self, device):
            return mock.Mock(return_value=t)
    c = MyCollector()

    c.coldplug_scan([d])
    assert c.healthy

    fams = list(c.collect())
    assert fams[0].name == 'temper_temperature_celsius'
    assert fams[0].type == 'gauge'
    assert fams[0].samples == [('temper_temperature_celsius', {'name': 'foo', 'phy': ':phy:', 'version': 'VERSIONSTRING___'}, 22)]
    assert fams[1].name == 'temper_humidity_rh'
    assert fams[1].type == 'gauge'
    assert fams[1].samples == [('temper_humidity_rh', {'name': 'bar', 'phy': ':phy:', 'version': 'VERSIONSTRING___'}, 45)]

    assert c.healthy

def test_open_failure():
    d = mock.create_autospec(pyudev.Device)
    d.action = None

    T = mock.Mock(side_effect = IOError)

    class MyCollector(exporter.Collector):
        def class_for_device(self, device):
            return T
    c = MyCollector()

    c.coldplug_scan([d])
    assert not c.healthy

def test_read_failure():
    d = mock.create_autospec(pyudev.Device)
    d.action = None

    t = mock.create_autospec(temper.usb_temper)
    t.read_sensor.side_effect = IOError

    T = mock.Mock(return_value=t)

    class MyCollector(exporter.Collector):
        def class_for_device(self, device):
            return T
    c = MyCollector()

    c.coldplug_scan([d])
    assert c.healthy

    list(c.collect())
    assert not c.healthy

    assert c._Collector__sensors == {}
