import json
import boto3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def lambda_handler(event, context):
    try:
        # Retrieve SES SMTP credentials
        ssm = boto3.client('ssm', region_name='ap-south-1')
        smtp_username = ssm.get_parameter(Name='/email-service/ses-smtp-username', WithDecryption=True)['Parameter']['Value']
        smtp_password = ssm.get_parameter(Name='/email-service/ses-smtp-password', WithDecryption=True)['Parameter']['Value']

        # Parse request
        body = json.loads(event['body'])
        sender = body['sender']
        to = body['to']
        subject = body['subject']
        message = body['body']

        # Validate inputs
        if not sender or not to or not isinstance(to, list) or not subject or not message:
            raise ValueError("Missing or invalid email data")

        # SES SMTP configuration
        smtp_server = 'email-smtp.ap-south-1.amazonaws.com'
        smtp_port = 587

        # Send email
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ', '.join(to)
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender, to, msg.as_string())

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'message': 'Email sent successfully'})
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