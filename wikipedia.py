"""
A small python wrapper for Wikipedia API
@kbandla

4/20/20 - Impl usercontribs, revisions
"""
from pprint import pprint
from datetime import datetime
import requests

URL = "https://en.wikipedia.org/w/api.php"

class Wikipedia:
    def __init__(self, debug=False):
        self.debug = debug
        self.session = requests.Session()

    def get_json(self, params={}):
        """
        Performs a request
        :return:
        """
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
            "format": "json",
            "list": "usercontribs",
        }
        # insert any other values from kwargs
        for key in keys:
            if key in kwargs:
                params[key] = kwargs.get(key)

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
        print('Showing Stats for %s'%params.get('ucuser'))
        if self.debug:
            pprint(stats_year)

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
                  "formatversion": "2", "format": "json",
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
        print('Query returned %s pages'%len(pagesL))
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
        xx = sorted(stats_user.items(), key=lambda x: x[1], reverse=True)
        if self.debug:
            pprint(stats_year)
            pprint(xx[:10])
        return stats_user

    def analyze_page(self, title):
        results = self.revisions(title)
        for username, num in results:
            self.usercontribs(ucuser=username)


if __name__ == "__main__":
    import sys
    wiki = Wikipedia()
    wiki.analyze_page(sys.argv[1])