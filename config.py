import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'yMrq2wIhxCZw7o32enHeIj721fs7FJHmRyGhjPn1WZk'
