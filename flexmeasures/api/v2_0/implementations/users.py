from functools import wraps

from flask import current_app, abort, request
from marshmallow import ValidationError, validate, validates, fields
from sqlalchemy.exc import IntegrityError
from webargs.flaskparser import use_args
from flask_security import current_user
from flask_json import as_json
from pytz import all_timezones

from flexmeasures.api import ma
from flexmeasures.data.models.user import User as UserModel
from flexmeasures.data.services.users import (
    get_users,
)
from flexmeasures.data.auth_setup import unauthorized_handler
from flexmeasures.api.common.responses import required_info_missing
from flexmeasures.data.config import db

"""
Plan:
1. GET /users using webargs
2. Try using FLask-Smorest
3. Get /users/{id}
4. Other endpoints
5. Make UI use this API
"""


class UserSchema(ma.SQLAlchemySchema):
    class Meta:
        model = UserModel

    @validates("timezone")
    def validate_timezone(self, timezone):
        if timezone not in all_timezones:
            raise ValidationError(f"Timezone {timezone} doesn't exist.")

    id = ma.auto_field()
    email = ma.auto_field(required=True, validate=validate.Email)
    username = ma.auto_field(required=True)
    active = ma.auto_field()
    timezone = ma.auto_field()
    flexmeasures_roles = ma.auto_field()


user_schema = UserSchema()
users_schema = UserSchema(many=True)


@use_args({"include_inactive": fields.Bool(missing=False)}, location="query")
@as_json
def get(args):
    """List all users."""
    users = get_users(only_active=not args["include_inactive"])
    return users_schema.dump(users), 200


def check_user(admins_only: bool = False):
    """Decorator which loads a user.
    Raises 400 if that is not possible due to wrong parameters.
    Raises 404 if user is not found.
    Raises 403 if unauthorized:
    Only the user themselves or admins can access a user object.
    The admins_only parameter can be used if not even the user themselves
    should do be allowed.

        @app.route('/user/<id>')
        @check_user
        def get_user(user):
            return user_schema.dump(user), 200

    The message must specify one id within the route.
    """

    def wrapper(fn):
        @wraps(fn)
        @as_json
        def decorated_endpoint(*args, **kwargs):

            args = list(args)
            if len(args) == 0:
                current_app.logger.warning("Request missing id.")
                return required_info_missing(["id"])
            if len(args) > 1:
                print(args)
                return (
                    dict(
                        status="UNEXPECTED_PARAMS",
                        message="Only expected one parameter (id).",
                    ),
                    400,
                )

            try:
                id = int(args[0])
            except ValueError:
                current_app.logger.warning("Cannot parse ID argument from request.")
                return required_info_missing(["id"], "Cannot parse ID arg as int.")

            user: UserModel = UserModel.query.filter_by(id=int(id)).one_or_none()

            if user is None:
                raise abort(404, f"User {id} not found")

            if not current_user.has_role("admin"):
                if admins_only or user != current_user:
                    return unauthorized_handler(None, [])

            args = (user,)
            return fn(*args, **kwargs)

        return decorated_endpoint

    return wrapper


# @use_args({"id": fields.Int(required=True)}, location="path")
@check_user()
@as_json
def fetch_one(user):
    """Fetch a given user"""
    return user_schema.dump(user), 200


@check_user()
@as_json
def patch(user):
    """Update a user given its identifier"""
    ignored_fields = [
        "id",
        "email",
        "username",
    ]  # TODO: allow to change email and username (we allow to change asset name)
    relevant_data = {
        k: v for k, v in request.json.items() if k not in ignored_fields
    }  # TODO: with webargs? Probably better error with wrong types (not on db level).
    user_data = user_schema.load(relevant_data, session=db.session, partial=True)
    for k, v in user_data.items():
        setattr(user, k, v)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError as ie:
        return dict(message="Duplicate user already exists", detail=ie._message()), 400
    return user_schema.dump(user), 200