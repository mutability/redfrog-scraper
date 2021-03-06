#!/usr/bin/env python2.7

import db, datetime

def load(conn):
    queue_contracts = db.Contract.load_by_state(conn = conn, state = db.Contract.IN_QUEUE)
    accepted_contracts = db.Contract.load_by_state(conn = conn, state = db.Contract.IN_PROGRESS)

    last_update = reduce(max, [x.last_seen for x in queue_contracts], datetime.datetime.min)
    last_update = reduce(max, [x.last_seen for x in accepted_contracts], last_update)

    return last_update, queue_contracts, accepted_contracts

def show(last_update, queue_contracts, accepted_contracts):
    print 'Last update:', last_update

    queue_contracts = list(queue_contracts)
    queue_contracts.sort(lambda x,y: cmp((x.created_min,x.contract_id), (y.created_min,y.contract_id)))
    print '     ==== IN QUEUE ({n}) ===='.format(n = len(queue_contracts))
    for contract in queue_contracts:
        print contract

    accepted_contracts = list(accepted_contracts)
    accepted_contracts.sort(lambda x,y: cmp((x.accepted,x.contract_id), (y.accepted,y.contract_id)))
    print '     ==== IN PROGRESS ({n}) ===='.format(n = len(accepted_contracts))
    for contract in accepted_contracts:
        print contract

if __name__ == '__main__':
    from contextlib import closing
    with closing(db.new_connection(initdb=False)) as conn:
        last_update, queue_contracts, accepted_contracts = load(conn)

    show(last_update, queue_contracts, accepted_contracts)
