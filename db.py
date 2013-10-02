import sqlite3, datetime

def _mergeidentical(a,b):
    if a != b:
        raise RuntimeError('Field value changed from {a} to {b} unexpectedly'.format(**locals()))
    return a

def _merge(a,b,f=_mergeidentical):
    if a is None: return b
    if b is None: return a
    return f(a,b)

class Contract:
    IN_QUEUE, IN_PROGRESS, DONE, GONE = ('IN_QUEUE', 'IN_PROGRESS', 'DONE', 'GONE')

    def __init__(self, contract_id, from_sys, to_sys, jumps, volume, collateral, reward, star, state, last_seen, created_min, created_max, accepted, contractor, contractor_id):
        self.contract_id = contract_id
        self.from_sys = from_sys
        self.to_sys = to_sys
        self.jumps = jumps
        self.volume = volume
        self.collateral = collateral
        self.reward = reward
        self.star = star
        self.state = state
        self.last_seen = last_seen
        self.created_min = created_min
        self.created_max = created_max
        self.accepted = accepted
        self.contractor = contractor
        self.contractor_id = contractor_id

    @staticmethod
    def _mergestates(a,b):
        if a == Contract.DONE or b == Contract.DONE: return Contract.DONE
        if a == Contract.IN_PROGRESS or b == Contract.IN_PROGRESS: return Contract.IN_PROGRESS
        if a == Contract.IN_QUEUE or b == Contract.IN_QUEUE: return Contract.IN_QUEUE
        return Contract.GONE

    @staticmethod
    def _mergestars(a,b):
        if a == b: return a
        if (not a) and b: return True  # no star -> star is OK
        raise RuntimeError('Field value changed from {a} to {b} unexpectedly'.format(**locals()))

    @staticmethod
    def merge(c1, c2):
        return Contract(contract_id = _merge(c1.contract_id, c2.contract_id),
                        from_sys = _merge(c1.from_sys, c2.from_sys),                        
                        to_sys = _merge(c1.to_sys, c2.to_sys),                        
                        jumps = _merge(c1.jumps, c2.jumps),                        
                        volume = _merge(c1.volume, c2.volume),                        
                        collateral = _merge(c1.collateral, c2.collateral),
                        reward = _merge(c1.reward, c2.reward), 
                        star = _merge(c1.star, c2.star, Contract._mergestars), 
                        state = _merge(c1.state, c2.state, Contract._mergestates),
                        last_seen = _merge(c1.last_seen, c2.last_seen, max),
                        created_min = _merge(c1.created_min, c2.created_min, max),
                        created_max = _merge(c1.created_max, c2.created_max, min),
                        accepted = _merge(c1.accepted, c2.accepted),
                        contractor = _merge(c1.contractor, c2.contractor),
                        contractor_id = _merge(c1.contractor_id, c2.contractor_id))
        
    @staticmethod
    def from_row(row):
        return Contract(contract_id = row['contract_id'],
                        from_sys = row['from_sys'],
                        to_sys = row['to_sys'],
                        jumps = row['jumps'],
                        volume = row['volume'],
                        collateral = row['collateral'],
                        reward = row['reward'],
                        star = (None if (row['star'] is None) else bool(row['star'])),
                        state = row['state'],
                        last_seen = row['last_seen'],
                        created_min = row['created_min'],
                        created_max = row['created_max'],
                        accepted = row['accepted'],
                        contractor = row['contractor'],
                        contractor_id = row['contractor_id'])

    @staticmethod
    def load(conn, contract_id):
        results = conn.cursor().execute('SELECT * FROM contracts WHERE contract_id = :contract_id', locals())
        row = results.fetchone()
        if row: return Contract.from_row(row)
        else: return None

    @staticmethod
    def load_where(conn, clause, **kwargs):
        contracts = []
        c = conn.cursor()
        c.execute('SELECT * FROM contracts WHERE ' + clause, kwargs)
        for row in c:
            contracts.append(Contract.from_row(row))
        return contracts

    @staticmethod
    def load_by_state(conn, state):
        return Contract.load_where(conn, 'state = :state', state = state)

    @staticmethod
    def load_completed_after(conn, cutoff):
        return Contract.load_where(conn, 'state = :state AND last_seen >= :cutoff', state = Contract.DONE, cutoff = cutoff)
        
    def insert_row(self, conn):
        conn.cursor().execute('''
INSERT INTO contracts (contract_id,from_sys,to_sys,jumps,volume,collateral,reward,star,state,last_seen,created_min,created_max,accepted,contractor,contractor_id)
VALUES (:contract_id, :from_sys, :to_sys, :jumps, :volume, :collateral, :reward, :star, :state, :last_seen, :created_min, :created_max, :accepted, :contractor, :contractor_id)''', self.__dict__)

    def update_row(self, conn):
        conn.cursor().execute('''
UPDATE contracts
SET from_sys = :from_sys, to_sys = :to_sys, jumps = :jumps, volume = :volume, collateral = :collateral, reward = :reward, star = :star, state = :state, last_seen = :last_seen, created_min = :created_min, created_max = :created_max, accepted = :accepted, contractor = :contractor, contractor_id = :contractor_id
WHERE contract_id = :contract_id''', self.__dict__)        
    

    def __str__(self):
        if self.created_min and self.created_max:
            if (self.created_max - self.created_min).total_seconds() <= 60:
                created = self.created_min.strftime('cr=%Y-%m-%d %H:%M')
            else:
                created = self.created_min.strftime('cr=%Y-%m-%d %H:%M-') + self.created_max.strftime('%H:%M')
        else:
            created = ''

        if self.accepted:
            accepted = self.accepted.strftime('ac=%Y-%m-%d %H:%M' )
        else:
            accepted = ''

        if self.volume is not None:
            if self.volume < 1000:
                volume = 'v= <1k'
            else:
                volume = 'v={volume:3d}k'.format(volume=self.volume/1000)
            if self.volume > 860000:
                volume += ' (big)'
        else:
            volume = ''

        if self.collateral is not None:
            collateral = 'c=' + format_isk(self.collateral)
            if self.collateral < 1000000:
                collateral += ' (low)'
        else:
            collateral = ''

        if self.reward is not None:
            reward = 'r=' + format_isk(self.reward)
            if self.jumps is not None:
                expected = self.jumps * 500000 + 1000000
                if self.reward < expected: reward += ' (low)'
                elif self.reward > expected: reward += ' (tip)'
        else:
            reward = ''

        if self.star:
            star = '(*)'
        else:
            star = ''

        if self.jumps is not None:
            jumps = 'j={:2d}'.format(self.jumps)
        else:
            jumps = ''

        if self.contractor is not None:
            contractor = self.contractor
        elif self.contractor_id is not None:
            contractor = '#' + str(self.contractor_id)
        else:
            contractor = ''

        last = self.last_seen.strftime('%Y-%m-%d %H:%M')

        return '{self.contract_id}: {self.state:11.11s} {self.from_sys:9.9s} -> {self.to_sys:9.9s} {jumps:4s} {reward:14s} {star:3s} {collateral:14s} {volume:12s} {contractor:15.15s} {created:25s} {accepted:19s} ls={last:16s}'.format(**locals())

    def __repr__(self):
        return 'Contract({contract_id})'.format(**self.__dict__)

