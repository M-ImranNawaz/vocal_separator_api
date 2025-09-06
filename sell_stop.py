import boto3
import requests
import time

def get_instance_id():
    try:
        response = requests.get('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
        return response.text
    except requests.RequestException:
        print("Not running on EC2 or metadata service unavailable.")
        return None

def stop_self():
    instance_id = get_instance_id()
    if not instance_id:
        print("Instance ID not found. Cannot stop.")
        return

    ec2 = boto3.client('ec2', region_name='your-region-name')  # e.g., us-east-1
    print(f"Stopping instance: {instance_id}")
    ec2.stop_instances(InstanceIds=[instance_id])
    print("Stop command sent.")

if __name__ == "__main__":
    print("Waiting before shutdown...")
    time.sleep(60)  # Optional: Wait 1 min before stopping (you can remove this)
    stop_self()
