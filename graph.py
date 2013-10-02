#!/usr/bin/env python2.7

import queue, tempfile, subprocess, contextlib, datetime
from contextlib import closing, contextmanager

@contextmanager
def r_subprocess():
    """ Context manager; use as 

with r_subprocess() as r:
    # Here, a R subprocess is running and awaiting commands on the file object 'r'
    # R's stdout and stderr go to the provided logger
    print >>r, 'some r commands'
    # On exit from the 'with' block, 'r' is closed and we wait for R to exit
"""
    r = subprocess.Popen(args=['R', '--vanilla', '--no-readline', '--slave'],
                         stdin=subprocess.PIPE,
                         stdout=None,
                         stderr=subprocess.STDOUT,
                         close_fds=True)
    yield r.stdin # caller does their work
    r.stdin.close()
    if r.wait() != 0:
        raise RuntimeError('R exited with status %s' % r.returncode)

def make_queue_graph(last_update, queue_contracts, accepted_contracts, filename, scale=3600):
    with closing(tempfile.NamedTemporaryFile()) as inqueue_file, closing(tempfile.NamedTemporaryFile()) as inprogress_file, r_subprocess() as r:
        queue_valid = filter(lambda x: x.created_min is not None and x.created_min < last_update, queue_contracts)
        accepted_valid = filter(lambda x: x.created_min is not None and x.created_min < last_update, accepted_contracts)

        print >>inqueue_file, 'contractid,age'
        for contract in queue_valid:
            print >>inqueue_file, '{contract_id},{age}'.format(contract_id = contract.contract_id,
                                                               age = (last_update - contract.created_min).total_seconds() - 1)
        inqueue_file.flush()

        print >>inprogress_file, 'contractid,age'
        for contract in accepted_valid:
            print >>inprogress_file, '{contract_id},{age}'.format(contract_id = contract.contract_id,
                                                                  age = (last_update - contract.created_min).total_seconds() - 1)
        inprogress_file.flush()

        bucketsize = int(scale / 60)

        

        print >>r, '''
iq <- read.csv("{inqueue_file.name}", header=TRUE)
iq <- iq[iq$age < 3600*72, ]
ip <- read.csv("{inprogress_file.name}", header=TRUE)
ip <- ip[ip$age < 3600*72, ]

xmax = min(3600*72, max(3600*48, iq$age, ip$age))
xmax = ceiling(xmax / 7200) * 7200
breaks <- seq(0, xmax, {scale})

iqh.lt24 <- hist(iq[iq$age < 3600*24,]$age, breaks=breaks, plot=FALSE)$counts
iph.lt24 <- hist(ip[ip$age < 3600*24,]$age, breaks=breaks, plot=FALSE)$counts
iqh.gt24 <- hist(iq[(iq$age >= 3600*24) & (iq$age < 3600*48), ]$age, breaks=breaks, plot=FALSE)$counts
iph.gt24 <- hist(ip[(ip$age >= 3600*24) & (ip$age < 3600*48), ]$age, breaks=breaks, plot=FALSE)$counts
iqh.gt48 <- hist(iq[(iq$age >= 3600*48) & (iq$age < 3600*72), ]$age, breaks=breaks, plot=FALSE)$counts
iph.gt48 <- hist(ip[(ip$age >= 3600*48) & (ip$age < 3600*72), ]$age, breaks=breaks, plot=FALSE)$counts

ymax = max(iqh.lt24 + iph.lt24, iqh.gt24 + iph.gt24, iqh.gt48 + iph.gt48)

m <- matrix(data = c(iph.lt24, iqh.lt24, iph.gt24, iqh.gt24, iph.gt48, iqh.gt48),
            nrow=6, ncol=length(iqh.lt24), byrow=TRUE,
            dimnames=list(c('in progress <24', 'in queue <24', 'in progress 24-48', 'in queue 24-48', 'in progress >48', 'in queue >48'), 
                          breaks[-(1:1)]/3600))

png(filename="{filename}", width=800, height=400)
barplot(m,
        legend.text = c('in transit (<24h)', 
                        'in queue (<24h)',
                        'in transit (24-48h)',
                        'in queue (24-48h)',
                        'in transit (>48h)',
                        'in queue (>48h)'), 
        xlab="contract age (hours)",
        ylab="undelivered contracts",
        main="Red Frog queue ({bucketsize}min buckets)",
        sub="last updated {last_update} GMT",
        space=0.2,
        xlim=c(0,1.2*xmax/{scale}), ylim=c(0,ymax), 
        col=c('#006000','#00E000','#606000','#D0D000','#800000','#FF0000'), 
        axisnames=FALSE,
        border=NA)
axis(1,
     at=seq(0, xmax/{scale}*1.2, 7200/{scale}*1.2) + 0.1,
     labels=seq(0, xmax/3600, 2),
     tick=TRUE)
'''.format(**locals())

