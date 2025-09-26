import boto3
import os
import json
import uuid
import time

# initialize clients
dynamodb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')

def lambda_handler(event, context):

    # get configuration from environment variables
    table_name = os.environ.get('DYNAMODB_TABLE_NAME')
    bucket_name = os.environ.get('S3_BUCKET_NAME')

    if not table_name or not bucket_name:
        print(f"error: missing environment variables")
        raise Exception("Configuration error: required environment variables not set.")

    # get batch instructions from the orchestrator's event payload
    # these will tell this worker which part of the table to scan
    segment = event.get('Segment')
    total_segments = event.get('TotalSegments')

    if segment is None or total_segments is None:
        print(f"error: event is missing segment information")
        raise Exception("Configuration error: segment and total_segments must be provided in the event.")

    print(f"starting worker for segment {segment}/{total_segments} on table '{table_name}'")

    try:
        # use a paginator for the scan operation. this is crucial for large tables.
        # it handles fetching data in 1MB chunks automatically, preventing memory issues.
        paginator = dynamodb_client.get_paginator('scan')

        # configure the parallel scan
        scan_kwargs = {
            'TableName': table_name,
            'Segment': segment,
            'TotalSegments': total_segments
        }

        # this list will hold all records for this specific segment
        segment_items = []

        # loop through each page of results from the paginated, parallel scan
        for page in paginator.paginate(**scan_kwargs):
            # boto3 returns items in the verbose dynamodb json format.
            # we don't need to manually convert them, as 'Items' contains them.
            segment_items.extend(page['Items'])

        if not segment_items:
            print(f"segment {segment} had no items to process.")
            return {'status': 'success', 'message': 'no items in segment'}

        print(f"segment {segment} scan complete. found {len(segment_items)} items.")

        # --- create the output file in jsonl (json lines) format ---
        # jsonl is a standard for streaming data, where each line is a valid json object.
        # we create the file content in-memory.
        jsonl_content = ""
        for item in segment_items:
            # important: boto3 scan returns dynamodb json. we need to convert it to a regular dict.
            # a deserializer handles this conversion.
            deserializer = boto3.dynamodb.types.TypeDeserializer()
            regular_dict = {k: deserializer.deserialize(v) for k, v in item.items()}
            jsonl_content += json.dumps(regular_dict) + "\n"

        # --- use naming convention for the output file ---
        timestamp = time.strftime('%Y-%m-%dT%H-%M-%SZ', time.gmtime())
        unique_id = str(uuid.uuid4())
        output_key = f"records/UserDataTable-dump-{timestamp}_{unique_id}.jsonl"

        # upload the batch file to the 'records/' prefix in s3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=jsonl_content
        )

        print(f"successfully uploaded batch file: {output_key}")

        return {
            'status': 'success',
            'segment': segment,
            'items_processed': len(segment_items),
            'output_file': output_key
        }

    except Exception as e:
        print(f"an error occurred in worker segment {segment}: {e}")
        # re-raise the exception to mark this specific invocation as failed
        raise e