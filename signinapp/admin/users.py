from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from sqlalchemy.future import select
from werkzeug.security import generate_password_hash
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TelField,
    EmailField,
)
from wtforms.validators import DataRequired, EqualTo

from ..model import Role, Subteam, User, db, ShirtSizes, get_form_ids
from ..util import admin_required
from .util import admin


class UserForm(FlaskForm):
    username = StringField(validators=[DataRequired()])
    name = StringField(validators=[DataRequired()])
    preferred_name = StringField("Preferred Name")
    password = PasswordField()
    role = SelectField()
    subteam = SelectField()

    phone_number = TelField("Phone Number")
    email = EmailField("Email Address")
    address = StringField("Street Address")
    tshirt_size = SelectField("T-Shirt Size", choices=ShirtSizes.get_size_names())

    approved = BooleanField()
    active = BooleanField()
    submit = SubmitField()


class DeleteUserForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    verify = StringField(
        "Confirm Name",
        validators=[DataRequired(), EqualTo("name", message="Enter the user's name")],
    )
    submit = SubmitField()


@admin.route("/admin/users/approve", methods=["POST"])
@admin_required
def user_approve():
    user_id = request.args.get("user_id", None)
    user = db.session.get(User, user_id)
    if user:
        user.approved = True
        db.session.commit()
    else:
        flash("Invalid user ID")
    return redirect(url_for("team.users"))


@admin.route("/admin/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    form = UserForm()
    form.role.choices = get_form_ids(Role)
    form.subteam.choices = get_form_ids(Subteam, add_null_id=True)

    if form.validate_on_submit():
        if User.get_canonical(form.name.data) is not None:
            flash("User already exists")
            return redirect(url_for("admin.new_user"))

        user = User.make(
            username=form.username.data,
            name=form.name.data,
            password=form.password.data,
            approved=form.approved.data,
            role=db.session.get(Role, form.role.data),
            preferred_name=form.preferred_name.data,
            phone_number=form.phone_number.data,
            email=form.email.data,
            address=form.address.data,
            tshirt_size=ShirtSizes[form.tshirt_size.data],
        )
        if form.subteam.data:
            user.subteam = db.session.get(Subteam, form.subteam.data)

        user.active = form.active.data
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("team.users"))

    form.role.process_data(Role.get_default().id)

    return render_template(
        "form.html.jinja2", form=form, title=f"New User - Chop Shop Sign In"
    )


@admin.route("/admin/users/edit", methods=["GET", "POST"])
@admin_required
def edit_user():
    user: User = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.users"))

    form = UserForm(obj=user)
    form.role.choices = get_form_ids(Role)
    form.subteam.choices = get_form_ids(Subteam, add_null_id=True)

    if form.validate_on_submit():
        # Cannot use form.populate_data because of the password
        user.username = form.username.data
        user.name = form.name.data
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.role_id = form.role.data
        user.subteam_id = form.subteam.data or None
        user.approved = form.approved.data
        user.active = form.active.data
        user.preferred_name = form.preferred_name.data
        user.phone_number = form.phone_number.data
        user.email = form.email.data
        user.address = form.address.data
        user.tshirt_size = ShirtSizes[form.tshirt_size.data]
        db.session.commit()
        return redirect(url_for("team.users"))

    form.role.process_data(user.role_id)
    form.subteam.process_data(user.subteam_id)
    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Edit User {user.name} - Chop Shop Sign In",
    )


@admin.route("/admin/users/delete", methods=["GET", "POST"])
@admin_required
def delete_user():
    form = DeleteUserForm()
    user = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.users"))

    if form.validate_on_submit():
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("team.users"))

    form.name.process_data(user.name)
    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Delete User {user.name} - Chop Shop Sign In",
    )
