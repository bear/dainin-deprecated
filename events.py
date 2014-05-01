#!/usr/bin/env python

"""
:copyright: (c) 2013 by Mike Taylor and Kartik Prabhu
:license: MIT, see LICENSE for more details.

"""

import os
import sys
import imp
import json


class Events(object):

    def __init__(self, config):
        self.handlers = {}
        self.config   = config

        self.loadHandlers()

    def loadHandlers(self):
        if 'handler_path' in self.config:
            handlerPath = os.path.abspath(
                os.path.expanduser(self.config['handler_path']))

            for (dirpath, dirnames, filenames) in os.walk(handlerPath):
                for filename in filenames:
                    moduleName, moduleExt = os.path.splitext(os.path.basename(filename))
                    if moduleExt == '.py':
                        module = imp.load_source(moduleName, os.path.join(handlerPath, filename))
                        if hasattr(module, 'setup'):
                            self.handlers[moduleName.lower()] = module

    def handle(self, eventClass, eventName, *args):
        eventClass = eventClass.lower()
        if eventClass in self.handlers:
            module = self.handlers[eventClass]
            try:
                if hasattr(module, eventName):
                    getattr(module, eventName)(*args)
            except Exception, e:
                raise Exception('error during call %s.%s(%s)' % (eventClass, eventName, ','.join(args)))
