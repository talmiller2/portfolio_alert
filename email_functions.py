import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import html
import os

def send_email(subject, message, email_details_file='email_details.txt'):
    """
    sends an email with the input message.
    requires the email_details_file with the content (for gmail):
    "
        smtp_server smtp.gmail.com
        port 587
        sender_email XXX@gmail.com
        receiver_email XXX@gmail.com
        password XXX
    "
    note that the password is not the standard gmail password but a dedicated "apps password", to set it up read the
    tutorial https://support.google.com/accounts/answer/185833?hl=en
    """
    email_details = {}
    with open(os.path.dirname(__file__) + '/' + email_details_file) as f:
        lines = f.readlines()
        for line in lines:
            element, value = line.split('\n')[0].split(' ')
            email_details[element] = value

    # Create a multipart message object
    msg = MIMEMultipart()
    msg["From"] = email_details['sender_email']
    msg["To"] = email_details['receiver_email']
    msg["Subject"] = subject

    # Format the message with inline CSS to make specific lines bold
    formatted_lines = []
    for line in message:
        if '===' in line:
            formatted_line = f'<span style="font-weight: bold;">{html.escape(line)}</span>'
        else:
            formatted_line = html.escape(line)
        formatted_lines.append(formatted_line)

    # Format the message with inline CSS and the <pre> tag to preserve line breaks and left-align text
    formatted_message = f"""
    <html>
      <body>
        <pre style="text-align: left; white-space: pre-wrap;" dir="ltr">{'<br>'.join(formatted_lines)}</pre>
      </body>
    </html>
    """

    # Attach the formatted message to the MIMEMultipart object
    msg.attach(MIMEText(formatted_message, "html"))

    try:
        # Create a secure SSL/TLS connection with the SMTP server
        server = smtplib.SMTP(email_details['smtp_server'], email_details['port'])
        server.starttls()

        # Log in to your SMTP server
        server.login(email_details['sender_email'], email_details['password'])

        # Send the email
        server.sendmail(email_details['sender_email'], email_details['receiver_email'], msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print("An error occurred while sending the email:", str(e))
    finally:
        # Close the connection to the SMTP server
        server.quit()

    return


