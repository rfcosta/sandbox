#!/usr/bin/env bash

REGION=$1
ASG=$2
DESIRED_COUNT=$3

count=$(aws autoscaling describe-auto-scaling-groups --region $REGION --auto-scaling-group-name $ASG --query AutoScalingGroups[0].DesiredCapacity --output text)

if [[ $count -lt $DESIRED_COUNT ]]
then
    count=$(($count + 1))
    aws autoscaling update-auto-scaling-group --region $REGION --auto-scaling-group-name $ASG --min-size $count --max-size $count --desired-capacity $count
fi

exit 0
