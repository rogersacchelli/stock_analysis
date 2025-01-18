import logging
import smtplib
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def send_html_email(receiver_email, subject, html_content,
                    config):
    """
  Sends an HTML email using SMTP.

  Args:
    receiver_email: The email address of the recipient.
    subject: The subject of the email.
    html_content: The HTML content of the email.
    config: Configuration File.
  """

    try:

        smtp_server = config['Email']['smtp_server']
        smtp_port = config['Email']['smtp_port']
        password = config['Email']['from_password']
        sender_email = config['Email']['from_email']

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

        logging.info("Email sent successfully!")

    except Exception as e:
        logging.error(f"Error sending email: {e}")


def csv_to_html(input_file, position):
    """Read CSV file and return it as a html data for mail"""

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
                    html_output += f"    <td style=\"font-family: 'Courier New', Courier, monospace; " \
                                   f"\"text-align: center; color: red;\"text-align: center; " \
                                   f"vertical-align: middle;\">{item}</td>\n"
                else:
                    if is_first_row:
                        html_output += f"    <td style=\"font-family: 'Courier New', Courier, monospace; " \
                                       f"\"text-align: center; font-weight: bold; \
                        vertical-align: middle;\">{item}</td>\n"
                    else:
                        html_output += f"    <td style=\"font-family: 'Courier New', Courier, monospace; " \
                                       f"\"text-align: center; vertical-align: middle;\">{item}</td>\n"
            html_output += "  </tr>\n"
            is_first_row = 0

        # Close the HTML table
        html_output += "</table>"
    return html_output


def mail_analysis(report_hash, config, rctp_to, subject, position):

    if position:
        position_list = list(position['Position'].keys())
        position_data = csv_to_html(f"reports/{report_hash}-position.csv", position=position_list)
    else:
        position_list = []

    report_data = csv_to_html(f"reports/{report_hash}.csv", position=position_list)

    head = f"""<html> \
                   <head>
                    </head> """
    body = f"""<body><h2 style="font-family: 'Courier New', Courier, monospace;">Daily Stock Report</h2> 
               <h3 style="font-family: 'Courier New', Courier, monospace;">Analysis</h3>
                {report_data}
                """

    if position:
        body += f"""<h3 style="font-family: 'Courier New', Courier, monospace;">Position Results</h3>\
                {position_data}
                <p style="font-family: 'Courier New', Courier, monospace;">** Lower or equal to stop margin</p>"""

    footer = "</body></html>"

    content = head + body + footer

    send_html_email(receiver_email=rctp_to, subject=f"{subject}", config=config, html_content=content)