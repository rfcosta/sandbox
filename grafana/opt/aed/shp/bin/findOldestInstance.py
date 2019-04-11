#!/usr/bin/python

import boto3
import dateutil
import datetime
import sys

if len(sys.argv) != 3:
    print ('Invalid arguments')
    sys.exit()

# Arguments
region = sys.argv[1]
asg = sys.argv[2]

# Setup Boto3 clients
autoscaling = boto3.client('autoscaling', region_name=region)
ec2 = boto3.client('ec2', region_name=region)

# Get AutoScaling groups
as_response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg])
instances = as_response['AutoScalingGroups'][0]['Instances']
oldesttime = datetime.datetime.utcnow()

# Iterate throught the instances in the auto scaling group and find the oldest
for i in instances:
    ec2_response = ec2.describe_instances(InstanceIds=[i['InstanceId']])
    if i['HealthStatus'] != "Healthy" or i['LifecycleState'] != "InService":
        # Do something... https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-describing-stacks.html

    lt = str(ec2_response['Reservations'][0]['Instances'][0]['LaunchTime'])
    #print(repr(lt))
    launchtime_raw = dateutil.parser.parse(lt)
    launchtime = launchtime_raw.replace(tzinfo=None)
    if launchtime < oldesttime:
        oldesttime = launchtime
        oldestID = i['InstanceId']

# Get the IP address of the oldest instance
ec2_response = ec2.describe_instances(InstanceIds=[oldestID])
ip = str(ec2_response['Reservations'][0]['Instances'][0]['PrivateIpAddress'])
print ip
