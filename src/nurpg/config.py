import os
import json
import uuid
import shutil

import nurpg.error as error


_NDS_DIR = '.nds'
_NDS_CFG_FILE = '{}/config'.format(_NDS_DIR)
_NDS_STASH_DIR = '{}/stash'.format(_NDS_DIR)


class ConfigurationError(error.ErrorMessage):
    pass


class Configuration(object):

    _DOCUMENT_FILE = 'document_file'
    _STASH_DIR = 'stash_dir'
    _STASH_STACK = 'stash_stack'

    def __init__(self, document_file=None, stash_dir=_NDS_STASH_DIR, stash_stack=None):
        self.document_file = document_file
        self.stash_dir = stash_dir
        self.stash_stack = stash_stack or list()

    @classmethod
    def from_dict(cls, source_dict):
        return Configuration(
            document_file=source_dict[Configuration._DOCUMENT_FILE],
            stash_dir=source_dict[Configuration._STASH_DIR],
            stash_stack=source_dict[Configuration._STASH_STACK],
        )

    @classmethod
    def from_json(cls, source_str):
        return Configuration.from_dict(json.loads(source_str))

    def push_onto_stash(self, stash_file):
        self.stash_stack.append(stash_file)

    def pop_from_stash(self):
        return self.stash_stack.pop() if len(self.stash_stack) > 0 else None

    def to_dict(self):
        return {
            Configuration._DOCUMENT_FILE: self.document_file,
            Configuration._STASH_DIR: self.stash_dir,
            Configuration._STASH_STACK: self.stash_stack
        }

    def to_json(self):
        return json.dumps(self.to_dict())


def check_nds_dir():
    if not os.path.isdir(_NDS_DIR):
        os.makedirs(_NDS_DIR)


def check_stash_dir():
    if not os.path.isdir(_NDS_STASH_DIR):
        os.makedirs(_NDS_STASH_DIR)


def cfg_exists():
    # Check for important directories
    check_nds_dir()
    check_stash_dir()

    # Return whether or not there's a configuration initialized
    return os.path.exists(_NDS_CFG_FILE)


def init_config(document_file):
    if cfg_exists():
        raise ConfigurationError('Cowardly refusing to reinit over a '
                                 'pre-existing NDS configuration')

    write_config(Configuration(document_file=document_file))


def read_config():
    if not cfg_exists():
        raise ConfigurationError('A valid NDS configuration was not found. '
                                 'Please run init first.')

    with open(_NDS_CFG_FILE, 'r') as fin:
        return Configuration.from_json(fin.read())


def write_config(cfg):
    with open(_NDS_CFG_FILE, 'w') as fout:
        fout.write(cfg.to_json())


def stash_push(document_file):
    stash_id = str(uuid.uuid4())
    cfg = read_config()

    # Copy the file, then push it onto our stash stack
    shutil.copyfile(document_file, os.path.join(cfg.stash_dir, stash_id))
    cfg.push_onto_stash(stash_id)

    # Write the updated configuration
    write_config(cfg)

    # Return the stash id
    return stash_id


def stash_pop():
    cfg = read_config()

    path = None
    stashed_file = cfg.pop_from_stash()

    if stashed_file is not None:
        # Write the updated configuration and return the stashed file
        write_config(cfg)
        path = os.path.join(_NDS_STASH_DIR, stashed_file)

    return path
