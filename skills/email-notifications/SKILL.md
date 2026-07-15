---
name: "email-notifications"
description: "Configure email notifications and alerts for the user"
---

# Email Notifications Skill

## Overview
Configure and manage email notifications for the user's email accounts.

## Capabilities
- Check for new/important emails
- Configure notification rules (priority, sender, subject filters)
- Set up email summaries (daily, weekly)
- Alert on urgent emails

## Setup
1. Ask user for email provider (Gmail, Outlook, etc.)
2. Help configure OAuth2 or app-specific passwords
3. Set up notification preferences
4. Test connection

## Notification Types
- **Real-time**: Forward urgent emails immediately
- **Digest**: Daily/weekly summary of important emails
- **Alert**: Custom rules (specific senders, keywords)

## Commands
- `/email check` - Check latest emails
- `/email setup` - Configure email access
- `/email rules` - View/edit notification rules
- `/email digest` - Configure digest frequency

## Security Notes
- Store credentials securely (never in plain text files)
- Use OAuth2 when possible
- Respect email provider rate limits
