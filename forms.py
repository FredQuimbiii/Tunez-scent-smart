from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField, RadioField, PasswordField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, URL, Email, Optional, Length, EqualTo
from flask_ckeditor import CKEditorField


# WTForm for creating a blog post
class PerfumeForm(FlaskForm):
    name = StringField("Perfume Name", validators=[DataRequired()])
    brand = StringField("Brand Name", validators=[DataRequired()])
    price = IntegerField("Price", validators=[DataRequired()])
    category = SelectField('Category', validators=[DataRequired()],
                          choices=[('', 'Choose...'),
                                   ('General', 'General'),
                                   ('Male', 'Male'),
                                   ('Female', 'Female'),
                                   ('Kids', 'Kids'),
                                   ('Wedding', 'Wedding'),
                                   ('Corporate', 'Corporate'),
                                   ('Arabian', 'Arabian'),
                                   ('Diffusers', 'Diffusers'),
                                   ],
                           default="General"
                          )
    units = IntegerField("Number of Units", validators=[DataRequired()])
    image = FileField("Perfume Image", validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    image_2 = FileField("Perfume Image", validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    image_3 = FileField("Perfume Image", validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    # description = StringField(label="Description")
    description = CKEditorField("Description", validators=[DataRequired()])
    submit = SubmitField("Save Perfume")

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    name = StringField('Your Name', validators=[DataRequired()])
    submit = SubmitField('SIGN UP')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('LET ME IN!')

# class CommentForm(FlaskForm):
#     body = CKEditorField("Comment", validators=[DataRequired()])
#     submit = SubmitField("Submit Post")

class SearchForm(FlaskForm):
    search = StringField('Search', validators=[DataRequired(), Length(max=200)])

class CheckoutForm(FlaskForm):
    first_name = StringField('First name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last name', validators=[DataRequired(), Length(max=50)])
    contact = StringField('Contact', validators=[Optional(), Length(max=11, min=11)])
    alt_contact = StringField('Alternative Contact', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    address = StringField('Address', validators=[DataRequired(), Length(max=200)])
    address2 = StringField('Address 2', validators=[Optional(), Length(max=200)])
    country = SelectField('Country', validators=[DataRequired()],
                           choices=[('', 'Choose...'),
                                    ('Nigeria', 'Nigeria'),
                                    ('USA', 'USA')
                                    ]
                          )
    state = SelectField('State', validators=[DataRequired()],
                         choices=[('', 'Choose...'),
                                  ('FCT', 'FCT - Abuja'),
                                  ('Nasarawa', 'Nasarawa')
                                  ]
                        )
    zip_code = StringField('Zip', validators=[Optional(), Length(max=10)])
    payment_method = RadioField(
        'Payment',
        choices=[('Bank transfer', 'Bank Transfer'), ('Pay on delivery', 'Pay on Delivery')],
        default='Bank transfer',
        validators=[DataRequired()]
    )

# TODO: Create a RegisterForm to register new users
def register():
    form = RegisterForm()
    return form



# TODO: Create a LoginForm to login existing users
def login():
    form = LoginForm()
    return form


# TODO: Create a CommentForm so users can leave comments below posts
# def comment():
#     form = CommentForm()
#     return form
