#!/bin/bash
set -e
REGION="us-east-1"

echo "Buscando recursos de InstaBox..."

EC2_INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=instabox" "Name=instance-state-name,Values=running,stopped" \
  --query "Reservations[0].Instances[0].InstanceId" --output text --region $REGION)

EC2_SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=instabox-ec2-sg \
  --query "SecurityGroups[0].GroupId" --output text --region $REGION)

DB_SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=instabox-db-sg \
  --query "SecurityGroups[0].GroupId" --output text --region $REGION)

# 1. EC2
if [ "$EC2_INSTANCE_ID" != "None" ]; then
  aws ec2 terminate-instances --instance-ids $EC2_INSTANCE_ID --region $REGION
  aws ec2 wait instance-terminated --instance-ids $EC2_INSTANCE_ID --region $REGION
fi

# 2. RDS (sin snapshot final, es un lab)
aws rds delete-db-instance --db-instance-identifier instabox-db \
  --skip-final-snapshot --region $REGION
aws rds wait db-instance-deleted --db-instance-identifier instabox-db --region $REGION

# 3. Secret
aws secretsmanager delete-secret --secret-id instabox/db-credentials \
  --force-delete-without-recovery --region $REGION

# 4. S3
aws s3 rm s3://instabox-vicky-2026 --recursive --region $REGION
aws s3 rb s3://instabox-vicky-2026 --region $REGION

# 5. Security groups y key pair (despues de que EC2 y RDS ya no existan)
aws ec2 delete-security-group --group-id $EC2_SG_ID --region $REGION
aws ec2 delete-security-group --group-id $DB_SG_ID --region $REGION
aws ec2 delete-key-pair --key-name instabox-key --region $REGION

echo "Recursos de InstaBox eliminados."