import json
import boto3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz

def lambda_handler(event, context):
    try:
        dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
        table = dynamodb.Table('EmailSchedules')
        ssm = boto3.client('ssm', region_name='ap-south-1')
        try:
            smtp_username = ssm.get_parameter(Name='/email-service/ses-smtp-username', WithDecryption=True)['Parameter']['Value']
            smtp_password = ssm.get_parameter(Name='/email-service/ses-smtp-password', WithDecryption=True)['Parameter']['Value']
        except Exception as e:
            print(f"Error fetching SSM parameters: {str(e)}")
            raise ValueError("Failed to retrieve SMTP credentials")

        current_utc = datetime.now(pytz.UTC)
        current_date = current_utc.date().strftime('%Y-%m-%d')
        current_hh_mm = current_utc.strftime('%H:%M')

        response = table.scan(
            FilterExpression='#status = :status AND #start_date <= :current_date AND #end_date >= :current_date',
            ExpressionAttributeNames={'#status': 'status', '#start_date': 'start_date', '#end_date': 'end_date'},
            ExpressionAttributeValues={':status': 'PENDING', ':current_date': current_date}
        )
        items = response.get('Items', [])
        print(f"Found {len(items)} PENDING items before time filter")

        filtered_items = []
        for item in items:
            schedule_time = item.get('schedule_time')
            if schedule_time:
                try:
                    schedule_dt = datetime.strptime(schedule_time, '%Y-%m-%dT%H:%M:%SZ')
                    schedule_hh_mm = schedule_dt.strftime('%H:%M')
                    if schedule_hh_mm == current_hh_mm:
                        filtered_items.append(item)
                except ValueError:
                    print(f"Invalid schedule_time format for schedule {item['id']}: {schedule_time}")

        print(f"Found {len(filtered_items)} PENDING items after time filter")

        smtp_server = 'email-smtp.ap-south-1.amazonaws.com'
        smtp_port = 587

        for item in filtered_items:
            schedule_id = item['id']
            sender = item['sender']
            to = [recipient['S'] for recipient in item['to']['L'] if recipient.get('S')]
            subject = item['subject']
            body = item['body']
            sent_dates = item.get('sent_dates', {'L': []})['L']
            sent_dates = [d['S'] for d in sent_dates if d.get('S')] if sent_dates else []
            end_date = item['end_date']

            print(f"Processing schedule {schedule_id}: to={to}, current_date={current_date}")

            if current_date in sent_dates:
                print(f"Skipping schedule {schedule_id}: Already sent on {current_date}")
                continue

            if not to:
                print(f"Skipping schedule {schedule_id}: No valid recipients")
                table.update_item(
                    Key={'id': schedule_id},
                    UpdateExpression="SET #status = :status",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': 'FAILED'}
                )
                continue

            try:
                # Mark as IN_PROGRESS to prevent duplicate processing
                table.update_item(
                    Key={'id': schedule_id},
                    UpdateExpression="SET #status = :status",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': 'IN_PROGRESS', ':pending': 'PENDING'},
                    ConditionExpression="#status = :pending"
                )

                msg = MIMEMultipart()
                msg['From'] = sender
                msg['To'] = ', '.join(to)
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'html'))

                with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_username, smtp_password)
                    server.sendmail(sender, to, msg.as_string())

                print(f"Email sent for schedule {schedule_id} on {current_date}")
                table.update_item(
                    Key={'id': schedule_id},
                    UpdateExpression="SET sent_dates = list_append(if_not_exists(sent_dates, :empty_list), :new_date), #status = :status",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':empty_list': {'L': []},
                        ':new_date': {'L': [{'S': current_date}]},
                        ':status': 'SENT' if end_date == current_date else 'PENDING'
                    }
                )
            except table.meta.client.exceptions.ConditionalCheckFailedException:
                print(f"Skipping schedule {schedule_id}: Already being processed")
                continue
            except smtplib.SMTPRecipientsRefused as e:
                print(f"SMTP error for schedule {schedule_id}: {str(e)}")
                table.update_item(
                    Key={'id': schedule_id},
                    UpdateExpression="SET #status = :status",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': 'FAILED'}
                )
                continue
            except Exception as e:
                print(f"Error sending email for schedule {schedule_id}: {str(e)}")
                table.update_item(
                    Key={'id': schedule_id},
                    UpdateExpression="SET #status = :status",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': 'FAILED'}
                )
                raise

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Processed scheduled emails'})
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }