from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
from forms import RegisterForm, FindCafeForm, LoginForm, AddCafeForm, CommentForm, EditCafeForm
from functools import wraps
import bleach
import smtplib
import os


# for visitors & users to mail me
MY_EMAIL = os.environ.get("EMAIL_ACCOUNT")
MY_PASSWORD = os.environ.get("EMAIL_PASSWORD")
TO_EMAIL = os.environ.get("TO_EMAIL")


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)
# ref: https://pythonhosted.org/Flask-Gravatar/
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ref: https://flask-login.readthedocs.io/en/latest/#configuring-your-application
# configure your Flask app to use Flask_Login.
# The most important part of an application that uses Flask-Login is the LoginManager class.
login_manager = LoginManager()
login_manager.init_app(app)

# provide a user_loader callback.
# This callback is used to reload the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


##CONFIGURE TABLES

class Cafe(db.Model):
    __tablename__ = "cafe_shops"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    open_time = db.Column(db.Text, nullable=False)
    map_url = db.Column(db.String(250), unique=True, nullable=False)
    location = db.Column(db.String(250), nullable=False)
    district = db.Column(db.String(250), nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    coffee_price = db.Column(db.String(250), nullable=False)

    # *******Add parent relationship*******#
    # "comment_cafe_shop" refers to the comment_cafe_shop property in the Comment class.
    comments = relationship("Comment", back_populates="comment_cafe_shop")

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # *******Add parent relationship*******#
    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # *******Add child relationship*******#
    # "users.id" The users refers to the tablename of the User class.
    # "comments" refers to the comments property in the User class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    # *******Add child relationship*******#
    # "cafe_shops.id" The users refers to the tablename of the Cafe class.
    # "comments" refers to the comments property in the User class.
    cafe_shops_id = db.Column(db.Integer, db.ForeignKey("cafe_shops.id"))
    comment_cafe_shop = relationship("Cafe", back_populates="comments")

#Line below only required once, when creating DB.
db.create_all()


# user can't see the buttons
# but they can manually access the /edit-post or /new-post or /delete routes.
# Protect these routes by creating a Python decorator called @admin_only
def admin_only(function):
    # 裝飾詞在被 wrapper 包一層後，其 __name__ 屬性就會被修改成 wrapper
    @wraps(function)
    def wrapper(*args, **kwargs):
        # "is_anonymous" catch unauthenticated users
        if current_user.is_anonymous or current_user.id != 1:
            return abort(403)
        else:
        # Otherwise continue with the route function
            return function(*args, **kwargs)
    return wrapper


# e.g. "07" --> "7"
def eliminate_title_zero(item):
    if len(item) == 2 and item[0] == "0":
        item = item[1]
    return item


def time_in_range(start_time, end_time, current_time):
    # if current time in range, return True
    if end_time > start_time:
        return start_time <= current_time <= end_time
    else:
        # over midnight
        return current_time >= start_time or end_time >= current_time

def send_email(name, email, phone, message):
    email_message = f"Subjects: New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(MY_EMAIL, MY_PASSWORD)
        connection.sendmail(
            from_addr=MY_EMAIL,
            to_addrs=TO_EMAIL,
            msg=email_message
        )

# Security cafe post from comment
# strips invalid tags/attributes
def strip_invalid_html(content):
    allowed_tags = ['a', 'abbr', 'acronym', 'address', 'b', 'br', 'div', 'dl', 'dt',
                    'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
                    'li', 'ol', 'p', 'pre', 'q', 's', 'small', 'strike',
                    'span', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
                    'thead', 'tr', 'tt', 'u', 'ul']

    allowed_attrs = {
        'a': ['href', 'target', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
    }

    cleaned = bleach.clean(content,
                           tags=allowed_tags,
                           attributes=allowed_attrs,
                           strip=True)

    return cleaned

@app.route('/', methods=["GET", "POST"])
def query_for_cafes():
    form = FindCafeForm()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to log in or register to use the service.")
            return redirect(url_for("login"))

        today = datetime.datetime.now()
        cafes = Cafe.query.filter_by(district=form.district.data).all()
        cafes_list = []

        # check if current time in cafes' opening time
        for cafe in cafes:
            # e.g. ['Mon: 07:00–22:00', 'Tue: 07:00–22:00', 'Wed: 07:00–22:00', 'Thu: 07:00–22:00', 'Fri: 07:00–22:00', 'Sat: 07:00–22:00', 'Sun: 07:00–22:00']
            open_time_list = cafe.open_time.split(",")
            open_time_dict = {}

            for item in open_time_list:
                weekday = item.split(": ")
                # e.g. {'Mon': '07:00–22:00', 'Tue': '07:00–22:00', 'Wed': '07:00–22:00', 'Thu': '07:00–22:00', 'Fri': '07:00–22:00', 'Sat': '07:00–22:00', 'Sun': '07:00–22:00'}
                open_time_dict[weekday[0]] = weekday[1]

            # e.g. 07:00–22:00
            operating_time = open_time_dict[today.strftime("%a")]

            # skip this cafe cuz it gets a day off
            if operating_time == "休息":
                continue

            # google map 上營業時間的 "–" 跟一般英打 "-" 有差
            # e.g. 07:00
            open_time = operating_time.split("–")[0]
            # e.g. 22:00
            close_time = operating_time.split("–")[1]

            # e.g. 07
            open_time_hour = open_time.split(":")[0]
            # e.g. 00
            open_time_min = open_time.split(":")[1]

            close_time_hour = close_time.split(":")[0]
            close_time_min = close_time.split(":")[1]

            # e.g. "07" --> 7; "00" --> 0
            is_open_time = datetime.time(int(eliminate_title_zero(open_time_hour)),
                                         int(eliminate_title_zero(open_time_min)))
            is_close_time = datetime.time(int(eliminate_title_zero(close_time_hour)),
                                          int(eliminate_title_zero(close_time_min)))
            current_time = datetime.datetime.now().time()

            in_time_range = time_in_range(start_time=is_open_time, end_time=is_close_time, current_time=current_time)

            if in_time_range:
                # pass cafe data and operating_time in nested list format
                cafes_list.append([cafe, operating_time])

        return render_template("index.html", form=form, be_searched=True, cafes=cafes_list)
    return render_template("index.html", form=form, be_searched=False)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        # check email had been signed or not
        if User.query.filter_by(email=form.email.data).first():
            # ref: https://flask.palletsprojects.com/en/1.1.x/patterns/flashing/
            flash("You have already signed up with that email, log in instead!")
            #Redirect to /login route.
            return redirect(url_for("login"))

        hash_and_salted_password = generate_password_hash(
            password=form.password.data,
            method="pbkdf2:sha256",
            salt_length=8
        )

        new_user = User(
            email=form.email.data,
            password=hash_and_salted_password,
            name=form.name.data
        )

        db.session.add(new_user)
        db.session.commit()

        #Log in and authenticate user after adding details to database.
        #This line will authenticate the user with Flask-Login
        login_user(new_user)

        return redirect(url_for("query_for_cafes"))

    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_email = form.email.data
        login_password = form.password.data
        user = User.query.filter_by(email=login_email).first()

        #Email doesn't exist
        if not user:
            flash("The email does not exist, please try again")
            return redirect(url_for("login"))

        #Password incorrect
        elif not check_password_hash(pwhash=user.password,
                                     password=login_password):
            flash("Password incorrect, please try again.")
            return redirect(url_for("login"))

        #Email exists and password correct
        else:
            login_user(user)
            return redirect(url_for("query_for_cafes"))

    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('query_for_cafes'))


@app.route("/cafe/<int:cafe_id>", methods=["GET", "POST"])
@login_required
def show_cafe(cafe_id):
    form = CommentForm()
    requested_cafe = Cafe.query.get(cafe_id)

    if form.validate_on_submit():

        clean_comment = strip_invalid_html(form.comment_text.data)

        new_comment = Comment(
            text=clean_comment,
            comment_author=current_user,
            comment_cafe_shop=requested_cafe
        )
        db.session.add(new_comment)
        db.session.commit()

    return render_template("cafe.html", cafe=requested_cafe, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["POST", "GET"])
def contact():
    if request.method == "POST":
        send_email(name=request.form["name"], email=request.form["email"],
                   phone=request.form["phone"], message=request.form["message"])

        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)


