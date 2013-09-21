#!/usr/bin/env python2.7

import db, scrape_ncf, scrape_tracker, sys, datetime, traceback, time, random, queue, graph, upload, rfweb

def log(f, *args, **kwargs):
    print >>sys.stderr, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), f.format(*args, **kwargs)
    
def run_one_cycle():
    log("Starting an update cycle")
    
    conn = db.new_connection()
    try:
        previous_update = db.get_last_update(conn)

        try:
            log("Scraping NCF page")
            ncf_results = scrape_ncf.scrape_ncf(write_copy = 'log/ncf-latest.html',
                                                write_error = datetime.datetime.now().strftime('log/ncf-missing-%Y%m%d%H%M%S.html'))
            log("NCF: Server time: {t}", t = ncf_results['server_time'])
            log("NCF: Last update: {t}", t = ncf_results['last_update'])
            log("NCF: Next update: {t}", t = ncf_results['next_update'])
            log("NCF: Outstanding: {n}", n = ncf_results['outstanding'])
            log("NCF: In progress: {n}", n = ncf_results['inprogress'])
            log("NCF: Refresh:     {r}", r = ncf_results['refresh'])
            if ncf_results['missing'] > 0: 
                log("NCF: *MISSING*:   {n}", n = ncf_results['missing'])
        except:
            log("Caught an exception processing the NCF page")
            traceback.print_exc()
            return datetime.timedelta(minutes=5)

        last_update = ncf_results['last_update']
        if previous_update is not None and last_update <= previous_update:
            log("NCF update ({last_update}) is not newer than database's last update ({previous_update}); skipping this update",
                **locals())
            return ncf_results['refresh']
            
        try:
            log("Scraping tracker page")
            tracker_results = scrape_tracker.scrape_tracker(write_copy = 'log/tracker-latest.html',
                                                            write_error = datetime.datetime.now().strftime('log/tracker-missing-%Y%m%d%H%M%S.html'))
            log("Tracker: Server time: {t}", t = tracker_results['server_time'])
            log("Tracker: Last update: {t}", t = tracker_results['last_update'])
            log("Tracker: Next update: {t}", t = tracker_results['next_update'])
            log("Tracker: Outstanding: {n}", n = tracker_results['outstanding'])
            log("Tracker: In progress: {n}", n = tracker_results['inprogress'])
            log("Tracker: Refresh:     {r}", r = tracker_results['refresh'])
            if tracker_results['missing'] > 0: 
                log("Tracker: *MISSING*:   {n}", n = tracker_results['missing'])
        except:
            log("Caught an exception processing the tracker page")
            traceback.print_exc()
            return datetime.timedelta(minutes=5)
        
        if last_update != tracker_results['last_update']:
            log("NCF and Tracker pages had different last update times. Retrying.")
            return datetime.timedelta(minutes=1)

        seen_contracts = set()
        
        for contract in ncf_results['contracts'] + tracker_results['contracts']:
            try:
                cid = contract.contract_id
                seen_contracts.add(cid)

                db_contract = db.Contract.load(conn = conn, contract_id = cid)
                if not db_contract:
                    if contract.state == db.Contract.IN_PROGRESS and contract.created_min is None:
                        # Missed it in queue. It must have been created between the last update we processed and the time it was accepted
                        contract.created_min = previous_update
                        contract.created_max = contract.accepted

                    log("New:  {contract}", **locals())
                    contract.insert_row(conn = conn)
                else:
                    merged_contract = db.Contract.merge(db_contract, contract)                    
                    if db_contract.state != merged_contract.state:
                        log("Upd:  {merged_contract}", **locals())
                    merged_contract.update_row(conn = conn)

            except:
                log("Exception processing contract: {contract}", **locals())
                raise
                    
        log("Looking for contracts that disappeared from the queue")
        for contract in db.Contract.load_by_state(conn = conn, state = db.Contract.IN_QUEUE):
            if contract.contract_id not in seen_contracts:
                contract.state = db.Contract.GONE
                log("Gone: {contract}", **locals())
                contract.update_row(conn = conn)
                
        log("Looking for contracts that disappeared from the tracker")
        for contract in db.Contract.load_by_state(conn = conn, state = db.Contract.IN_PROGRESS):
            if contract.contract_id not in seen_contracts:
                contract.state = db.Contract.DONE
                log("Done: {contract}", **locals())
                contract.update_row(conn = conn)

        db.add_update_info(conn,
                           update_time = ncf_results['last_update'],
                           queue_count = len(ncf_results['contracts']), 
                           in_progress_count = len(tracker_results['contracts']))
        db.set_last_update(conn, ncf_results['last_update'])
        conn.commit()

        try:
            regenerate_graphs(conn)
        except:
            log("Exception generating graphs (ignored)")
            traceback.print_exc()

    except:
        log("Exception in update cycle")
        traceback.print_exc()
        return datetime.timedelta(minutes=5)

    finally:
        conn.close()

    refresh = max(ncf_results['refresh'], tracker_results['refresh'])
    log("Update cycle is done, next refresh in {refresh}", **locals())
    return refresh

