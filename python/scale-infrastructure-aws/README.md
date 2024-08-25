# AWS Infrastructure Management - Lambda Functions

This repository contains two AWS Lambda functions designed to stop and start infrastructure (EC2 instances, RDS instances, and EKS clusters) across multiple AWS regions based on tags. These Lambda functions are triggered by scheduled cron jobs at specific times and can also be triggered manually via Jenkins.

## Function Overview

### 1. Stop Infrastructure Lambda Function
This function performs the following actions every evening:
- Stops all EC2 instances tagged with `Autorestart: true`.
- Stops all RDS instances tagged with `Autorestart: true`.
- Scales down EKS clusters tagged with `Autorestart: true`.

### 2. Start Infrastructure Lambda Function
This function performs the following actions every morning:
- Starts all EC2 instances tagged with `Autorestart: true`.
- Starts all RDS instances tagged with `Autorestart: true`.
- Scales up EKS clusters tagged with `Autorestart: true`.

## Configuration

### AWS Regions
The functions target infrastructure in the following AWS regions:
- `us-east-1`
- `us-west-2`

You can modify the regions in the code by editing the `REGIONS` list.

### Tags
Only resources tagged with the following key-value pair will be managed by these functions:
- **Tag Key:** `Autorestart`
- **Tag Value:** `true`

Ensure that your EC2 instances, RDS instances, and EKS clusters are tagged accordingly to be included in the start/stop process.

## Cron Jobs

The two Lambda functions are scheduled using cron expressions in AWS Lambda. Here's how to set them up:

1. **Stop Infrastructure Function:** 
   - **Trigger Time:** 11:45 PM (daily)
   - **Cron Expression:** `cron(45 23 * * ? *)`

2. **Start Infrastructure Function:**
   - **Trigger Time:** 6:45 AM (daily)
   - **Cron Expression:** `cron(45 6 * * ? *)`

You can configure these cron jobs via the AWS Lambda console.

### Jenkins Integration

In addition to the cron jobs, these functions can be triggered manually via Jenkins as needed. Configure your Jenkins pipeline to trigger the Lambda functions at any time.

## Email Notification

If any resources fail to stop, start, or scale as expected, an email notification will be sent to the specified email address. The email will contain details of the failed resources.

- **Recipient Email:** `abc@def.com`
- **Email Service:** AWS SES (Simple Email Service)

### Setup AWS SES
To ensure that the email functionality works, make sure that:
- Your SES configuration is set up and verified.
- The email address `abc@def.com` is verified in SES.

## Error Handling

Both Lambda functions include error handling. If a resource fails to stop, start, or scale up/down, the error will be logged, and an email notification will be sent. The email is only triggered if there are failures, so no email is sent on success.

## How to Deploy

1. **Package the Code:**
   - Zip the contents of the Python code files (`lambda_function.py`) along with any required dependencies.
   - Deploy the zipped package to your Lambda function in the AWS console.

2. **Configure Lambda Execution Role:**
   - The Lambda functions require permissions to manage EC2, RDS, EKS, and SES. Ensure that the Lambda execution role has the appropriate permissions.

3. **Set up the Cron Job:**
   - Use the AWS console to create scheduled events for triggering the functions at the desired times.

## Dependencies

The functions use the following AWS services:
- **EC2 API**: To start and stop EC2 instances.
- **RDS API**: To start and stop RDS instances.
- **EKS API**: To scale up and down EKS clusters.
- **SES API**: To send email notifications in case of failures.

> **Note** :Ensure that the required permissions are granted to the Lambda execution role. The required IAM permission are also defined in the policy added in this repository

