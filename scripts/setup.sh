#!/bin/bash
set -e
REGION="us-east-1"

# 1. S3
aws s3 mb s3://instabox-vicky-2026 --region $REGION

# 2. RDS
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
  --query "Vpcs[0].VpcId" --output text --region $REGION)

DB_SG_ID=$(aws ec2 create-security-group \
  --group-name instabox-db-sg \
  --description "SG para RDS de InstaBox" \
  --vpc-id $VPC_ID \
  --query "GroupId" --output text --region $REGION)

aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG_ID \
  --protocol tcp --port 5432 \
  --cidr 0.0.0.0/0 \
  --region $REGION

aws rds create-db-instance \
  --db-instance-identifier instabox-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username instabox_admin \
  --master-user-password "CasaRivera347" \
  --allocated-storage 20 \
  --vpc-security-group-ids $DB_SG_ID \
  --publicly-accessible \
  --region $REGION

aws rds wait db-instance-available --db-instance-identifier instabox-db --region $REGION

# 3. Secrets Manager
RDS_HOST=$(aws rds describe-db-instances --db-instance-identifier instabox-db \
  --query "DBInstances[0].Endpoint.Address" --output text --region $REGION)

SECRET_JSON=$(cat <<EOF
{
  "host": "$RDS_HOST",
  "port": 5432,
  "dbname": "postgres",
  "username": "instabox_admin",
  "password": "CasaRivera347"
}
EOF
)

aws secretsmanager create-secret \
  --name "instabox/db-credentials" \
  --secret-string "$SECRET_JSON" --region $REGION

# 4. EC2
aws ec2 create-key-pair --key-name instabox-key \
  --query 'KeyMaterial' --output text --region $REGION > instabox-key.pem
chmod 400 instabox-key.pem

EC2_SG_ID=$(aws ec2 create-security-group \
  --group-name instabox-ec2-sg \
  --description "SG para EC2 de InstaBox" \
  --query "GroupId" --output text --region $REGION)

aws ec2 authorize-security-group-ingress --group-id $EC2_SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $REGION
aws ec2 authorize-security-group-ingress --group-id $EC2_SG_ID \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region $REGION

aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG_ID \
  --protocol tcp --port 5432 \
  --source-group $EC2_SG_ID \
  --region $REGION

AMI_ID=$(aws ec2 describe-images --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-*-amd64-server-*" \
  --query "sort_by(Images,&CreationDate)[-1].ImageId" --output text --region $REGION)

aws ec2 run-instances \
  --image-id $AMI_ID \
  --count 1 \
  --instance-type t3.micro \
  --key-name instabox-key \
  --security-group-ids $EC2_SG_ID \
  --iam-instance-profile Name=LabInstanceProfile \
  --region $REGION \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=instabox}]'

echo "Recursos creados. Espera un momento y saca la IP publica con:"
echo "aws ec2 describe-instances --query \"Reservations[*].Instances[*].{ID:InstanceId,IP:PublicIpAddress,State:State.Name}\" --output table --region $REGION"