# -*- coding: UTF-8 -*-
from flask import render_template, redirect, request, url_for, flash
from flask.ext.login import login_user, logout_user, login_required, \
    current_user
from . import auth
from .. import db
from ..models import User,Role
from ..email import send_email
from .forms import LoginForm, RegistrationForm, ChangePasswordForm,\
    PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm

'''
fun:更新已登录用户访问时间
before_app_request处理程序在每次请求前运行
每次请求前运行当前用户登入时间->无登录->返回无登录页面
'''
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping() #每次请求前运行当前用户登入时间
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


'''
fun:登录路由
搜索用户email->判断存在并且密码正确->登入用户->重定向之前页面
'''
@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):#加入密码判断
            login_user(user, form.remember_me.data)  #登录用户
            return redirect(request.args.get('next') or url_for('main.index'))#重定向到之前页面
        flash('Invalid username or password.')
    return render_template('auth/login.html', form=form)

'''
fun:登出路由
@login_required   #Flask-Login的保护路由，拦截未登录用户请求，并把用户发往登录页面
'''
@auth.route('/logout')
@login_required  #Flask-Login的保护路由
def logout():
    logout_user()  #登出用户
    flash('You have been logged out.')
    return redirect(url_for('main.index'))

'''
fun:注册路由
获取表单数据，commit数据库->陈生成令牌字符串->发送账号确认邮件->重定向到登录页面
'''
@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():

        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data,
                    confirmed=True,
                    #role=Role(permissions=0xff)
                    )
        db.session.add(user)
        db.session.commit()

        token = user.generate_confirmation_token() #生成令牌字符串
        send_email(user.email, 'Confirm Your Account',
                   'auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

'''
fun:确认用户，
用户点击带令牌字符串的链接->confirm(token)解析确认
'''
@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

'''
fun:发送带令牌的email
'''
@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))

'''
fun:更换密码
'''
@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash('Your password has been updated.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password.')
    return render_template("auth/change_password.html", form=form)

'''
fun:发送带令牌的email
'''
@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash('An email with instructions to reset your password has been '
              'sent to you.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

'''
fun:确认更改的密码

'''
@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash('Your email address has been updated.')
    else:
        flash('Invalid request.')
    return redirect(url_for('main.index'))

