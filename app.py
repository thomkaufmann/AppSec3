from flask import Flask, flash, session, render_template, redirect, url_for, request
import sqlite3 as sql
import subprocess, random
import os
from subprocess import check_output
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import InputRequired, Regexp, Length, NumberRange, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

def create_app():

   sql.connect("database.db")
   project_dir = os.path.dirname(os.path.abspath(__file__))
   database_file = "sqlite:///{}".format(os.path.join(project_dir, "database.db"))

   app = Flask(__name__)

   app.config.update(
      SESSION_COOKIE_SECURE=False, # should be set to true upon adding SSL
      SESSION_COOKIE_HTTPONLY=True,
      SESSION_COOKIE_SAMESITE='Strict',
      TESTING=True,
      SECRET_KEY=os.urandom(16),
      SQLALCHEMY_DATABASE_URI = database_file,
      SQLALCHEMY_TRACK_MODIFICATIONS = False
   )
   db = SQLAlchemy(app)

   class User(db.Model):
      id = db.Column('id', db.Integer, primary_key = True)
      username = db.Column(db.String(50), unique = True)
      password = db.Column(db.String(100))  
      pin = db.Column(db.Integer)

      def __init__(self, username, password, pin):
         self.username = username
         self.password = generate_password_hash(password)
         self.pin = pin 

   db.create_all()
   admin = User.query.filter_by(username='admin').first()
   if admin is None:
      db.engine.execute("INSERT INTO user (username,password,pin) VALUES ('admin','pbkdf2:sha256:150000$FvnZM8fM$f37c7ec344b2aaef2d23ffd50507222e3215518c45ed7a326f986b4912c4c12b','19008675309')")
   
   @app.after_request
   def set_headers(response):
      response.headers['Content-Security-Policy'] = "default-src 'self'"
      response.headers["X-Frame-Options"] = "SAMEORIGIN"
      response.headers['X-Content-Type-Options'] = 'nosniff'
      response.headers['X-XSS-Protection'] = '1; mode=block'      
      return response

   @app.route("/")
   def index():
      #if logged in, send to spell check form, otherwise send to login
      if 'username' in session: 
         return redirect(url_for('spell_check'))
      
      return redirect(url_for('login'))

   @app.route("/spell_check", methods = ['POST', 'GET'])
   def spell_check():
      if 'username' in session: 
         form = SpellForm()
         if form.validate_on_submit():
            text = form.inputtext.data
            #set textout field to be input text
            form.textout.data = form.inputtext.data
            form.inputtext.data = ""
            
            #define filename to include username and a random number
            username = session['username']
            filename = username+'-'+str(random.randint(1, 1000))+'.txt'

            #create file and set output of check_words to misspelled input text
            with open(filename, 'w') as f:
               f.write(str(text))
               f.close()
               if os.path.isfile(filename):
                  form.misspelled.data = check_words(filename)
                  os.remove(filename)
               else:
                  print("Error: %s file not found" % filename)            

         return render_template("spell_check.html", form = form)
      else:
         return redirect(url_for('login'))

   @app.route('/register', methods = ['POST', 'GET'])
   def register():
      if 'username' in session: 
         return redirect(url_for('spell_check'))

      form = UserForm()
      # form_type is used to put a title on the html view and to set the form action (register or login)
      form_type = "Register"

      if request.method == "POST":
         if form.validate_on_submit():
            username = form.uname.data
            password = form.pword.data
            pin = form.pin.data

            if username != '' and password != '' and pin != '':
               user = User.query.filter_by(username=username).first()
               if user != None:
                  flash("Failure: Account already exists. Please login or select a different username.","success")
                  return redirect(url_for('login'))  
               else:
                  user = User(username, password, pin)
                  db.session.add(user)
                  db.session.commit()                     
                  flash("Success: Account registered!","success")
                  return redirect(url_for('login'))  
            else:
               flash("Failure: Invalid account details. Please try again.","success")
         else:   
            flash("Failure: Please try again.","success")

      return render_template("form.html", type = form_type, form = form)

   @app.route('/login', methods = ['POST', 'GET'])
   def login():
      if 'username' in session: 
         return redirect(url_for('spell_check'))
      
      form = UserForm()
      # form_type is used to put a title on the html view and to set the form action (register or login)
      form_type = 'Login'
      if request.method == 'POST':
         if form.validate_on_submit():
            
            username = form.uname.data
            password = form.pword.data
            pin = form.pin.data
            
            user = User.query.filter_by(username=username).first()

            if user != None and check_password_hash(user.password,password):
               if (pin == user.pin) or (pin == "" and user.pin is None):
                  session['username'] = username
                  flash("Success: You are logged in!","result")
                  return redirect(url_for('spell_check'))                              
               else:
                  flash("Two-factor failure. Please try again.","result")   
            else:
               flash("Incorrect username or password. Please try again.","result")
         else:
            flash("Failure: Please try again.","result")

      return render_template("form.html", type = form_type, form = form)      

   @app.route('/logout')
   def logout():
      session.clear()
      return redirect(url_for('login'))

   def check_words(filename):
      stdout = check_output(['./a.out',filename, 'wordlist.txt']).decode('utf-8').replace('\n',', ')[:-2]
      return stdout

   class UserForm(FlaskForm):
      uname = StringField('Username', validators=[InputRequired(), Regexp(r'^[\w.@+-]+$'), Length(min=4, max=25)])
      pword = PasswordField('Password', validators=[InputRequired()])
      pin = IntegerField('Two-Factor Authentication', validators=[Optional(), NumberRange(min=10000000000,max=99999999999)], id='2fa')
      submit = SubmitField('Submit')

   class SpellForm(FlaskForm):
      inputtext = TextAreaField('Text', validators=[InputRequired()], id="inputtext", render_kw={"rows": 4, "cols": 100})
      textout = TextAreaField('Text out', id="textout", render_kw={"disabled": "disabled", "rows": 4, "cols": 100})
      misspelled = TextAreaField('Misspelled', id="misspelled", render_kw={"disabled": "disabled", "rows": 4, "cols": 100})
      submit = SubmitField('Submit')

   return app
if __name__ == '__app__':
   create_app().run(debug = True)