def format_isk(x):
    if x is None: return '      '
    if x < 1000: return '{:6d}'.format(x)
    #if x < 10000: return '{:5.3f}k'.format(x/1000.0)
    #if x < 100000: return '{:5.2f}k'.format(x/1000.0)
    if x < 1000000: return '{:5.1f}k'.format(x/1000.0)
    #if x < 10000000: return '{:5.3f}M'.format(x/1000000.0)
    #if x < 100000000: return '{:5.2f}M'.format(x/1000000.0)
    if x < 1000000000: return '{:5.1f}M'.format(x/1000000.0)
    return '{:5.3f}B'.format(x/1000000000.0)    

def add_update_info(conn, update_time, queue_count, in_progress_count):
    conn.cursor().execute("INSERT INTO serverupdates(update_time,queue_count,in_progress_count) VALUES (:update_time, :queue_count, :in_progress_count)",
                          {'update_time': update_time,
                           'queue_count': queue_count,
                           'in_progress_count': in_progress_count})

def add_queue_history(conn, update_time, q0to24, q24to48, q48to72, ip0to24, ip24to48, ip48to72):
    conn.cursor().execute("INSERT INTO queuehistory(update_time,queue_0_to_24,queue_24_to_48,queue_48_to_72,in_progress_0_to_24,in_progress_24_to_48,in_progress_48_to_72) VALUES (:update_time,:q0to24,:q24to48,:q48to72,:ip0to24,:ip24to48,:ip48to72)", locals())

def get_last_update(conn):
    c = conn.cursor()
    c.execute("SELECT last_update FROM lastupdated")
    row = c.fetchone()
    if row: return row['last_update']
    else: return None

def set_last_update(conn, last_update):
    conn.cursor().execute("DELETE FROM lastupdated")
    conn.cursor().execute("INSERT INTO lastupdated(last_update) VALUES (:last_update)", {"last_update": last_update})

_dbfile = None
def init():
    global _dbfile
    if _dbfile is None:
        import ConfigParser
        parser = ConfigParser.ConfigParser()
        parser.read('rfscrape.ini')
        _dbfile = parser.get('db','dbfile')

def new_connection(initdb=True):
    init()
    conn = sqlite3.connect(_dbfile, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row

    if initdb:
        c = conn.cursor()
        c.execute('''
CREATE TABLE IF NOT EXISTS contracts (
  contract_id INTEGER  NOT NULL PRIMARY KEY,
  from_sys    TEXT     NULL,
  to_sys      TEXT     NULL,
  jumps       INTEGER  NULL,
  volume      INTEGER  NULL,
  collateral  INTEGER  NULL,
  reward      INTEGER  NULL,  
  star        INTEGER  NULL,

  state       TEXT      NULL,
  last_seen   timestamp NULL,
  created_min timestamp NULL,
  created_max timestamp NULL,
  accepted    timestamp NULL,
  contractor  TEXT      NULL,
  contractor_id INTEGER NULL
)
''')  

        c.execute('CREATE INDEX IF NOT EXISTS contracts_state ON contracts (state)')

        c.execute('''
CREATE TABLE IF NOT EXISTS serverupdates (
  update_time       timestamp NOT NULL PRIMARY KEY,
  queue_count       INTEGER   NOT NULL,
  in_progress_count INTEGER   NOT NULL
)
''')

        c.execute('''
CREATE TABLE IF NOT EXISTS lastupdated (
  last_update       timestamp NOT NULL
)
''')

        c.execute('''
CREATE TABLE IF NOT EXISTS queuehistory (
  update_time       timestamp NOT NULL PRIMARY KEY,
  queue_0_to_24     INTEGER NOT NULL,
  queue_24_to_48    INTEGER NOT NULL,
  queue_48_to_72    INTEGER NOT NULL,
  in_progress_0_to_24     INTEGER NOT NULL,
  in_progress_24_to_48    INTEGER NOT NULL,
  in_progress_48_to_72    INTEGER NOT NULL
)
''')

    return conn
