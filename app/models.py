# -*- coding: UTF-8 -*-
from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request, flash
from flask.ext.login import UserMixin, AnonymousUserMixin
from . import db, login_manager


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

db.event.listen(Comment.body, 'set', Comment.on_changed_body)



class Praise(db.Model):
    __tablename__ = 'praises'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    points = db.relationship('Point', backref='author', lazy='dynamic')
    praises = db.relationship('Praise',
                              foreign_keys=[Praise.user_id],
                              backref='praised', lazy='dynamic')
    praise_count = db.Column(db.Integer,default=0)

    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    '''
    初始化，赋予环境变量指定的管理员权限
    '''
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()
        #self.followed.append(Follow(followed=self))
    @staticmethod
    def Del(self):
        user = User.query.filter_by(email=self).first()
        db.session.delete(user)
        db.session.commit()
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    #只写属性，避免生成的散列值被读取（单向）
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    #接受一个密码并与和存储在 User 模型中的密码散列值进行比对
    #return true 密码正确
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    #根据一个字符串生成一个令牌字符串，默认时间1h
    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})
    #检验令牌，正确设置confirm字段为true
    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        #加对比current_user 中的已登录来用户来匹配，防止恶意用户知道如何生成签名令牌
        #这样无法确认别人的账户
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})
    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True
    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})
    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True
    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions
    def is_administrator(self):
        return self.can(Permission.ADMINISTER)
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

class TagPointmap(db.Model):
    __tablename__ = 'tagpoint'
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'),
                            primary_key=True)
    point_id = db.Column(db.Integer, db.ForeignKey('points.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)






class Point(db.Model):
    __tablename__ = 'points'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(128))
    explain = db.Column(db.String(128))
    tags = db.Column(db.String(64))
    Anonymous = db.Column(db.Boolean, default=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    tag_id = db.relationship('TagPointmap',
                               foreign_keys=[TagPointmap.point_id],
                               backref=db.backref('point', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')


    post_id = db.relationship('Post', backref='point', lazy='dynamic')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    '''
    fun:返回指定tag问题的Point对象
    '''
    @staticmethod
    def get_points(self):
        return db.session.query(Point).select_from(TagPointmap).\
                filter_by(tag_id = self.id).\
                join(Point,TagPointmap.tag_id == Point.id)

    @staticmethod
    def check(body):
        point = Point.query.filter_by(body=body).first()
        if point:
            flash(u'已经有一样的问题啦！')
            return -1
        else:
            return 0


    @staticmethod
    def Del(id):
        point = Point.query.filter_by(author_id = id).all
        db.session.delete(point)
        db.session.commit()


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    count = db.Column(db.Integer,default=0)
    point_id = db.relationship('TagPointmap',
                               foreign_keys=[TagPointmap.tag_id],
                               backref=db.backref('tag', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    '''
    fun:
    '''
    @staticmethod
    def TagList(taglists,point):
        #from sqlalchemy.exc import IntegrityError
        #利用循环创建多个tag标签并加到单个point问题，形成中间表TagPointmap
        #这样就可以利用中间表联结查找一个问题下的多个tag/标签，反之也可查找一个tag标签下的若干个point/问题
        for taglist in taglists.split(';'):
            if taglist :
                tag = Tag.query.filter_by(name=taglist).first()
                if not tag:
                    tag = Tag(name = taglist,
                              count = 1,
                              #timestamp=datetime.utcnow()
                              )

                else:
                    tag.count = tag.count+1


                #参数左边(tag)代表Tag对象，point同理，创建TagPointmap对象
                tp = TagPointmap(tag = tag,
                                 point = point,
                                 #timestamp=datetime.utcnow()
                                 ) #创建多对多关系的中间表TagPointmap
                #加入数据库
                db.session.add(tag)
                db.session.add(tp)
                '''
                try:
                    db.session.commit()
                except :
                    db.session.rollback()
                    raise
                finally:
                    db.session.close()  # optional, depends on use case
                '''

        '''
    fun:返回指定point问题的Tag对象
    db.session.query(Tag)                   指定查询返回Tag对象;
    select_from(TagPointmap)                这个查询从 TagPointmap 模型开始;
    filter_by(point_id = self.id)           使用问题过滤 TagPointmap 表;
    join(Tag,TagPointmap.tag_id == Tag.id)  联结 filter_by() 得到的结果和
                                            Tag对象;联结更加高效
    '''
    @staticmethod
    def get_tags(point):
        return db.session.query(Tag).select_from(TagPointmap).\
                filter_by(point = point).\
                join(Tag,TagPointmap.tag_id == Tag.id)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    post_notice = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    Anonymous = db.Column(db.Boolean, default=True)
    reprint = db.Column(db.Boolean, default=False)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    point_id = db.Column(db.Integer, db.ForeignKey('points.id'))

    praised = db.relationship('Praise',
                              foreign_keys=[Praise.post_id],
                              backref='praises', lazy='dynamic')

    comments = db.relationship('Comment', backref='post', lazy='dynamic')


login_manager.anonymous_user = AnonymousUser
