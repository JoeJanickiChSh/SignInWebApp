from collections import defaultdict
from datetime import datetime, timedelta

from dateutil.rrule import WEEKLY, rrule
from flask import Blueprint, flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import (BooleanField, DateField, DateTimeLocalField, SelectField,
                     SelectMultipleField, StringField, SubmitField, TimeField)
from wtforms.validators import DataRequired

from .mentor import mentor_required
from .model import Event, EventType, Stamps, db, event_code

events = Blueprint("events", __name__)

DATE_FORMATS = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M']

WEEKDAYS = ["Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday"]


class EventForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    code = StringField(validators=[DataRequired()])
    start = DateTimeLocalField(format=DATE_FORMATS)
    end = DateTimeLocalField(format=DATE_FORMATS)
    type_ = SelectField(label="Type")
    enabled = BooleanField(default=True)
    submit = SubmitField()

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        if self.start.data >= self.end.data:
            self.end.errors.append('End time must not be before start time')
            return False

        return True


class BulkEventForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    start_day = DateField(validators=[DataRequired()])
    end_day = DateField(validators=[DataRequired()])
    days = SelectMultipleField(choices=WEEKDAYS, validators=[DataRequired()])
    start_time = TimeField(validators=[DataRequired()])
    end_time = TimeField(validators=[DataRequired()])
    type_ = SelectField(label="Type")
    submit = SubmitField()

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        if self.start_time.data >= self.end_time.data:
            self.end_time.errors.append(
                'End time must not be before start time')
            rv = False

        if self.start_day.data >= self.end_day.data:
            self.end_day.errors.append('End day must not be before start day')
            rv = False

        return rv


@events.route("/events")
@mentor_required
def list_events():
    events = Event.query.filter_by(enabled=True).all()
    return render_template("events.html.jinja2", events=events)


@events.route("/events/stats")
@mentor_required
def event_stats():
    event = Event.query.get(request.args["event_id"])
    stamps = Stamps.query.filter_by(event_id=event.id).all()
    users = defaultdict(timedelta)
    for stamp in stamps:
        users[stamp.user.name] += stamp.elapsed
    users = sorted(users.items())
    return render_template("event_stats.html.jinja2",
                           event=event, users=users)


@events.route("/events/bulk", methods=["GET", "POST"])
@mentor_required
def bulk_events():
    form = BulkEventForm()
    form.type_.choices = [(t.id, t.name) for t in EventType.query.all()]

    if form.validate_on_submit():
        start_time = datetime.combine(form.start_day.data,
                                      form.start_time.data)
        end_time = datetime.combine(form.end_day.data, form.end_time.data)
        days = rrule(WEEKLY,
                     byweekday=[WEEKDAYS.index(d) for d in form.days.data]
                     ).between(start_time, end_time, inc=True)
        for d in [d.date() for d in days]:
            ev = Event(
                name=form.name.data,
                description=form.description.data,
                start=datetime.combine(d, form.start_time.data),
                end=datetime.combine(d, form.end_time.data),
                code=event_code(),
                type_=EventType.query.get(form.type_.data)
            )
            db.session.add(ev)
        db.session.commit()

        return redirect(url_for("events.list_events"))
    return render_template("form.html.jinja2", form=form,
                           title="Bulk Event Add - Chop Shop Sign In")


@events.route("/events/new", methods=["GET", "POST"])
@mentor_required
def new_event():
    form = EventForm()
    form.type_.choices = [(t.id, t.name) for t in EventType.query.all()]
    if form.validate_on_submit():
        ev = Event()
        form.populate_obj(ev)
        ev.type_=EventType.query.get(form.type_.data)
        db.session.add(ev)
        db.session.commit()
        return redirect(url_for("events.list_events"))

    form.code.process_data(event_code())
    return render_template("form.html.jinja2", form=form,
                           title="New Event - Chop Shop Sign In")


@events.route("/events/edit", methods=["GET", "POST"])
@mentor_required
def edit_event():
    event = Event.query.get(request.args["event_id"])
    if not event:
        flash("Event does not exist")
        return redirect(url_for("events.list_events"))

    form = EventForm(obj=event)
    form.type_.choices = [(t.id, t.name) for t in EventType.query.all()]
    if form.validate_on_submit():
        form.populate_obj(event)
        event.type_ = EventType.query.get(form.type_.data)
        db.session.commit()
        return redirect(url_for("events.list_events"))

    form.type_.process_data(event.type_id)
    return render_template("form.html.jinja2", form=form,
                           title=f"Edit Event {event.name} - Chop Shop Sign In")
