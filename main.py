import copy
import ipaddress
from collections import ChainMap


class DeepChainMap(ChainMap):

    def __setitem__(self, key, value):
        if key in self.maps[0]:
            self.maps[0][key + '/1'] = value
        self.maps[0][key] = value


class InterfaceError(Exception):
    pass


class SwitchError(Exception):
    pass


class Interface:
    def __init__(self, name=None, ip=None, mask=None, gateway=None):
        self.name = name
        if ip:
            self.ip = ip
        if mask:
            self.mask = mask
        if gateway:
            self.gateway = gateway

    @property
    def ip(self):
        return self.__ip

    @ip.setter
    def ip(self, value):
        try:
            self.__ip = ipaddress.ip_address(value)
        except ValueError:
            raise InterfaceError("{} must be IPv4 address".format(value)) from None

    @property
    def mask(self):
        return self.__mask

    @mask.setter
    def mask(self, value):
        if not 1 <= int(value) <= 32:
            raise InterfaceError("{} must be number from 1 to 32".format(value))
        self.__mask = value

    @property
    def gateway(self):
        return self.__gateway

    @gateway.setter
    def gateway(self, value):
        try:
            self.__gateway = ipaddress.ip_address(value)
        except ValueError:
            raise InterfaceError("{} must be IPv4 address".format(value)) from None


class Computer:
    def __init__(self, name):
        self.name = name
        self._eths = DeepChainMap()
        self._routes = []

    def _set_routes(func):
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            for k, v in self._eths['']
            if func.__name__ == "set_interface":
                for i, (_, eth) in enumerate(self._eths.maps[0].items(), start=1):
                    self._routes.append(
                        # (instance <interface>, metric)
                        (i, eth['eth'])
                    )
            elif func.__name__ == "del_interface":
                for i, r in enumerate(self._routes):
                    if r[1]['eth'].name == args[0]:
                        del self._routes[i]

        return wrapper

    @_set_routes
    def set_interface(self, name, interface=None):
        if interface is None:
            self._eths[name] = {
                'connect_to': None,
                'eth': Interface(name)
            }
        elif isinstance(interface, Interface):
            eth = copy.copy(interface)
            self._eths[name] = {
                'connect_to': None,
                'eth': eth
            }

    @_set_routes
    def del_interface(self, name):
        try:
            del self._eths[name]
        except KeyError:
            pass

    def connect_eth(self, name, connect_to=None):
        try:
            if connect_to:
                self._eths[name]['connect_to'] = connect_to
        except KeyError:
            pass

    def disconnect_eth(self, name):
        try:
            self._eths[name]['connect_to'] = None
        except KeyError:
            pass

    def map_arp(self):
        pass

    def __str__(self):
        if len(self._eths) != 0:
            eths_str = []
            for e, v in self._eths.maps[0].items():
                eths_str.append("{}: {}/{}".format(v.name, v.ip, v.mask))
            return "<{}: {} eths: {}>".format(self.__class__.__name__, self.name, " - ".join(eths_str))
        return "<{}: {}>".format(self.__class__.__name__, self.name)


class Switch:
    MAX_PORTS = 24
    LABEL_PORT_NAME = "GigaEthernet_"

    class _Interface:
        __slots__ = (
            'port_name',
            'port_number',
            'port_type',
            'device',
            'vlan_id',
            'eth_device'
        )

        def __init__(self, port_name):
            self.port_name = port_name
            (self.port_number, self.port_type, self.device, self.eth_device) = [None] * 4
            self.vlan_id = 1

    def __init__(self):
        self.__ports = [
            Switch._Interface(Switch.LABEL_PORT_NAME + '_' + str(i)) for i in range(1, Switch.MAX_PORTS + 1)
        ]

    def connect(self, port_number, device, device_name_interface, force=False):
        if not 1 <= port_number <= Switch.MAX_PORTS:
            raise SwitchError("port_number {} must be from to 1 to {}".format(
                port_number, Switch.MAX_PORTS
            ))
        if not isinstance(device, (Computer,)):
            raise SwitchError("Unknown Type of device")
        if self.__ports[port_number].device is None:
            self.__ports[port_number].device = device
            self.__ports[port_number].eth_device = device_name_interface
            device.connect_eth(device_name_interface, self)
        else:
            if not force:
                raise SwitchError(
                    "{} has already connect to another device".format(self.__ports[port_number].port_name)
                )
            self.__ports[port_number].device = device
            self.__ports[port_number].eth_device = device_name_interface
            device.connect_eth(device_name_interface, self)

    def disconnect(self, port_number):
        try:
            self.__ports[port_number].device.disconnect_eth(
                self.__ports[port_number].eth_device
            )
            self.__ports[port_number] = Switch._Interface(Switch.LABEL_PORT_NAME + '_' + str(port_number))
        except IndexError:
            pass


p = Computer("toto")

i = Interface()
i.ip = "192.168.10.10"
i.mask = "22"
i.gateway = "192.168.170.1"

p.set_interface('eth0', i)
p.set_interface('eth0')

sw = Switch()

sw.connect(1, p, 'eth0')




