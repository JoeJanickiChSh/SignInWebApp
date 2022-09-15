from datetime import datetime, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from flask import current_app, redirect, request, url_for
from flask_login import current_user
from flask_login.config import EXEMPT_METHODS
from wtforms import SelectMultipleField, widgets


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


def permission_required(perm):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if request.method in EXEMPT_METHODS or \
                    current_app.config.get('LOGIN_DISABLED'):
                pass
            elif not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            elif not perm(current_user):
                return redirect(url_for("auth.forbidden"))
            try:
                # current_app.ensure_sync available in Flask >= 2.0
                return current_app.ensure_sync(func)(*args, **kwargs)
            except AttributeError:
                return func(*args, **kwargs)
        return decorated_view
    return wrapper


admin_required = permission_required(lambda u: u.role.admin)
mentor_required = permission_required(lambda u: u.role.mentor)


def correct_time_for_storage(time: datetime):
    # Check if datetime has a tz already:
    if time.tzinfo is None:
        # If not, set TZ to ET
        time.replace(tzinfo=ZoneInfo(current_app.config['time_zone']))
    return time.astimezone(timezone.utc)


def correct_time_from_storage(time: datetime):
    # Check if datetime has a tz already:
    if time.tzinfo is None:
        # If not, set TZ to ET
        time = time.replace(tzinfo=timezone.utc)
    return time.astimezone(ZoneInfo(current_app.config['time_zone']))
