import smtplib
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_html_email(sender_email, receiver_email, subject, html_content,
                    smtp_server, smtp_port, password):
    """
  Sends an HTML email using SMTP.

  Args:
    sender_email: The email address of the sender.
    receiver_email: The email address of the recipient.
    subject: The subject of the email.
    html_content: The HTML content of the email.
    smtp_server: The SMTP server address.
    smtp_port: SMTP Server port.
    password: The password for SMTP authentication.
  """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email

        text_part = "This is a plain text version of the message."
        html_part = html_content

        msg.attach(MIMEText(text_part, 'plain'))
        msg.attach(MIMEText(html_part, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # Enable TLS for secure communication
            server.starttls()

            # **Important:** Use an app password instead of your actual Gmail password
            # Get your app password from your Google Account security settings.
            # Refer to Google's documentation for detailed instructions.

            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())

        print("Email sent successfully!")

    except Exception as e:
        print(f"Error sending email: {e}")


def csv_to_html(input_file, position=None):
    """Read CSV file and return it as a html data for mail"""

    if position is None:
        position = []

    with open(input_file, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)

        # Start the HTML table
        html_output = "<table border='1'>\n"
        # Read each row of the CSV file
        is_first_row = 1
        for row in csv_reader:
            html_output += "  <tr>\n"
            for item in row:
                if any(member in row for member in position):
                    html_output += f"    <td style=\"text-align: center; color: red;\"text-align: center; " \
                                   f"vertical-align: middle;\">{item}</td>\n"
                else:
                    if is_first_row:
                        html_output += f"    <td style=\"text-align: center; font-weight: bold; \
                        vertical-align: middle;\">{item}</td>\n"
                    else:
                        html_output += f"    <td style=\"text-align: center; vertical-align: middle;\">{item}</td>\n"
            html_output += "  </tr>\n"
            is_first_row = 0

        # Close the HTML table
        html_output += "</table>"
    return html_output
