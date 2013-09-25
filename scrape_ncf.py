#!/usr/bin/env python2.7

import re, datetime, db, rfweb, scrape
from contextlib import closing

_re_contract_line = re.compile(
    r'<tr id="tr(?P<rowid>\d+)">\n' + # table row ID
    r'.*\n' + # jumps to start
    r'.*\n' + # jumps from dest
    r'^<td><a href="jumps.php/(?P<fromsys>[^,]+)?,(?P<tosys>[^/]+)?/show">.*onclick="CCPEVE.showContract\((?P<solarsystemid>\d+),\s*(?P<contractid>\d+)\).*\((?P<volume>\d+(?:,\d+)*) m<sup>3</sup>\).*\n' + # contract link, volume, comment
    r'.*\n' +    # region from-to
    r'<td [^>]*>(?P<jumps>\d+)?</td>\n' + # jumps
    r'<td [^>]*>(?P<age>[^<]+)</td>\n' + # age
    r'<td><span [^>]*>(?P<reward>(?:\d+,)*\d+(?:\.\d+)?)(?P<rewardunit> Thousand| Million| Billion|) isk.*?(?P<star>star\.png.*)?\n' + # reward, star
    r'<td><span [^>]*>(?P<collateral>(?:\d+,)*\d+(?:\.\d+)?)(?P<collateralunit> Thousand| Million| Billion|) isk.*\n', # collateral
    re.MULTILINE)

def scrape_ncf(override=None, write_copy=None, write_error=None):
    if override: source = open(override,'r')
    else: source = rfweb.urlopen('http://www.red-frog.org/nearest.php')

    with closing(source):
        contents = source.read()
        if write_copy:
            with closing(open(write_copy,'w')) as out:
                out.write(contents)

        (server_time, last_update_time, next_update_time, processing, n_outstanding, n_inprogress, refresh) = scrape.scrape_update_info(contents)

        contracts = []
        for row in _re_contract_line.finditer(contents):
            contract = db.Contract(contract_id = int(row.group('contractid')),
                                   from_sys = row.group('fromsys'),
                                   to_sys = row.group('tosys'),
                                   jumps = scrape.int_or_none(row.group('jumps')),
                                   volume = int(row.group('volume').replace(',','')),
                                   reward = scrape.convert_isk(row.group('reward'), row.group('rewardunit')),
                                   star = (row.group('star') is not None),
                                   collateral = scrape.convert_isk(row.group('collateral'), row.group('collateralunit')),
                                   state = db.Contract.IN_QUEUE,
                                   last_seen = last_update_time,
                                   created_min = server_time - scrape.age_to_delta_high(row.group('age')),
                                   created_max = server_time - scrape.age_to_delta_low(row.group('age')),
                                   accepted = None,
                                   contractor = None,
                                   contractor_id = None)
            #print contract
            contracts.append(contract)

        missing = n_outstanding - len(contracts)
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
    r = scrape_ncf(override=sys.argv[1])
    print 'Server time:  ', r['server_time']
    print 'Next update:  ', r['next_update']
    print 'Last update:  ', r['last_update']
    print 'Refresh:      ', r['refresh']
    print '# outstanding:', r['outstanding']
    print '# in progress:', r['inprogress']
    print '# missing:    ', r['missing']

    for contract in r['contracts']:
        print contract
