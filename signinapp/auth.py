from flask import Blueprint, flash, redirect, request, url_for
from flask.templating import render_template
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo

from .forms import UserForm
from .model import Guardian, Role, ShirtSizes, Student, Subteam, User, db, get_form_ids

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table,
    # use it to look up the user
    user = db.session.get(User, int(user_id))
    if user and user.approved:
        return user


auth = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired()])
    new_password_rep = PasswordField(
        "New Password (again)",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match"),
        ],
    )
    submit = SubmitField()


@auth.route("/register", methods=["GET", "POST"])
def register():
    form = UserForm()
    form.subteam.choices = get_form_ids(Subteam, add_null_id=True)
    form.password.flags.is_required = True
    del form.admin_data

    if form.validate_on_submit():
        # if this returns a user, then the user already exists in database
        username = form.username.data
        user = User.from_username(username)

        # if a user is found, we want to redirect back to signup page
        # so the user can try again
        if user:
            flash("User already exists")
            return redirect(url_for("auth.register"))

        # Create a new user with the form data.
        # Hash the password so the plaintext version isn't saved.
        student = Student.make(
            username=username,
            name=form.name.data,
            password=form.password.data,
            graduation_year=form.student_data.graduation_year.data,
            preferred_name=form.preferred_name.data,
            phone_number=form.phone_number.data,
            email=form.email.data,
            address=form.address.data,
            tshirt_size=ShirtSizes[form.tshirt_size.data],
            subteam=db.session.get(Subteam, form.subteam.data),
        )

        student.student_user_data.add_guardian(
            guardian=Guardian.get_from(
                name=form.student_data.first_guardian_name.data,
                phone_number=form.student_data.first_guardian_phone_number.data,
                email=form.student_data.first_guardian_email.data,
                contact_order=1,
            )
        )

        if form.student_data.second_guardian_name.data:
            student.student_user_data.add_guardian(
                Guardian.get_from(
                    name=form.student_data.second_guardian_name.data,
                    phone_number=form.student_data.second_guardian_phone_number.data,
                    email=form.student_data.second_guardian_email.data,
                    contact_order=2,
                )
            )

        db.session.commit()
        return redirect("/login")
    return render_template(
        "auth/register.html.jinja2",
        form=form,
        user_type="Student",
        qr_route="qr.register_qr",
    )


@auth.route("/register/mentor", methods=["GET", "POST"])
def register_mentor():
    form = UserForm()
    form.subteam.choices = get_form_ids(Subteam, add_null_id=True)
    form.password.flags.is_required = True
    del form.student_data
    del form.admin_data

    if form.validate_on_submit():
        # if this returns a user, then the user already exists in database
        username = form.username.data
        user = User.from_username(username)

        # if a user is found, we want to redirect back to signup page
        # so the user can try again
        if user:
            flash("User already exists")
            return redirect(url_for("auth.register"))

        # Create a new user with the form data.
        # Hash the password so the plaintext version isn't saved.
        user = User.make(
            username=username,
            name=form.name.data,
            password=form.password.data,
            role=Role.from_name("mentor"),
            preferred_name=form.preferred_name.data,
            phone_number=form.phone_number.data,
            email=form.email.data,
            address=form.address.data,
            tshirt_size=ShirtSizes[form.tshirt_size.data],
            subteam=db.session.get(Subteam, form.subteam.data),
        )

        db.session.commit()
        return redirect("/login")
    return render_template(
        "auth/register.html.jinja2",
        form=form,
        user_type="Mentor",
        qr_route="qr.register_mentor_qr",
    )


@auth.route("/register/guardian", methods=["GET", "POST"])
def register_guardian():
    form = UserForm()
    form.password.flags.is_required = True
    del form.admin_data
    del form.student_data
    del form.subteam

    if form.validate_on_submit():
        # Cannot use form.populate_data because of the password
        user = Guardian.get_from(
            form.name.data, form.phone_number.data, form.email.data, 0
        ).user
        user.username = form.username.data
        user.name = form.name.data
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.role = Role.from_name("guardian")
        user.preferred_name = form.preferred_name.data
        user.phone_number = form.phone_number.data
        user.email = form.email.data
        user.address = form.address.data
        user.tshirt_size = ShirtSizes[form.tshirt_size.data]
        db.session.commit()
        return redirect(url_for("index"))

    return render_template(
        "auth/register.html.jinja2",
        form=form,
        user_type="Guardian",
        qr_route="qr.register_guardian_qr",
    )


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember.data

        # if this returns a user, then the email already exists in database
        user = User.from_username(username)

        if not user or not check_password_hash(user.password, password):
            flash("Please check your login details and try again.")
            return redirect(url_for("auth.login"))

        if not user.approved:
            flash("User is not approved")
            return redirect(url_for("auth.login"))

        login_user(user, remember=remember)

        return redirect("/")
    return render_template("auth/login.html.jinja2", form=form)


@auth.route("/logout")
def logout():
    logout_user()
    return redirect("/")


@auth.route("/password", methods=["GET", "POST"])
@login_required
def password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(current_user.password, form.current_password.data):
            flash("Incorrect current password")
            return redirect(url_for("auth.password"))

        current_user.password = generate_password_hash(form.new_password.data)
        db.session.commit()
        return redirect(url_for("user.profile"))

    return render_template("auth/password.html.jinja2", form=form)


@auth.route("/forbidden")
def forbidden():
    return render_template("auth/forbidden.html.jinja2")
