# -*- coding: UTF-8 -*-
from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField,SelectField
from wtforms.validators import Required, Length, Email, Regexp
from wtforms import ValidationError
from flask.ext.pagedown.fields import PageDownField
from ..models import Role, User,Point


class NameForm(Form):
    name = StringField('What is your name?', validators=[Required()])
    submit = SubmitField('Submit')


class EditProfileForm(Form):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[
        Required(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                          'Usernames must have only letters, '
                                          'numbers, dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')



class PointForm(Form):
    body = StringField(u'写下你的问题 :', validators=[Required()])
    explain = StringField(u'问题说明（可选）:')
    tags = StringField(u'选择话题 :', validators=[Required()])
    Anonymous = BooleanField(u'匿名')
    submit = SubmitField(u'发布')

class AnswerForm(Form):
    body = PageDownField(u'写下你的答案 :', validators=[Required()])
    Anonymous = BooleanField(u'匿名')
    submit = SubmitField(u'发布答案')

class CommentForm(Form):
    body = StringField('Enter your comment', validators=[Required()])
    submit = SubmitField(u'评论')