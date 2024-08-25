import boto3
import logging

REGIONS = ['us-east-1', 'us-west-2']
TAG_KEY = 'Autorestart'
TAG_VALUE = 'true'
SES_EMAIL = 'abc@def.com'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

failed_resources = []

def start_ec2_instances(region):
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        instances = ec2_client.describe_instances(
            Filters=[{'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]}]
        )
        instance_ids = [instance['InstanceId'] for reservation in instances['Reservations'] 
                        for instance in reservation['Instances'] if instance['State']['Name'] == 'stopped']
        
        if instance_ids:
            ec2_client.start_instances(InstanceIds=instance_ids)
            logger.info(f'Started EC2 instances: {instance_ids} in region {region}')
        return instance_ids
    except Exception as e:
        logger.error(f"Error starting EC2 instances in region {region}: {str(e)}")
        failed_resources.append(f"EC2 in {region}: {str(e)}")
        return []

def start_rds_instances(region):
    try:
        rds_client = boto3.client('rds', region_name=region)
        instances = rds_client.describe_db_instances()
        started_instances = []
        
        for instance in instances['DBInstances']:
            tags = rds_client.list_tags_for_resource(ResourceName=instance['DBInstanceArn'])['TagList']
            if any(tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE for tag in tags) and instance['DBInstanceStatus'] == 'stopped':
                rds_client.start_db_instance(DBInstanceIdentifier=instance['DBInstanceIdentifier'])
                logger.info(f'Started RDS instance: {instance["DBInstanceIdentifier"]} in region {region}')
                started_instances.append(instance['DBInstanceIdentifier'])
        return started_instances
    except Exception as e:
        logger.error(f"Error starting RDS instances in region {region}: {str(e)}")
        failed_resources.append(f"RDS in {region}: {str(e)}")
        return []

def scale_up_eks_clusters(region):
    try:
        eks_client = boto3.client('eks', region_name=region)
        clusters = eks_client.list_clusters()['clusters']
        scaled_up_clusters = []
        
        for cluster_name in clusters:
            cluster_info = eks_client.describe_cluster(name=cluster_name)
            if cluster_info['cluster']['tags'].get(TAG_KEY) == TAG_VALUE:
                nodegroups = eks_client.list_nodegroups(clusterName=cluster_name)['nodegroups']
                for nodegroup in nodegroups:
                    eks_client.update_nodegroup_config(
                        clusterName=cluster_name,
                        nodegroupName=nodegroup,
                        scalingConfig={'desiredSize': 3}
                    )
                logger.info(f'Scaled up EKS cluster: {cluster_name} in region {region}')
                scaled_up_clusters.append(cluster_name)
        return scaled_up_clusters
    except Exception as e:
        logger.error(f"Error scaling up EKS clusters in region {region}: {str(e)}")
        failed_resources.append(f"EKS in {region}: {str(e)}")
        return []

def check_infrastructure_state(region):
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        rds_client = boto3.client('rds', region_name=region)
        eks_client = boto3.client('eks', region_name=region)

        # Check if EC2 instances are started
        instances = ec2_client.describe_instances(
            Filters=[{'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]}]
        )
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] != 'running':
                    failed_resources.append(f"EC2 instance {instance['InstanceId']} in {region} is not started.")

        # Check if RDS instances are started
        instances = rds_client.describe_db_instances()
        for instance in instances['DBInstances']:
            tags = rds_client.list_tags_for_resource(ResourceName=instance['DBInstanceArn'])['TagList']
            if any(tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE for tag in tags):
                if instance['DBInstanceStatus'] != 'available':
                    failed_resources.append(f"RDS instance {instance['DBInstanceIdentifier']} in {region} is not started.")

        # Check if EKS clusters are scaled up
        clusters = eks_client.list_clusters()['clusters']
        for cluster_name in clusters:
            cluster_info = eks_client.describe_cluster(name=cluster_name)
            if cluster_info['cluster']['tags'].get(TAG_KEY) == TAG_VALUE:
                nodegroups = eks_client.list_nodegroups(clusterName=cluster_name)['nodegroups']
                for nodegroup in nodegroups:
                    nodegroup_info = eks_client.describe_nodegroup(
                        clusterName=cluster_name,
                        nodegroupName=nodegroup
                    )
                    if nodegroup_info['nodegroup']['scalingConfig']['desiredSize'] <= 0:
                        failed_resources.append(f"EKS nodegroup {nodegroup} in {region} is not scaled up.")
    except Exception as e:
        logger.error(f"Error checking infrastructure state in region {region}: {str(e)}")
        failed_resources.append(f"State check error in {region}: {str(e)}")

def send_failure_email():
    if failed_resources:
        ses_client = boto3.client('ses')
        subject = "Infrastructure Start Failure"
        body = f"The following resources failed to start or scale up:\n" + "\n".join(failed_resources)
        
        try:
            ses_client.send_email(
                Source=SES_EMAIL,
                Destination={'ToAddresses': [SES_EMAIL]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Text': {'Data': body}}
                }
            )
            logger.info("Sent failure email.")
        except Exception as e:
            logger.error(f"Error sending failure email: {str(e)}")

def lambda_handler(event, context):
    try:
        # Attempt to start/scale up the infrastructure
        for region in REGIONS:
            start_ec2_instances(region)
            start_rds_instances(region)
            scale_up_eks_clusters(region)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        failed_resources.append(f"General Error: {str(e)}")
    finally:
        # Check infrastructure state and only send an email if there are failures
        try:
            for region in REGIONS:
                check_infrastructure_state(region)
        finally:
            if failed_resources:  # Only send email if there are failures
                send_failure_email()

