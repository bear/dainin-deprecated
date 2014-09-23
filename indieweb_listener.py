#!/usr/bin/env python

"""
:copyright: (c) 2013-2014 by Mike Taylor
:license: MIT, see LICENSE for more details.

A simple Flask web service to handle inbound HTML
events that IndieWeb sites require.
"""

import os, sys
import json
import uuid
import urllib
import logging
import datetime

import redis
import requests
import ronkyuu
import ninka

from urlparse import urlparse, ParseResult
from mf2py.parser import Parser
from flask import Flask, request, redirect, render_template, session, flash

from flask.ext.wtf import Form
from wtforms import TextField, HiddenField, BooleanField
from wtforms.validators import Required


class LoginForm(Form):
    domain       = TextField('domain', validators = [ Required() ])
    client_id    = HiddenField('client_id')
    redirect_uri = HiddenField('redirect_uri')
    from_uri     = HiddenField('from_uri')

class NoteForm(Form):
    note = TextField('note', validators = [])

class TokenForm(Form):
    app_id     = TextField('app_id', validators = [ Required() ])
    invalidate = BooleanField('invalidate')
    app_token  = TextField('app_token')
    client_id  = HiddenField('client_id')

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


# check for uwsgi, use PWD if present or getcwd() if not
_uwsgi = __name__.startswith('uwsgi')
if _uwsgi:
    _ourPath    = os.getenv('PWD', None)
    _configFile = '/etc/indieweb_listener.cfg'
else:
    _ourPath    = os.getcwd()
    _configFile = os.path.join(_ourPath, 'indieweb_listener.cfg')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'foo'  # replaced downstream
cfg = None
db  = None
templateData = {}


@app.route('/login', methods=['GET', 'POST'])
def handleLogin():
    app.logger.info('handleLogin [%s]' % request.method)

    form = LoginForm(client_id=cfg['client_id'], 
                     redirect_uri='%s/success' % cfg['baseurl'], 
                     from_uri=request.args.get('from_uri'))

    if form.validate_on_submit():
        app.logger.info('login domain [%s]' % form.domain.data)
        domain = form.domain.data
        url    = urlparse(domain)
        if url.scheme not in ('http', 'https'):
            if len(url.netloc) == 0:
                domain = 'http://%s' % url.path
            else:
                domain = 'http://%s' % url.netloc

        authEndpoints = ninka.indieauth.discoverAuthEndpoints(domain)

        if 'authorization_endpoint' in authEndpoints:
            authURL = None
            for url in authEndpoints['authorization_endpoint']:
                authURL = url
                break

            if authURL is not None:
                url = ParseResult(authURL.scheme, 
                                  authURL.netloc,
                                  authURL.path,
                                  authURL.params,
                                  urllib.urlencode({ 'me':            domain,
                                                     'redirect_uri':  form.redirect_uri.data,
                                                     'client_id':     form.client_id.data,
                                                     'scope':         'post',
                                                     'response_type': 'id'
                                                   }),
                                  authURL.fragment).geturl()

                if db is not None:
                    db.hset(domain, 'from_uri',     form.from_uri.data)
                    db.hset(domain, 'redirect_uri', form.redirect_uri.data)
                    db.hset(domain, 'client_id',    form.client_id.data)
                    db.hset(domain, 'scope',        'post')
                    db.hdel(domain, 'code')  # clear any existing auth code
                    db.expire(domain, cfg['auth_timeout']) # expire in N minutes unless successful

                return redirect(url)
        else:
            return 'insert fancy no auth endpoint found error message here', 403

    templateData['title'] = 'Authenticate'
    templateData['form']  = form
    return render_template('login.jinja', **templateData)

