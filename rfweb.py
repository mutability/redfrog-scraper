import urllib2

_opener = None
REQUEST_TIMEOUT=60.0

def init():
    global _opener
    if _opener is None:
        # Yes, this is a completely insecure way of authenticating;
        # but we can't help that. The default ini file doesn't have
        # character info at least, to slightly raise the bar.

        import ConfigParser
        parser = ConfigParser.ConfigParser()
        parser.read('rfscrape.ini')

        _opener = urllib2.build_opener()
        _opener.addheaders = [
            ('User-agent',       'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/532.0 (KHTML, like Gecko) Chrome/3.0.195.27 Safari/532.0 EVE-IGB'),
            ('EVE_CHARNAME',     parser.get('rf','char.name')),
            ('EVE_CHARID',       parser.get('rf','char.id')),
            ('EVE_CORPNAME',     parser.get('rf','corp.name')),
            ('EVE_CORPID',       parser.get('rf','corp.id')),
            ('EVE_ALLIANCENAME', parser.get('rf','alliance.name')),
            ('EVE_ALLIANCEID',   parser.get('rf','alliance.id')),
            ('EVE_SERVERIP',     parser.get('rf','serverip')),
            ('EVE_TRUSTED',      'Yes')]

def urlopen(url, timeout=REQUEST_TIMEOUT):
    init()
    return _opener.open(url, timeout=timeout)

