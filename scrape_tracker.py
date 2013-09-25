#!/usr/bin/env python2.7

import re, datetime, db, scrape, rfweb
from contextlib import closing

_re_contract_line = re.compile(
    r'^<tr id="tr\d+">\n' + # table row ID
    r'<td><a.*onclick="CCPEVE.showContract\(\d+,\s*(?P<contractid>\d+)\); return false;">.*\((?P<volume>[\d,]+) m<sup>3</sup>\).*\n' +  # contract link, volume, comment
    r'<td>\n' +
    r'  <a href="jumps.php/(?P<fromsys>[^,]+),(?P<tosys>[^/]+)/show.*\n' +       # Calculator link
    r'</td>\n' +
    r'<td>\n' + 
    r'  (?P<collateral>(?:\d+,)*\d+(?:\.\d+)?)(?P<collateralunit> Thousand| Million| Billion|) isk</td>\n' +  # collateral
    r'<td>\n' +
    r'  (?:<span[^>]*>)?<a href="#" onclick="CCPEVE.showInfo\(1377,\s*(?P<charid>\d+)\); return false;">(?P<contractor>[^<]*)</a>(?:</span>)?</td>\n' +
    r'<td>\n' +
    r'  (?P<year>\d+)\.(?P<month>\d+)\.(?P<day>\d+) (?P<hour>\d+):(?P<minute>\d+)</td>\n',
    re.MULTILINE)

def scrape_tracker(override=None, write_copy=None, write_error=None):
    if override: source = open(override,'r')
    else: source = rfweb.urlopen('http://www.red-frog.org/rf-contracts.php')

    with closing(source):
        contents = source.read()
        if write_copy:
            with closing(open(write_copy,'w')) as out:
                out.write(contents)

        (server_time, last_update_time, next_update_time, processing, n_outstanding, n_inprogress, refresh) = scrape.scrape_update_info(contents)

        contracts = []
        for row in _re_contract_line.finditer(contents):
            contractor = row.group('contractor')
            if contractor == '': contractor = None

            contract = db.Contract(contract_id = int(row.group('contractid')),
                                   from_sys = row.group('fromsys'),
                                   to_sys = row.group('tosys'),
                                   jumps = None,
                                   volume = int(row.group('volume').replace(',','')),
                                   collateral = scrape.convert_isk(row.group('collateral'), row.group('collateralunit')),
                                   reward = None,
                                   star = None,
                                   state = db.Contract.IN_PROGRESS,
                                   last_seen = last_update_time,
                                   created_min = None,
                                   created_max = None,
                                   accepted = datetime.datetime(year = int(row.group('year')),
                                                                month = int(row.group('month')),
                                                                day = int(row.group('day')),
                                                                hour = int(row.group('hour')),
                                                                minute = int(row.group('minute')),
                                                                second = 0,
                                                                microsecond = 0,
                                                                tzinfo = None),
                                   contractor = contractor,
                                   contractor_id = scrape.int_or_none(row.group('charid')))
            #print contract
            contracts.append(contract)

        missing = n_inprogress - len(contracts)
        if write_error and missing > 0:
            with closing(open(write_error,'w')) as out:
                out.write(contents)

        return {
            'server_time' : server_time,
            'next_update' : next_update_time,
            'last_update' : last_update_time,
            'refresh'     : refresh,
            'contracts'   : contracts,
            'outstanding' : n_outstanding,
            'inprogress'  : n_inprogress,
            'missing'     : missing
            }

if __name__ == '__main__':
    import sys
    r = scrape_tracker(override=sys.argv[1])
    print 'Server time:  ', r['server_time']
    print 'Next update:  ', r['next_update']
    print 'Last update:  ', r['last_update']
    print 'Refresh:      ', r['refresh']
    print '# outstanding:', r['outstanding']
    print '# in progress:', r['inprogress']
    print '# missing:    ', r['missing']

    for contract in r['contracts']:
        print contract
