#!/usr/bin/env bash

REGION=$1
STACK=$2
ASG_NAME=$3

# Method 1 - use python
META_ASG_1=$(aws cloudformation describe-stack-resource --region $REGION --stack-name $STACK \
    --logical-resource-id $ASG_NAME | python -c 'import json,sys;print json.load(sys.stdin)["StackResourceDetail"]["PhysicalResourceId"]')

# Method 2 - better method with query
META_ASG_2=$(aws cloudformation describe-stack-resource --region $REGION --stack-name $STACK \
    --logical-resource-id $ASG_NAME --query StackResourceDetail.PhysicalResourceId --output text)

echo META_ASG_2
exit 0
