#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
:copyright: (c) 2014 by Mike Taylor
:license: MIT, see LICENSE for more details.

"""

import os, sys
import time
import socket
import logging
import platform

from multiprocessing import Process, current_process
from tools import loadConfig, getRedis

import sleekxmpp
from sleekxmpp.componentxmpp import ComponentXMPP


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(_ourName)

#
# configuration example
#
{
  "redis": { "host": "127.0.0.1",
             "port": 6379,
             "db":   0
           },
  "xmpp":  { "jid": ""
           }
}


class Dainin(object):
    def __init__(self, cfgFilename):
        self.config  = loadConfig(cfgFilename)

    def start(self):
        for item in mCfg['active']:
            log.info('starting worker for %s' % item)
            worker = Process(name=item, target=handleMetric, args=(config, item)).start()
            self.workers.append(worker)


class DaininXMPP(object):
    def __init__(self, cfgFilename):
        self.config  = loadConfig(cfgFilename)

    def start(self):
        for item in mCfg['active']:
            log.info('starting worker for %s' % item)
            worker = Process(name=item, target=handleMetric, args=(config, item)).start()
            self.workers.append(worker)
