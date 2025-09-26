import boto3
import os
import json
import math

# initialize aws clients
dynamodb_client = boto3.client('dynamodb')
lambda_client = boto.client('lambda')

def lambda_handler(event, context):

    # get configuration from environment variables
    table_name = os.environ.get('DYNAMODB_TABLE_NAME')
    worker_function_name = os.environ.get('WORKER_FUNCTION_NAME')
    # get our new tuning parameter, default to 50 if not set
    target_concurrency = int(os.environ.get('TARGET_CONCURRENCY', 50))

    if not table_name or not worker_function_name:
        print("error: missing environment variables")
        raise Exception("Configuration error: required environment variables not set.")

    try:
        # get the total number of items in the table
        response = dynamodb_client.describe_table(TableName=table_name)
        total_items = response['Table']['ItemCount']

        # calculate the number of parallel workers (segments) to use
        total_segments = target_concurrency

        print(f"table has {total_items} items. starting {total_segments} parallel workers.")

        # loop to invoke one worker for each segment
        for i in range(total_segments):

            # create the event payload for the worker
            payload = {
                'Segment': i,
                'TotalSegments': total_segments
            }

            # invoke the worker lambda function asynchronously
            lambda_client.invoke(
                FunctionName=worker_function_name,
                InvocationType='Event',
                Payload=json.dumps(payload)
            )

        success_message = f"successfully invoked {total_segments} workers to process {total_items} items."
        print(success_message)

        return {
            'statusCode': 200,
            'body': success_message
        }

    except Exception as e:
        print(f"an error occurred: {e}")
        raise e