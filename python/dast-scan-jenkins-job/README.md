# README #
## What is this Repository for? ##

The purpose of this repository is to manage the process of scanning BitBucket repositories for DAST (Dynamic Application Security Testing) vulnerabilities 
using Nuclei within a Jenkins environment.

Within this repository, you will find the following files:

1. `requirements.txt`: This file lists the Python dependencies required for the project.

2. `scan.sh`: A Bash script designed to create a virtual environment install necessary dependencies, and execute the Python code.

3. `nuclei-scan.py`: The primary file written in python responsible for scanning BitBucket repositories for DAST vulnerabilities and uploading the resulting vulnerability list to the corresponding google-spreadsheet and in the AWS S3 bucket.

## Requirements
The below software packages should already installed in the jenkins server to run the scans.
1. Python3
2. Nuclei

## How to use ?
To initiate scanning, a Jenkins job is supposed to be created. The Jenkins job will have the below mentioned parameters;

| **Parameter Name** 	| **Description** | **Parameter Type** |
|--- |--- |--- |
| `SpreadSheet_ID` | The unique ID of the SpreadSheet | Password Parameter 	|
| `Spreadsheet_Key` | The json key downloaded from the google organisation account| Password Parameter |
| `ENDPOINTS` | The list of endpoints to be scanned should be mentioned in value of this parameter | Multi-line String Parameter 	|
| `Bucket` | The AWS S3 bucket where the logs should be pushed | String Parameter |
| `FOLDER_NAME` | The AWS S3 bucket where the logs should be pushed | String Parameter |



Finally, the below mentioned script should be added in the pipeline script.
Build Steps > Execute Shell

```
git clone https://github.com/faizu6/jenkins.git
cd python/dast-scan-jenkins-job
./scan.sh
```
**Note** : you can yourself clone the repository and customize if needed, then run the job accordingly 

**Info** : If required a cron schedular can also be set for the job.

