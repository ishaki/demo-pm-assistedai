import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime

from ..config import get_settings
from ..models.machine import Machine
from ..models.work_order import WorkOrder

logger = logging.getLogger(__name__)

# Brand strings for the email footers. Defined once rather than repeated in
# each template. Non-ASCII is safe here: MIMEText detects it and falls back
# from us-ascii to utf-8 automatically.
APP_NAME = "AI Harvest®"
APP_FULL_NAME = f"{APP_NAME} - WO Automation"
EMAIL_FOOTER_NOTE = f"This is an automated message from {APP_FULL_NAME}."


class NotificationService:
    """Service for sending email notifications"""

    def __init__(self):
        self.settings = get_settings()

    async def send_work_order_notification(
        self,
        machine: Machine,
        work_order: WorkOrder,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send work order notification email to supplier.

        Args:
            machine: Machine object
            work_order: WorkOrder object
            additional_context: Optional additional information

        Returns:
            True if email sent successfully, False otherwise
        """
        if not machine.supplier_email:
            logger.warning(f"No supplier email for machine {machine.machine_id}")
            return False

        try:
            subject = f"PM Work Order - {machine.machine_id}"
            body = self._build_work_order_email(machine, work_order, additional_context)

            success = await self._send_email(
                to_email=machine.supplier_email,
                subject=subject,
                body=body,
                html=True
            )

            if success:
                logger.info(
                    f"Work order notification sent to {machine.supplier_email} "
                    f"for WO {work_order.wo_number}"
                )
            else:
                logger.error(
                    f"Failed to send work order notification to {machine.supplier_email}"
                )

            return success

        except Exception as e:
            logger.error(f"Error sending work order notification: {e}")
            return False

    async def send_approval_notification(
        self,
        machine: Machine,
        work_order: WorkOrder
    ) -> bool:
        """
        Send notification when work order is approved.

        Args:
            machine: Machine object
            work_order: WorkOrder object

        Returns:
            True if email sent successfully, False otherwise
        """
        if not machine.supplier_email:
            logger.warning(f"No supplier email for machine {machine.machine_id}")
            return False

        try:
            # The subject has to satisfy two downstream consumers: the n8n
            # check_maintenance_email workflow only forwards replies whose
            # subject contains "Maintenance", and the date-extraction webhook
            # locates this WO by matching WO-YYYY-NNN in it. A "Re:" prefix on
            # the supplier's reply leaves both intact.
            subject = f"Maintenance Work Order Approved - {work_order.wo_number}"
            body = self._build_approval_email(machine, work_order)

            success = await self._send_email(
                to_email=machine.supplier_email,
                subject=subject,
                body=body,
                html=True
            )

            if success:
                logger.info(
                    f"Approval notification sent to {machine.supplier_email} "
                    f"for WO {work_order.wo_number}"
                )

            return success

        except Exception as e:
            logger.error(f"Error sending approval notification: {e}")
            return False

    async def send_completion_notification(
        self,
        machine: Machine,
        work_order: WorkOrder
    ) -> bool:
        """
        Send notification when work order is completed.

        Args:
            machine: Machine object
            work_order: WorkOrder object

        Returns:
            True if email sent successfully, False otherwise
        """
        if not machine.supplier_email:
            logger.warning(f"No supplier email for machine {machine.machine_id}")
            return False

        try:
            subject = f"Work Order Completed - {work_order.wo_number}"
            body = self._build_completion_email(machine, work_order)

            success = await self._send_email(
                to_email=machine.supplier_email,
                subject=subject,
                body=body,
                html=True
            )

            if success:
                logger.info(
                    f"Completion notification sent to {machine.supplier_email} "
                    f"for WO {work_order.wo_number}"
                )

            return success

        except Exception as e:
            logger.error(f"Error sending completion notification: {e}")
            return False

    def _build_work_order_email(
        self,
        machine: Machine,
        work_order: WorkOrder,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build HTML email body for work order notification"""

        days_until_pm = (machine.next_pm_date - datetime.now().date()).days

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #1976d2; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .info-table th {{ background-color: #e0e0e0; padding: 10px; text-align: left; }}
                .info-table td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                .status-badge {{
                    display: inline-block;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                .status-urgent {{ background-color: #f44336; color: white; }}
                .status-medium {{ background-color: #ff9800; color: white; }}
                .status-low {{ background-color: #4caf50; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Preventive Maintenance Work Order</h1>
                </div>

                <div class="content">
                    <p>Dear {machine.assigned_supplier},</p>

                    <p>This is an automated notification regarding preventive maintenance for the following machine:</p>

                    <table class="info-table">
                        <tr>
                            <th>Machine Information</th>
                            <th>Details</th>
                        </tr>
                        <tr>
                            <td><strong>Machine ID</strong></td>
                            <td>{machine.machine_id}</td>
                        </tr>
                        <tr>
                            <td><strong>Machine Name</strong></td>
                            <td>{machine.name}</td>
                        </tr>
                        <tr>
                            <td><strong>Location</strong></td>
                            <td>{machine.location}</td>
                        </tr>
                        <tr>
                            <td><strong>PM Frequency</strong></td>
                            <td>{machine.pm_frequency}</td>
                        </tr>
                        <tr>
                            <td><strong>Next PM Date</strong></td>
                            <td>{machine.next_pm_date}</td>
                        </tr>
                        <tr>
                            <td><strong>Days Until PM</strong></td>
                            <td>
                                {abs(days_until_pm)} days {"overdue" if days_until_pm < 0 else "remaining"}
                            </td>
                        </tr>
                    </table>

                    <table class="info-table">
                        <tr>
                            <th>Work Order Information</th>
                            <th>Details</th>
                        </tr>
                        <tr>
                            <td><strong>Work Order Number</strong></td>
                            <td>{work_order.wo_number}</td>
                        </tr>
                        <tr>
                            <td><strong>Priority</strong></td>
                            <td>
                                <span class="status-badge status-{work_order.priority.lower()}">
                                    {work_order.priority}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>Status</strong></td>
                            <td>{work_order.status.replace('_', ' ')}</td>
                        </tr>
                        <tr>
                            <td><strong>Created</strong></td>
                            <td>{work_order.created_at}</td>
                        </tr>
                    </table>

                    {self._add_notes_section(work_order.notes)}

                    {self._add_ai_context(additional_context)}

                    <p><strong>Action Required:</strong></p>
                    <p>Please schedule the preventive maintenance for this machine at your earliest convenience.</p>

                    <p>If you have any questions, please contact the maintenance team.</p>

                    <p>Best regards,<br>
                    <strong>PM - AI-Assisted Demo</strong></p>
                </div>

                <div class="footer">
                    <p>{EMAIL_FOOTER_NOTE}</p>
                    <p>© {datetime.now().year} {APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _build_approval_email(
        self,
        machine: Machine,
        work_order: WorkOrder
    ) -> str:
        """
        Build HTML email body for approval notification.

        This is the message the supplier replies to with the date they will do
        the work: the n8n check_maintenance_email workflow picks the reply up
        over IMAP and posts it to /workflow/email-date-extraction, which writes
        the extracted date onto this WO. Two constraints follow from that round
        trip, and both are easy to break by editing this template casually:

        - The body must ask for one explicit calendar date. The extractor is
          instructed to return null for relative dates like "next Monday".
        - The reply must keep the subject line, because the webhook locates the
          WO by matching WO-YYYY-NNN in it.
        """
        supplier = machine.assigned_supplier or "Supplier"
        priority = work_order.priority or "Not set"
        location = machine.location or "-"
        scheduled_date = work_order.scheduled_date or "Awaiting your confirmation"

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4caf50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .info-table th {{ background-color: #e0e0e0; padding: 10px; text-align: left; }}
                .info-table td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                .action-box {{ background-color: #fff3cd; padding: 15px; margin: 15px 0; border-left: 4px solid #ffc107; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>&#10003; Work Order Approved</h1>
                </div>

                <div class="content">
                    <p>Dear {supplier},</p>

                    <p>The preventive maintenance work order below has been approved.
                    Please confirm the date on which you can carry out the work.</p>

                    <table class="info-table">
                        <tr>
                            <th>Work Order</th>
                            <th>Details</th>
                        </tr>
                        <tr>
                            <td><strong>Work Order Number</strong></td>
                            <td>{work_order.wo_number}</td>
                        </tr>
                        <tr>
                            <td><strong>Machine</strong></td>
                            <td>{machine.machine_id} - {machine.name}</td>
                        </tr>
                        <tr>
                            <td><strong>Location</strong></td>
                            <td>{location}</td>
                        </tr>
                        <tr>
                            <td><strong>Priority</strong></td>
                            <td>{priority}</td>
                        </tr>
                        <tr>
                            <td><strong>PM Frequency</strong></td>
                            <td>{machine.pm_frequency}</td>
                        </tr>
                        <tr>
                            <td><strong>PM Due Date</strong></td>
                            <td>{machine.next_pm_date}</td>
                        </tr>
                        <tr>
                            <td><strong>Scheduled Date</strong></td>
                            <td>{scheduled_date}</td>
                        </tr>
                        <tr>
                            <td><strong>Approved By</strong></td>
                            <td>{work_order.approved_by}</td>
                        </tr>
                        <tr>
                            <td><strong>Approved At</strong></td>
                            <td>{work_order.approved_at}</td>
                        </tr>
                    </table>

                    {self._add_notes_section(work_order.notes)}

                    <div class="action-box">
                        <p><strong>Action required: confirm your maintenance date</strong></p>
                        <p>Please <strong>reply to this email</strong> with the date you will
                        perform the maintenance.</p>
                        <ul>
                            <li>Give one specific calendar date, for example
                            <strong>{machine.next_pm_date}</strong>.</li>
                            <li>Relative dates such as "next Monday" or "in two weeks"
                            cannot be processed automatically.</li>
                            <li>Please keep the subject line unchanged so your reply can be
                            matched to {work_order.wo_number}.</li>
                        </ul>
                        <p>Your reply updates the schedule for this work order automatically.
                        If the date has to change later, simply reply again with the new date.</p>
                    </div>

                    <p>If you have any questions, please contact the maintenance team.</p>

                    <p>Best regards,<br>
                    <strong>PM - AI-Assisted Demo</strong></p>
                </div>

                <div class="footer">
                    <p>{EMAIL_FOOTER_NOTE}</p>
                    <p>&copy; {datetime.now().year} {APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _build_completion_email(
        self,
        machine: Machine,
        work_order: WorkOrder
    ) -> str:
        """Build HTML email body for completion notification"""

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2196f3; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .info-box {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #2196f3; }}
                .success-badge {{
                    display: inline-block;
                    background-color: #4caf50;
                    color: white;
                    padding: 8px 15px;
                    border-radius: 4px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Work Order Completed</h1>
                </div>

                <div class="content">
                    <p>Dear {machine.assigned_supplier},</p>

                    <p>Thank you for completing the preventive maintenance work order.</p>

                    <div class="success-badge">
                        ✓ COMPLETED
                    </div>

                    <div class="info-box">
                        <p><strong>Work Order:</strong> {work_order.wo_number}</p>
                        <p><strong>Machine:</strong> {machine.machine_id} - {machine.name}</p>
                        <p><strong>Location:</strong> {machine.location}</p>
                        <p><strong>Completed At:</strong> {work_order.completed_at}</p>
                        <p><strong>Priority:</strong> {work_order.priority}</p>
                    </div>

                    <div class="info-box">
                        <p><strong>Maintenance Schedule Updated:</strong></p>
                        <p>Next PM Date: {machine.next_pm_date}</p>
                        <p>PM Frequency: {machine.pm_frequency}</p>
                    </div>

                    {self._add_notes_section(work_order.notes)}

                    <p>This work order has been marked as completed in our system. The machine's next preventive maintenance schedule has been updated accordingly.</p>

                    <p>If you have any questions or concerns about this work order, please contact the maintenance team.</p>

                    <p>Best regards,<br>
                    <strong>PM - AI-Assisted Demo</strong></p>
                </div>

                <div class="footer">
                    <p>{EMAIL_FOOTER_NOTE}</p>
                    <p>© {datetime.now().year} {APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _add_notes_section(self, notes: Optional[str]) -> str:
        """Add notes section to email if notes exist"""
        if not notes:
            return ""

        return f"""
        <div style="background-color: #fff3cd; padding: 15px; margin: 15px 0; border-left: 4px solid #ffc107;">
            <p><strong>Notes:</strong></p>
            <p>{notes}</p>
        </div>
        """

    def _add_ai_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Add AI decision context to email if available"""
        if not context or 'explanation' not in context:
            return ""

        return f"""
        <div style="background-color: #e3f2fd; padding: 15px; margin: 15px 0; border-left: 4px solid #2196f3;">
            <p><strong>AI Decision:</strong></p>
            <p>{context.get('explanation', '')}</p>
            {f"<p><em>Confidence: {context.get('confidence', 0):.2f}</em></p>" if 'confidence' in context else ""}
        </div>
        """

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        Send email using SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            html: Whether body is HTML

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.settings.SMTP_HOST or not self.settings.SMTP_USERNAME:
            logger.warning("SMTP not configured. Email not sent.")
            logger.info(f"Would have sent email to: {to_email}")
            logger.info(f"Subject: {subject}")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.settings.SMTP_FROM_EMAIL
            msg['To'] = to_email

            # Attach body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Connect to SMTP server and send
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                if self.settings.SMTP_USE_TLS:
                    server.starttls()

                if self.settings.SMTP_USERNAME and self.settings.SMTP_PASSWORD:
                    server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)

                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
