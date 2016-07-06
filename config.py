# -*- coding: UTF-8 -*-
import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
    FLASKY_MAIL_SENDER = 'FLASKY_ADMIN'
    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')


    MAIL_USERNAME = '852996883@qq.com'
    MAIL_PASSWORD = '××××××'
    FLASKY_ADMIN = '852996883@qq.com'


    @staticmethod
    def init_app(app):
        pass




class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@127.0.0.1/cozh'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL')


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
