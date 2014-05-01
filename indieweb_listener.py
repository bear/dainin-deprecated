#!/usr/bin/env python

"""
:copyright: (c) 2013 by Mike Taylor
:license: MIT, see LICENSE for more details.

A simple Flask web service to handle inbound HTML POST
events that IndieWeb Webmention's require.
"""

import os, sys
import requests
import logging
import datetime
import ronkyuu
import events

from urlparse import urlparse
from mf2py.parser import Parser
from flask import Flask, request


# check for uwsgi, use PWD if present or getcwd() if not
_uwsgi = __name__.startswith('uwsgi')
if _uwsgi:
    _ourPath    = os.getenv('PWD', None)
    _configFile = '/etc/indieweb_listener.cfg'
else:
    _ourPath    = os.getcwd()
    _configFile = os.path.join(_ourPath, 'indieweb_listener.cfg')

app = Flask(__name__)
cfg = None


def validURL(targetURL):
    """Validate the target URL exists by making a HEAD request for it
    """
    r = requests.head(targetURL)
    return r.status_code == requests.codes.ok

noteTemplate = """<span id="%(url)s"><p class="byline h-entry" role="note"> <a href="%(url)s">%(name)s</a> <time datetime="%(date)s">%(date)s</time></p></span>
%(marker)s
"""

def extractHCard(mf2Data):
    result = { 'name': '', 
               'url':  '',
             }
    if 'items' in mf2Data:
        for item in p['items']:
            if 'type' in item and 'h-card' in item['type']:
                hcard['name'] = item['properties']['name']
                if 'url' in item['properties']:
                    hcard['url'] = item['properties']['url']
    return result

def generateSafeName(sourceURL):
    urlData = urlparse(sourceURL)
    result  = '%s_%s.mention' % (urlData.netloc, urlData.path.replace('/', '_')
    result  = os.path.join(cfg['basepath'], result)
    return result

def processWebmention(sourceURL, targetURL):
    h = open(os.path.join(cfg['logpath'], 'mentions.log', 'w+')
    h.write('target=%s source=%s' % (targetURL, sourceURL))
    h.close()

    r = requests.get(sourceURL, verify=False)
    if r.status_code == requests.codes.ok:
        mentionData = { 'url':       sourceURL,
                        'targetURL': targetURL,
                        'recvDate':  datetime.date.today().strftime('%d %b %Y %H:%M')
                      }
        if 'charset' in r.headers.get('content-type', ''):
            mentionData['content'] = r.text
        else:
            mentionData['content'] = r.content

        mf2Data = Parser(doc=mentionData['content']).to_dict()
        hcard   = extractHCard(mf2Data)

        mentionData['hcardName'] = hcard['name']
        mentionData['hcardURL']  = hcard['url']
        mentionData['mf2data']   = mf2Data

        targetFile = generateSafeName(sourceURL)

        open(targetFile, 'w').write(json.dumps(mentionData))

def mention(sourceURL, targetURL):
    """Process the Webmention of the targetURL from the sourceURL.

    To verify that the sourceURL has indeed referenced our targetURL
    we run findMentions() at it and scan the resulting href list.
    """
    app.logger.info('discovering Webmention endpoint for %s' % sourceURL)

    mentions = ronkyuu.findMentions(sourceURL)

    for href in mentions['refs']:
        if href != sourceURL and href == targetURL:
            app.logger.info('post at %s was referenced by %s' % (targetURL, sourceURL))

            # event.inboundWebmention(sourceURL, targetURL, mentions=mentions)
            processWebmention(sourceUrl, targetURL)

@app.route('/webmention', methods=['POST'])
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

def loadConfig(configFilename, host=None, port=None, basepath=None, logpath=None):
    if os.path.exists(configFilename):
        result = json.load(open(configFilename, 'r'))
    else:
        result = {}

    if host is not None:
        result['host'] = host
    if port is not None:
        result['port'] = port
    if basepath is not None:
        result['basepath'] = basepath
    if logpath is not None:
        result['logpath'] = logpath

    return result

# event = events.Events(config={ "handler_path": os.path.join(_ourPath, "handlers") })

if _uwsgi:
    cfg = loadConfig(_configFile, logpath=_ourPath)
    initLogging(app.logger, cfg['logpath'])


#
# None of the below will be run for nginx + uwsgi
#
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--host',     default='0.0.0.0')
    parser.add_argument('--port',     default=5000, type=int)
    parser.add_argument('--logpath',  default='/srv/webmention')
    parser.add_argument('--basepath', default='/opt/bearlog/')
    parser.add_argument('--config',   default='/etc/indieweb_listener.cfg')

    args = parser.parse_args()

    cfg = loadConfig(args.config, args.host, args.port, args.basepath, args.logpath)

    initLogging(app.logger, cfg['logpath'], echo=True)

    app.run(host=cfg['host'], port=cfg['port'])
