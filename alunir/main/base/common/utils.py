# -*- coding: utf-8 -*-
import json
import os.path
import time

from functools import wraps
from xross_common.SystemLogger import SystemLogger


class Dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class ReloadableJsondict(Dotdict):
    logger, test_handler = SystemLogger("ReloadableJsondict").get_logger()

    def __init__(self, jsonfile, default_value={}):
        super().__init__()
        self.reloaded = False
        self.mtime = 0
        self.path = os.path.normpath(os.getcwd() + jsonfile)
        self.update(default_value)
        self.reload()

    def reload(self):
        try:
            mtime = os.path.getmtime(self.path)
            if mtime > self.mtime:
                json_dict = json.load(open(self.path, 'r'), object_hook=Dotdict)
                self.update(json_dict)
                self.mtime = mtime
                self.reloaded = True
        except Exception as e:
            self.logger.warning(type(e).__name__ + ": %s where %s" % (e, self.path))
            raise e
        return self


def stop_watch(func):
    @wraps(func)
    def wrapper(*args, **kargs):
        start = time.time()
        result = func(*args, **kargs)
        process_time =  (time.time() - start)
        units = 's'
        if process_time < 1:
            process_time *= 1000
            units = 'ms'
        if process_time < 1:
            process_time *= 1000
            units = 'us'
        print("Processing time for {0}:{1:.3f}{2}".format(func.__name__, process_time, units))
        return result
    return wrapper
