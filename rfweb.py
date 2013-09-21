import urllib2

_opener = None
REQUEST_TIMEOUT=60.0

def init():
    global _opener
    if _opener is None:
        # Yes, this is a completely insecure way of authenticating;
        # but we can't help that.
        # Require that the char ID/name is provided separately to
        # provide a brief stumbling block, at least.

        import os
        charname = os.getenv('EVE_CHARNAME')
        charid = os.getenv('EVE_CHARID')
        corpname = os.getenv('EVE_CORPNAME', 'Red Frog Freight')
        corpid = os.getenv('EVE_CORPID', '1495741119')
        alliancename = os.getenv('EVE_ALLIANCENAME', 'Red-Frog')
        allianceid = os.getenv('EVE_ALLIANCEID', '1496500070')
        serverip = os.getenv('EVE_SERVERIP', '87.237.38.200:26000')

        if not charname: raise RuntimeError("Missing environment setting: EVE_CHARNAME")
        if not charid: raise RuntimeError("Missing environment setting: EVE_CHARID")

        _opener = urllib2.build_opener()
        _opener.addheaders = [
            ('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/532.0 (KHTML, like Gecko) Chrome/3.0.195.27 Safari/532.0 EVE-IGB'),
            ('EVE_CHARNAME', charname),
            ('EVE_CHARID', charid),
            ('EVE_CORPNAME', corpname),
            ('EVE_CORPID', corpid),
            ('EVE_ALLIANCENAME', alliancename),
            ('EVE_ALLIANCEID', allianceid),
            ('EVE_SERVERIP', serverip),
            ('EVE_TRUSTED', 'Yes')]

def urlopen(url, timeout=REQUEST_TIMEOUT):
    init()
    return _opener.open(url, timeout=timeout)

