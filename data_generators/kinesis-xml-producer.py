import boto3
import os
import time
import uuid
import argparse
from datetime import datetime

# Load environment variables from .env file if using python-dotenv
# from dotenv import load_dotenv
# load_dotenv(dotenv_path='../.env') # Adjust path as necessary

# Configuration from environment variables
KINESIS_STREAM_NAME = os.getenv('KINESIS_STREAM_NAME', 'pulsar-test-stream')
LOCALSTACK_KINESIS_ENDPOINT = os.getenv('LOCALSTACK_KINESIS_ENDPOINT', 'http://localhost:4566') # Default for running script on host
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'test')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

def create_kinesis_client():
    """Creates a Boto3 Kinesis client configured for LocalStack."""
    return boto3.client(
        'kinesis',
        endpoint_url=LOCALSTACK_KINESIS_ENDPOINT,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION
    )

def generate_xml_message():
    """Generates a sample XML message with a unique ID and timestamp."""
    event_id = str(uuid.uuid4())
    # Ensure timestamp is in a format that's easily parseable and sortable, ISO 8601 is good.
    generation_timestamp = datetime.utcnow().isoformat() 
    
    xml_data = f"""
    <event>
        <id>{event_id}</id>
        <source>kinesis_xml_producer</source>
        <timestamp>{generation_timestamp}</timestamp>
        <payload>
            <value1>Some random data: {uuid.uuid4().hex[:8]}</value1>
            <value2>{time.time()}</value2>
        </payload>
    </event>
    """
    return xml_data.strip()

def send_message_to_kinesis(client, stream_name, message):
    """Sends a single message to the specified Kinesis stream."""
    try:
        response = client.put_record(
            StreamName=stream_name,
            Data=message.encode('utf-8'), # Kinesis expects bytes
            PartitionKey=str(uuid.uuid4()) # Ensure good distribution across shards
        )
        # print(f"Message sent. ShardId: {response['ShardId']}, SequenceNumber: {response['SequenceNumber']}")
        return True
    except Exception as e:
        print(f"Error sending message to Kinesis: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Kinesis XML Data Producer")
    parser.add_argument(
        "--stream-name",
        default=KINESIS_STREAM_NAME,
        help=f"Kinesis stream name (default: {KINESIS_STREAM_NAME})"
    )
    parser.add_argument(
        "--num-messages",
        type=int,
        default=10,
        help="Number of messages to send (default: 10)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between messages in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--endpoint-url",
        default=LOCALSTACK_KINESIS_ENDPOINT,
        help=f"Kinesis endpoint URL (default: {LOCALSTACK_KINESIS_ENDPOINT})"
    )
    args = parser.parse_args()

    # Override endpoint from arg if provided, primarily for flexibility
    global LOCALSTACK_KINESIS_ENDPOINT
    LOCALSTACK_KINESIS_ENDPOINT = args.endpoint_url 

    kinesis_client = create_kinesis_client()
    
    print(f"Attempting to send {args.num_messages} XML messages to Kinesis stream '{args.stream_name}' at endpoint '{args.endpoint_url}'...")
    
    # Optional: Check if stream exists (requires describe_stream permission)
    try:
        kinesis_client.describe_stream(StreamName=args.stream_name)
        print(f"Stream '{args.stream_name}' found.")
    except kinesis_client.exceptions.ResourceNotFoundException:
        print(f"Error: Stream '{args.stream_name}' not found. Please create it first.")
        print("Example: aws --endpoint-url={LOCALSTACK_KINESIS_ENDPOINT} kinesis create-stream --stream-name {KINESIS_STREAM_NAME} --shard-count 1")
        return
    except Exception as e:
        print(f"Error describing stream: {e}. Attempting to send messages anyway.")


    for i in range(args.num_messages):
        xml_message = generate_xml_message()
        if send_message_to_kinesis(kinesis_client, args.stream_name, xml_message):
            print(f"Sent message {i+1}/{args.num_messages}: ID {xml.etree.ElementTree.fromstring(xml_message).find('id').text}")
        else:
            print(f"Failed to send message {i+1}/{args.num_messages}. Halting.")
            break
        time.sleep(args.delay)
    
    print(f"Finished sending {args.num_messages} messages.")

if __name__ == "__main__":
    import xml.etree.ElementTree
    main()