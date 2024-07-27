#!/bin/bash

#Create a python virtual environment named trivy-venv
python3 -m venv nuclei-venv

#Activate the virtual environment
source nuclei-venv/bin/activate

#Install the required package within the virtual environment
pip install -r requirements.txt

#Run the python code to scan the repositories in the bitbucket
python3 nuclei-scan.py

#Deactivate the virtual environment
deactivate
