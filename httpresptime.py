#!/usr/bin/env python3
"""httpresptime - HTTP response time measurements.

httpresptime is a tool to help with measurement of the response time of
HTTP requests.

The primary goal is to measure the time it takes the server to generate
the response to the GET request, as such, keepalive is used when availble
to avoid measuring TCP connection time.

$ httpresptime www.google.com
Using URL: http://www.google.se/?gfe_rd=cr&dcr=0&ei=b3UFWrjJC8T37gTYxrfYAQ (173.194.222.94)
Sending requests: .....
Response times (s): min: 0.0562 max: 0.0647 avg: 0.0607
"""

import sys
import time
import argparse
import datetime
import requests
import socket
from urllib.parse import urlparse
## Disable warnings about not doing SSL verification
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


CHROME_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'


def request_headers(headers = {}):
    """Permanent store for request headers.

    Returns a dict of request headers that can be updated for future calls.
    """
    return headers


def get_redirected_url(url):
    """Get the final redirected URL for en URL."""
    resp = requests.get(url, verify=False, headers=request_headers())
    return resp.url


def get_url_hostname(url):
    """Return the hostname part of an URL."""
    p_url = urlparse(url)
    return p_url.hostname


def time_url(url, num_requests=10, display_progress=True, use_keepalive=True):
    """Perform response time measurements for an URL."""
    if use_keepalive:
        session = requests.Session()
        session.get(url, verify=False, headers=request_headers())
    else:
        session = requests
    resp_times = []
    if display_progress:
        print('Sending requests: ', end='', flush=True)
    for _ in range(num_requests):
        start = time.time()
        r = session.get(url, verify=False, headers=request_headers())
        end = time.time()
        resp_times.append(end - start)
        r.raise_for_status()
        if display_progress:
            print('.', end='', flush=True)
    if display_progress:
        print()
    return calc_resp_times(resp_times)


def calc_resp_times(resp_times):
    """Calculate response times collected by time_url."""
    first = True
    ret = {'min_time': None, 'max_time': None, 'avg_time': None}
    total_time = 0
    for resp_time in resp_times:
        if first:
            ret['min_time'] = ret['max_time'] = resp_time
            first = False
        ret['min_time'] = min(ret['min_time'], resp_time)
        ret['max_time'] = max(ret['max_time'], resp_time)
        total_time += resp_time
    ret['avg_time'] = total_time / len(resp_times)
    return ret


def display_url_info(url, include_headers=False):
    """Display information about an URL."""
    r = requests.get(url, verify=False, headers=request_headers())
    print('Input URL: %s' % (url))
    print('Final URL: %s' % (r.url))
    print('HTTP status code: %d' % r.status_code)
    print('Response size: %d' % len(r.text))
    print('Number of redirects: %d' % len(r.history))
    if len(r.history) > 0:
        urls = [h.url for h in r.history] + [r.url]
        print('URL history: %s' % (' '.join(urls)))
    if include_headers:
        print()
        print('Headers:')
        for key, value in r.headers.items():
            print('%s: %s' % (key, value))
    else:
        print('Content-type: %s' % r.headers.get('content-type'))


def loop_url(url, delay=10, use_keepalive=True):
    """Enter an endless loop that keeps requesting the same URL."""
    while True:
        now = datetime.datetime.now()
        print('%02d:%02d:%02d: ' % (now.hour, now.minute, now.second), end='', flush=True)
        res = time_url(url, num_requests=1, display_progress=False, use_keepalive=use_keepalive)
        print('%.04f' % res['min_time'])
        time.sleep(delay)


def parse_args():
    """Command line argument handler."""
    parser = argparse.ArgumentParser(description='HTTP response time checker..')
    parser.add_argument('-n', '--requests', default=5, type=int, help='number of requests to run')
    parser.add_argument('--no-keepalive', default=True, dest='keepalive', action='store_false',
            help='disable http keepalive')
    parser.add_argument('-l', '--loop', default=False, action='store_true',
            help='loop sending requests forever')
    parser.add_argument('--loop-delay', default=10, type=int, help='delay between requests with -l')
    parser.add_argument('-i', '--info', default=False, action='store_true',
            help='display http response information')
    parser.add_argument('-H', '--display-headers', default=False, dest='headers', action='store_true',
            help='display http response information headers (only with -i)')
    parser.add_argument('-p', '--parsable', default=False, action='store_true',
            help='machine parsable output')
    parser.add_argument('--ua-spoof', default=False, action='store_true',
            help='spoof a Chrome user agent')
    parser.add_argument('url', help='URL to check')
    args = parser.parse_args()
    return args


def print_using_url(url):
    url_ip = socket.gethostbyname(get_url_hostname(url))
    print('Using URL: %s (%s)' % (url, url_ip))


def main():
    args = parse_args()
    url = args.url
    if args.ua_spoof:
        request_headers()['User-Agent'] = CHROME_USER_AGENT
    if '://' not in url:
        url = 'http://%s' % url
    if args.loop:
        redir_url = get_redirected_url(url)
        if not args.parsable:
            print_using_url(redir_url)
        loop_url(redir_url, args.loop_delay, args.keepalive)
    elif args.info:
        display_url_info(url, args.headers)
    else:
        redir_url = get_redirected_url(url)
        if not args.parsable:
            print_using_url(redir_url)
        display_progress = True
        if args.parsable:
            display_progress = False
        resp = time_url(redir_url, args.requests, display_progress, args.keepalive)
        if args.parsable:
            print('%.04f %.04f %.04f' % (resp['min_time'], resp['max_time'], resp['avg_time']))
        else:
            print('Response times (s): min: %.04f max: %.04f avg: %.04f' % (resp['min_time'], resp['max_time'], resp['avg_time']))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nAborted.')
