import sys
import os
from collections import namedtuple
from yaml import load
try:
    import ConfigParser as configparser
except ImportError:
    import configparser


class ConfigNotFoundError(Exception):
    pass


def cross_input(text):
    """
    Returns the correct input function callback to be used for python 3.x
    and python 2.x
    """
    if sys.version_info[0] < 3:
        return raw_input(text)
    return input(text)


def config_reader(conf_path):
    """
    Reads a conf file and returns the onfigParser object
    """
    config = configparser.ConfigParser()
    config.read(conf_path)
    return config


def find_conffile(conf_path, prefix='', suffix=".ini"):
    """
    Checks if a local configuration file has been created and is not empty
    and returns it, otherwise it checks if a default configuration exists and
    is not empty
    If none of the two exists, it raises an Exception
    """
    conf_params = (conf_path, prefix, suffix)
    confs = ("{0}/{1}.local{2}".format(*conf_params),
             "{0}/{1}{2}".format(*conf_params))
    for conffile in confs:
        if os.path.exists(conffile):
            if os.stat(conffile).st_size:
                return conffile

    raise ConfigNotFoundError('No configuration file found in {0}'
                              .format(conf_path))


def yaml_loader(yaml_path):
    if os.path.exists(yaml_path):
        folder_structure = namedtuple('fst', ('dir', 'folders', 'files'))
        structure = folder_structure(*tuple(os.walk(yaml_path))[0])
        for filename in structure.files:
            with open("{0}/{1}".format(yaml_path, filename), 'r') as f:
                yield f


def load_yamls(yaml_path):
    yaml_mapping = dict()
    for f in yaml_loader(yaml_path):
        yaml_mapping.update(load(f))
    return yaml_mapping
