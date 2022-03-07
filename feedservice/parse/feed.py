# -*- coding: utf-8 -*-
#

import time
from xml.sax import SAXException
import requests

import feedparser

from feedservice.parse.models import Feed, Episode, File
from feedservice.utils import parse_time, url_fix
from feedservice.parse.mimetype import get_mimetype
from feedservice.parse import mimetype
from feedservice.parse.core import Parser
from feedservice.parse.models import ParserException

DEFAULT_TIMEOUT=10


class FeedparserError(ParserException):
    pass


class Feedparser(Parser):
    """ A parsed Feed """

    def __init__(self, url, resp, text_processor=None):
        super(Feedparser, self).__init__(url, resp)
        self.url = url
        self.response_stream = None

        headers = {
            'Accept': 'application/rss+xml,application/xml;q=0.9,*/*;q=0.8',
            # Custom user agent. Some web servers will give 403
            # or 400 if no user agent is present. Found some web
            # servers block curl.
            "User-Agent": "gpodder-feedparser/1.0",
        }

        try:
            stream = requests.get(self.url, headers=headers,
                                  timeout=DEFAULT_TIMEOUT)
            self.response_stream = stream
            self.feed = feedparser.parse(stream.content)

        except UnicodeEncodeError as e:
            raise FeedparserError(e)

        except TypeError as ex:
            # http://www.t-shops.co.uk/poll/hidden/podcasting/mwm_8.xml
            raise FeedparserError(ex)

        except SAXException as saxe:
            raise FeedparserError('malformed feed, or no feed at all: %s' %
                                  (str(saxe)))

        except requests.exceptions.RequestException as re:
            raise FeedparserError('Error fetching feed') from re

        self.text_processor = text_processor

    @classmethod
    def handles_url(cls, url):
        """ Generic class that can handle every RSS/Atom feed """
        return True

    def get_feed(self):
        feed = Feed(text_processor=self.text_processor)
        feed.title = self.get_title()
        feed.link = self.get_link()
        feed.description = self.get_description()
        feed.subtitle = self.get_subtitle()
        feed.author = self.get_author()
        feed.language = self.get_language()
        feed.urls = self.get_urls()
        feed.new_location = self.get_new_location()
        feed.logo = self.get_logo_url()
        feed.tags = self.get_feed_tags()
        feed.hub = self.get_hub_url()
        feed.http_last_modified = self.get_last_modified()
        feed.http_etag = self.get_etag()
        feed.flattr = self.get_flattr()
        feed.license = self.get_license()
        feed.authentication = self.get_authentication()

        #feed.logo_data = self.get_logo_inline()

        feed.set_episodes(self.get_episodes())

        return feed

    def get_title(self):
        return self.feed.feed.get('title', None)

    def get_urls(self):
        return [self.url]

    def get_link(self):
        return self.feed.feed.get('link', None)

    def get_description(self):
        return self.feed.feed.get('description', None)

    def get_subtitle(self):
        return self.feed.feed.get('subtitle', None)

    def get_author(self):
        return self.feed.feed.get('author',
                                  self.feed.feed.get('itunes_author', None))

    def get_language(self):
        return self.feed.feed.get('language', None)

    def get_new_location(self):
        return super(Feedparser, self).get_new_location() or \
            self.feed.feed.get('newlocation', None)

    def get_logo_url(self):
        image = self.feed.feed.get('image', None)
        if image is not None:
            for key in ('href', 'url'):
                cover_art = getattr(image, key, None)
                if cover_art:
                    return url_fix(cover_art)

        return None

    def get_flattr(self):
        links = self.feed.feed.get('links', [])
        flattr_links = [l['href'] for l in links if l['rel'] == 'payment']
        return next(iter(flattr_links), None)

    def get_license(self):
        return self.feed.feed.get('license', None)

    def get_feed_tags(self):
        tags = []

        for tag in self.feed.feed.get('tags', []):
            if tag['term']:
                tags.extend([_f for _f in tag['term'].split(',') if _f])

            if tag['label']:
                tags.append(tag['label'])

        return list(set(tags))

    def get_hub_url(self):
        """ Returns the Hub URL as specified by

        http://pubsubhubbub.googlecode.com/svn/trunk/pubsubhubbub-core-0.3.html#discovery
        """

        for l in self.feed.feed.get('links', []):
            if l.rel == 'hub' and l.get('href', None):
                return l.href
        return None

    def get_episodes(self):
        parser = [FeedparserEpisodeParser(e, self.text_processor) for e in
                  self.feed.entries]
        return [p.get_episode() for p in parser]

    def get_authentication(self):
        if self.response_stream is None:
            return None

        feed_auth_code = None
        temp_auth_flag = self.response_stream.headers.get("www-authenticate", None)
        if temp_auth_flag:
            feed_auth_code = temp_auth_flag.split(" ")[0]

        return feed_auth_code


