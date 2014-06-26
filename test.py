
import datetime
import requests
# import pprint

from mf2py.parser import Parser

# pp = pprint.PrettyPrinter(indent=2)

sourceURL = 'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/'

r = requests.get(sourceURL, verify=False)
print r.status_code
if r.status_code == requests.codes.ok:
    d = { 'url':  sourceURL,
          'date': datetime.date.today().strftime('%d %b %Y %H:%M')
        }
    if 'charset' in r.headers.get('content-type', ''):
        d['content'] = r.text
    else:
        d['content'] = r.content

    p = Parser(doc=d['content']).to_dict()

    if 'items' in p:
        for item in p['items']:
            if 'type' in item and 'h-card' in item['type']:
                d['name'] = item['properties']['name']
                if 'url' in item['properties']:
                    d['hcard_url'] = item['properties']['url']
                else:
                    d['hcard_url'] = ''

#     pp.pprint(p.to_dict())

# { 'alternates': [ { 'type': u'application/rss+xml',
#                     'url': u'http://silencematters.com/feed/'},
#                   { 'type': u'application/rss+xml',
#                     'url': u'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/feed/'}],
#   'items': [ { 'properties': { 'name': [u'Jeremy Zilar'],
#                                u'photo': [ u'http://silencematters.com/blog/wp-content/themes/silencematters/img/JeremyZilar2013.png'],
#                                'url': [u'http://silencematters.com/']},
#                'type': [u'h-card']},
#              { 'properties': { u'like-of': [ u'http://tiny.n9n.us/2014/04/25/video-embed-test/'],
#                                'name': [u'\u2026\n i like this'],
#                                'url': [ u'http://tiny.n9n.us/2014/04/25/video-embed-test/']},
#                'type': [u'h-entry']}],
#   'rels': { u'EditURI': [u'http://silencematters.com/blog/xmlrpc.php?rsd'],
#             u'author': [u'http://silencematters.com'],
#             u'bookmark': [ u'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/'],
#             u'canonical': [ u'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/'],
#             u'external': [ u'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/',
#                            u'http://david.shanske.com',
#                            u'http://david.shanske.com',
#                            u'http://david.shanske.com',
#                            u'http://becausetherefore.com/2014/04/xoxo/',
#                            u'http://becausetherefore.com/2014/04/xoxo/'],
#             u'home': [ u'http://silencematters.com/',
#                        u'http://silencematters.com/',
#                        u'http://silencematters.com/'],
#             u'http://webmention.org/': [ u'http://silencematters.com/blog/?webmention=endpoint'],
#             u'in-reply-to': [ u'http://tiny.n9n.us/2014/04/25/video-embed-test/',
#                               u'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/'],
#             u'me': [ u'https://twitter.com/jeremyzilar',
#                      u'http://jeremyzilar.com#work',
#                      u'http://silencematters.com',
#                      u'http://jeremyzilar.com#about',
#                      u'http://www.flickr.com/photos/silencematters/',
#                      u'https://twitter.com/jeremyzilar',
#                      u'http://www.facebook.com/jeremy.zilar',
#                      u'http://instagram.com/jeremyz'],
#             u'nofollow': [ u'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/',
#                            u'http://indiewebcamp.com/webmentions',
#                            u'https://github.com/indieweb/wordpress-indieweb',
#                            u'https://github.com/pfefferle/wordpress-webmention-form',
#                            u'https://github.com/pfefferle/wordpress-webmention',
#                            u'https://github.com/barnabywalters/web-action-hero-toolbelt/',
#                            u'http://tiny.n9n.us/2014/04/25/video-embed-test/',
#                            u'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/',
#                            u'http://tiny.n9n.us/2014/04/25/video-embed-test/',
#                            u'http://david.shanske.com',
#                            u'http://silencematters.com/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/',
#                            u'http://david.shanske.com',
#                            u'http://david.shanske.com',
#                            u'http://becausetherefore.com/2014/04/xoxo/',
#                            u'http://becausetherefore.com/2014/04/xoxo/',
#                            u'/2014/04/26/indiewebcamp-nyc-setting-up-webmentions-on-wordpress/#respond'],
#             u'pingback': [u'http://silencematters.com/blog/xmlrpc.php'],
#             u'prev': [u'http://silencematters.com/2014/04/25/958/'],
#             u'profile': [u'http://gmpg.org/xfn/11'],
#             u'shortlink': [u'http://wp.me/p5Wuc-fz'],
#             u'stylesheet': [ u'http://silencematters.com/blog/wp-content/plugins/jetpack/modules/subscriptions/subscriptions.css?ver=3.9',
#                              u'http://silencematters.com/blog/wp-content/plugins/jetpack/modules/widgets/widgets.css?ver=20121003',
#                              u'http://silencematters.com/blog/wp-includes/js/mediaelement/mediaelementplayer.min.css?ver=2.13.0',
#                              u'http://silencematters.com/blog/wp-includes/js/mediaelement/wp-mediaelement.css?ver=3.9',
#                              u'http://silencematters.com/blog/wp-content/themes/silencematters/css/bootstrap.min.css?ver=jz108',
#                              u'http://silencematters.com/blog/wp-content/themes/silencematters/css/openwebicons-bootstrap.css?ver=jz108',
#                              u'http://silencematters.com/blog/wp-content/themes/silencematters/style.css?ver=jz108'],
#             u'webmention': [ u'http://silencematters.com/blog/?webmention=endpoint'],
#             u'wlwmanifest': [ u'http://silencematters.com/blog/wp-includes/wlwmanifest.xml']}}
