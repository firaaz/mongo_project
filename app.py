from flask import Flask, render_template, url_for, redirect, request, session, flash
from flask_pymongo import PyMongo
import bcrypt
import datetime
from functools import wraps

app = Flask(__name__)

app.config["MONGO_DBNAME"] = "Digipay"
app.config["MONGO_URI"] = "mongodb://localhost:27017/Digipay"
mongo = PyMongo(app)

#Check is session.logged_in is True
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Please Log in First', 'danger')
			return redirect(url_for('signin'))
	return wrap


@app.route("/selection_page")
@is_logged_in
def selection_page():
    return render_template("selection_page.html")

@app.route("/", methods=['POST', 'GET'])
@app.route("/signin", methods=['POST', 'GET'])
def signin():
    if request.method == 'POST':
        users = mongo.db.users
        login_user = users.find_one({'Email' : request.form['email']})
        if login_user: 
            if bcrypt.hashpw(request.form['password'].encode('utf-8'), login_user['Password']) == login_user['Password']:
                session['Username'] = login_user['Username']
                session['Email'] = request.form['email']
                session['logged_in'] = True
                return redirect(url_for('selection_page'))
            flash("Incorrect email/password", 'danger')
            return redirect(url_for('signin'))
    return render_template("signin.html")

@app.route("/signup", methods=['POST','GET'])
def signup():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'Email' : request.form['email']})
        if existing_user is None:
            hashpassword = bcrypt.hashpw(request.form['pwd'].encode('utf-8'), bcrypt.gensalt())
            users.insert({'Name' : request.form['Name'], 'Email' : request.form['email'], 'Username' : request.form['uname'], 'Password' : hashpassword, })
            flash("SignUp successful, please login", 'success')
            return redirect(url_for('signin'))
        flash("User already exists", 'danger')
        return redirect(url_for('signup'))
    return render_template("signup.html")   

@app.route("/balance", methods=['POST', 'GET'])
@is_logged_in
def add_balance():
    total = mongo.db.total
    balance = mongo.db.balance
    if request.method == 'POST':
        balance.insert({'Username' : session['Username'], 'Email' : session['Email'], 'Amount' : request.form['amount'], "C_no" : request.form['c_no'], "Date" : datetime.datetime.now()})
        new_entry = total.find_one({'Email' : session['Email']})
        if new_entry:
            bal = int(new_entry['Total_bal'])
            bal = bal + int(request.form['amount'])
            total.replace_one({'Email':session['Email']}, {'Email' : session['Email'], 'Total_bal' : bal}, upsert=False)
        else:
            total.insert_one({'Email' : session['Email'], "Total_bal" : request.form['amount']})
        flash("Added amount successfully", "success")
        return redirect(url_for('selection_page'))    
    return render_template("balance_insertion.html", balance_list1 = balance.find({'Email': session['Email']}), 
                           total_balance = total.find_one({'Email': session['Email']}))


@app.route("/payment", methods=['GET', 'POST'])
@is_logged_in
def transaction():
    transaction_db = mongo.db.transaction
    total = mongo.db.total
    if request.method == "POST":
        if mongo.db.total.find_one({'Email' : request.form['r_id']}) is None:
            if mongo.db.users.find_one({'Email' : request.form['r_id']}) is None:
                flash("User does not exist", "danger")
                return redirect(url_for("transaction"))
            else:
                total.insert_one({'Email' : request.form['r_id'], "Total_bal" : 0})
        transaction_db.insert({'sender': session['Email'], 'recipient': request.form['r_id'], 'value': int(request.form['amount']), 'description': request.form['desc'],'date': datetime.datetime.now()})
        sender_bal = int(mongo.db.total.find_one({'Email' : session['Email']})['Total_bal'])
        sender_bal = sender_bal - int(request.form['amount'])
        mongo.db.total.replace_one({'Email':session['Email']}, {'Email' : session['Email'], 'Total_bal' : sender_bal}, upsert=False)
        recv_bal = int(mongo.db.total.find_one({'Email' : request.form['r_id']})['Total_bal'])
        recv_bal = recv_bal + int(request.form['amount'])
        mongo.db.total.replace_one({'Email':request.form['r_id']}, {'Email' : request.form['r_id'], 'Total_bal' : recv_bal}, upsert=False)
        flash("Payment successful", "success")
        return redirect(url_for('selection_page'))
        # do the updating of both the databases
    return render_template("transaction.html", transaction_sender_list = transaction_db.find({"sender": session['Email']}),
                           total_balance = total.find_one({"Email": session['Email']}),
                           transaction_recv_list = transaction_db.find({'recipient': session['Email']}))

@app.route("/user_info", methods = ['GET', 'POST'])
@is_logged_in
def user_info():
    users = mongo.db.users
    return render_template("user_info.html", curr_user = users.find({'Email': session['Email']}))

@app.route("/user_contact")
@is_logged_in
def user_contact():
    users = mongo.db.users
    return render_template("user_contact.html", curr_user = users.find())

@app.route("/user_delete", methods = ['GET', 'POST'])
@is_logged_in
def delete_user():
    users = mongo.db.users
    users.delete_one({"Email": session['Email']})
    mongo.db.total.delete_one({"Email" : session['Email']})
    return render_template("user_delete.html")

@app.route("/signout")
def signout():
    session.clear()
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.secret_key = "something"
    app.run(debug=True)