class FeedparserEpisodeParser(object):
    """ Parses episodes from a feedparser feed """

    def __init__(self, entry, text_processor=None):
        self.entry = entry
        self.text_processor = text_processor

    def get_episode(self):
        episode = Episode(self.text_processor)
        episode.guid = self.get_guid()
        episode.title = self.get_title()
        episode.description = self.get_description()
        episode.subtitle = self.get_subtitle()
        episode.content = self.get_content()
        episode.link = self.get_link()
        episode.author = self.get_author()
        episode.duration = self.get_duration()
        episode.language = self.get_language()
        episode.set_files(list(self.get_files()))
        episode.released = self.get_timestamp()
        episode.flattr = self.get_flattr()
        episode.license = self.get_license()
        return episode

    def get_guid(self):
        return self.entry.get('id', None)

    def get_title(self):
        return self.entry.get('title', None)

    def get_link(self):
        return self.entry.get('link', None)

    def get_author(self):
        return self.entry.get('author', self.entry.get('itunes_author', None))

    def list_files(self):
        for enclosure in getattr(self.entry, 'enclosures', []):
            if not 'href' in enclosure:
                continue

            mimetype = get_mimetype(enclosure.get('type', ''),
                                    enclosure['href'])

            try:
                filesize = int(enclosure.get('length', None))
            except (TypeError, ValueError):
                filesize = None

            #TODO: optional: urls = tils.get_redirect_chain(enclosure['href'])
            urls = [enclosure['href']]
            yield (urls, mimetype, filesize)

        media_content = getattr(self.entry, 'media_content', [])
        for media in media_content:
            if not 'url' in media:
                continue

            mimetype = get_mimetype(media.get('type', ''), media['url'])

            try:
                filesize = int(media.get('fileSize', None))
            except (TypeError, ValueError):
                filesize = None

            #TODO: optional: urls = utils.get_redirect_chain(media['url'])
            urls = [media['url']]
            yield urls, mimetype, filesize

    def get_description(self):
        return self.entry.get('summary', None)

    def get_subtitle(self):
        return self.entry.get('subtitle', None)

    def get_content(self):
        for content in getattr(self.entry, 'content', []):
            if content.value:
                return content.value

    def get_duration(self):
        str = self.entry.get('itunes_duration', '')
        try:
            return parse_time(str)
        except ValueError:
            return None

    def get_language(self):
        return self.entry.get('language', None)

    def get_timestamp(self):
        if not getattr(self.entry, 'published_parsed', False):
            return None

        try:
            value = int(time.mktime(self.entry.published_parsed))

        except (ValueError, OverflowError):
            # dates before 1970 cause OverflowError
            return None

        # there were no podcasts released before timestamp 0
        if value <= 0:
            return None

        return value

    def get_files(self):
        """Get the download / episode URL of a feedparser entry"""

        files = []

        for urls, mtype, filesize in self.list_files():

            # skip if we've seen this list of URLs already
            if urls in [f.urls for f in files]:
                break

            if not mimetype.get_type(mtype):
                continue

            f = File(urls, mtype, filesize)
            files.append(f)

        return files

    def get_flattr(self):
        links = self.entry.get('links', [])
        flattr_links = [l['href'] for l in links if l['rel'] == 'payment']
        return next(iter(flattr_links), None)

    def get_license(self):
        return self.entry.get('license', None)