@app.route("/new-cafe", methods=["GET", "POST"])
@admin_only
def add_new_cafe():
    form = AddCafeForm()
    if form.validate_on_submit():

        opening_time = f"Mon: {form.open_time_Mon.data}," \
                       f"Tue: {form.open_time_Tue.data}," \
                       f"Wed: {form.open_time_Wed.data}," \
                       f"Thu: {form.open_time_Thu.data}," \
                       f"Fri: {form.open_time_Fri.data}," \
                       f"Sat: {form.open_time_Sat.data}," \
                       f"Sun: {form.open_time_Sun.data}"

        new_cafe = Cafe(
            name=form.name.data,
            open_time=opening_time,
            map_url=form.map_url.data,
            location=form.location.data,
            district=form.district.data,
            has_wifi=form.wifi.data,
            has_sockets=form.sockets.data,
            coffee_price=form.coffee_price.data
        )
        db.session.add(new_cafe)
        db.session.commit()
        return redirect(url_for("query_for_cafes"))
    return render_template("add-cafe.html", form=form)


@app.route("/edit-cafe/<int:cafe_id>", methods=["GET", "POST"])
@admin_only
def edit_cafe(cafe_id):
    cafe = Cafe.query.get(cafe_id)
    edit_form = EditCafeForm(
        name=cafe.name,
        location=cafe.location,
        district=cafe.district,
        open_time=cafe.open_time,
        map_url=cafe.map_url,
        coffee_price=cafe.coffee_price,
        wifi=cafe.has_wifi,
        sockets=cafe.has_sockets
    )

    if edit_form.validate_on_submit():
        cafe.name = edit_form.name.data
        cafe.open_time = edit_form.open_time.data
        cafe.map_url = edit_form.map_url.data
        cafe.location = edit_form.location.data
        cafe.district = edit_form.district.data
        cafe.has_wifi = edit_form.wifi.data
        cafe.has_sockets = edit_form.sockets.data
        cafe.coffee_price = edit_form.coffee_price.data

        db.session.commit()
        return redirect(url_for("show_cafe", cafe_id=cafe.id))

    return render_template("add-cafe.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:cafe_id>")
@admin_only
def delete_cafe(cafe_id):
    post_to_delete = Cafe.query.get(cafe_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('query_for_cafes'))


if __name__ == "__main__":
    app.run(debug=True)
