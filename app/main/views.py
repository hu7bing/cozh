# -*- coding: UTF-8 -*-
from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask.ext.login import login_required, current_user
from . import main
from .forms import EditProfileForm, EditProfileAdminForm,PointForm,AnswerForm
from .. import db
from ..models import Permission, Role, User,Point,Tag,TagPointmap,Post



@main.route('/', methods=['GET', 'POST'])
def index():

    return render_template('index.html')
'''
fun:用户资料页面路由
搜索指定用户->渲染用户页面
'''
@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user,)

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required

def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


'''
新问题对象的 author 属性值为表达式 current_user._get_current_object()。
变量current_user 由 Flask-Login 提供,和所有上下文变量一样,也是通过线程内的代理对象实
现。这个对象的表现类似用户对象,但实际上却是一个轻度包装,包含真正的用户对象。
数据库需要真正的用户对象,因此要调用 _get_current_object() 方法。
'''

@main.route('/edit_point',methods=['GET', 'POST'])
@login_required

def edit_point():
    from sqlalchemy.exc import IntegrityError
    #point = Point(author = current_user)
    form = PointForm()
    if form.validate_on_submit():
        if Point.check(form.body.data) == -1 :
            return render_template('edit_point.html', form=form)
        point = Point(body = form.body.data,
                      explain = form.explain.data,
                      tags = form.tags.data,
                      Anonymous = form.Anonymous.data,
                      author = current_user._get_current_object()
                      )

        Tag.TagList(point.tags,point)#创建多个tag标签并加到单个point问题，并形成tag和TagPointmap
                            #两个实例到数据库
        db.session.add(point)
        try:
            db.session.commit()
        except :
            db.session.rollback()
            raise
        finally:
            db.session.close()  # optional, depends on use case
        #db.session.commit()
        flash('The point has been updated.')
        #tags = Tag.get_tags(point)
        #return render_template('point.html', point = point,tags = tags,)
        point = db.session.merge(point)
        return redirect(url_for('.point',id = point.id))
    return render_template('edit_point.html', form=form)

@main.route('/point/<int:id>',methods=['GET', 'POST'])
@login_required

def point(id):
    form = AnswerForm()
    point = Point.query.get_or_404(id)
    tags = Tag.get_tags(point)
    tags = tags
    posts = Post.query.filter_by(point = point).all()
    show_AnswerForm = 1
    for post in posts:
        if post.author == current_user:
            show_AnswerForm = 0

    if current_user.can(Permission.WRITE_ARTICLES) and \
        form.validate_on_submit():
        if show_AnswerForm:
            post = Post(body=form.body.data,
                        Anonymous=form.Anonymous.data,
                        point=Point.query.get_or_404(id),
                        author=current_user._get_current_object(),
                        )
            db.session.add(post)
            return redirect(url_for('.point',id = id))
        else:
            flash(u'你已经回答了该问题.')
            return redirect(url_for('.point',id = id))

    return render_template('point.html', point = point,tags = tags,posts=posts,form=form,
                           show_AnswerForm=show_AnswerForm,
                           )


@main.route('/post_edit/<int:id>',methods=['GET', 'POST'])
@login_required

def post_edit(id):
    point = Point.query.get_or_404(id)
    #point = Point.query.get_or_404(id)
    tags = Tag.get_tags(point)
    tags = tags
    posts = Post.query.filter_by(point = point).all()

    post = Post.query.filter_by(point = point).\
    filter_by(author = current_user).first()

    form = AnswerForm()

    if current_user.can(Permission.WRITE_ARTICLES) and \
        form.validate_on_submit():
        post.body = form.body.data
        post.Anonymous = form.Anonymous.data
        db.session.add(post)#更新回答
        flash('The Answer has been updated.')
        return redirect(url_for('.point',id = id))
    form.body.data = post.body
    form.Anonymous.data = post.Anonymous
    return render_template('post_edit.html',point = point,tags = tags,posts=posts,form=form,)


@main.route('/del_point/<int:id>',methods=['GET', 'POST'])
@login_required

def del_point(id):
    point = Point.query.get_or_404(id)
    tags = Tag.get_tags(point)
    for tag in tags :
        tag.count = tag.count - 1
        if not tag.count :
            db.session.delete(tag)
        else:
            db.session.add(tag)
        db.session.commit()
    db.session.delete(point)
    db.session.commit()
    return redirect(url_for('.index'))