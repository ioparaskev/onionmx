import sys
import os
from collections import namedtuple
from yaml import load
try:
    import ConfigParser as configparser
except ImportError:
    import configparser


class ConfigError(Exception):
    pass


class ConfigNotFoundError(ConfigError):
    pass


class ConfigIntegrityError(ConfigError):
    pass


class ConfigIntegrityChecker(object):
    def __init__(self, ref_config, other_config):
        self._ref_reader = config_reader(ref_config)
        self._oth_reader = config_reader(other_config)
        self.ref_config = ref_config
        self.other_config = other_config

    def _verify_sections(self):
        if set(self._ref_reader.sections()).difference(
                set(self._oth_reader.sections())):
            raise RuntimeError

    def _verify_options(self):
        for section in self._ref_reader.sections():
            if set(self._ref_reader.options(section)).difference(
                    set(self._oth_reader.options(section))):
                raise RuntimeError

    def verify(self):
        try:
            self._verify_sections()
            self._verify_options()
        except RuntimeError:
            raise ConfigIntegrityError(
                "{loc} does not match the reference config file {ref}\n"
                "Is your local config up to date?".format(
                    loc=self.other_config, ref=self.ref_config))


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


def get_full_path_files_for_dir(directory_path):
    """
    List all filepaths in a dir recursively
    """
    return {os.path.join(dirpath, fname)
            for dirpath, dirnames, filenames in tuple(os.walk(directory_path))
            for fname in filenames}


def find_file(directory_path, filename):
    """
    Find filename in a dir recursively
    """
    return next((x for x in get_full_path_files_for_dir(directory_path)
                 if filename == os.path.split(x)[-1]), None)


def get_conffile(conf_path, prefix='', suffix=".ini"):
    """
    Finds conf file in `conf_path`
    If `conf_path` is file, returns `conf_path`
    Else it searches to find a file with `prefix``suffix` format
    """
    if os.path.isfile(conf_path):
        return conf_path

    found_file = find_file(conf_path, "{0}{1}".format(prefix, suffix))
    if not found_file:
        raise ConfigNotFoundError('No configuration file found in {0}'
                                  .format(conf_path))
    return found_file


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
