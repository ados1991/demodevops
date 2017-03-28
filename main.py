import copy
import ipaddress
from collections import ChainMap


class PingProtocolResponse:

    def __init__(self, *, response=None):
        self.response = response

    def __set__(self, instance, value):
        if isinstance(value, tuple):
            count, msg = value
        for _ in range(count):
            print(msg)

    def __get__(self, instance, owner):
        pass

    def __delete__(self, instance):
        pass


class PingProtocol:

    _MAP_MSG_DATAGRAM = {
        200: '{} replies with success',
        400: 'Bad request',
        404: 'host Unreachable',
        504: 'timeout no route found'
    }

    response = PingProtocolResponse()

    def ping(self, ip_destination, n=4):
        try:
            ipaddress.ip_address(ip_destination)
        except ValueError:
            self.response = (
                4,
                PingProtocol._make_datagram(400, ipd=ip_destination)
            )
            return
        # table arp search
        if len(self._arp_cache) == 0:
            self.response = (
                4,
                PingProtocol._make_datagram(504, ipd=ip_destination)
            )

    def _send(self, other):
        pass

    def _recv(self, other):
        if id(self) == id(other):
            # it is me
            pass

    @staticmethod
    def _make_datagram(code, *, ips=None, ipd=None):
        return PingProtocol._datagram_ip(
            ips, ipd, PingProtocol._datagram_msg(code, ipd)
        )

    @staticmethod
    def _datagram_ip(ip_source, ip_destination, msg):
        return "from {ips} to {ipd} : {msg}".format(
            ips=ip_source, ipd=ip_destination,
            msg=msg
        )

    @staticmethod
    def _datagram_msg(code, ip):
        if code == 200:
            return PingProtocol._MAP_MSG_DATAGRAM[code].format(ip)
        return "{}".format(PingProtocol._MAP_MSG_DATAGRAM[code])


class DeepChainMap(ChainMap):
    pass


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
        try:
            return self.__ip
        except AttributeError:
            return None

    @ip.setter
    def ip(self, value):
        try:
            self.__ip = ipaddress.ip_address(value)
        except ValueError:
            raise InterfaceError("{} must be IPv4 address".format(value)) from None

    @property
    def mask(self):
        try:
            return self.__mask
        except AttributeError:
            return None

    @mask.setter
    def mask(self, value):
        if not 1 <= int(value) <= 32:
            raise InterfaceError("{} must be number from 1 to 32".format(value))
        self.__mask = value

    @property
    def gateway(self):
        try:
            return self.__gateway
        except AttributeError:
            return None

    @gateway.setter
    def gateway(self, value):
        try:
            self.__gateway = ipaddress.ip_address(value)
        except ValueError:
            raise InterfaceError("{} must be IPv4 address".format(value)) from None


class Computer(PingProtocol):
    def __init__(self, name):
        self.name = name
        self._eths = DeepChainMap()
        self._routes = []

    def _set_routes(func):
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            if func.__name__ == "set_interface":
                self._routes.append(
                    # (metric, instance <interface>)
                    (len(self._eths.keys()), self._eths[args[0]]['eth'])
                )
            elif func.__name__ == "del_interface":
                for i, r in enumerate(self._routes):
                    if r[1]['eth'].name == args[0]:
                        del self._routes[i]

        return wrapper

    @_set_routes
    def set_interface(self, name, interface=None):
        if name in self._eths.keys():
            raise InterfaceError(
                "Interface {} already exists".format(name)
            )
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

    def __getattr__(self, item):
        if item == "_arp_cache":
            return self.map_arp()
        return getattr(self, item)

    def map_arp(self):
        return []

    def __str__(self):
        if len(self._eths) != 0:
            eths_str = []
            for e, v in self._eths.maps[0].items():
                eths_str.append("{}: {}/{}".format(v['eth'].name, v['eth'].ip, v['eth'].mask))
            return "<{}: {} eths: {}>".format(self.__class__.__name__, self.name, " - ".join(eths_str))
        return "<{}: {}>".format(self.__class__.__name__, self.name)


class Switch(PingProtocol):
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
        self.__ports = [None] + [
            Switch._Interface(Switch.LABEL_PORT_NAME + str(i)) for i in range(1, Switch.MAX_PORTS + 1)
        ]

    def connect(self, port_number, device, device_name_interface, force=False):
        if not 1 <= port_number <= Switch.MAX_PORTS:
            raise SwitchError("port_number {} must be from to 1 to {}".format(
                port_number, Switch.MAX_PORTS
            ))
        if not isinstance(device, (Computer,)):
            raise SwitchError("Unknown Type of device")
        if self.__ports[port_number].device is not None:
            if not force:
                raise SwitchError(
                    "{} has already connect to another device".format(self.__ports[port_number].port_name)
                )
        self.__ports[port_number].device = device
        self.__ports[port_number].port_number = port_number
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
p.set_interface('eth1')

sw = Switch()

sw.connect(1, p, 'eth0')

print(p)

p.ping("192.168.46.10")




