# AWS AMI and Snapshot Listing Script

## Overview

This script lists Amazon Machine Images (AMIs) and EBS Snapshots created before a specified cutoff date in a given AWS region. Results are saved in an Excel file.

## Features

- Specify AWS region, profile, and cutoff date.
- Generates an Excel file with AMIs and Snapshots details.

## Prerequisites

- AWS CLI installed and configured.
- Python 3 installed.
- Required Python packages:
  ```bash
  pip install -r requirements.txt
