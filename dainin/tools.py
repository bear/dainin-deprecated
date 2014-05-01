#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
:copyright: (c) 2014 by Mike Taylor
:license: MIT, see LICENSE for more details.

"""

import os, sys
import json
import redis


def normalizeFilename(filename):
    result = os.path.expanduser(filename)
    result = os.path.abspath(result)
    return result

def loadConfig(cfgFilename):
    result = {}
    if not os.path.exists(cfgFilename):
        for cfgpath in configPaths:
            possibleFile = normalizeFilename(os.path.join(cfgpath, configName))
            if os.path.exists(possibleFile):
                result = json.load(open(possibleFile, 'r'))
                break
    else:
        possibleFile = normalizeFilename(cfgFilename)
        if os.path.exists(possibleFile):
            result = json.load(open(possibleFile, 'r'))
    return result

def getRedis(config):
    if 'redis' in config:
        cfg = config['redis']
    else:
        cfg = config
    host     = cfg.get('host', '127.0.0.1')
    port     = cfg.get('port', 6379)
    database = cfg.get('db',   0)

    return redis.StrictRedis(host=host, port=port, db=database)
