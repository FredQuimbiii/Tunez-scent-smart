from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
import os
import smtplib
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
Bootstrap5(app)

my_email = "rajiabdulkadir2020@gmail.com"
password = os.environ.get('EMAIL_PAS')

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/web-scraping')
def web_scraping():
    return render_template("scrape.html")

@app.route('/ai-gui')
def ai_gui():
    return render_template("ai-gui.html")

@app.route('/data-science')
def data_science():
    return render_template("data-science.html")

@app.route('/about', methods=["GET", "POST"])
def about():
    if request.method == "POST":
        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(user=my_email, password=password)
            connection.sendmail(from_addr=my_email,
                                to_addrs="rajiabdulkadir15@gmail.com",
                                msg=f'Subject:Contact from Portfolio\n\nHello Raji, {request.form['name']} has sent you the message below\n'
                                    f'{request.form['message']}\nemail: {request.form['email']}\nPhone Number: {request.form['phone']}')
        return render_template("about.html")
    return render_template("about.html")


if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    app.run(debug=True)