#!/bin/sh

# experimental - animate a week's worth of queue state

# find last 168 hours worth of 60-min graphs (= 672 graphs)
# pick every 4th graph
cd `dirname $0`/graphs
lastweek=$(
 ls queue_3600_*.png |
  sort -n |
  tail -672 | (
  while read x
  do
    echo $x
    read x
    read x
    read x
  done
 )
)

convert -layers optimize -delay 10 -loop 0 $lastweek lastweek-animated.gif

