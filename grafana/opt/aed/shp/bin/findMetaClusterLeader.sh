#!/usr/bin/env bash

REGION=$1
ASG=$2
NODETYPE=$3

LOCAL_IP=$(hostname -I | sed -e 's/[[:space:]]*$//')
AWS_TEMP=$(aws autoscaling describe-auto-scaling-instances --region $REGION --output text \
    --query "AutoScalingInstances[?AutoScalingGroupName=='$ASG'].InstanceId")
AWS_HOSTS=$(aws ec2 describe-instances --region $REGION --instance-ids $AWS_TEMP \
    --query Reservations[].Instances[].PrivateIpAddress --output text)

for HOST in ${AWS_HOSTS}
do
  if [ "${HOST}" == "${LOCAL_IP}" ] ; then
    continue;
  fi
  echo ${HOST}
  exit 0
done

if [ "${NODETYPE}" == "meta" ] ; then
  echo ${LOCAL_IP}
fi
exit 0
