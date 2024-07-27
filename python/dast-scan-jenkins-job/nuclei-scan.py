import json
import subprocess
import os
import datetime
import re
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account

DATE = datetime.datetime.now().strftime('%Y-%m-%d')
YEAR = datetime.datetime.now().strftime('%Y')
MONTH = datetime.datetime.now().strftime('%m')

ENDPOINTS = os.getenv('ENDPOINTS')
BUCKET = os.getenv('BUCKET')
FOLDER_NAME = os.getenv('FOLDER_NAME')

log_file =  f"{FOLDER_NAME}.log"
json_file = f"{FOLDER_NAME}-{DATE}.json"

def run_nuclei(FOLDER_NAME, json_file, log_file):
     command = f'nuclei -header \'User-Agent: Jenkins-Nuclei-Scans\' -list {FOLDER_NAME}.txt -es info -json-export {json_file} -o {log_file} -exclude-templates ssl/untrusted-root-certificate.yaml'

     try:
         subprocess.run(command, shell=True, check=True)
         print(f"Command executed successfully for: {FOLDER_NAME} endpoints")
     except subprocess.CalledProcessError as e:
         print(f"Error for endpoint {FOLDER_NAME}: {e}")


def parse_log_file(log_file):
    data = []

    with open(log_file, 'r') as log_file:
        lines = log_file.readlines()

    for line in lines:
        match = re.match(r'\[(\S+)\]\s+\[(\S+)\]\s+\[(\S+)\]\s+(\S+)', line)
        if match:
            data.append([match.group(1), match.group(3), match.group(4)])
        else:
            print(f"Line not matched: {line}")
    return data

def copy_to_s3(json_file, BUCKET, FOLDER_NAME, YEAR, MONTH):
    os.environ['AWS_PROFILE'] = 'siem'
    s3_copy_command = f"aws s3 cp {json_file} s3://{BUCKET}/{FOLDER_NAME}/{YEAR}/{MONTH}/ --profile siem"

    try:
        subprocess.run(s3_copy_command, shell=True, check=True)
        print(f"File pushed to S3: {json_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def copy_endpoints_to_file(FOLDER_NAME):   
    if ENDPOINTS is not None:
        with open(f'{FOLDER_NAME}.txt', 'w') as txt_file:
            txt_file.write(ENDPOINTS)

        print(f"endpoints data saved to {FOLDER_NAME}.txt")
    else:
        print("Environment variable 'ENDPOINT' not set.")

def setup_spreadsheet_key():
    spreadsheet_key = os.getenv('Spreadsheet_Key')
    
    if spreadsheet_key is not None:
        spreadsheet_key = spreadsheet_key.replace("'", "").rstrip(',')
        spreadsheet_key_dict = json.loads(spreadsheet_key)

        with open('spreadsheet-key.json', 'w') as json_file:
            json.dump(spreadsheet_key_dict, json_file, indent=2)

        print("JSON data saved to spreadsheet-key.json")
    else:
        print("Environment variable 'Spreadsheet_Key' not set.")

def get_credentials():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = "./spreadsheet-key.json"

    return service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

def main():
    copy_endpoints_to_file(FOLDER_NAME)
    setup_spreadsheet_key()
    creds = get_credentials()
    
    run_nuclei(FOLDER_NAME, json_file, log_file)  

    for entry in os.listdir(os.getcwd()):
        file_path = os.path.join(os.getcwd(), entry)

        # Check if the entry is a file and not a directory
        if os.path.isfile(file_path) and entry.startswith(FOLDER_NAME) and entry.endswith('.log'):
            data = parse_log_file(file_path)

            if not data:
                print(f"Warning: {entry} has no relevant data. Skipping...")
                continue

            # Update the spreadsheet with the parsed data
            sheet_name = os.path.splitext(entry)[0]
            RANGE_NAME = f'{sheet_name}!A5'
            
            service = build('sheets', 'v4', credentials=creds)

            clear_values_request_body = {}
            service.spreadsheets().values().clear(
                spreadsheetId=os.environ['SpreadSheet_ID'],
                range=f'{sheet_name}!A5:ZZ',
                body=clear_values_request_body
            ).execute()

            # Convert data to DataFrame for easier manipulation
            data_df = pd.DataFrame(data, columns=['Column1', 'Column2', 'Column3'])

            try:
                request = service.spreadsheets().values().update(
                    spreadsheetId=os.environ['SpreadSheet_ID'],
                    range=RANGE_NAME,
                    valueInputOption="USER_ENTERED",
                    body={"values": data_df.values.tolist()}
                ).execute()

            except Exception as e:
                print(f"Error updating spreadsheet for {entry}: {str(e)}")

            # Copy the log file to S3
            copy_to_s3(json_file, BUCKET, FOLDER_NAME, YEAR, MONTH)

if __name__ == "__main__":
    main()

