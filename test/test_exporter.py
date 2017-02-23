import types
from unittest import mock

import pytest
import pyudev

from temper_exporter import exporter, temper

def test_collection():
    d = mock.create_autospec(pyudev.Device)

    t = mock.create_autospec(temper.usb_temper)
    t.phy.return_value = ':phy:'
    t.version = 'VERSIONSTRING___'
    t.read_sensor.return_value = [
        ('temp', 'foo', 22),
        ('humid', 'bar', 45),
    ]

    c = exporter.Collector()
    c._Collector__sensors = {d: t}

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

    t = mock.create_autospec(temper.usb_temper)
    t.read_sensor.side_effect = IOError

    c = exporter.Collector()
    c._Collector__sensors = {d: t}

    list(c.collect())
    assert c._Collector__sensors == {}
    assert not c.healthy

def test_add_device():
    d1 = mock.create_autospec(pyudev.Device)
    d1.action = 'add'

    t = mock.create_autospec(temper.usb_temper)

    T = mock.Mock(return_value=t)

    class MyCollector(exporter.Collector):
        def class_for_device(self, device):
            return T
    c = MyCollector()

    c.handle_device_event(d1)
    assert c._Collector__sensors == {d1: t}

def test_add_duplicate_device():
    d1 = mock.create_autospec(pyudev.Device, name='d1')
    d1.device_path = '/sys/foo'
    d1.__hash__.return_value = hash(d1.device_path)

    t1 = mock.create_autospec(temper.usb_temper, name='t1')
    t2 = mock.create_autospec(temper.usb_temper, name='t2')
    T = mock.Mock()

    c = exporter.Collector()
    c.class_for_device=mock.create_autospec(c.class_for_device)
    c._Collector__sensors = {d1: t1}

    d2 = mock.create_autospec(pyudev.Device, name='d2')
    d2.action = 'add'
    d2.device_path = '/sys/foo'
    d2.__hash__.return_value = hash(d2.device_path)

    def eq(a, b):
        return a is d1 and b is d2 or a is d2 and b is d1
    d1.__eq__ = eq
    d2.__eq__ = eq

    c.handle_device_event(d2)

    assert not c.class_for_device.called
    # The original usb_temper should still be in the dict
    assert len(c._Collector__sensors) == 1
    assert c._Collector__sensors.popitem()[1] == t1

def test_remove_device():
    d1 = mock.create_autospec(pyudev.Device, name='d1')
    d1.device_path = '/sys/foo'
    d1.__hash__.return_value = hash(d1.device_path)

    t = mock.create_autospec(temper.usb_temper, name='t1')

    c = exporter.Collector()
    c._Collector__sensors = {d1: t}

    d2 = mock.create_autospec(pyudev.Device, name='d2')
    d2.action = 'remove'
    d2.device_path = '/sys/foo'
    d2.__hash__.return_value = hash(d2.device_path)

    def eq(a, b):
        return a is d1 and b is d2 or a is d2 and b is d1
    d1.__eq__ = eq
    d2.__eq__ = eq

    c.handle_device_event(d2)

    assert c._Collector__sensors == {}
