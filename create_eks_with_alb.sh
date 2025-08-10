#!/bin/bash
set -e

# ---------------------------
# CONFIGURATION
# ---------------------------
CLUSTER_NAME="snp500-prediction-cluster-v2"
REGION="us-east-1"
NODE_TYPE="m5.2xlarge"  # 8 vCPU, 32 GB memory per node
NODE_COUNT=1            # 2 nodes = 64 GB total
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

# ---------------------------
# CREATE EKS CLUSTER
# ---------------------------
echo "Creating EKS cluster: $CLUSTER_NAME in $REGION..."
eksctl create cluster \
  --name $CLUSTER_NAME \
  --region $REGION \
  --version 1.29 \
  --nodegroup-name standard-workers \
  --node-type $NODE_TYPE \
  --nodes $NODE_COUNT \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed

# ---------------------------
# ASSOCIATE IAM OIDC PROVIDER
# ---------------------------
echo "Associating IAM OIDC provider..."
eksctl utils associate-iam-oidc-provider \
  --region $REGION \
  --cluster $CLUSTER_NAME \
  --approve

# ---------------------------
# CREATE IAM POLICY FOR LOAD BALANCER CONTROLLER
# ---------------------------
echo "Creating IAM policy for AWS Load Balancer Controller..."
curl -o iam-policy.json \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam-policy.json || true

# ---------------------------
# CREATE IAM ROLE + SERVICE ACCOUNT
# ---------------------------
echo "Creating IAM service account for AWS Load Balancer Controller..."
eksctl create iamserviceaccount \
  --cluster $CLUSTER_NAME \
  --namespace kube-system \
  --name aws-load-balancer-controller \
  --attach-policy-arn arn:aws:iam::$AWS_ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# ---------------------------
# INSTALL CERT-MANAGER
# ---------------------------
echo "Installing cert-manager..."
helm repo add jetstack https://charts.jetstack.io
helm repo update

kubectl apply --validate=false -f \
  https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.crds.yaml

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.14.2

# ---------------------------
# INSTALL AWS LOAD BALANCER CONTROLLER
# ---------------------------
echo "Installing AWS Load Balancer Controller..."
helm repo add eks https://aws.github.io/eks-charts
helm repo update

VPC_ID=$(aws eks describe-cluster \
  --name $CLUSTER_NAME \
  --query "cluster.resourcesVpcConfig.vpcId" \
  --output text)

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set region=$REGION \
  --set vpcId=$VPC_ID \
  --namespace kube-system

# ---------------------------
# VERIFY
# ---------------------------
echo "Verifying AWS Load Balancer Controller installation..."
kubectl rollout status deployment/aws-load-balancer-controller -n kube-system
kubectl get deployment -n kube-system aws-load-balancer-controller

echo "✅ EKS cluster '$CLUSTER_NAME' with AWS Load Balancer Controller is ready!"
