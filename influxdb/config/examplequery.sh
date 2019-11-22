#!/bin/sh

# curl -G 'http://localhost:8086/query?pretty=true' \
#      --data-urlencode "db=kpi" \t
#      --data-urlencode "q=SELECT \"date\" FROM \"kpi\" \
#      WHERE \"region\"='us-west'"

RANGE="4m"
INTERVAL=60000ms

OPTION=${1:-sum}

echo "OPTION = $OPTION"

set -x
if [ "$OPTION" = "mean" ] ; then
	curl -G 'http://localhost:8086/query?pretty=true' \
	     --data-urlencode "db=_internal" \
	     --data-urlencode "q=SELECT mean(\"numSeries\") AS \"mean_numSeries\" 
	                       FROM \"_internal\".\"monitor\".\"database\" \
	                       WHERE time > now() -${RANGE}  AND \
	                        \"database\"='_internal' \
	                        GROUP BY time(${INTERVAL}) FILL(null)"
fi


if [ "$OPTION" = "count" ] ; then
	curl -G 'http://localhost:8086/query?pretty=true' \
	     --data-urlencode "db=_internal" \
	     --data-urlencode "q=SELECT count(\"numSeries\") AS \"count_numSeries\" 
	                       FROM \"_internal\".\"monitor\".\"database\" \
	                       WHERE time > now() -${RANGE}  AND \
	                        \"database\"='_internal' \
	                        GROUP BY time(${INTERVAL}) FILL(null)"
fi

if [ "$OPTION" = "sum" ] ; then
	curl -G 'http://localhost:8086/query?pretty=true' \
	     --data-urlencode "db=_internal" \
	     --data-urlencode "q=SELECT sum(\"numSeries\") AS \"sum_numSeries\" 
	                       FROM \"_internal\".\"monitor\".\"database\" \
	                       WHERE time > now() -${RANGE}  AND \
	                        \"database\"='_internal' \
	                        GROUP BY time(${INTERVAL}) FILL(null)"
fi

if [ "$OPTION" = "max" ] ; then
	curl -G 'http://localhost:8086/query?pretty=true' \
	     --data-urlencode "db=_internal" \
	     --data-urlencode "q=SELECT max(\"numSeries\") AS \"max_numSeries\" 
	                       FROM \"_internal\".\"monitor\".\"database\" \
	                       WHERE time > now() -${RANGE}  AND \
	                        \"database\"='_internal' \
	                        GROUP BY time(${INTERVAL}) FILL(null)"
fi



