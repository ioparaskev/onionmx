#!/usr/bin/env python

from collections import namedtuple
from os.path import dirname, abspath
from socket import error as SocketError
import argparse
import libs
import postfixrerouter
from olookup import OnionServiceLookup
from server import daemonize_server

root_folder = dirname(dirname(abspath(__file__)))
default_config_path = "{0}/config".format(root_folder)
default_mappings_path = "{0}/sources".format(root_folder)


class PostDNS(object):
    def __init__(self, config_path, map_path=None):
        self.config = libs.config_reader(libs.find_conffile(config_path,
                                                            prefix="postdns"))
        self.mappings_path = map_path
        self.rerouters = namedtuple('rerouters', ('lazy', 'onion'))

    @property
    def myname(self):
        return self.config.get("DOMAIN", "hostname")

    @staticmethod
    def get_domain(name):
        return name.split("@")[1]

    def configure(self):
        onion_resolver = OnionServiceLookup(self.config)
        self.rerouters.lazy = postfixrerouter.LazyPostfixRerouter(
            self.config, self.mappings_path)
        self.rerouters.onion = postfixrerouter.OnionPostfixRerouter(
            self.config, onion_resolver)

    def _reroute(self, domain):
        if self.myname == domain:
            return tuple(["200 :"])
        else:
            return (self.rerouters.lazy.reroute(domain)
                    or self.rerouters.onion.reroute(domain))

    def run(self, address):
        try:
            domain = self.get_domain(address)
        except IndexError:
            return "500 Domain not found"
        routing = self._reroute(domain)
        return "\n".join(routing) if routing else "500 Not found"

def main():
    parser = argparse.ArgumentParser(description='PostDNS daemon for '
                                                 'postifx rerouting')
    parser.add_argument('--simple', '-s', default=False, action='store_true',
                        help='Simple test route mode no daemon)')
    parser.add_argument('--config', '-c', default=default_config_path,
                        help='Absolute path to config folder', type=str)
    parser.add_argument('--mappings', '-m', default=default_mappings_path,
                        help='Absolute path to static mappings', type=str)
    parser.add_argument('--host', '-lh', default="127.0.0.1",
                        help="Host for daemon to listen", type=str)
    parser.add_argument('--port', '-p', help="Port for daemon to listen",
                        default=2026, type=int)
    args = parser.parse_args()
    try:
        postdns = PostDNS(config_path=args.config, map_path=args.mappings)
        postdns.configure()
        if not args.simple:
            daemonize_server(postdns, args.host, args.port)
        else:
            addr = libs.cross_input("")
            if addr == 'get *':
                print("500 request key is not an email address")
            print(postdns.run(addr))
    except (libs.ConfigNotFoundError, SocketError) as err:
        print(err)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