def regenerate_graphs(conn):
    last_update, queue_contracts, accepted_contracts = queue.load(conn)            
    
    try:
        log("Regenerating 60-min queue graph")
        queue_60mins = last_update.strftime('graphs/queue_3600_%Y%m%d%H%M%S.png')
        graph.make_queue_graph(last_update = last_update, queue_contracts = queue_contracts, accepted_contracts = accepted_contracts, filename=queue_60mins, scale=3600)
        log("Uploading 60-min queue graph")
        upload.upload(f=queue_60mins, key_name='queue.png')
    except:
        log("Exception generating 60-min graph (ignored)")
        traceback.print_exc()        

    try:
        log("Regenerating 15-min queue graph")
        queue_15mins = last_update.strftime('graphs/queue_900_%Y%m%d%H%M%S.png')
        graph.make_queue_graph(last_update = last_update, queue_contracts = queue_contracts, accepted_contracts = accepted_contracts, filename=queue_15mins, scale=900)
        log("Uploading 15-min queue graph")
        upload.upload(f=queue_15mins, key_name='queue15.png')
    except:
        log("Exception generating 60-min graph (ignored)")
        traceback.print_exc()
    
    try:        
        log("Regenerating 1-day delivery time graph")
        delivery_1day = last_update.strftime('graphs/delivery_1day_%Y%m%d%H%M%S.png')
        contracts = db.Contract.load_completed_after(conn = conn, cutoff = last_update - datetime.timedelta(days=1))
        graph.make_delivery_graph(last_update = last_update, done_contracts = contracts, filename=delivery_1day, scale=3600, title="Red Frog delivery times - last day")
        log("Uploading 1-day delivery time graph")
        upload.upload(f=delivery_1day, key_name='delivery_1day.png')
    except:
        log("Exception generating 1-day delivery graph (ignored)")
        traceback.print_exc()

    try:        
        log("Regenerating 7-day delivery time graph")
        delivery_7day = last_update.strftime('graphs/delivery_7day_%Y%m%d%H%M%S.png')
        contracts = db.Contract.load_completed_after(conn = conn, cutoff = last_update - datetime.timedelta(days=7))
        graph.make_delivery_graph(last_update = last_update, done_contracts = contracts, filename=delivery_7day, scale=3600, title="Red Frog delivery times - last week")
        log("Uploading 7-day delivery time graph")
        upload.upload(f=delivery_7day, key_name='delivery_7day.png')
    except:
        log("Exception generating 7-day delivery graph (ignored)")
        traceback.print_exc()


def run_indefinitely():
    log("Starting up..")
    rfweb.init() # provoke errors early

    while True:
        delay = run_one_cycle() + datetime.timedelta(seconds = random.normalvariate(mu=0.0, sigma=15.0))
        log ("Sleeping for {delay}", **locals())
        time.sleep(delay.total_seconds())

if __name__ == '__main__':
    run_indefinitely()
