from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField, BooleanField
# pip install email_validator in terminal
# using "heroku run python 執行的檔案 runserver" find error
from wtforms.validators import DataRequired, URL, Email, Length
from flask_ckeditor import CKEditorField

##WTForm

class FindCafeForm(FlaskForm):
    district = SelectField("District Search",
                           choices=["北投區", "士林區", "大同區", "中山區",
                                    "松山區", "內湖區", "萬華區", "中正區",
                                    "大安區", "信義區", "南港區", "文山區"],
                           validators=[DataRequired()])
    submit = SubmitField("Search!")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("SIGN UP!")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("LOG IN!")

class AddCafeForm(FlaskForm):
    name = StringField("Shop Name", validators=[DataRequired()])
    location = StringField("Shop Address", validators=[DataRequired()])
    district = StringField("District", validators=[DataRequired()])
    open_time_Mon = StringField("Open time on Monday", validators=[DataRequired()])
    open_time_Tue = StringField("Open time on Tuesday", validators=[DataRequired()])
    open_time_Wed = StringField("Open time on Wednesday", validators=[DataRequired()])
    open_time_Thu = StringField("Open time on Thursday", validators=[DataRequired()])
    open_time_Fri = StringField("Open time on Friday", validators=[DataRequired()])
    open_time_Sat = StringField("Open time on Saturday", validators=[DataRequired()])
    open_time_Sun = StringField("Open time on Sunday", validators=[DataRequired()])
    map_url = StringField("Map URL", validators=[DataRequired(), URL()])
    coffee_price = StringField("Coffee Price", validators=[DataRequired()])
    wifi = BooleanField("Wifi", default=False)
    sockets = BooleanField("Sockets 🔌", default=False)
    submit = SubmitField("Commit")

class EditCafeForm(FlaskForm):
    name = StringField("Shop Name", validators=[DataRequired()])
    location = StringField("Shop Address", validators=[DataRequired()])
    district = StringField("District", validators=[DataRequired()])
    open_time = StringField("Open time", validators=[DataRequired()])
    map_url = StringField("Map URL", validators=[DataRequired(), URL()])
    coffee_price = StringField("Coffee Price", validators=[DataRequired()])
    wifi = BooleanField("Wifi", default=False)
    sockets = BooleanField("Sockets 🔌", default=False)
    submit = SubmitField("Commit")

class CommentForm(FlaskForm):
    comment_text = CKEditorField("Write Comment", validators=[DataRequired()])
    submit = SubmitField("SUBMIT COMMENT")

