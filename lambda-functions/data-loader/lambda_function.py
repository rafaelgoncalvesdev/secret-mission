import boto3
import os
import uuid
import random
import time

# initialize dynamodb resource
dynamodb_resource = boto3.resource('dynamodb')

def lambda_handler(event, context):

    # get table name from environment variables
    table_name = os.environ.get('DYNAMODB_TABLE_NAME')

    if not table_name:
        print("error: DYNAMODB_TABLE_NAME environment variable not set")
        return {'statusCode': 500, 'body': 'configuration error'}

    table = dynamodb_resource.Table(table_name)

    # configure data generation
    number_of_items = 500000
    statuses = ['active', 'withdrawn']
    purposes = ['User analytics', 'Billing record', 'Marketing Campaign', 'Support Ticket']

    print(f"starting to load {number_of_items} items into table '{table_name}'...")

    try:
        # use batch_writer for efficient insertion
        with table.batch_writer() as batch:
            for i in range(number_of_items):
                item = {
                    'email': f'user-{uuid.uuid4()}@example.com',
                    'purpose': random.choice(purposes),
                    'last_transaction': time.strftime('%Y-%m-%d', time.gmtime(time.time() - random.randint(0, 31536000))),
                    'status': random.choice(statuses)
                }
                batch.put_item(Item=item)

                if (i + 1) % 100 == 0:
                    print(f"queued {i + 1}/{number_of_items} items...")

        print("all items successfully loaded.")

        return {
            'statusCode': 200,
            'body': f'successfully loaded {number_of_items} items into {table_name}.'
        }

    except Exception as e:
        print(f"an error occurred during batch write: {e}")
        return {'statusCode': 500, 'body': f'an error occurred: {str(e)}'}