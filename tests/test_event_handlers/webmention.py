"""Test Event Handler
"""

import requests

test_results = { 'inbound': None,
                 'outbound': None,
               }

def setup():
    pass

def inbound(sourceURL, targetURL):
    test_results['inbound'] = targetURL
    return targetURL

def outbound(sourceURL, targetURL):
    test_results['outbound'] = targetURL
