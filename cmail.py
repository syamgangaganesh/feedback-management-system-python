import smtplib
from smtplib import SMTP_SSL
from email.message import EmailMessage
def sendmail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('supuriganesh5@gmail.com','bderljlpzsmflzct')
    msg=EmailMessage()
    msg['from']='supuriganesh5@gmail.com'
    msg['Subject']=subject
    msg['To']=to
    msg.set_content(body)
    server.send_message(msg)
    server.quit()
