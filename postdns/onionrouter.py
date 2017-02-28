#!/usr/bin/env python
from __future__ import absolute_import, print_function
import argparse
from collections import namedtuple
from socket import error as socket_error
from functools import partial
import postdns.libs as libs
import postdns.routers as routers
from postdns.lookups import OnionServiceLookup
from postdns.sockets import daemonize_server, client, resolve

default_config_path = "/etc/onionrouter/"
default_mappings_path = "/etc/onionrouter/mappings"


class PostDNS(object):
    ref_config = ("{0}/onionrouter.ini".format(default_config_path))

    def __init__(self, config_path, map_path=None):
        self.config = None
        self.config_file = libs.get_conffile(config_path,
                                             prefix="onionrouter")
        self.mappings_path = map_path
        self.rerouters = namedtuple('rerouters', ('lazy', 'onion'))

    @property
    def myname(self):
        return self.config.get("DOMAIN", "hostname")

    @staticmethod
    def get_domain(name):
        return name.split("@")[1]

    def configure(self):
        libs.ConfigIntegrityChecker(ref_config=self.ref_config,
                                    other_config=self.config_file).verify()
        self.config = libs.config_reader(self.config_file)
        onion_resolver = OnionServiceLookup(self.config)
        self.rerouters.lazy = routers.LazyPostfixRerouter(
            self.config, self.mappings_path)
        self.rerouters.onion = routers.OnionPostfixRerouter(
            self.config, onion_resolver)

    def _reroute(self, domain):
        if self.myname == domain:
            return tuple(["200 :"])
        else:
            return (self.rerouters.lazy.reroute(domain)
                    or self.rerouters.onion.reroute(domain))

    def run(self, address):
        if not self.config:
            self.configure()
        try:
            domain = self.get_domain(address)
        except IndexError:
            return "500 Request key is not an email address"
        routing = self._reroute(domain)
        # in the end, there can be only one response
        return routing[0] if routing else "500 Not found"


def add_arguments():
    parser = argparse.ArgumentParser(
        description='PostDNS daemon for postifx rerouting')
    parser.add_argument('--interactive', '-i', default=False,
                        action='store_true',
                        help='Simple test route mode without daemon')
    parser.add_argument('--debug', '-d', default=False, action='store_true',
                        help='Run daemon and also print the '
                             'queries & replies'),
    parser.add_argument('--client', '-c', default=False, action='store_true',
                        help='Connect as a client to daemon for debug')
    parser.add_argument('--config', default=default_config_path,
                        help='Absolute path to config folder/file '
                             '(default: %(default)s)', type=str)
    parser.add_argument('--mappings', default=default_mappings_path,
                        help='Absolute path to static mappings folder/file '
                             '(default: %(default)s)', type=str)
    parser.add_argument('--host', '-l', default="127.0.0.1",
                        help="Host for daemon to listen "
                             "(default: %(default)s)", type=str)
    parser.add_argument('--port', '-p', default=23000, type=int,
                        help="Port for daemon to listen "
                             "(default: %(default)s)")
    return parser


def interactive_reroute(postdns):
    while True:
        addr = libs.cross_input("Enter an email address: ")
        if addr == 'get *':
            print("500 Request key is not an email address")
        else:
            print(postdns.run(addr))


def reroute_debugger(question, answer):
    print("[Q]: {q}\n"
          "[A]: {a}".format(q=question, a=answer))


def craft_resolver(callback):
    return partial(resolve, resolve_callback=callback)


def main():
    args = add_arguments().parse_args()
    try:
        postdns = PostDNS(config_path=args.config, map_path=args.mappings)
        if args.interactive:
            interactive_reroute(postdns)

        if args.client:
            client(args.host, args.port)
        else:
            resolver = craft_resolver(reroute_debugger
                                      if args.debug else lambda *args:args)
            daemonize_server(postdns, args.host, args.port, resolver=resolver)
    except (libs.ConfigError, socket_error) as err:
        print(err)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
