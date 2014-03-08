#!/usr/bin/env python

"""
:copyright: (c) 2013 by Mike Taylor
:license: MIT, see LICENSE for more details.

A simple Flask web service that handles those inbound IndieWeb
items that require HTML POSTs:

  webmention
"""

import os, sys
import requests
import logging
import ronkyuu

from flask import Flask, request

# check for uwsgi, use PWD if present or getcwd() if not
_uwsgi = __name__.startswith('uwsgi')
if _uwsgi:
    _ourPath = os.getenv('PWD', None)
else:
    _ourPath = os.getcwd()

app = Flask(__name__)

def validURL(targetURL):
    """Validate the target URL exists by making a HEAD request for it
    """
    r = requests.head(targetURL)
    return r.status_code == requests.codes.ok

def mention(sourceURL, targetURL):
    """Process the Webmention of the targetURL from the sourceURL.

    To verify that the sourceURL has indeed referenced our targetURL
    we run findMentions() at it and scan the resulting href list.
    """
    app.logger.info('discovering Webmention endpoint for %s' % sourceURL)

    mentions = ronkyuu.findMentions(sourceURL)

    for href in mentions['refs']:
        if href <> sourceURL and href == targetURL:
            app.logger.info('post at %s was referenced by %s' % (targetURL, sourceURL))
            events.inboundWebmention(sourceURL, targetURL, mentions=mentions)

@app.route('/webmention', methods=['GET', 'POST'])
def handleWebmention():
    app.logger.info('handleWebmention [%s]' % request.method)
    if request.method == 'POST':
        valid  = False
        source = None
        target = None

        if 'source' in request.form:
            source = request.form['source']
        if 'target' in request.form:
            target = request.form['target']

        valid = validURL(target)

        app.logger.info('source: %s target: %s valid? %s' % (source, target, valid))

        if valid:
            mention(source, target)

        if valid:
            return 'done'
        else:
            return 'invalid post', 404
    else:
        s = ''
        for k in os.environ.keys():
            s += '%s = %s<br/>' % (k, os.environ[k])
        return '[%s] [%s]<br/>%s' % (os.getcwd(), __name__, s), 200

def initLogging(logger, logpath=None, echo=False):
    logFormatter = logging.Formatter("%(asctime)s %(levelname)-9s %(message)s", "%Y-%m-%d %H:%M:%S")

    if logpath is not None:
        from logging.handlers import RotatingFileHandler

        logfilename = os.path.join(logpath, 'webmentions.log')
        logHandler  = logging.handlers.RotatingFileHandler(logfilename, maxBytes=1024 * 1024 * 100, backupCount=7)
        logHandler.setFormatter(logFormatter)
        logger.addHandler(logHandler)

    if echo:
        echoHandler = logging.StreamHandler()
        echoHandler.setFormatter(logFormatter)
        logger.addHandler(echoHandler)

    logger.setLevel(logging.INFO)
    logger.info('starting Webmention App')


if _uwsgi:
    initLogging(app.logger, _ourPath)

events = ronkyuu.Events(config={ "handler_path": "/srv/webmention/handlers" })


#
# None of the below will be run for nginx + uwsgi
#
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--host',    default='0.0.0.0')
    parser.add_argument('--port',    default=5000, type=int)
    parser.add_argument('--logpath', default=None)

    args = parser.parse_args()

    initLogging(app.logger, args.logpath, echo=True)

    app.run(host=args.host, port=args.port)
