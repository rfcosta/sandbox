#!/usr/bin/env bash

AWS_REGION=$1
META_ASG=$2
NODETYPE=$3
#debug=/var/log/debug.log

[[ -z $debug ]] || echo "$0" >>$debug
[[ -z $debug ]] || echo "AWS_REGION=\"$AWS_REGION\", META_ASG=\"$META_ASG\", NODETYPE=\"$NODETYPE\"" >>$debug

LOCAL_IP=$(hostname -I | sed -e 's/[[:space:]]*$//')
INSTANCE_IDS=$(aws autoscaling describe-auto-scaling-instances --region "$AWS_REGION" --output text --query "AutoScalingInstances[?AutoScalingGroupName=='$META_ASG'].InstanceId")
AWS_HOSTS=$(aws ec2 describe-instances --region "$AWS_REGION" --instance-ids $INSTANCE_IDS --query Reservations[].Instances[].PrivateIpAddress --output text)

[[ -z $debug ]] || echo "LOCAL_IP=\"$LOCAL_IP\", INSTANCE_IDS=\"$INSTANCE_IDS\", AWS_HOSTS=\"$AWS_HOSTS\"" >>$debug

for HOST in ${AWS_HOSTS}; do
  if [ "${HOST}" == "${LOCAL_IP}" ]; then
    continue
  fi
  echo "${HOST}"
  exit 0
done

if [ "${NODETYPE}" == "meta" ]; then
  echo "${LOCAL_IP}"
fi
exit 0
