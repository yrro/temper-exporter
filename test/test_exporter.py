import types

import pytest

from temper_exporter import exporter

def test_empty_collector():
    c = exporter.Collector()

    c.coldplug_scan(list)
    assert c.healthy()

    for fam in c.collect():
        assert fam.samples == []
    assert c.healthy()

class Device(types.SimpleNamespace):
    action = None
    device_node = None

    def __hash__(self):
        return hash(tuple(sorted(self.__dict__.items())))

    def find_parent(self, subsystem, device_type=None, device_node=None):
        raise NotImplementedError

    def get(self, attribute, default=None):
        return default

class NonUSBDevice(Device):
    def find_parent(self, subsystem, device_type=None):
        return None

class NonTemperUSBInterface(Device):
    pass

class NonTemperDevice(Device):
    def find_parent(self, subsystem, device_type=None):
        return NonTemperUSBInterface()

def test_nonusb_devices_ignored():
    c = exporter.Collector()
    c.coldplug_scan(lambda: [NonUSBDevice()])
    assert c.healthy()

def test_non_temper_devices_ignored():
    c = exporter.Collector()
    c.coldplug_scan(lambda: [NonTemperDevice()])
