from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField
from wtforms.validators import InputRequired, Email, Length
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, current_user, UserMixin, login_required


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SECRET_KEY'] = 'wololo'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(20), unique = True, nullable = False)
    password = db.Column(db.String(20), unique = True, nullable = False)

class UserForm(FlaskForm):
    username = StringField('USERNAME ', validators= [InputRequired(), Length(min = 6, max =20)])
    password = StringField('PASSWORD ', validators= [ InputRequired(), Length(min = 8, max = 20)])


class loginform(FlaskForm):
    username = StringField('USERNAME ', validators= [InputRequired(), Length(min = 6, max =20)])
    password = StringField('PASSWORD ', validators= [ InputRequired(), Length(min = 8, max = 20)])

class Student(db.Model):
    sid = db.Column(db.Integer, primary_key=True)
    sname = db.Column(db.String(50), nullable=False)
    sage = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Student {self.sname}>"

class Person(db.Model):
    pid = db.Column(db.Integer, primary_key=True)
    pusername = db.Column(db.String(50), nullable=False)
    pword = db.Column(db.String(255), nullable=False) 
    pmail = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.pusername}>"



class StudentRegForm(FlaskForm):
    stud_name = StringField(
        'Student Name',
        validators=[InputRequired(), Length(min=2, max=50)]
    )
    stud_age = IntegerField(
        'Student Age',
        validators=[InputRequired()]
    )


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/dashboard')
@login_required
def signup():
    return render_template('dash.html')

@app.route('/signup', methods=['GET', 'POST'])
def dash():
    form = UserForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        new_user = User(
            username=form.username.data,
            password=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect('/login')
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")

    return render_template('signup.html', form=form)


@app.route('/login', methods = ['GET', 'POST'])
def logincls():
    form = loginform()
    return render_template('login.html', form = form)


@app.route('/', methods=['GET', 'POST'])
def index():
    form = StudentRegForm()
    details = Student.query.all()

    if form.validate_on_submit():
        lname = form.stud_name.data
        myage = form.stud_age.data

        try:
            student = Student(sname=lname, sage=myage)
            db.session.add(student)
            db.session.commit()
            return redirect('/')

        except Exception as e:
            db.session.rollback()
            print(f"Error inserting data: {e}")

    return render_template('index.html', form=form, details=details)

@app.route('/about')
def about():
    return 'About Our Life'



if __name__ == '__main__':
    app.run(debug=True, port=5555)