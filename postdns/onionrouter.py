#!/usr/bin/env python

import argparse
from collections import namedtuple
from socket import error as SocketError
from os.path import dirname, abspath
import libs
import routers
from lookups import OnionServiceLookup
from server import daemonize_server

root_folder = dirname(dirname(abspath(__file__)))
default_config_path = "{0}/config".format(root_folder)
default_mappings_path = "{0}/sources".format(root_folder)


class PostDNS(object):
    ref_config = ("{0}/config/onionrouter.ini"
                  .format(dirname(dirname(abspath(__file__)))))

    def __init__(self, config_path, map_path=None):
        self.config = None
        self.config_file = libs.find_conffile(config_path,
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
    parser = argparse.ArgumentParser(description='PostDNS daemon for '
                                                 'postifx rerouting')
    parser.add_argument('--interactive', '-i', default=False,
                        action='store_true',
                        help='Simple test route mode no daemon')
    parser.add_argument('--config', '-c', default=default_config_path,
                        help='Absolute path to config folder', type=str)
    parser.add_argument('--mappings', '-m', default=default_mappings_path,
                        help='Absolute path to static mappings folder',
                        type=str)
    parser.add_argument('--host', '-lh', default="127.0.0.1",
                        help="Host for daemon to listen", type=str)
    parser.add_argument('--port', '-p', help="Port for daemon to listen",
                        default=23000, type=int)
    return parser


def main():
    args = add_arguments().parse_args()
    try:
        postdns = PostDNS(config_path=args.config, map_path=args.mappings)
        if not args.interactive:
            daemonize_server(postdns, args.host, args.port)
        else:
            addr = libs.cross_input("Enter an email address: ")
            if addr == 'get *':
                print("500 Request key is not an email address")
            print(postdns.run(addr))
    except (libs.ConfigError, SocketError) as err:
        print(err)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
