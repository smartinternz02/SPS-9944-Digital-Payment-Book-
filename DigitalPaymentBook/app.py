from flask import Flask,render_template,request,redirect,session,url_for,flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
import config
app = Flask(__name__)

app.config['SECRET_KEY'] = '65f4f0838c7644381511d1ebd7f51622'
app.config['MYSQL_HOST'] = 'remotemysql.com'
app.config['MYSQL_USER'] = 'MHhwhqx1hC'
app.config['MYSQL_PASSWORD'] = 'BAK3Oi1qJ6'
app.config['MYSQL_DB'] = 'MHhwhqx1hC'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = config.email
app.config['MAIL_PASSWORD'] = config.password
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False

mysql = MySQL(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

@app.route('/')
def home():
	return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    msg = "Create an account to continue."
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confpassword = request.form['confpassword']
        phoneno = request.form['phoneno']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = % s', (email, ))
        account = cursor.fetchone()
        if account:
            msg = "Account with this Email ID already exists!"
            return render_template('register.html',msg=msg)
        elif password != confpassword:
            msg = password + " " + confpassword
            msg = "Passwords doesn't match"
        else:
            hash_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute('INSERT INTO users(name,email,password,phoneno) VALUES(% s,% s,% s,% s)',(username,email,hash_password,phoneno))
            mysql.connection.commit()
            msg = Message(
                'Thanks for registering',
                sender=config.email,
                recipients=[email]
            )
            msg.body = f'''
                    Welcome to Digital Payments Book {username}!
                    Account creation in Digital Payments Book was successful!
                    Thank you for using DigitalPaymentsBook.
                '''
            mail.send(msg)
            msg = "Registered Successfully! Log In to continue"
            return render_template('register.html',msg=msg)
    return render_template('register.html',msg=msg)

@app.route('/login',methods=['POST','GET'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = % s', (email, ))
        account = cursor.fetchone()
        if account and bcrypt.check_password_hash(account['password'],password):
            session['loggedin'] = True
            session['id'] = account['userid']
            session['username'] = account['name']
            session['isretailer']=account['isretailer']
            info = 'Logged in successfully !' + 'Welcome ' + session['username'] 
            return redirect(url_for('dashboard'))
        else:
            msg = 'Incorrect email / password !'
    return render_template('login.html', msg = msg)

@app.route('/logout')
def logout():
    session.pop('loggedin',None)
    session.pop('id',None)
    session.pop('username',None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session.keys():
        return redirect(url_for('login'))
    elif 'loggedin' in session.keys() and session['isretailer'] == 1:
        return redirect(url_for('admin'))
    else:
        if 'loggedin' in session.keys() and session['isretailer'] == 0:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT name,email,phoneno FROM users WHERE userid = % s",[session['id']])
            user_details = cursor.fetchall()
            cursor.execute("SELECT purchaseid,userid,itemname, price, amountpaid, purchasedate  FROM purchase WHERE userid = % s",[session['id']])
            purchase_details = cursor.fetchall()
            cursor.execute("SELECT purchaseid,userid,itemname, price, amountpaid, purchasedate FROM purchase WHERE amountpaid<price AND userid = % s",[session['id']])
            pending_payments = cursor.fetchall()
        return render_template('dashboard.html',user_details=user_details,pending_payments=pending_payments,purchase_details=purchase_details,username=session['username'],userid=session['id'])

@app.route('/contactus')
def contactus():
    if 'loggedin' in session.keys():
        return render_template('contactus.html')
    else:
        return render_template('contact.html')

@app.route('/allpurchases')
def allpurchases():
    if 'loggedin' in session.keys():
        if session['isretailer'] == 1:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchaseid,userid,itemname, price, amountpaid, purchasedate FROM purchase")
            all_purchase_details = cursor.fetchall()
            return render_template('allpurchases.html',all_purchase_details=all_purchase_details)
        else:
            return '<h3>This page can only be accessed by admin.</h3>'
    else:
        return redirect(url_for('login'))

@app.route('/addpurchase',methods=['POST','GET'])
def addpurchase():
    if 'loggedin' in session.keys():
        if session['isretailer'] == 1:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT userid,email FROM users WHERE isretailer=0")
            users=cursor.fetchall()
            msg = ''
            if request.method == 'POST':
                userid = request.form['userid']
                itemname = request.form['itemname']
                purchasedate = request.form['purchasedate']
                amountpaid = request.form['amountpaid']
                price = request.form['price']
                cursor = mysql.connection.cursor()
                cursor.execute("INSERT INTO purchase(userid,itemname,price,purchasedate,amountpaid) VALUES(% s,% s,% s,% s, % s)",[userid,itemname,price,purchasedate,amountpaid])
                mysql.connection.commit()
                cursor.execute("SELECT MAX(purchaseid) FROM purchase")
                purid = cursor.fetchone()[0]
                cursor.execute("INSERT INTO payments(purchaseid, amountpaid, paymentdate) VALUES(% s,% s,% s)",[purid,amountpaid,purchasedate])
                mysql.connection.commit()
                msg = "Purchase Added"
            return render_template('addpurchase.html',users=users,msg=msg)
        else :
            return '<h3>This page can only be accessed by admin.</h3>'
    else:
        return redirect(url_for('login'))

@app.route('/addpayment',methods=['POST','GET'])
def addpayment():
    if 'loggedin' in session.keys():
        if session['isretailer'] == 1:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchaseid FROM purchase WHERE amountpaid<price")
            purchases=cursor.fetchall()
            msg = ''
            if request.method == 'POST':
                purchaseid = request.form['purchaseid']
                amountpaid = request.form['amountpaid']
                paymentdate = request.form['paymentdate']
                cursor = mysql.connection.cursor()
                cursor.execute("INSERT INTO payments(purchaseid, amountpaid, paymentdate) VALUES(% s,% s,% s)",[purchaseid,amountpaid,paymentdate])
                cursor.execute("UPDATE purchase SET amountpaid=amountpaid + % s WHERE purchaseid = % s",[amountpaid,purchaseid])
                mysql.connection.commit()
                msg = 'Payment Added to record'
            return render_template('addpayment.html',purchases=purchases,msg=msg)
        else :
            return '<h3>This page can only be accessed by admin.</h3>'
    else:
        return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if 'loggedin' in session.keys():
        if session['isretailer'] == 1:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchaseid,userid,itemname, price, amountpaid, purchasedate FROM purchase WHERE amountpaid<price")
            pending_payments = cursor.fetchall()
            return render_template('admin.html',pending_payments=pending_payments)
        else :
            return '<h3>This page can only be accessed by admin.</h3>'
    else:
        return redirect(url_for('login'))

@app.route('/sendmail/<int:purchaseid>')
def sendmail(purchaseid):
    if 'loggedin' in session.keys():
        if session['isretailer'] == 1:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT userid,amountpaid,price,purchasedate,itemname FROM purchase WHERE purchaseid=% s",[purchaseid])
            purchase_details = cursor.fetchone()
            cursor.execute("SELECT email,name FROM users WHERE userid=% s",[purchase_details[0]])
            user_details = cursor.fetchone()
            msg = Message(
                'Regarding pending payments',
                sender=config.email,
                recipients=[user_details[0]]
            )
            msg.body = f'''
                    Grettings {user_details[1]}!
                    You have a pending payment for the purchase : 
                        Item Name : {purchase_details[4]}
                        Amount Paid : {purchase_details[1]}
                        Total price : {purchase_details[2]}
                    You have to pay Rs.{purchase_details[2]-purchase_details[1]}.
                    Please complete the payment soon.
                    Thank you.
                '''
            mail.send(msg)
            return redirect(url_for('admin'))
        else :
            return '<h3>This page can only be accessed by admin.</h3>'
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
	app.run(debug=True)