from unittest import mock

import pytest
import pyudev

from temper_exporter import temper

class hidraw_device:
    def __init__(self):
        self.__response = []

    def write(self, data):
        assert isinstance(data, bytes)
        assert data[0] == 0
        assert len(data) == 9
        self.__handle_write(data[1:9])
        return 9

    def __handle_write(self, data):
        if data == b'\x01\x86\xff\x01\x00\x00\x00\x00':
            self.__response.append(b'mock_tem')
            self.__response.append(b'per_devi')
        else:
            assert not data
            self._handle_write_sub(data)

    def _handle_write_sub(self, data):
        pass

    def read(self, data):
        assert self.__response, 'No report recieved from device - would block'
        return self.__response.pop(0)

    close = mock.MagicMock()

@pytest.fixture
def udev_device(mocker):
    dev = mock.create_autospec(pyudev.Device)
    dev.device_node = '/dev/hidrawX'

    o = mocker.patch('temper_exporter.temper.open', mocker.mock_open())
    def _open(path, mode, buffering):
        assert path == dev.device_node
        assert mode == 'r+b'
        assert buffering == 0
        return hidraw_device()
    o.side_effect = _open

    return dev

def test_init(udev_device):
    t = temper.usb_temper(udev_device)
    assert t.version == 'mock_temper_devi'

def test_close(udev_device):
    t = temper.usb_temper(udev_device)
    t.close()
    assert t._usb_temper__device.close.called

def test_del(udev_device):
    t = temper.usb_temper(udev_device)
    f = t._usb_temper__device
    del t
    assert f.close.called