@app.route('/success', methods=['GET',])
def handleLoginSuccess():
    app.logger.info('handleLoginSuccess [%s]' % request.method)
    me       = request.args.get('me')
    code     = request.args.get('code')
    scope    = None
    from_uri = None
    if db is not None:
        app.logger.info('getting data to validate auth code [%s]' % me)
        data = db.hgetall(me)
        if data:
            r = ninka.indieauth.validateAuthCode(code=code, 
                                                 client_id=data['client_id'],
                                                 redirect_uri=data['redirect_uri'])
            if 'response' in r:
                app.logger.info('login code verified')
                scope    = data['scope']
                from_uri = data['from_uri']
                token    = str(uuid.uuid4())
                db.hset(me, 'code', code)
                db.hset(me, 'token', token)
                db.expire(me, cfg['auth_timeout'])
                db.set('code-%s' % code, me)
                db.set('token-%s' % token, me)
                db.expire('code-%s' % code, cfg['auth_timeout'])

                session['indieauth_token'] = token
                session['indieauth_scope'] = scope
                session['indieauth_id']    = me
            else:
                app.logger.info('login invalid')
                db.delete(me)
                session.pop('indieauth_token', None)
                session.pop('indieauth_scope', None)
                session.pop('indieauth_id', None)
        else:
            app.logger.info('nothing found for domain [%s]' % me)

    if scope:
        if from_uri:
            return redirect(from_uri)
        else:
            return redirect('/')
    else:
        return 'authentication failed', 403

@app.route('/auth', methods=['GET',])
def handleAuth():
    app.logger.info('handleAuth [%s]' % request.method)
    result = False
    if db is not None:
        token = request.args.get('token')
        if token is not None:
            me = db.get('token-%s' % token)
            if me:
                data = db.hgetall(me)
                if data and data['token'] == token:
                    result = True
    if result:
        return 'valid', 200
    else:
        session.pop('indieauth_token', None)
        session.pop('indieauth_scope', None)
        session.pop('indieauth_id', None)
        return 'invalid', 403

@app.route('/note', methods=['GET', 'POST'])
def handleNote():
    app.logger.info('handleNote [%s]' % request.method)

    authed = False
    if 'indieauth_id' in session and 'indieauth_token' in session:
        indieauth_id    = session['indieauth_id']
        indieauth_token = session['indieauth_token']
        app.logger.info('session cookie found')
        if db is not None:
            me = db.get('token-%s' % indieauth_token)
            if me:
                data = db.hgetall(me)
                if data and data['token'] == indieauth_token:
                    authed = True
    else:
        app.logger.info('session cookie missing')

    form = NoteForm(note='')

    if request.method == 'POST':
        app.logger.info('note post')
        if form.validate():
            return 'do something with this new note (auth = %s)' % authed, 200
        else:
            flash('all fields are required')

    templateData['title']  = 'Leave a note'
    templateData['form']   = form
    templateData['authed'] = authed
    return render_template('note.jinja', **templateData)

@app.route('/token', methods=['GET', 'POST'])
def handleToken():
    app.logger.info('handleToken [%s]' % request.method)

    authed = False
    me     = None
    if 'indieauth_id' in session and 'indieauth_token' in session:
        indieauth_id    = session['indieauth_id']
        indieauth_token = session['indieauth_token']
        app.logger.info('session cookie found')
        if db is not None:
            me = db.get('token-%s' % indieauth_token)
            if me:
                app.logger.info('token found in store')
                data = db.hgetall(me)
                if data and data['token'] == indieauth_token:
                    authed = True
    else:
        app.logger.info('session cookie missing')

    app.logger.info('authed = %s' % authed)

    if authed:
        app_id        = request.args.get('app_id')
        app_token     = request.args.get('app_token')
        caption       = 'Update'
        token_present = True

        if app_id is None:
            app_id = ''
        if app_token is None:
            app_token = ''
            caption   = 'Generate'
            token_present = False

        form = TokenForm(client_id=indieauth_id, app_id=app_id, app_token=app_token)

        if request.method == 'POST':
            app.logger.info('token post')
            if form.validate():
                if len(form.app_token.data) > 0:
                    app.logger.info('app_token present')
                    if form.invalidate.data:
                        app.logger.info('app_token cleared')
                        db.delete('app-%s-%s' % (me, app_id))
                        return redirect('/token?%s' % urllib.urlencode({'app_id': app_id}))
                    else:
                        app_token = db.get('app-%s-%s' % (me, app_id))
                        if form.app_token.data != app_token:
                            app.logger.info('app_token updated')
                            app_token = form.app_token.data
                            db.set('app-%s-%s' % (me, app_id), app_token)
                        return redirect('/token?%s' % urllib.urlencode({'app_id': app_id, 'app_token': app_token}))
                else:
                    app_id    = form.app_id.data
                    app_token = db.get('app-%s-%s' % (me, app_id))
                    if app_token is None:
                        app_token = str(uuid.uuid4())
                        db.set('app-%s-%s' % (me, app_id), app_token)
                    return redirect('/token?%s' % urllib.urlencode({'app_id': app_id, 'app_token': app_token}))
            else:
                flash('all fields are required')

        templateData['title']         = 'App Token'
        templateData['form']          = form
        templateData['authed']        = authed
        templateData['caption']       = caption
        templateData['token_present'] = token_present
        return render_template('token.jinja', **templateData)
    else:
        return redirect('/')

