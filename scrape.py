import urllib2, re, datetime

def int_or_none(s):
    return None if (s is None) else int(s)

def unit_multiplier(s):
    s1 = s.strip().lower()
    if s1 == 'billion': return 1000000000.0
    elif s1 == 'million': return 1000000.0
    elif s1 == 'thousand': return 1000.0
    elif s1 == '': return 1.0
    else:
        raise AssertionError('Unknown unit multiplier: ' + s)

def convert_isk(a,b):
    return int( float(a.replace(',','')) * unit_multiplier(b) )

_re_dayshours = re.compile('\s*(\d+)d (\d+)h\s*')
_re_hours = re.compile('\s*(\d+)h\s*')
_re_minutes = re.compile('\s*(\d+)m\s*')

def age_to_delta_low(s):
    m = _re_dayshours.match(s)
    if m: return datetime.timedelta(days=int(m.group(1)), hours=int(m.group(2)))
    m = _re_hours.match(s)
    if m: return datetime.timedelta(hours=int(m.group(1)))
    m = _re_minutes.match(s)
    if m: return datetime.timedelta(minutes=int(m.group(1)))
    raise RuntimeError("Don't know how to parse an age of {s}".format(**locals()))

def age_to_delta_high(s):
    m = _re_dayshours.match(s)
    if m: return datetime.timedelta(days=int(m.group(1)), hours=int(m.group(2))+1)
    m = _re_hours.match(s)
    if m: return datetime.timedelta(hours=int(m.group(1))+1)
    m = _re_minutes.match(s)
    if m: return datetime.timedelta(minutes=int(m.group(1))+1)
    raise RuntimeError("Don't know how to parse an age of {s}".format(**locals()))

_re_queuestatus = re.compile(
    r'^  <b>(\d+)</b> outstanding,\n' +
    r'  <b>(\d+)</b> in progress$', re.MULTILINE)

_re_last_update = re.compile(
    r'Last update:</td>\n<td>\n<b>(\d+) (minute|second)s?</b> ago</td>\n.*\((\d\d\d\d)\.(\d\d)\.(\d\d) (\d\d):(\d\d)\).*$',
    re.MULTILINE)

_re_next_update = re.compile(
    r'Next update:</td>\n<td>\n(?:(<b>Processing\.\.\.)|(?:in <b>(\d+) (minute|second)s?))</b></td>\n.*\((\d\d\d\d)\.(\d\d)\.(\d\d) (\d\d):(\d\d)\).*$',
    re.MULTILINE)

PROCESSING_DELAY = 60
PARSE_ERROR_BACKOFF = 600

def scrape_update_info(contents):
    """ returns (server_time, last_update_time, next_update_time, processing, refresh) """
    queuestatus = _re_queuestatus.search(contents)
    last_update = _re_last_update.search(contents)
    next_update = _re_next_update.search(contents)
    
    if not queuestatus or not last_update or not next_update:
        return (None, None, None, False, None, None, datetime.datetime.now() + datetime.timedelta(seconds=PARSE_ERROR_BACKOFF))

    last_update_time = datetime.datetime(year = int(last_update.group(3)), 
                                         month = int(last_update.group(4)), 
                                         day = int(last_update.group(5)), 
                                         hour = int(last_update.group(6)), 
                                         minute = int(last_update.group(7)), 
                                         second = 0,
                                         microsecond = 0,
                                         tzinfo = None)
    if last_update.group(2) == 'second':
        server_time = last_update_time + datetime.timedelta(seconds = int(last_update.group(1)))
    else:
        server_time = last_update_time + datetime.timedelta(minutes = int(last_update.group(1)))
            
    next_update_time = datetime.datetime(year = int(next_update.group(4)), 
                                         month = int(next_update.group(5)), 
                                         day = int(next_update.group(6)), 
                                         hour = int(next_update.group(7)), 
                                         minute = int(next_update.group(8)), 
                                         second = 0,
                                         microsecond = 0,
                                         tzinfo = None)
    
    if next_update_time > server_time:
        refresh = (next_update_time + datetime.timedelta(seconds = PROCESSING_DELAY) - server_time)
    else:
        refresh = datetime.timedelta(seconds = PROCESSING_DELAY)

    processing = (next_update.group(1) is not None)

    status_outstanding = int(queuestatus.group(1))
    status_inprogress = int(queuestatus.group(2))
    
    return (server_time, last_update_time, next_update_time, processing, status_outstanding, status_inprogress, refresh)
