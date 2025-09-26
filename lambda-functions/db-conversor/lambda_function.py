import boto3
import os
import json
import csv
import xml.etree.ElementTree as ET
import time
import uuid
from io import StringIO
from urllib.parse import unquote_plus

# initialize clients
s3_client = boto3.client('s3')
dynamodb_resource = boto3.resource('dynamodb')

def lambda_handler(event, context):

    # get configuration from environment variables
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    output_format = os.environ.get('OUTPUT_FORMAT', 'csv').lower()
    job_table_name = os.environ.get('JOB_TABLE_NAME')

    if not bucket_name or not job_table_name:
        print("error: missing environment variables")
        raise Exception("Configuration error: required environment variables not set.")

    # parse s3 event to get the uploaded file details
    try:
        s3_event = event['Records'][0]['s3']
        source_key = unquote_plus(s3_event['object']['key'])

        print(f"processing file: {source_key}")

        # only process files in records/ folder with .jsonl extension
        if not source_key.startswith('records/') or not source_key.endswith('.jsonl'):
            print(f"skipping file {source_key} - not a records JSONL file")
            return {'status': 'skipped', 'reason': 'not a target file'}

    except Exception as e:
        print(f"error parsing s3 event: {e}")
        raise Exception("Invalid S3 event format")

    # extract filename without path and extension for job coordination
    filename = source_key.split('/')[-1]
    base_filename = filename.replace('.jsonl', '')
    
    # extract extraction folder name from source path
    extraction_folder = source_key.split('/')[1] if '/' in source_key else 'unknown'

    try:
        # get or create conversion job per extraction folder
        job_id, output_folder = get_or_create_job(job_table_name, output_format, extraction_folder)

        # check if this file was already processed
        if is_file_already_processed(job_table_name, job_id, filename):
            print(f"file {filename} already processed, skipping")
            return {'status': 'skipped', 'reason': 'already processed'}

        # download and process the jsonl file
        print(f"downloading file from s3: {source_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=source_key)
        jsonl_content = response['Body'].read().decode('utf-8')

        # convert jsonl to target format
        converted_content = convert_jsonl_to_format(jsonl_content, output_format)

        # generate output filename
        output_filename = f"{base_filename}.{output_format}"
        output_key = f"processed/{output_folder}/{output_filename}"

        # upload converted file
        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=converted_content
        )

        # mark file as processed
        mark_file_as_processed(job_table_name, job_id, filename, output_key)

        # update job log
        update_job_log(bucket_name, output_folder, filename, "SUCCESS", f"converted to {output_format}")

        print(f"successfully converted {filename} to {output_format}")

        return {
            'status': 'success',
            'input_file': source_key,
            'output_file': output_key,
            'job_id': job_id
        }

    except Exception as e:
        error_msg = f"error processing {filename}: {str(e)}"
        print(error_msg)

        # log error to job log
        try:
            job_id, output_folder = get_or_create_job(job_table_name, output_format)
            update_job_log(bucket_name, output_folder, filename, "ERROR", error_msg)
        except:
            pass  # don't fail if logging fails

        raise e

def get_or_create_job(job_table_name, output_format, extraction_folder):
    """get existing job or create new one for this extraction folder"""
    table = dynamodb_resource.Table(job_table_name)
    
    import uuid
    timestamp = time.strftime('%Y-%m-%dT%H-%M-%SZ', time.gmtime())
    unique_id = str(uuid.uuid4())[:8]
    job_id = f"db-to-{output_format}-{extraction_folder}-{unique_id}"
    output_folder = job_id

    try:
        # check if job already exists for this extraction folder
        response = table.scan(
            FilterExpression='extraction_folder = :folder AND output_format = :format',
            ExpressionAttributeValues={
                ':folder': extraction_folder,
                ':format': output_format
            }
        )

        if response['Items']:
            # use existing job for this extraction folder
            existing_job = response['Items'][0]
            return existing_job['job_id'], existing_job['job_id']

        # create new job for this extraction folder
        current_time = int(time.time())
        table.put_item(
            Item={
                'job_id': job_id,
                'status': 'IN_PROGRESS',
                'output_format': output_format,
                'extraction_folder': extraction_folder,
                'processed_files': [],
                'created_at': current_time,
                'updated_at': current_time
            }
        )

        print(f"created new conversion job: {job_id} for extraction: {extraction_folder}")
        return job_id, output_folder

    except Exception as e:
        print(f"error managing job: {e}")
        # fallback to timestamp-based job
        return job_id, output_folder

def is_file_already_processed(job_table_name, job_id, filename):
    """check if file was already processed in this job"""
    try:
        table = dynamodb_resource.Table(job_table_name)
        response = table.get_item(Key={'job_id': job_id})

        if 'Item' in response:
            processed_files = response['Item'].get('processed_files', [])
            return filename in processed_files

    except Exception as e:
        print(f"error checking processed files: {e}")

    return False

def mark_file_as_processed(job_table_name, job_id, filename, output_key):
    """mark file as processed in the job record"""
    try:
        table = dynamodb_resource.Table(job_table_name)
        table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='ADD processed_files :file SET updated_at = :time',
            ExpressionAttributeValues={
                ':file': {filename},
                ':time': int(time.time())
            }
        )
    except Exception as e:
        print(f"error updating job record: {e}")

def convert_jsonl_to_format(jsonl_content, output_format):
    """convert jsonl content to specified format"""
    lines = jsonl_content.strip().split('\n')
    records = [json.loads(line) for line in lines if line.strip()]

    if not records:
        return ""

    if output_format == 'csv':
        return convert_to_csv(records)
    elif output_format == 'xml':
        return convert_to_xml(records)
    else:
        raise Exception(f"unsupported output format: {output_format}")

def convert_to_csv(records):
    """convert records to csv format"""
    if not records:
        return ""

    output = StringIO()
    fieldnames = records[0].keys()
    writer = csv.DictWriter(output, fieldnames=fieldnames)

    writer.writeheader()
    for record in records:
        writer.writerow(record)

    return output.getvalue()

def convert_to_xml(records):
    """convert records to xml format"""
    root = ET.Element('records')

    for record in records:
        record_elem = ET.SubElement(root, 'record')
        for key, value in record.items():
            field_elem = ET.SubElement(record_elem, key)
            field_elem.text = str(value) if value is not None else ""

    return ET.tostring(root, encoding='unicode')

def update_job_log(bucket_name, output_folder, filename, status, message):
    """update the job log file in s3"""
    log_key = f"processed/{output_folder}/conversion-log.txt"
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
    log_entry = f"[{timestamp}] {filename}: {status} - {message}\n"

    try:
        # try to get existing log
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=log_key)
            existing_log = response['Body'].read().decode('utf-8')
        except s3_client.exceptions.NoSuchKey:
            existing_log = f"Conversion Job Log - Started at {timestamp}\n" + "="*50 + "\n"

        # append new entry
        updated_log = existing_log + log_entry

        # upload updated log
        s3_client.put_object(
            Bucket=bucket_name,
            Key=log_key,
            Body=updated_log
        )

    except Exception as e:
        print(f"error updating job log: {e}")
