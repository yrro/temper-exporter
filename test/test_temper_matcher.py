from unittest import mock

import pyudev
import pytest

from temper_exporter import temper

def test_matcher_searches_for_parent_usb_interface():
    d = mock.create_autospec(pyudev.Device)
    assert temper.matcher.match(d) is None
    d.find_parent.assert_called_with(subsystem=b'usb', device_type=b'usb_interface')

def test_matcher_ignores_device_without_parent_usb_interface():
    d = mock.create_autospec(pyudev.Device)
    d.find_parent.return_value = None
    assert temper.matcher.match(d) is None

def test_matcher_ignores_device_with_non_matching_parent_usb_interface():
    di = mock.create_autospec(pyudev.Device)
    di.get.return_value = 'wibble'
    dh = mock.create_autospec(pyudev.Device)
    dh.find_parent.return_value = di
    assert temper.matcher.match(dh) is None
    di.get.assert_called_with(b'MODALIAS')

@pytest.mark.parametrize('modalias', [
    'usb:v0C45p7401d0001dc00dsc00dp00ic03isc01ip02in01',
    'usb:v1130p660Cd0150dc00dsc00dp00ic03isc00ip00in01',
    'usb:v0C45p7402d0001dc00dsc00dp00ic03isc01ip02in01',
])
def test_matcher_matches_device_with_recognized_parent_usb_interface(modalias):
    di = mock.create_autospec(pyudev.Device)
    def _get(arg):
        assert arg == b'MODALIAS'
        return modalias
    di.get.side_effect = _get
    dh = mock.create_autospec(pyudev.Device)
    dh.find_parent.return_value = di
    assert issubclass(temper.matcher.match(dh), temper.usb_temper)
    di.get.assert_called_with(b'MODALIAS')

