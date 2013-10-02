#!/usr/bin/env python2.7

import db, datetime, queue

def update(conn, active_contracts, update_time):
    q0to24 = q24to48 = q48to72 = ip0to24 = ip24to48 = ip48to72 = 0
    for contract in active_contracts:
        if contract.created_min is None: continue
        age = (update_time - contract.created_min).total_seconds() / 3600.0
        if contract.accepted is not None and update_time > contract.accepted:
            if age < 24.0: ip0to24 += 1
            elif age < 48.0: ip24to48 += 1
            elif age < 72.0: ip48to72 += 1
        else:
            if age < 24.0: q0to24 += 1
            elif age < 48.0: q24to48 += 1
            elif age < 72.0: q48to72 += 1
            
    db.add_queue_history(conn, update_time, q0to24, q24to48, q48to72, ip0to24, ip24to48, ip48to72)

def regenerate(conn):
    # load server update history
    update_times = []
    c = conn.cursor()
    c.execute("SELECT update_time FROM serverupdates")
    for row in c:
        update_times.append(row['update_time'])
    update_times.sort()

    # load contract history
    all_contracts = db.Contract.load_where(conn = conn, clause = 'created_min IS NOT NULL')
    contracts_by_creation_time = list(all_contracts)
    contracts_by_creation_time.sort(lambda x,y: cmp(x.created_min,y.created_min))
    contracts_by_completion_time = [x for x in all_contracts if (x.state in (db.Contract.DONE,db.Contract.GONE))]
    contracts_by_completion_time.sort(lambda x,y: cmp(x.last_seen,y.last_seen))

    # reconstruct queue at each time in the server update history
    add_idx = 0
    remove_idx = 0
    q = set()
    for update_time in update_times:
        # update queue
        while add_idx < len(contracts_by_creation_time) and contracts_by_creation_time[add_idx].created_min <= update_time:
            #print 'add:', contracts_by_creation_time[add_idx]
            q.add(contracts_by_creation_time[add_idx])
            add_idx += 1
        while remove_idx < len(contracts_by_completion_time) and contracts_by_completion_time[remove_idx].last_seen < update_time:
            #print 'remove:', contracts_by_completion_time[remove_idx]
            q.remove(contracts_by_completion_time[remove_idx])
            remove_idx += 1

        # recalculate age buckets for this queue
        update(conn, q, update_time)

        #queue_contracts = [x for x in q if not (x.accepted is not None and update_time > x.accepted)]
        #queue_contracts.sort(lambda x,y: cmp(x.created_min, y.created_min))
        #accepted_contracts = [x for x in q if (x.accepted is not None and update_time > x.accepted)]
        #accepted_contracts.sort(lambda x,y: cmp(x.accepted, y.accepted))
        #queue.show(update_time, queue_contracts, accepted_contracts)

if __name__ == '__main__':
    from contextlib import closing
    with closing(db.new_connection(initdb=True)) as conn:
        regenerate(conn=conn)
        conn.commit()
