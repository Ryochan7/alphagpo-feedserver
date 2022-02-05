#!/usr/bin/python
# -*- coding: utf-8 -*-
#

import urllib.parse
import time
import email.utils
import cgi
import html
import json

from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.sites.requests import RequestSite
from django.views.generic.base import View
from django.views.generic import TemplateView
from django.conf import settings

from feedservice.parse import parse_feeds
from feedservice.utils import select_matching_option
from feedservice.webservice.utils import ObjectEncoder
from feedservice.parse.text import StripHtmlTags, ConvertMarkdown


class IndexView(TemplateView):

    template_name = 'index.html'


class ParseView(View):
    """ Parser Endpoint """

    def get(self, request):

        urls = request.GET.getlist('url') + request.POST.getlist('url')
        urls = list(map(urllib.parse.unquote, urls))

        parse_args = dict(
            inline_logo = request.GET.get('inline_logo', default=0),
            scale_to    = request.GET.get('scale_logo',  default=0),
            logo_format = request.GET.get('logo_format', None),
        )

        # support deprecated param 'strip_html'; newer 'process_text' overrides
        if int(request.GET.get('strip_html', 0)):
            process_text = get_text_processor('strip_html')

        text_processor = get_text_processor(request.GET.get('process_text', ''))

        # TODO: caching has been removed; ?use_cache is not used atm

        mod_since_utc = request.META.get('HTTP_IF_MODIFIED_SINCE', None)
        accept = request.META.get('HTTP_ACCEPT', 'application/json')

        base_url = request.build_absolute_uri('/')

        if urls:
            podcasts = parse_feeds(urls, mod_since_utc, text_processor)
            last_mod_utc = self.get_earliest_last_modified(podcasts)
            response = self.send_response(request, podcasts, last_mod_utc, accept)

        else:
            response = HttpResponse()
            response.status_code = 400
            response.write('parameter url missing')

        return response

    post = get


    def get_earliest_last_modified(self, podcasts):
        """ returns the earliest Last-Modified date of all podcasts """
        timestamps = (getattr(p, 'http_last_modified', None) for p in podcasts)
        timestamps = [_f for _f in timestamps if _f]
        timestamps = list(map(email.utils.parsedate, timestamps))
        timestamps = sorted(timestamps)
        return next(iter(timestamps), None)


    def send_response(self, request, podcasts, last_mod_utc, accepted_formats):

        SUPPORTED_FORMATS = ['text/html', 'application/json']

        fmt = select_matching_option(SUPPORTED_FORMATS, accepted_formats)

        if fmt in (None, 'application/json'): #serve json as default
            content_type = 'application/json'
            response = HttpResponse()

            dense_json = json.dumps(podcasts, sort_keys=True,
                    indent=None, separators=(',', ':'), cls=ObjectEncoder)
            response.write(dense_json)

            if last_mod_utc:
                last_mod_time = time.mktime(last_mod_utc)
                response['Last-Modified'] = email.utils.formatdate(last_mod_time)


        else:
            content_type = 'text/html'
            pretty_json = json.dumps(podcasts, sort_keys=True, indent=4, cls=ObjectEncoder)
            pretty_json = html.escape(pretty_json)
            response = render(request, 'pretty_response.html', {
                    'response': pretty_json,
                    'site': RequestSite(request),
                })

        response['Content-Type'] = content_type
        response['Vary'] = 'Accept, User-Agent, Accept-Encoding'

        return response


def get_text_processor(name):
    if name == 'strip_html':
        return StripHtmlTags()
    elif name == 'markdown':
        return ConvertMarkdown()
