from flask import Flask,redirect,url_for,render_template,request,flash,abort,session,send_file
from flask_session import Session
from key import secret_key,salt1,salt2,salt3
import flask_excel as excel
from stoken import token
from cmail import sendmail
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
from io import BytesIO
import random
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
Session(app)
excel.init_excel(app)
mydb=mysql.connector.connect(host='localhost',user='root',password='dhedhipya@143',db='ganesh')
@app.route('/')
def index():
    return render_template('title.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from users where username=%s and password=%s',[username,password])
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['user']=username
                cursor.execute('select email_status from users where username=%s',[username])
                status=cursor.fetchone()[0]
                cursor.close()
                if status!='confirmed':
                    return redirect(url_for('inactive'))
                else:
                    return redirect(url_for('home'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('login.html')
        else:
            cursor.close()
            flash('invalid username')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/inactive')
def inactive():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return redirect(url_for('home'))
        else:
            return render_template('inactive.html')
    else:
        return redirect(url_for('login'))
@app.route('/homepage',methods=['GET','POST'])
def home():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':

            return render_template('homepage.html')
        else:
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/resendconfirmation')
def resend():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.execute('select email from users where username=%s',[username])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('home'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into users (username,password,email) values(%s,%s,%s)',(username,password,email))
        except mysql.connector.IntegrityError:
            flash('Username or email is already in use')
            return render_template('registration.html')
        else:
            mydb.commit()
            cursor.close()
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Thanks for signing up.Follow this link-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return render_template('registration.html')
    return render_template('registration.html')
    
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=120)
    except Exception as e:
        #print(e)
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('login'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update users set email_status='confirmed' where email=%s",[email])
            mydb.commit()
            flash('Email confirmation success')
            return redirect(url_for('login'))
@app.route('/forget',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('SELECT email_status from users where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='confirmed':
                flash('Please Confirm your email first')
                return render_template('forgot.html')
            else:
                subject='Forget Password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('login'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')
@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update users set password=%s where email=%s',[newpassword,email])
                mydb.commit()
                flash('Reset Successful')
                return redirect(url_for('login'))
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')

@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))
@app.route('/create',methods=['GET','POST'])
def create():
    if session.get('user'):
        if request.method=='POST':
            upc=[chr(i) for i in range(ord('A'),ord('Z')+1)]
            lwc=[chr(i) for i in range(ord('a'),ord('z')+1)]
            otp=''
            for i in range(2):
                otp+=random.choice(upc)
                otp+=str(random.randint(0,9))
                otp+=random.choice(lwc)
            time=request.form['time']
            cursor=mydb.cursor(buffered=True)
            url=url_for('survey_start',token=token(otp,salt3),_external=True)
            cursor.execute('insert into survey (sr_id,sr_link,time,added_by) values(%s,%s,%s,%s)',[otp,url,time,session.get('user')])
            mydb.commit()
            flash('Survey created')
            return redirect(url_for('allsurveys'))
        return render_template('create.html')
    else:
        return redirect(url_for('login'))
@app.route('/allsurveys')
def allsurveys():
    if session.get('user'):
        cursor=mydb.cursor()
        cursor.execute('SELECT * FROM survey where added_by=%s',[session.get('user')])
        data=cursor.fetchall()
        return render_template('feedbackform.html',data=data)
    else:
        return redirect(url_for('login'))  

@app.route('/feedback/<int:typ>')
def feedback(typ):
    if session.get('user'):
        if typ==1:
            return render_template('training.html')
    else:
        return redirect(url_for('login'))

@app.route('/survey/<token>',methods=['GET','POST'])
def survey_start(token):
    try:
        s=URLSafeTimedSerializer(secret_key)
        cursor=mydb.cursor(buffered=True)
        sid=s.loads(token,salt=salt3)
        cursor.execute('SELECT time FROM survey where sr_id=%s',[sid])
        time=cursor.fetchone()[0]
        cursor.close()
        survey_dict=s.loads(token,salt=salt3,max_age=time)
        sid=survey_dict
        if request.method=='POST':
            name=request.form['name']
            rollno=request.form['rollno']
            one=request.form['1']
            two=request.form['2']
            three=request.form['3']
            four=request.form['4']
            five=request.form['5']
            six=request.form['6']
            seven=request.form['7']
            eight=request.form['8']
            nine=request.form['9']
            ten=request.form['Comment']       
            cursor=mydb.cursor()
            cursor.execute('insert into surv_data values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',[sid,name,rollno,one,two,three,four,five,six,seven,eight,nine,ten])
            mydb.commit()
            cursor.close()
            return 'Survey submitted successfully'
        return render_template("training.html")
    except Exception as e:
        print(e)
        abort(410,description='SUrvey link expired')
@app.route('/download/<sid>')
def download(sid):
    cursor=mydb.cursor()
    lst=['Name','Roll no','1.The training met your expectations?',
    '2.How do you rate the training overall?',
    '3.Class participation and interaction were encouraged?',
    '4.After attending the session,what did you think?',
    '5.Is the sessions are clear and understandable?',
    '6.is this training is useful to you?',
    '7.Do you learn a new thing from this training?',
    '8.what you think about this internship?',
    '9.Do you like your traning?',
    '10.Any other feedback you would like to share']
   

    cursor.execute('SELECT * from surv_data where surv_id=%s',[sid])
    user_data=[list(i)[1:] for i in cursor.fetchall()]
    user_data.insert(0,lst)
    print(user_data)
    return excel.make_response_from_array(user_data, "xlsx",file_name="Faculty_data")

app.run(debug=True,use_reloader=True)
