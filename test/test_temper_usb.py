from unittest import mock

import pytest
import pyudev

from temper_exporter import temper

class hidraw_device:
    def __init__(self):
        self.__commands = {}
        self.__response = []
        self.cmd_response(b'\x01\x86\xff\x01\x00\x00\x00\x00', [b'mock_tem', b'per_devi'])

    def cmd_response(self, cmd, response):
        assert isinstance(cmd, bytes)
        assert isinstance(response, list)
        assert response
        for x in response:
            assert isinstance(x, bytes)
        self.__commands[cmd] = response

    def write(self, data):
        assert isinstance(data, bytes)
        assert data[0] == 0
        assert len(data) == 9
        self.__handle_write(data[1:9])
        return 9

    def __handle_write(self, data):
        assert self.__commands[data]
        self.__response.extend(self.__commands[data])

    def read(self, data):
        assert self.__response, 'No report received from device - would block'
        return self.__response.pop(0)

    close = mock.MagicMock()

@pytest.fixture
def utemper(mocker):
    hid = mock.create_autospec(pyudev.Device)
    def _get(k):
        assert k == 'HID_PHYS'
        return 'fakephy'
    hid.properties.get.side_effect = _get

    dev = mock.create_autospec(pyudev.Device)
    dev.device_node = '/dev/hidrawX'
    dev.sys_path = '/sys/somewhere'
    def _find_parent(subsystem):
        assert subsystem == b'hid'
        return hid
    dev.find_parent.side_effect = _find_parent

    o = mocker.patch('temper_exporter.temper.open', mocker.mock_open())
    def _open(path, mode, buffering):
        assert path == dev.device_node
        assert mode == 'r+b'
        assert buffering == 0
        return hidraw_device()
    o.side_effect = _open

    return temper.usb_temper(dev)

def test_init(utemper):
    assert utemper.version == 'mock_temper_devi'

def test_close(utemper):
    utemper.close()
    assert utemper._usb_temper__device.close.called

def test_del(utemper):
    f = utemper._usb_temper__device
    del utemper
    assert f.close.called

def test_phy(utemper):
    assert utemper.phy() == 'fakephy'

def test_repr(utemper):
    assert '/sys/somewhere' in repr(utemper)

def test_send_response_very_short(utemper):
    utemper._usb_temper__device.cmd_response(b'\xff\x79\x00\x00\x00\x00\x00\x00', [b'\x79'])
    with pytest.raises(IOError):
        utemper.send(b'\xff\x79\x00\x00\x00\x00\x00\x00', '>bbbb')

def test_send_response_bad_cmd(utemper):
    utemper._usb_temper__device.cmd_response(b'\xff\x79\x00\x00\x00\x00\x00\x01', [b'\xff\x04\x00\x00\x00\x00\x00\x00'])
    with pytest.raises(IOError):
        utemper.send(b'\xff\x79\x00\x00\x00\x00\x00\x01', '>bbbb')

def test_send_response_wrong_size_field(utemper):
    utemper._usb_temper__device.cmd_response(b'\xff\x79\x00\x00\x00\x00\x00\x02', [b'\x79\xff\x00\x00\x00\x00\x00\x00'])
    with pytest.raises(IOError):
        utemper.send(b'\xff\x79\x00\x00\x00\x00\x00\x02', '>bbbb')

def test_send_response_short(utemper):
    utemper._usb_temper__device.cmd_response(b'\xff\x79\x00\x00\x00\x00\x00\x03', [b'\x79\x04\x00\x00'])
    with pytest.raises(IOError):
        utemper.send(b'\xff\x79\x00\x00\x00\x00\x00\x03', '>bbbb')

def test_send_response_ok(utemper):
    utemper._usb_temper__device.cmd_response(b'\xff\x79\x00\x00\x00\x00\x00\x04', [b'\x79\x04\x54\x16\x54\x16'])
    assert utemper.send(b'\xff\x79\x00\x00\x00\x00\x00\x04', '>bbh') == (84, 22, 21526)
