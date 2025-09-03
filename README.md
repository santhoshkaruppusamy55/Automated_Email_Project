# Email Scheduling Web Application

## Overview

This project is a web application that allows users to schedule emails to be sent automatically at a specified time. Built using AWS services, it ensures reliable email delivery. Only email addresses verified by the owner in AWS SES can be used as senders or receivers, ensuring secure communication.

## Features

- Schedule emails with a user-friendly web interface.
- Supports IST time input, converted to UTC for accurate scheduling.
- Stores email schedules in DynamoDB and sends emails via AWS SES.
- Handles multiple recipients per schedule.

## Architecture

- **Frontend**: Hosted on AWS Amplify,(URL: `https://main.d3c44meg51hu5x.amplifyapp.com/`).
- **Backend**:
  - `ScheduleEmail` Lambda: Stores email schedules in DynamoDB with `sent_dates` as a List.
  - `SendScheduledEmails` Lambda: Sends emails at the scheduled time via SES, triggered by EventBridge (every minute).
  - API Gateway: Connects the frontend to the `ScheduleEmail` Lambda.
  - DynamoDB: Stores email schedules with fields like `id`, `sender`, `to`, `schedule_time`, `status`, and `sent_dates`.
  - SES: Sends emails (sandbox mode, requires verified sender/receiver emails).
  - SSM: Securely stores SES SMTP credentials.

## Prerequisites

- AWS account with SES, Lambda, DynamoDB, API Gateway, Amplify, and EventBridge configured.
- Verified email addresses in SES for senders and receivers.
- Python 3.8+ for Lambda deployment.

## Architecture
The application follows a layered architecture:
- **Presentation Layer**: React frontend on AWS Amplify with GitHub for instant updates.
- **Application Layer**: Lambda functions (`ScheduleEmail`, `SendScheduledEmails`) for scheduling and sending emails.
- **Data Layer**: DynamoDB for storing email schedules with verified sender/receiver IDs.
- **Integration Layer**: API Gateway, EventBridge, and SES for seamless connectivity and email delivery.
