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


def find_attached_snapshots(ec2, snapshots):
    """Find snapshots that are associated with one or more AMIs."""
    attached_snapshots = []

    print("Checking snapshot associations in parallel...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_snapshot = {
            executor.submit(check_snapshot_association, ec2, snapshot['SnapshotId']): snapshot['SnapshotId']
            for snapshot in snapshots
        }

        for future in tqdm(as_completed(future_to_snapshot), total=len(future_to_snapshot), desc="Processing Snapshots"):
            snapshot_id, associated_amis = future.result()
            if associated_amis is not None and len(associated_amis) > 0:
                attached_snapshots.append({'SnapshotId': snapshot_id, 'AssociatedAMIs': ', '.join(associated_amis)})

    return attached_snapshots


def save_attached_snapshots_to_csv(data, filename):
    """Save attached snapshot data to a CSV file."""
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['SnapshotId', 'AssociatedAMIs'])
        writer.writeheader()
        for row in data:
            writer.writerow({'SnapshotId': row['SnapshotId'], 'AssociatedAMIs': row['AssociatedAMIs']})
    print(f"Data saved to {filename}")


def generate_filename(profile, region):
    """Generate a filename based on profile, region, date, and time."""
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"attached_snapshots_{profile}_{region}_{current_time}.csv"
    return filename


def main():
    # Default settings
    default_profile = "glassfish"
    default_region = "ap-south-1"

    try:
        # Initialize AWS client
        ec2 = initialize_aws_client(default_profile, default_region)

        # Fetch snapshots
        snapshots = get_all_snapshots(ec2)

        # Find attached snapshots
        attached_snapshots = find_attached_snapshots(ec2, snapshots)

        # Generate filename dynamically
        output_file = generate_filename(default_profile, default_region)

        # Save attached snapshot data to the generated file
        save_attached_snapshots_to_csv(attached_snapshots, output_file)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
