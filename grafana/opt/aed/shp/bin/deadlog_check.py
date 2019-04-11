import json

#Change these to the data/time you want to look at
timeStartString = "2019-02-08T03:3"
timeEndString = "2019-02-08T07:3"

summaryJSON = {}

with open('/var/log/shp/deadman_alerts.log') as deadLog:
    for line in deadLog:
        if -1 != line.find(timeStartString):
            break

    for line in deadLog:
            service = ""
            key = ""
            deadTime = ""
            if -1 != line.find(timeEndString):
                break
            lineJSON = json.loads(line)
            if "data" in lineJSON:
                if "series" in lineJSON["data"]:
                    if "tags" in lineJSON["data"]["series"][0]:
                        if "ci" in lineJSON["data"]["series"][0]["tags"]:
                            service = str(lineJSON["data"]["series"][0]["tags"]["ci"])
                            if "key" in lineJSON["data"]["series"][0]["tags"]:
                                key = str(lineJSON["data"]["series"][0]["tags"]["key"])
                                if "columns" in lineJSON["data"]["series"][0]:
                                    if "values" in lineJSON["data"]["series"][0]:
                                        timeIndex = lineJSON["data"]["series"][0]["columns"].index("time")
                                        deadTime = str(lineJSON["data"]["series"][0]["values"][0][timeIndex])
                                        # Add this to summaryJson
                                        if service not in summaryJSON:
                                            summaryJSON[service] = {}
                                        if key not in summaryJSON[service]:
                                            summaryJSON[service][key] = []
                                        if deadTime not in summaryJSON[service][key]:
                                            summaryJSON[service][key].append(deadTime)

print summaryJSON