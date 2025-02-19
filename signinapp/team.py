from flask import Blueprint, request
from flask.templating import render_template
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.future import select

from .model import Role, Subteam, User, db
from .util import mentor_required

team = Blueprint("team", __name__)


@team.route("/users")
@mentor_required
def users():
    users = User.get_visible_users()
    roles = db.session.scalars(select(Role))
    return render_template("users.html.jinja2", users=users, roles=roles)


@team.route("/subteam")
@login_required
def subteam():
    st_id = request.args.get("st_id")
    subteam = db.session.get(Subteam, st_id)
    return render_template("subteam.html.jinja2", subteam=subteam)


@team.route("/users/students")
@mentor_required
def list_students():
    users = db.session.scalars(select(User).where(User.role.has(name="student")))
    return render_template(f"user_list.html.jinja2", role="Student", users=users)


@team.route("/users/guardians")
@mentor_required
def list_guardians():
    users = db.session.scalars(select(User).where(User.role.has(guardian=True)))
    return render_template(f"user_list.html.jinja2", role="Guardian", users=users)


@team.route("/users/mentors")
@mentor_required
def list_mentors():
    users = db.session.scalars(select(User).where(User.role.has(name="mentor")))
    return render_template(f"user_list.html.jinja2", role="Mentor", users=users)
