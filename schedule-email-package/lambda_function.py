import json
import boto3
import uuid
from datetime import datetime
import pytz
import re

def lambda_handler(event, context):
    try:
        dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
        table = dynamodb.Table('EmailSchedules')

        body = json.loads(event.get('body', '{}'))
        sender = body.get('sender')
        to = body.get('to', [])
        subject = body.get('subject')
        content = body.get('body')
        send_time = body.get('send_time')  # IST HH:MM
        start_date = body.get('start_date')
        end_date = body.get('end_date')

        # Validate inputs
        if not sender or not to or not isinstance(to, list) or not subject or not content or not send_time or not start_date or not end_date:
            raise ValueError("Missing required fields")
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, sender):
            raise ValueError(f"Invalid sender email: {sender}")
        valid_to = [email for email in to if re.match(email_regex, str(email))]
        if not valid_to:
            raise ValueError("No valid recipient emails provided")

        ist = pytz.timezone('Asia/Kolkata')
        try:
            send_time_dt = datetime.strptime(f"{start_date} {send_time}:00", '%Y-%m-%d %H:%M:%S')
            send_time_dt = ist.localize(send_time_dt)
            utc_time = send_time_dt.astimezone(pytz.UTC)
            schedule_time = utc_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            raise ValueError(f"Invalid time format: {send_time}")

        item = {
            'id': str(uuid.uuid4()),
            'sender': sender,
            'to': {'L': [{'S': str(email)} for email in valid_to]},
            'subject': subject,
            'body': content,
            'schedule_time': schedule_time,
            'send_time': send_time,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'PENDING',
            'sent_dates': {'L': []}
        }
        table.put_item(Item=item)

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'message': 'Email scheduled successfully', 'id': item['id']})
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'error': str(e)})
        }