from flask import Blueprint, render_template
from models import *

views = Blueprint('views', __name__)

@views.route('/')
def index():
    strings = QuestionnaireResponse.query.all()
    return render_template('index.html', strings=strings)

@views.route('/Home')
def get_home():
    return render_template('index.html')

@views.route('/Questionario')
def get_quest():
    return render_template('questionario.html')


@views.route('/get_database')
def get_database():
    return render_template('database.html')

@views.route('/Test')
def test():
    strings = User.query.all()
    return render_template('test.html', strings=strings)


