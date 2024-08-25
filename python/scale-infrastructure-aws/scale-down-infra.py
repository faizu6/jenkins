import boto3
import logging

REGIONS = ['us-east-1', 'us-west-2']
TAG_KEY = 'Autorestart'
TAG_VALUE = 'true'
SES_EMAIL = 'abc@def.com'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

failed_resources = []

def stop_ec2_instances(region):
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        instances = ec2_client.describe_instances(
            Filters=[{'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]}]
        )
        instance_ids = [instance['InstanceId'] for reservation in instances['Reservations'] 
                        for instance in reservation['Instances'] if instance['State']['Name'] == 'running']
        
        if instance_ids:
            ec2_client.stop_instances(InstanceIds=instance_ids)
            logger.info(f'Stopped EC2 instances: {instance_ids} in region {region}')
        return instance_ids
    except Exception as e:
        logger.error(f"Error stopping EC2 instances in region {region}: {str(e)}")
        failed_resources.append(f"EC2 in {region}: {str(e)}")
        return []

def stop_rds_instances(region):
    try:
        rds_client = boto3.client('rds', region_name=region)
        instances = rds_client.describe_db_instances()
        stopped_instances = []
        
        for instance in instances['DBInstances']:
            tags = rds_client.list_tags_for_resource(ResourceName=instance['DBInstanceArn'])['TagList']
            if any(tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE for tag in tags) and instance['DBInstanceStatus'] == 'available':
                rds_client.stop_db_instance(DBInstanceIdentifier=instance['DBInstanceIdentifier'])
                logger.info(f'Stopped RDS instance: {instance["DBInstanceIdentifier"]} in region {region}')
                stopped_instances.append(instance['DBInstanceIdentifier'])
        return stopped_instances
    except Exception as e:
        logger.error(f"Error stopping RDS instances in region {region}: {str(e)}")
        failed_resources.append(f"RDS in {region}: {str(e)}")
        return []

def scale_down_eks_clusters(region):
    try:
        eks_client = boto3.client('eks', region_name=region)
        clusters = eks_client.list_clusters()['clusters']
        scaled_down_clusters = []
        
        for cluster_name in clusters:
            cluster_info = eks_client.describe_cluster(name=cluster_name)
            if cluster_info['cluster']['tags'].get(TAG_KEY) == TAG_VALUE:
                # Example: Set desired capacity to 0 for node group scaling
                nodegroups = eks_client.list_nodegroups(clusterName=cluster_name)['nodegroups']
                for nodegroup in nodegroups:
                    eks_client.update_nodegroup_config(
                        clusterName=cluster_name,
                        nodegroupName=nodegroup,
                        scalingConfig={'desiredSize': 0}
                    )
                logger.info(f'Scaled down EKS cluster: {cluster_name} in region {region}')
                scaled_down_clusters.append(cluster_name)
        return scaled_down_clusters
    except Exception as e:
        logger.error(f"Error scaling down EKS clusters in region {region}: {str(e)}")
        failed_resources.append(f"EKS in {region}: {str(e)}")
        return []

def check_infrastructure_state(region):
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        rds_client = boto3.client('rds', region_name=region)
        eks_client = boto3.client('eks', region_name=region)

        # Check if EC2 instances are stopped
        instances = ec2_client.describe_instances(
            Filters=[{'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]}]
        )
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] != 'stopped':
                    failed_resources.append(f"EC2 instance {instance['InstanceId']} in {region} is not stopped.")

        # Check if RDS instances are stopped
        instances = rds_client.describe_db_instances()
        for instance in instances['DBInstances']:
            tags = rds_client.list_tags_for_resource(ResourceName=instance['DBInstanceArn'])['TagList']
            if any(tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE for tag in tags):
                if instance['DBInstanceStatus'] != 'stopped':
                    failed_resources.append(f"RDS instance {instance['DBInstanceIdentifier']} in {region} is not stopped.")

        # Check if EKS clusters are scaled down
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
                    if nodegroup_info['nodegroup']['scalingConfig']['desiredSize'] != 0:
                        failed_resources.append(f"EKS nodegroup {nodegroup} in {region} is not scaled down.")
    except Exception as e:
        logger.error(f"Error checking infrastructure state in region {region}: {str(e)}")
        failed_resources.append(f"State check error in {region}: {str(e)}")

def send_failure_email():
    if failed_resources:
        ses_client = boto3.client('ses')
        subject = "Infrastructure Scaling Failure"
        body = f"The following resources failed to stop or scale down:\n" + "\n".join(failed_resources)
        
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
        # Attempt to stop/scale down the infrastructure
        for region in REGIONS:
            stop_ec2_instances(region)
            stop_rds_instances(region)
            scale_down_eks_clusters(region)
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

