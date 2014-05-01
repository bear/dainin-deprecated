dainin
======

代人 -- a proxy, substitute, deputy or agent - a tool to manage events and actions on my behalf

This is a collection of tools and scripts that enable IndieWeb static sites.


indieweb_listener.py
--------------------
A uwsgi (or commandline) Flask app that will listen for:

    POST /webmention

The [Ronkyuu](https://github.com/bear/ronkyuu) library is used to verify and validate the webmention.

Events
------
During the processing each task, be it an incoming webmention, reply or even a new
post - a new event will be generated and any event handlers found will be given a
chance to process the event.

This is done to allow for external scripts or calls to be made to update the static
site and/or data files.

Right now I'm going to use a very simple "plugin" style for inbound, outbound and posts
where any .py file found in a directory is imported as a module. This will, I think, let
me use the event plugins via the command line, but also via WebHooks because I can create 
a Flask listener for WebHook urls and then call the event plugins.

Events consist of the event type and a payload - not much else is really needed.

* webmention inbound
 * source url, target url
* webmention outbound
 * source url, target url
* article post
 * source url or file

Roadmap
=======
Pending
* ...

Working
* command line tool to trigger an event
* examples for event handling


Contributors
============
* bear (Mike Taylor)

Requires
========
Python v2.6+ but see requirements.txt for a full list
