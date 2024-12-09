#!/bin/bash

# Author(s): Your Name, Other Author (if applicable)
# Date: YYYY-MM-DD
# Description: Script to list AMIs and snapshots created before a specified date.
# This script prompts the user for AWS region, profile, and a cutoff date,
# then generates an Excel file containing AMIs and snapshots created before that date.

# Check if the required parameters are provided
if [ "$#" -ne 0 ]; then
    echo "Usage: $0"
    exit 1
fi

# Prompt for user input
read -p "Enter AWS Region (e.g., ap-south-1): " REGION
read -p "Enter AWS Profile (e.g., cigar): " PROFILE
read -p "Enter a cutoff date (YYYY-MM-DD) to check for AMIs/Snapshots: " CUTOFF_DATE

OUTPUT_FILE="amis_and_snapshots_${REGION}_${PROFILE}_$(date +%Y%m%d_%H%M%S).xlsx"
DATE_THRESHOLD=$(date -d "${CUTOFF_DATE}" '+%Y-%m-%dT%H:%M:%S')

# Create an Excel workbook for AMIs and Snapshots
python3 -c "
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = 'AMIs and Snapshots'
ws.append(['Type', 'ID', 'Name/Description', 'Created', 'Tags'])
wb.save('${OUTPUT_FILE}')
"

# Function to list AMIs
list_amis() {
    echo "Listing AMIs in region ${REGION} for profile ${PROFILE}:"
    python3 -c "
import boto3
from openpyxl import load_workbook

session = boto3.Session(profile_name='${PROFILE}')
ec2 = session.client('ec2', region_name='${REGION}')
response = ec2.describe_images(Owners=['self'])

found_ami = False

def get_tags(tags):
    return ', '.join([f'{tag[\"Key\"]}={tag[\"Value\"]}' for tag in tags]) if tags else 'None'

for ami in response['Images']:
    if ami['CreationDate'] < '${DATE_THRESHOLD}':
        tags = get_tags(ami.get('Tags', []))
        found_ami = True
        wb = load_workbook('${OUTPUT_FILE}')
        ws = wb['AMIs and Snapshots']
        ws.append(['AMI', ami['ImageId'], ami['Name'] or 'Unnamed', ami['CreationDate'], tags])
        wb.save('${OUTPUT_FILE}')

if not found_ami:
    wb = load_workbook('${OUTPUT_FILE}')
    ws = wb['AMIs and Snapshots']
    ws.append(['AMI', 'None', 'None', 'None', 'None'])
    wb.save('${OUTPUT_FILE}')
"
}

# Function to list Snapshots
list_snapshots() {
    echo "Listing Snapshots in region ${REGION} for profile ${PROFILE}:"
    python3 -c "
import boto3
from openpyxl import load_workbook

session = boto3.Session(profile_name='${PROFILE}')
ec2 = session.client('ec2', region_name='${REGION}')
response = ec2.describe_snapshots(OwnerIds=['self'])

found_snapshot = False

def get_tags(tags):
    return ', '.join([f'{tag[\"Key\"]}={tag[\"Value\"]}' for tag in tags]) if tags else 'None'

for snapshot in response['Snapshots']:
    if snapshot['StartTime'].strftime('%Y-%m-%dT%H:%M:%S') < '${DATE_THRESHOLD}':
        start_time = snapshot['StartTime'].strftime('%Y-%m-%d %H:%M:%S')
        tags = get_tags(snapshot.get('Tags', []))
        found_snapshot = True
        wb = load_workbook('${OUTPUT_FILE}')
        ws = wb['AMIs and Snapshots']
        ws.append(['Snapshot', snapshot['SnapshotId'], snapshot['Description'] or 'Unnamed', start_time, tags])
        wb.save('${OUTPUT_FILE}')

if not found_snapshot:
    wb = load_workbook('${OUTPUT_FILE}')
    ws = wb['AMIs and Snapshots']
    ws.append(['Snapshot', 'None', 'None', 'None', 'None'])
    wb.save('${OUTPUT_FILE}')
"
}

# Execute the functions
list_amis
list_snapshots

echo "Data saved to ${OUTPUT_FILE}"