def validURL(targetURL):
    """Validate the target URL exists by making a HEAD request for it
    """
    result = 404
    try:
        r = requests.head(targetURL)
        result = r.status_code
    except:
        result = 404
    return result

noteTemplate = """<span id="%(url)s"><p class="byline h-entry" role="note"> <a href="%(url)s">%(name)s</a> <time datetime="%(date)s">%(date)s</time></p></span>
%(marker)s
"""

def extractHCard(mf2Data):
    result = { 'name': '', 
               'url':  '',
             }
    if 'items' in mf2Data:
        for item in mf2Data['items']:
            if 'type' in item and 'h-card' in item['type']:
                result['name'] = item['properties']['name']
                if 'url' in item['properties']:
                    result['url'] = item['properties']['url']
    return result

def generateSafeName(sourceURL):
    urlData = urlparse(sourceURL)
    result  = '%s_%s.mention' % (urlData.netloc, urlData.path.replace('/', '_'))
    return result

def processWebmention(sourceURL, targetURL):
    h = open(os.path.join(cfg['logpath'], 'mentions.log'), 'w+')
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

        safeID     = generateSafeName(sourceURL)
        targetFile = os.path.join(cfg['basepath'], safeID)
        sData      = json.dumps(mentionData)
        if db is not None:
            db.set('mention::%s' % safeID, sData)
        open(targetFile, 'w').write(sData)

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
            processWebmention(sourceURL, targetURL)

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

        if valid == requests.codes.ok:
            mention(source, target)
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
    filename = os.path.abspath(configFilename)

    if os.path.exists(filename):
        result = json.load(open(filename, 'r'))
    else:
        result = {}

    if host is not None and 'host' not in result:
        result['host'] = host
    if port is not None and 'port' not in result:
        result['port'] = port
    if basepath is not None and 'basepath' not in result:
        result['basepath'] = basepath
    if logpath is not None and 'logpath' not in result:
        result['logpath'] = logpath
    if 'auth_timeout' not in result:
        result['auth_timeout'] = 300

    return result

def getRedis(cfgRedis):
    if 'host' not in cfgRedis:
        cfgRedis['host'] = '127.0.0.1'
    if 'port' not in cfgRedis:
        cfgRedis['port'] = 6379
    if 'db' not in cfgRedis:
        cfgRedis['db'] = 0

    return redis.StrictRedis(host=cfgRedis['host'], port=cfgRedis['port'], db=cfgRedis['db'])

# event = events.Events(config={ "handler_path": os.path.join(_ourPath, "handlers") })

def buildTemplateContext(config):
    result = {}
    for key in ('baseurl', 'title', 'meta'):
        if key in config:
            value = config[key]
        else:
            value = ''
        result[key] = value
    return result

def doStart(app, configFile, ourHost=None, ourPort=None, ourBasePath=None, ourPath=None, echo=False):
    _cfg = loadConfig(configFile, host=ourHost, port=ourPort, basepath=ourBasePath, logpath=ourPath)
    _db  = None
    if 'secret' in _cfg:
        app.config['SECRET_KEY'] = _cfg['secret']
    initLogging(app.logger, _cfg['logpath'], echo=echo)
    if 'redis' in _cfg:
        _db = getRedis(_cfg['redis'])
    return _cfg, _db

if _uwsgi:
    cfg, db = doStart(app, _configFile, _ourPath)
    templateData = buildTemplateContext(cfg)
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

    cfg, db = doStart(app, args.config, args.host, args.port, args.basepath, args.logpath, echo=True)
    templateData = buildTemplateContext(cfg)

    app.run(host=cfg['host'], port=cfg['port'], debug=True)
