import smtplib, ssl

def send_email(message, password_file='email_details.txt'):
    """
    sends an email with the input message.
    requires the password_file with the content (for gmail):
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
    with open(password_file) as f:
        lines = f.readlines()
        for line in lines:
            element, value = line.split('\n')[0].split(' ')
            email_details[element] = value

    context = ssl.create_default_context()
    with smtplib.SMTP(email_details['smtp_server'], int(email_details['port'])) as server:
        server.starttls(context=context)
        server.login(email_details['sender_email'], email_details['password'])
        server.sendmail(email_details['sender_email'], email_details['receiver_email'], message)

    return

# send_email('sup')
# message = """\
# Subject: Hi there
#
# This message is sent from Python."""
