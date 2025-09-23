import boto3
import os
import json

# Initializing AWS clients for DynamoDB and S3.
dynamodb_resource = boto3.resource('dynamodb')
s3_client = boto3.client('s3')


def lambda_handler(event, context):

    # --- 1. Get Configuration from Environment Variables ---
    # CORRECTED: 'environ' typo fixed and variable name standardized.
    table_name = os.environ.get('DYNAMODB_TABLE_NAME')
    bucket_name = os.environ.get('S3_BUCKET_NAME')

    # CORRECTED: Error message now accurately reflects the variable names.
    if not table_name or not bucket_name:
        print("Error: DYNAMODB_TABLE_NAME or S3_BUCKET_NAME environment variables not set.")
        return {'statusCode': 500, 'body': json.dumps('Configuration error.')}

    print(f"Reading from table: {table_name}")
    print(f"Writing to bucket: {bucket_name}")

    table = dynamodb_resource.Table(table_name)

    try:
        # --- 2. Read ALL Data from the DynamoDB Table ---
        response = table.scan()
        items = response.get('Items', [])

        if not items:
            print("No items found in the table.")
            return {'statusCode': 200, 'body': json.dumps('No items to process.')}

        # --- 3. Process and Upload Data in JSON Format ---
        json_data = json.dumps(items, indent=4)

        output_key = 'data/data.json'

        s3_client.put_object(Bucket=bucket_name, Key=output_key, Body=json_data)

        # CORRECTED: Log message is now more specific.
        print(f"Successfully uploaded {output_key}")

        # --- 4. Return a Success Response ---
        return {
            'statusCode': 200,
            'body': json.dumps(f"Successfully processed {len(items)} items and uploaded to {output_key}.")
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return {'statusCode': 500, 'body': json.dumps(f"An error occurred: {str(e)}")}