#!/usr/bin/python
import json
import pprint
from InfluxdCtlUtil import InfluxdCtlUtil

debug = True

iUtil = InfluxdCtlUtil(debug)
cluster_node_data = iUtil.show("example_show.output")

if debug:
    print("============================================")
    pprint.pprint(cluster_node_data)

    for node_type in cluster_node_data.keys():
        print("DEBUG: " + node_type + " nodes ---")
        pprint.pprint(cluster_node_data[node_type]);


    print("============================================")

for node_type in cluster_node_data.keys():
    nodes = cluster_node_data[node_type]
    for item in nodes:
        if not item['version']:
            status = "DOWN"
        else:
            status = "UP"

        print(node_type + " node " + item['ip'] + "\t port " + item['port'] + "\t is " + status)



