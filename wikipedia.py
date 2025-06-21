"""
A small python wrapper for Wikipedia API
@kbandla

4/20/20 - Impl usercontribs, revisions
"""
from pprint import pprint
from datetime import datetime
import logging
import requests

logger = logging.getLogger('wikipedia')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter2 = logging.Formatter('%(levelname)s-%(name)s %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter2)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

URL = "https://en.wikipedia.org/w/api.php"
URL_USER = "https://en.wikipedia.org/wiki/User:"
URL_ARTICLE= "https://en.wikipedia.org/wiki/"

class Wikipedia:
    def __init__(self, debug=False):
        self.debug = debug
        self.session = requests.Session()

    def get_json(self, params={}):
        """
        Performs a request
        :return:
        """
        if 'format' not in params:
            params["format"] = "json"
        response = self.session.get(url=URL, params=params)
        return response.json()

    def usercontribs(self, **kwargs):
        """
        Documentation: https://www.mediawiki.org/wiki/API:Usercontribs

        :param kwargs:
        :return:
        """
        keys = ['uclimit', 'ucstart', 'ucend', 'uccontinue', 'ucuser', 'ucuserids', 'ucuserprefix', 'ucnamespace', 'ucshow', 'uctag', 'uctoponly']
        params = {
            "action": "query",
            "list": "usercontribs",
        }
        # insert any other values from kwargs
        for key in keys:
            if key in kwargs:
                params[key] = kwargs.get(key)
        username = params.get('ucuser')
        logger.debug(f"Fetching user contributions for {username}..")
        data = self.get_json(params)
        queryD = data.get('query')
        usercontribsL = queryD.get('usercontribs')
        mykeys = ['title', 'timestamp', 'comment']
        stats_year = {}
        for num, contrib in enumerate(usercontribsL):
            timestamp = contrib.get('timestamp').rstrip('Z')
            timestamp = datetime.fromisoformat(timestamp)
            title = contrib.get('title')
            if timestamp.year not in stats_year:
                stats_year[timestamp.year] = []
            stats_year[timestamp.year].append(title)
        logger.debug(f'Showing Stats for {username}')
        self.outfile.write(f'# Stats for {username}\n')
        self.outfile.write(f'| Username | Articles |\n| -- | -- |\n')
        for year in stats_year:
            self.outfile.write(f"| {year} | ")
            for article in stats_year.get(year):
                self.outfile.write(f'[{article}](<{URL_ARTICLE}{article}>)<br>')
            self.outfile.write(' |\n')
        self.outfile.write('\n\n')
        if self.debug:
            pprint(stats_year)
            pprint('-'*110)
        batchcompleteB = bool(data.get('batchcomplete'))
        continueD = data.get('continue', {})
        uccontinue = continueD.get('uccontinue')

        # TODO : add recursive requests, with uccontinue

    def revisions(self, titles, **kwargs):
        """
        See https://www.mediawiki.org/wiki/API:Revisions for documentation

        :param titles: pipe delimited list of titles
        :param kwargs: see API docs
        :return:
        """
        keys = ['rvprop', 'rvslots', 'rvlimit', 'rvuser', 'rvexcludeuser', 'rvtag', '']
        params = {"action": "query",
                  "prop": "revisions",
                  "rvprop": "timestamp|user|comment|size",
                  "rvslots": "main",
                  "formatversion": "2", 
                  "titles": titles,
                  "rvlimit": 500}
        # insert any other values from kwargs
        for key in keys:
            if key in kwargs:
                params[key] = kwargs.get(key)

        data = self.get_json(params)
        batchcompleteB = bool(data.get('batchcomplete'))
        queryD = data.get('query')
        pagesL = queryD.get('pages')
        logger.debug('Query returned %s pages'%len(pagesL))
        stats_year = {}
        stats_user = {}
        for num, page in enumerate(pagesL):
            revisions = page.get('revisions', [])
            for revision in revisions:
                user = revision.get('user')
                timestamp = revision.get('timestamp').rstrip('Z')
                timestamp = datetime.fromisoformat(timestamp)
                # collect yearly stats
                if timestamp.year not in stats_year:
                    stats_year[timestamp.year] = set()
                stats_year[timestamp.year].add(user)
                # collect user stats
                if user not in stats_user:
                    stats_user[user] = 0
                stats_user[user] += 1
        userstats_sorted = sorted(stats_user.items(), key=lambda x: x[1], reverse=True)
        title = ''.join(titles)
        # Report yearly stats
        self.outfile.write(f'# Yearly stats for {title}\n')
        self.outfile.write(f'| year | Users |\n| -- | -- |\n')
        for year in stats_year:
            self.outfile.write(f'| {year} | ')
            for user in stats_year.get(year):
                self.outfile.write(f'[{user}](<{URL_USER}{user}>)<br>')
            self.outfile.write(' |\n')
        self.outfile.write('\n\n')
        self.outfile.write(f'# Stats by username for {title}\n')
        self.outfile.write(f'| Username | Revisions |\n| -- | -- |\n')
        # Report user stats (sorted)
        for name, revcount in userstats_sorted:
            self.outfile.write(f"| [{name}](<{URL_USER}{name}>) | {revcount} |\n")
        self.outfile.write('\n\n')
        if self.debug:
            pprint(stats_year)
            pprint(userstats_sorted[:10])
        return stats_user

    def analyze_page(self, titles):
        filename = ''.join(titles).replace(' ','')
        self.outfile = open(f'{filename}_report.md', 'w')
        title = ''.join(titles)
        self.outfile.write(f"# Wikipedia Analysis : {title}\n\n")
        summary = self.get_lead(titles)
        self.outfile.write(f"{summary}\n\n")
        results = self.revisions(titles)
        for username, num in results.items():
            self.usercontribs(ucuser=username)

    def get_lead(self, titles):
        """
        Get the lead section for a page in plaintext 
        
        NOTE: response is like
        {   'batchcomplete': '',
            'query': {
                'normalized': [{'from': 'pizza', 'to': 'Pizza'}],
                'pages': {
                    '24768': {'extract': 'Pizza is an Italian, specifically '
        """
        params = {
            'action' : 'query',
            'prop': 'extracts',
            'exintro': True,
            'explaintext': True,
            'titles': titles,
        }
        data = self.get_json(params)
        batchcompleteB = bool(data.get('batchcomplete'))
        queryD = data.get('query')
        pagesD = queryD.get('pages')
        logger.debug('Query returned %s pages'%len(pagesD))
        for num, extractD in pagesD.items():
            extract = extractD.get('extract')
            logger.debug(extract)
        return extract

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Wikipedia Search')
    parser.add_argument('-v', '--verbose', action='store_true', help="Increase output verbosity")
    parser.add_argument('-a', '--analyze', action='store_true', help='Analyze edits to a page')
    parser.add_argument('--summary', action='store_true', help='Get summary for a page')
    parser.add_argument('titles', nargs='*', action='store', help='Search query')
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug(args)
    wiki = Wikipedia()
    wiki.debug = args.verbose
    if args.analyze:
        wiki.analyze_page(args.titles)
    elif args.summary:
        summary = wiki.get_lead(args.titles)
    else:
        parser.print_help()
