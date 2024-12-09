import boto3
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from datetime import datetime


def initialize_aws_client(profile, region):
    """Initialize AWS client using the specified profile and region."""
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        ec2 = session.client('ec2')
        print(f"AWS client initialized with profile '{profile}' and region '{region}'.")
        return ec2
    except (NoCredentialsError, PartialCredentialsError):
        print("AWS credentials not found. Ensure you have configured your profile correctly.")
        exit(1)
    except Exception as e:
        print(f"Error initializing AWS client: {e}")
        exit(1)


def get_all_snapshots(ec2):
    """Retrieve all snapshots in the account."""
    snapshots = []
    print("Fetching all snapshots...")
    paginator = ec2.get_paginator('describe_snapshots')
    for page in paginator.paginate(OwnerIds=['self']):
        snapshots.extend(page['Snapshots'])
    return snapshots


def check_snapshot_association(ec2, snapshot_id):
    """Check if a snapshot is associated with an AMI."""
    try:
        amis_response = ec2.describe_images(
            Filters=[{'Name': 'block-device-mapping.snapshot-id', 'Values': [snapshot_id]}]
        )
        associated_amis = [image['ImageId'] for image in amis_response['Images']]
        return snapshot_id, associated_amis
    except Exception as e:
        print(f"Error processing snapshot {snapshot_id}: {e}")
        return snapshot_id, None


def categorize_snapshots(ec2, snapshots):
    """Categorize snapshots into attached and unattached using parallel processing."""
    attached_snapshots = []
    unattached_snapshots = []

    print("Checking snapshot associations in parallel...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_snapshot = {
            executor.submit(check_snapshot_association, ec2, snapshot['SnapshotId']): snapshot['SnapshotId']
            for snapshot in snapshots
        }

        for future in tqdm(as_completed(future_to_snapshot), total=len(future_to_snapshot), desc="Processing Snapshots"):
            snapshot_id, associated_amis = future.result()
            if associated_amis is not None and len(associated_amis) > 0:
                attached_snapshots.append({'SnapshotId': snapshot_id, 'AssociatedAMIs': associated_amis})
            elif associated_amis is not None:
                unattached_snapshots.append({'SnapshotId': snapshot_id})

    return attached_snapshots, unattached_snapshots


def save_data_to_csv(data, filename, is_attached=False):
    """Save snapshot data to a CSV file."""
    fieldnames = ['SnapshotId', 'AssociatedAMIs'] if is_attached else ['SnapshotId']
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            # Make sure we handle unattached snapshots properly
            if is_attached:
                writer.writerow({
                    'SnapshotId': row['SnapshotId'],
                    'AssociatedAMIs': ", ".join(row['AssociatedAMIs']) if row.get('AssociatedAMIs') else "None"
                })
            else:
                writer.writerow({'SnapshotId': row['SnapshotId']})
    print(f"Data saved to {filename}")


def generate_filename(prefix, profile, region):
    """Generate a filename based on profile, region, date, and time."""
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{prefix}_snapshots_{profile}_{region}_{current_time}.csv"
    return filename


def main():
    print("Welcome to the Snapshot Checker!")
    
    # Prompt for AWS profile and region
    profile = input("Enter the AWS profile to use (default is 'default'): ").strip() or "default"
    region = input("Enter the AWS region to use (default is 'us-east-1'): ").strip() or "us-east-1"

    try:
        # Initialize AWS client
        ec2 = initialize_aws_client(profile, region)

        # Fetch snapshots
        snapshots = get_all_snapshots(ec2)

        # Categorize snapshots into attached and unattached
        attached_snapshots, unattached_snapshots = categorize_snapshots(ec2, snapshots)

        # Generate filenames dynamically
        attached_file = generate_filename("attached", profile, region)
        unattached_file = generate_filename("unattached", profile, region)

        # Save data to the generated files
        save_data_to_csv(attached_snapshots, attached_file, is_attached=True)
        save_data_to_csv(unattached_snapshots, unattached_file)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