def make_delivery_graph(last_update, done_contracts, filename, title, scale=3600):
    with closing(tempfile.NamedTemporaryFile()) as done_file, r_subprocess() as r:
        done_valid = filter(lambda x: x.created_min is not None, done_contracts)

        print >>done_file, 'contractid,age'
        for contract in done_valid:
            print >>done_file, '{contract_id},{age}'.format(contract_id = contract.contract_id,
                                                            age = (contract.last_seen - contract.created_min).total_seconds() - 1)
        done_file.flush()

        bucketsize = int(scale / 60)

        print >>r, '''
d <- read.csv("{done_file.name}", header=TRUE)
d <- d[d$age < 3600*72, ]

xmax = min(3600*72, max(3600*48, d$age))
xmax = ceiling(xmax / 7200) * 7200
breaks <- seq(0, xmax, {scale})

dh.lt24 <- hist(d[d$age < 3600*24,]$age, breaks=breaks, plot=FALSE)$counts
dh.gt24 <- hist(d[(d$age >= 3600*24) & (d$age < 3600*48), ]$age, breaks=breaks, plot=FALSE)$counts
dh.gt48 <- hist(d[(d$age >= 3600*48) & (d$age < 3600*72), ]$age, breaks=breaks, plot=FALSE)$counts
total <- sum(dh.lt24) + sum(dh.gt24) + sum(dh.gt48)

ymax = max(dh.lt24, dh.gt24, dh.gt48) * 100 / total

m <- matrix(data = c(dh.lt24, dh.gt24, dh.gt48),
            nrow=3, ncol=length(dh.lt24), byrow=TRUE,
            dimnames=list(c('<24', '24-48', '>48'),
                          breaks[-(1:1)]/3600)) * 100 / total

png(filename="{filename}", width=800, height=400)
barplot(m,
        legend.text = c(sprintf('<24h (%.0f%%)', 100 * sum(dh.lt24) / total), 
                        sprintf('24-48h (%.0f%%)', 100 * sum(dh.gt24) / total),
                        sprintf('>48h (%.0f%%)', 100 * sum(dh.gt48) / total)), 
        xlab="delivery time (hours)",
        ylab="% delivered",
        main="{title}",
        sub="last updated {last_update} GMT",
        space=0.2,
        xlim=c(0,1.2*xmax/{scale}), ylim=c(0,ymax), 
        col=c('#00E000','#D0D000','#FF0000'), 
        axisnames=FALSE,
        border=NA)
axis(1,
     at=seq(0, xmax/{scale}*1.2, 7200/{scale}*1.2) + 0.1,
     labels=seq(0, xmax/3600, 2),
     tick=TRUE)
'''.format(**locals())


def make_history_graph(queue_history, filename, title):    
    last_update = max([x[0] for x in queue_history])

    with closing(tempfile.NamedTemporaryFile()) as history_file, r_subprocess() as r:
        print >>history_file, 'time,iq24,iq48,iq72,ip24,ip48,ip72'    
        for row in queue_history:
            print >>history_file, '{0},{1},{2},{3},{4},{5},{6}'.format(*row)

        history_file.flush()
        
        print >>r, '''
d <- read.csv("{history_file.name}", header=TRUE, colClasses=c("POSIXct","numeric","numeric","numeric","numeric","numeric","numeric"))

ymax <- max(d$iq24 + d$iq48 + d$iq72 + d$ip24 + d$ip48 + d$ip72) * 1.20

# with antialias=none, this is very sensitive to res vs. lwd - be careful
png(filename="{filename}", width=800, height=400, antialias="none", res=96)
par(cex=0.75, lwd=1, xpd=TRUE)
plot(x=d$time,
     y=d$iq24 + d$iq48 + d$iq72 + d$ip24 + d$ip48 + d$ip72,
     type="h",
     col="#FF0000",
     xlab="date",
     ylab="number of contracts",
     ylim=c(0,ymax),
     main="{title}",
     sub="last updated {last_update} GMT",
     frame.plot=FALSE)
lines(x=d$time,
      y=d$iq24 + d$iq48 + d$ip24 + d$ip48 + d$ip72,
      type="h",
      col="#D0D000")
lines(x=d$time,
      y=d$iq24 + d$ip24 + d$ip48 + d$ip72,
      type="h",
      col="#00E000")
lines(x=d$time,
      y=d$ip24 + d$ip48 + d$ip72,
      type="h",
      col="#800000")
lines(x=d$time,
      y=d$ip24 + d$ip48,
      type="h",
      col="#606000")
lines(x=d$time,
      y=d$ip24,
      type="h",
      col="#006000")
legend("topright",
       legend=c('in transit (<24h)', 
                'in queue (<24h)',
                'in transit (24-48h)',
                'in queue (24-48h)',
                'in transit (>48h)',
                'in queue (>48h)'),
       ncol=3,
       col=c("#006000", "#00E000", "#606000", "#D0D000", "#800000", "#FF0000"),
       lty=1)
'''.format(**locals())

if __name__ == '__main__':
    import queue, db
    with closing(db.new_connection(initdb=False)) as conn:
        last_update, queue_contracts, accepted_contracts = queue.load(conn)
        done_1day = db.Contract.load_completed_after(conn = conn, cutoff = last_update - datetime.timedelta(days=1))
        done_7day = db.Contract.load_completed_after(conn = conn, cutoff = last_update - datetime.timedelta(days=7))
        history = db.load_queue_history(conn = conn, first_update = last_update - datetime.timedelta(days=7), last_update = last_update)

    make_queue_graph(last_update, queue_contracts, accepted_contracts, scale=3600, filename="queue_3600.png")
    make_queue_graph(last_update, queue_contracts, accepted_contracts, scale=900, filename="queue_900.png")
    make_delivery_graph(last_update, done_1day, scale=3600, filename="delivery_1day.png", title="Red Frog delivery times - last day")
    make_delivery_graph(last_update, done_7day, scale=3600, filename="delivery_7day.png", title="Red Frog delivery times - last week")
    make_history_graph(history, filename="queue_history_7day.png", title="Red Frog queue size - last week")
