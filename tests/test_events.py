#!/usr/bin/env python

import os, sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from events import Events


post_url     = "https://bear.im/bearlog/2013/325/indiewebify-and-the-new-site.html"
tantek_url   = "http://tantek.com/2013/322/b1/homebrew-computer-club-reunion-inspiration"
event_config = { "handler_path": "./tests/test_event_handlers",
                    
               }

class TestEventConfig(unittest.TestCase):
    def runTest(self):
        event = Events(config=event_config)

        assert event is not None
        assert len(event.handlers) > 0
        assert 'webmention' in event.handlers
        assert 'article' in event.handlers

class TestEventHandlerCalls(unittest.TestCase):
    def runTest(self):
        event = Events(config=event_config)

        event.handle('webmention', 'inbound', tantek_url, post_url)
        assert event.handlers['webmention'].test_results['inbound'] == post_url

        event.handle('webmention', 'outbound', tantek_url, post_url)
        assert event.handlers['webmention'].test_results['outbound'] == post_url

        event.handle('article', 'post', post_url)
        assert event.handlers['article'].test_results['post'] == post_url
