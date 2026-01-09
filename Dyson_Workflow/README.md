# n8n Workflow Automation

This directory contains n8n workflows for automating preventive maintenance tasks.

## Workflows

### Daily PM Checker (`daily_pm_checker.json`)

This workflow runs daily at 01:00 AM to check for machines requiring preventive maintenance.

#### Workflow Steps:

1. **Schedule Trigger** - Runs daily at 01:00 (Cron: `0 1 * * *`)
2. **Get Machines Due for PM** - Fetches machines with PM status "due_soon" or "overdue"
3. **Split In Batches** - Processes machines in batches of 5
4. **Get AI Decision** - Calls AI API to get decision for each machine
5. **Decision Router** - Routes based on AI decision:
   - **CREATE_WORK_ORDER** → Check confidence threshold
   - **SEND_NOTIFICATION** → Send email to supplier
   - **WAIT** → No action
6. **Check Confidence** - Only creates WO if confidence >= 0.7
7. **Create Work Order** - Creates work order via API
8. **Send Email Notification** - Sends email to supplier
9. **Log Workflow Results** - Logs execution to database

## Setup Instructions

### 1. Import Workflow

1. Access n8n at `http://localhost:5678`
2. Login with credentials:
   - Username: `admin`
   - Password: `admin123` (change this in production!)
3. Click "Workflows" → "Import from File"
4. Select `daily_pm_checker.json`

### 2. Configure SMTP Credentials

For email notifications to work:

1. Go to "Credentials" in n8n
2. Click "Add Credential" → "SMTP"
3. Enter your SMTP details:
   - **Host:** smtp.gmail.com (or your SMTP server)
   - **Port:** 587
   - **Username:** your-email@gmail.com
   - **Password:** your-app-password
   - **Secure:** TLS
4. Save as "SMTP account"

> **Note:** For Gmail, you need to use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### 3. Activate Workflow

1. Open the "Daily PM Checker" workflow
2. Click the toggle switch at the top to activate
3. The workflow will now run automatically at 01:00 daily

### 4. Manual Execution (Testing)

To test the workflow manually:

1. Open the workflow
2. Click "Execute Workflow" button
3. Check the execution log for results

## Workflow Configuration

### Backend API URL

The workflow uses `http://backend:8000/api/v1` as the API base URL. This works within Docker Compose network.

If running n8n separately, update all HTTP Request nodes to use:
- `http://localhost:8000/api/v1` (local development)
- Your actual backend URL (production)

### Schedule Configuration

To change the schedule:

1. Open "Schedule Trigger" node
2. Modify the cron expression
   - Current: `0 1 * * *` (01:00 daily)
   - Examples:
     - `0 */6 * * *` - Every 6 hours
     - `0 9 * * 1` - Every Monday at 9 AM
     - `0 0 * * *` - Every day at midnight

### Batch Size

The workflow processes machines in batches of 5. To change:

1. Open "Split In Batches" node
2. Modify "Batch Size" parameter

## Monitoring

### Execution History

View execution history in n8n:
1. Go to "Executions" tab
2. Filter by workflow name
3. Click on execution to see details

### Database Logs

The workflow logs results to the `workflow_logs` table:

```sql
SELECT * FROM workflow_logs
ORDER BY started_at DESC
LIMIT 10;
```

## Troubleshooting

### Workflow Not Running

1. **Check if workflow is active:**
   - Toggle should be ON (blue)

2. **Check schedule trigger:**
   - Verify cron expression is valid

3. **Check n8n logs:**
   ```bash
   docker logs dyson_n8n
   ```

### API Connection Errors

1. **Verify backend is running:**
   ```bash
   docker ps | grep dyson_backend
   ```

2. **Check network connectivity:**
   - Ensure n8n and backend are on same Docker network

3. **Test API manually:**
   ```bash
   curl http://backend:8000/api/v1/machines
   ```

### Email Not Sending

1. **Check SMTP credentials:**
   - Verify username/password are correct
   - For Gmail, use App Password

2. **Check email node configuration:**
   - Verify "Send Email Notification" node settings

3. **Check supplier email addresses:**
   - Ensure machines have valid `supplier_email` values

## Advanced Configuration

### Custom Email Template

Edit the "Send Email Notification" node to customize:

- **Subject:** Email subject line
- **Message:** HTML email body
- **From Email:** Sender email address

### Additional Notifications

To add Slack/Teams notifications:

1. Add "Slack" or "Microsoft Teams" node
2. Connect to decision router
3. Configure webhook URL
4. Map message template

### Error Handling

The workflow includes basic error handling:

- Continues processing on individual failures
- Logs errors to workflow_logs table
- Use "On Error" workflow for advanced error handling

## Security Notes

⚠️ **Important:**

1. **Change default n8n credentials** in production
2. **Use environment variables** for sensitive data
3. **Enable HTTPS** for n8n in production
4. **Restrict network access** to n8n interface
5. **Regularly backup** workflow configurations

## Support

For issues or questions:
- Check n8n documentation: https://docs.n8n.io
- Review backend API docs: http://localhost:8000/docs
- Check Docker logs for errors
