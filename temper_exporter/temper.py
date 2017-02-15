import contextlib
import struct

import pyudev

cmd_read_temper     = b'\x01\x80\x33\x01\x00\x00\x00\x00'
cmd_get_calibration = b'\x01\x82\x77\x01\x00\x00\x00\x00'
cmd_get_version     = b'\x01\x86\xff\x01\x00\x00\x00\x00'
cmd_stop            = b'\x01\x88\x55\x00\x00\x00\x00\x00' # kills the temperhum if sent - so why bother anyway
cmd_read_sensor_id  = b'\x01\x89\x55\x00\x00\x00\x00\x00' # temper2 only

class matcher(type):
    matchers = []

    def __new__(meta, name, bases, class_dict):
        cls = super().__new__(meta, name, bases, class_dict)
        meta.matchers.append(cls)
        return cls

class usb_temper:
    @classmethod
    def match_interface(cls, udev_device, fn):
        intf = udev_device.find_parent(subsystem=b'usb', device_type=b'usb_interface')
        return fn(intf) if intf else False

    def __init__(self, udev_device):
        self.__udev_device = udev_device
        self.__device = open(udev_device.device_node, 'r+b', buffering=0)

    def __repr__(self):
        return '<{}({!r})>'.format(self.__class__.__name__, self.__udev_device.sys_path)

    def read(self, nbytes):
        # NB, first byte is report id iff the device uses numbered reports.
        # Otherwise it's the data!
        return self.__device.read(nbytes)

    def write(self, data, report_id=b'\x00'):
        buf = report_id + data
        nbytes = self.__device.write(buf)
        if nbytes != len(buf):
            raise IOError('Short write ({}/{})'.format(nbytes, len(buf)))

    def read_version(self):
        self.write(cmd_get_version)
        version = self.read(8) + self.read(8)
        return version.decode('ascii', errors='replace')

    def close(self):
        self.__device.close()

    def hid_phys(self):
        hid = self.__udev_device.find_parent(subsystem=b'hid')
        return hid.properties.get('HID_PHYS')

class temper(usb_temper, metaclass=matcher):
    @classmethod
    def match(cls, udev_device):
        if cls.match_interface(udev_device, lambda i: i.get(b'MODALIAS') == 'usb:v1130p660Cd0150dc00dsc00dp00ic03isc00ip00in01'):
            return cls(udev_device)

    def read_sensor(self):
        self.write(b'\x54\x00\x00\x00\x00\x00\x00\x00')
        return self.read(8)

class temper2(usb_temper, metaclass=matcher):
    @classmethod
    def match(cls, udev_device):
        if cls.match_interface(udev_device, lambda i: i.get(b'MODALIAS') == 'usb:v0C45p7401d0001dc00dsc00dp00ic03isc01ip02in01'):
            return cls(udev_device)

    def read_calibration(self):
        self.write(cmd_get_calibration)
        buf = self.read(8)
        cmd, nbytes, correction, wtf = struct.unpack('>BBbbxxxx', buf)
        if cmd != 0x82 or nbytes != 2:
            raise IOError('Unexpected calibration response: {}'.format(buf))
        return correction/16

    def read_id(self):
        self.write(cmd_read_sensor_id)
        buf = self.read(8)
        cmd, nbytes, id_ = struct.unpack('>BBBxxxxx', buf)
        if cmd != 0x89 or nbytes != 1:
            raise IOError('Unexpected id response: {}'.format(id_buf))
        return id_ & 0xf >> 1

    def read_sensor(self):
        self.write(cmd_read_temper)
        read_buf = self.read(8)
        cmd, nbytes, tempi, tempe = struct.unpack('>BBhhxx', read_buf)
        if cmd != 0x80 or nbytes != 4:
            raise IOError('Unexpected read response: {}'.format(read_buf))

        tempi_c = tempi * 125 / 32000
        tempe_c = tempe * 125 / 32000

        return tempi_c, tempe_c

class temper2hum(usb_temper, metaclass=matcher):
    @classmethod
    def match(cls, udev_device):
        if cls.match_interface(udev_device, lambda i: i.get(b'MODALIAS') == 'usb:v0C45p7402d0001dc00dsc00dp00ic03isc01ip02in01'):
            return cls(udev_device)

    def read_calibration(self):
        self.write(cmd_get_calibration)
        buf = self.read(8)
        cmd, nbytes, correction, wtf, correction2, wtf2 = struct.unpack('>BBbbbbxx', buf)
        if cmd != 0x82 or nbytes != 4:
            raise IOError('Unexpected calibration response: {}'.format(buf))
        return correction/16, correction2/16

    def read_sensor(self):
        self.write(cmd_read_temper)
        read_buf = self.read(8)
        cmd, nbytes, temp, rh = struct.unpack('>BBhhxx', read_buf)
        if cmd != 0x80 or nbytes != 4:
            raise IOError('Unexpected read response: {}'.format(read_buf))

        temp_c = temp/100 - 39.7;
        rh_pc = -2.0468 + 0.0367 * rh - 1.5955e-6 * rh * rh
        rh_pc += (temp_c - 25) * (0.01 + 0.00008 * rh)
        rh_pc = min(max(rh_pc, 0.0), 100.0)
        return temp_c, rh_pc

if __name__ == '__main__':
    ctx = pyudev.Context()
    for hr in ctx.list_devices(subsystem=b'hidraw'):
        for m in matcher.matchers:
            with contextlib.ExitStack() as e:
                d = m.match(hr)
                if d is None:
                    continue
                e.push(contextlib.closing(d))
                print(d)
                print(d.hid_phys())
                print(d.read_version())
                print(d.read_sensor())
                print()
