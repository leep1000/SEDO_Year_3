from datetime import datetime

from wtforms import Form, IntegerField, PasswordField, SelectField, StringField, validators


class LoginForm(Form):
    username = StringField(
        "Username",
        [
            validators.DataRequired(),
            validators.Length(min=3, max=50),
            validators.Regexp(
                r"^[A-Za-z0-9._-]+$",
                message="Username can only contain letters, numbers, dots, underscores and hyphens.",
            ),
        ],
    )
    password = PasswordField("Password", [validators.DataRequired(), validators.Length(max=128)])


class RegisterForm(Form):
    username = StringField(
        "Username",
        [
            validators.DataRequired(),
            validators.Length(min=3, max=50),
            validators.Regexp(
                r"^[A-Za-z0-9._-]+$",
                message="Username can only contain letters, numbers, dots, underscores and hyphens.",
            ),
        ],
    )
    password = PasswordField(
        "Password",
        [
            validators.DataRequired(),
            validators.Length(min=10, max=128),
            validators.Regexp(
                r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).+$",
                message="Password must include uppercase, lowercase and a number.",
            ),
        ],
    )


class BookForm(Form):
    title = StringField("Title", [validators.DataRequired(), validators.Length(max=200)])
    author = StringField("Author", [validators.DataRequired(), validators.Length(max=100)])
    publication_year = IntegerField(
        "Publication year",
        [
            validators.DataRequired(),
            validators.NumberRange(
                min=1600,
                max=max(2030, datetime.now().year + 1),
                message="Publication year must be realistic.",
            ),
        ],
    )
    isbn = StringField(
        "ISBN",
        [
            validators.DataRequired(),
            validators.Length(min=10, max=20),
            validators.Regexp(r"^[0-9Xx-]+$", message="ISBN can only contain numbers, X and hyphens."),
        ],
    )
    amazon_url = StringField(
        "Amazon UK link",
        [
            validators.Optional(),
            validators.Length(max=500),
            validators.URL(require_tld=True, message="Enter a valid Amazon UK URL."),
            validators.Regexp(
                r"^https://(www\.)?amazon\.co\.uk/",
                message="The link must start with https://www.amazon.co.uk/.",
            ),
        ],
    )
    checked_out_by_id = IntegerField("Checked out by", [validators.Optional()])


class UserEditForm(Form):
    username = StringField(
        "Username",
        [
            validators.DataRequired(),
            validators.Length(min=3, max=50),
            validators.Regexp(
                r"^[A-Za-z0-9._-]+$",
                message="Username can only contain letters, numbers, dots, underscores and hyphens.",
            ),
        ],
    )
    role = SelectField("Role", choices=[("regular", "Regular"), ("admin", "Admin")])
