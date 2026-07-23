from flask import Flask, abort, render_template, redirect, url_for, flash, request, session
from flask_bootstrap import Bootstrap5
import os
import smtplib
import pandas as pd
from sqlalchemy import func
from flask_ckeditor import CKEditor
from sqlalchemy.exc import NoResultFound, IntegrityError
from datetime import datetime, timedelta, timezone
import hashlib
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps

from unicodedata import category
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from flask_migrate import Migrate
import random
import forms
from forms import PerfumeForm, CheckoutForm, SearchForm
from send_mail import place_order, send_order_confirmation, send_otp
from quote import PERFUME_QUOTES
import cloudinary
import cloudinary.uploader
import os

app = Flask(__name__)
@app.context_processor
def inject_cart_count():
    return dict(cart_count=len(basket))

app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI', 'sqlite:///perfume.db')
# if uri and uri.startswith("postgres://"):
#     uri = uri.replace("postgres://", "postgresql://", 1)
# app.config['SQLALCHEMY_DATABASE_URI'] = uri

db = SQLAlchemy(model_class=Base)
db.init_app(app)
migrate = Migrate(app, db)

UPLOAD_FOLDER = "static/assets/img/uploads"


class Perfume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    brand = db.Column(db.String(250), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    units = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    image_url_2 = db.Column(db.String(300), nullable=True)
    image_url_3 = db.Column(db.String(300), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    order_count = db.Column(db.Integer, nullable=True)
    category = db.Column(db.String(100), nullable=True)


# TODO: Create a User table for all your registered users.
class PerfumeUsers(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    otp_code = db.Column(db.String(6), nullable=True)
    otp_created_at = db.Column(db.DateTime, nullable=True)
    verified = db.Column(db.Boolean, nullable=True, default=False)


# TODO: Create a User table for all Orders.
class PerfumeOrders(UserMixin, db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    unit = db.Column(db.Integer, nullable=False)
    price = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(250), nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.String(250), nullable=True)
    order_date = db.Column(db.DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))

class PerfumeReviews(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    user_email = db.Column(db.String(250), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

with app.app_context():
    db.create_all()

s_login = False
user_pane = False

basket = []
orders = []


def num_runs(num=0):
    count = 0
    count += num
    return count


def upload_perfume_image(file):
    """Uploads a single image to Cloudinary, resized to fit 800x800. Returns the URL or None."""
    if not file:
        return None
    result = cloudinary.uploader.upload(
        file,
        width=800,
        height=800,
        crop="limit"  # resizes to fit within 800x800, keeps aspect ratio, like your thumbnail() did
    )
    return result["secure_url"]


def admin_only(func):
    @wraps(func)
    def check(*args, **kwargs):
        if current_user.is_anonymous or current_user.id != 1:
            abort(403)
        else:
            return func(*args, **kwargs)

    return check

@app.route('/', methods=["GET", "POST"])
def home():
    searched = False
    not_found = False
    page = request.args.get('page', 1, type=int)
    per_page = 14
    categories = request.args.get('category')
    search_form = SearchForm()

    if current_user.is_authenticated:
        u_name = current_user.name
        u_id = current_user.id
        u_mail = current_user.email

        query = db.select(Perfume)

        if request.method == "POST" and search_form.search.data:
            searched = True
            query = query.filter(Perfume.name.ilike(f"%{search_form.search.data}%"))

        if categories:
            searched = True
            query = query.filter(Perfume.category == categories)

        pagination = db.paginate(
            query,
            page=page,
            per_page=per_page,
            error_out=False
        )
        perfumes = pagination.items
        num_pef = len(perfumes)

        if num_pef == 0 and searched:
            not_found = True

        pef_ratings = {}
        for data in perfumes:
            pef_reviews = db.session.execute(
                db.select(PerfumeReviews).filter_by(product_id=data.id)
            ).scalars().all()
            if pef_reviews:
                avg = sum(r.rating for r in pef_reviews) / len(pef_reviews)
                count = len(pef_reviews)
            else:
                avg = 0
                count = 0
            pef_ratings[data.id] = {"avg": avg, "count": count}

        pef_img = []
        for data in perfumes:
            pef_img.append(data.image_url)
        random.shuffle(pef_img)

        result_2 = db.session.execute(db.select(Perfume).order_by(Perfume.order_count.desc()))
        best_pefs = result_2.scalars().all()
        recent_pef = []
        recent_od = []
        result_3 = db.session.execute(db.select(PerfumeOrders).order_by(PerfumeOrders.id.desc()))
        hot_pefs = result_3.scalars().all()
        for pef in hot_pefs:
            if pef.product_id not in recent_pef:
                recent_od.append(pef)
                recent_pef.append(pef.product_id)
        quote = random.choice(PERFUME_QUOTES)
        return render_template("index.html", pef=perfumes,
                               count=num_runs(), num_pef=num_pef, pef_img=pef_img,
                               top_pef=best_pefs, quote=quote, logged_in=True, u_id=u_id, u_mail=u_mail,
                               pagination=pagination, hot_pef=recent_od, search_form=search_form, is_home=True,
                               not_found=not_found, pef_ratings=pef_ratings)


    else:

        query = db.select(Perfume)

        if request.method == "POST" and search_form.search.data:
            searched = True
            query = query.filter(Perfume.name.ilike(f"%{search_form.search.data}%"))

        if categories:
            searched = True
            query = query.filter(Perfume.category == categories)

        pagination = db.paginate(

            query,

            page=page,

            per_page=per_page,

            error_out=False

        )

        perfumes = pagination.items

        num_pef = len(perfumes)

        if num_pef == 0 and searched:
            not_found = True

        pef_ratings = {}
        for data in perfumes:
            pef_reviews = db.session.execute(
                db.select(PerfumeReviews).filter_by(product_id=data.id)
            ).scalars().all()
            if pef_reviews:
                avg = sum(r.rating for r in pef_reviews) / len(pef_reviews)
                count = len(pef_reviews)
            else:
                avg = 0
                count = 0
            pef_ratings[data.id] = {"avg": avg, "count": count}

        pef_img = []
        for data in perfumes:
            pef_img.append(data.image_url)
        random.shuffle(pef_img)

        result_2 = db.session.execute(db.select(Perfume).order_by(Perfume.order_count.desc()))
        best_pefs = result_2.scalars().all()
        recent_pef = []
        recent_od = []
        result_3 = db.session.execute(db.select(PerfumeOrders).order_by(PerfumeOrders.id.desc()))
        hot_pefs = result_3.scalars().all()
        for pef in hot_pefs:
            if pef.product_id not in recent_pef:
                recent_od.append(pef)
                recent_pef.append(pef.product_id)

        quote = random.choice(PERFUME_QUOTES)
        return render_template("index.html", pef=perfumes,
                               count=num_runs(), num_pef=num_pef, pef_img=pef_img,
                               top_pef=best_pefs, quote=quote, logged_out=True, not_user=True,
                               pagination=pagination, hot_pef=recent_od, search_form=search_form,
                               is_home=True, not_found=not_found, pef_ratings=pef_ratings)

@app.route('/products/<pef_id>')
def show_perfume(pef_id):
    pef_to_show = db.get_or_404(Perfume, pef_id)

    reviews = db.session.execute(
        db.select(PerfumeReviews).filter_by(product_id=pef_id)
    ).scalars().all()

    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        review_count = len(reviews)
    else:
        avg_rating = 0
        review_count = 0

    for r in reviews:
        reviewer = db.session.execute(
            db.select(PerfumeUsers).filter_by(email=r.user_email)
        ).scalar_one_or_none()
        r.reviewer_name = reviewer.name if reviewer else "Anonymous"

    user_review = None
    if current_user.is_authenticated:
        user_review = db.session.execute(
            db.select(PerfumeReviews).filter_by(product_id=pef_id, user_email=current_user.email)
        ).scalar_one_or_none()

    if current_user.is_authenticated:
        u_name = current_user.name
        u_mail = current_user.email
        u_id = current_user.id
        result_2 = db.session.execute(db.select(Perfume).order_by(Perfume.order_count.desc()))
        best_pefs = result_2.scalars().all()
        result_3 = db.session.execute(db.select(PerfumeOrders).order_by(PerfumeOrders.id.desc()))
        hot_pefs = result_3.scalars().all()
        return render_template("show-perfume.html", top_pef=best_pefs,
                               pef=pef_to_show, logged_in=True, u_id=u_id, u_mail=u_mail, hot_pef=hot_pefs,
                               avg_rating=avg_rating, review_count=review_count, user_review=user_review, reviews=reviews)
    else:
        result_2 = db.session.execute(db.select(Perfume).order_by(Perfume.order_count.desc()))
        best_pefs = result_2.scalars().all()
        result_3 = db.session.execute(db.select(PerfumeOrders).order_by(PerfumeOrders.id.desc()))
        hot_pefs = result_3.scalars().all()
        return render_template("show-perfume.html", top_pef=best_pefs,
                               pef=pef_to_show, logged_out=True, not_user=True, hot_pef=hot_pefs,
                               avg_rating=avg_rating, review_count=review_count, user_review=user_review, reviews=reviews)

@app.route('/rate/<int:pef_id>', methods=["POST"])
def submit_review(pef_id):
    if not current_user.is_authenticated:
        flash("Please log in to leave a rating.")
        return redirect(url_for('login'))

    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or rating < 1 or rating > 5:
        flash("Please select a rating between 1 and 5.")
        return redirect(url_for('show_perfume', pef_id=pef_id))

    existing_review = db.session.execute(
        db.select(PerfumeReviews).filter_by(product_id=pef_id, user_email=current_user.email)
    ).scalar_one_or_none()

    if existing_review:
        existing_review.rating = rating
        existing_review.comment = comment or None
        existing_review.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        flash("Your rating has been updated.")
    else:
        new_review = PerfumeReviews(
            product_id=pef_id,
            user_email=current_user.email,
            rating=rating,
            comment=comment or None
        )
        db.session.add(new_review)
        db.session.commit()
        flash("Thanks for your rating!")

    return redirect(url_for('show_perfume', pef_id=pef_id))


@app.route('/add-perfume', methods=['GET', 'POST'])
@admin_only
def add_perfume():
    form = PerfumeForm()
    u_name = current_user.name
    u_id = current_user.id
    if form.validate_on_submit():
        web_path = upload_perfume_image(form.image.data)
        web_path_2 = upload_perfume_image(form.image_2.data)
        web_path_3 = upload_perfume_image(form.image_3.data)

        new_perfume = Perfume(
            name=form.name.data,
            brand=form.brand.data,
            price=form.price.data,
            units=form.units.data,
            image_url=web_path,
            image_url_2=web_path_2,
            image_url_3=web_path_3,
            description=form.description.data,
            order_count=0,
            category=form.category.data
        )

        db.session.add(new_perfume)
        db.session.commit()
        return redirect(url_for('add_perfume'))
    return render_template('add-perfume.html', form=form,
                           u_id=u_id, logged_in=True, u_mail=current_user.email)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    global basket, orders
    form = CheckoutForm()
    total = 0
    if current_user.is_authenticated:
        u_name = current_user.name
        u_id = current_user.id
        u_mail = current_user.email
        product = ""
        for pef in basket:
            total += pef["price"]
            product += f"{pef["name"]}: {pef['unit']} Unit @ ₦{pef["price"]:,.2f}\n"
        if form.validate_on_submit():
            # process order using form.first_name.data, form.contact.data, etc.
            message = (
                f"New order placed!\n\n"
                f"--- Customer ---\n"
                f"Name: {form.first_name.data} {form.last_name.data}\n"
                f"Account Email: {current_user.email}\n"
                f"Checkout Email: {form.email.data}\n"
                f"Phone: {form.contact.data}\n"
                f"Alt Phone: {form.alt_contact.data or 'N/A'}\n\n"
                f"--- Delivery Address ---\n"
                f"{form.address.data}\n"
                f"{form.address2.data + chr(10) if form.address2.data else ''}"
                f"{form.state.data}, {form.country.data} {form.zip_code.data}\n\n"
                f"--- Order ---\n"
                f"{product}"
                f"Payment mode: {form.payment_method.data}\n"
                f"Total Price: ₦{total:,.2f}\n"
            )

            place_order(message)

            customer_message = (
                f"Thank you for your order! Here's a summary:\n\n"
                f"--- Your Order ---\n"
                f"{product}"
                f"Total Price: ₦{total:,.2f}\n"
                f"Payment mode: {form.payment_method.data}\n\n"
                f"--- Delivery Address ---\n"
                f"{form.address.data}\n"
                f"{form.address2.data + chr(10) if form.address2.data else ''}"
                f"{form.state.data}, {form.country.data} {form.zip_code.data}\n\n"
            )

            if form.payment_method.data == "Bank transfer":
                customer_message += (
                    f"Please complete payment of ₦{total:,.2f} to the account below, "
                    f"then reply to this email with a screenshot of your receipt:\n\n"
                    f"Account Name: Tunez scent mart\n"
                    f"Bank: Monie point\n"
                    f"Account Number: 6917376549\n\n"
                )
            else:
                customer_message += "Please have the total amount ready for payment on delivery.\n\n"

            customer_message += "We'll notify you once your order status updates. Thank you for shopping with us!"

            send_order_confirmation(customer_message, form.first_name.data, current_user.email)
            for pef in basket:
                pef_to_add = db.get_or_404(Perfume, pef['id'])
                pef_to_add.order_count = pef_to_add.order_count + pef['unit']
                pef_to_add.units = pef_to_add.units - pef['unit']
                new_order = PerfumeOrders(
                    email=current_user.email,
                    name=pef["name"],
                    unit=pef['unit'],
                    price=pef["price"],
                    status="Pending",
                    image_url=pef_to_add.image_url,
                    product_id=pef['id'],
                    unit_price=pef["unit_price"]

                )

                db.session.add(new_order)
                db.session.commit()
            basket = []
            orders = []

            return redirect(url_for('home'))
        num_cart = len(basket)
        return render_template('checkout.html', form=form,
                               logged_in=True, u_id=u_id, cart=basket, num_cart=num_cart,
                               total=total, u_mail=u_mail)
    else:
        form = CheckoutForm()
        num_cart = len(basket)
        return render_template('checkout.html', form=form, logged_in=False,
                               cart=basket, num_cart=num_cart, total=total, not_user=True, logged_out=True)


@app.route('/update_cart/<pef_id>')
def update_cart(pef_id):
    global basket, orders
    qty = request.args.get('qty', 1, type=int)
    if current_user.is_authenticated:
        pef_to_buy = db.get_or_404(Perfume, pef_id)
        unit = qty
        if len(basket) == 0:
            cart = {
                "id": pef_to_buy.id,
                "name": pef_to_buy.name,
                "price": pef_to_buy.price * unit,
                "unit": unit,
                "unit_price": pef_to_buy.price
            }
            basket.append(cart)
            orders.append(pef_to_buy.id)
        else:
            for pef in basket:
                if pef['id'] == pef_to_buy.id:
                    unit = pef["unit"] + 1
                    pef["id"] = pef_to_buy.id
                    pef["name"] = pef_to_buy.name
                    pef["price"] = pef_to_buy.price * unit
                    pef["unit"] = unit
                    pef["unit_price"] = pef_to_buy.price
                    return redirect(url_for('show_perfume', pef_id=pef_id))
                elif pef_to_buy.id not in orders:
                    cart = {
                        "id": pef_to_buy.id,
                        "name": pef_to_buy.name,
                        "price": pef_to_buy.price * unit,
                        "unit": unit,
                        "unit_price": pef_to_buy.price
                    }
                    basket.append(cart)
                    orders.append(pef_to_buy.id)
                    return redirect(url_for('show_perfume', pef_id=pef_id))
    else:
        flash("You need to login or register to place an order.")
        return redirect(url_for('login'))
    return redirect(url_for('show_perfume', pef_id=pef_id))


@app.route('/delete_item/<pef_id>')
def delete_item(pef_id):
    global basket, orders
    basket = [item for item in basket if item["id"] != int(pef_id)]
    orders = [oid for oid in orders if oid != int(pef_id)]
    return redirect(url_for('checkout'))


@app.route("/orders")
def show_orders():
    global user_pane
    user_pane = False
    date_range = request.args.get('range', 'all')

    if current_user.id == 1:
        query = db.select(PerfumeOrders)
    else:
        u_mail = current_user.email
        query = db.select(PerfumeOrders).filter_by(email=current_user.email)

    if date_range != 'all':
        days_map = {
            '2weeks': 14,
            '1month': 30,
            '2months': 60,
        }
        days = days_map.get(date_range)
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(PerfumeOrders.order_date >= cutoff)

    query = query.order_by(PerfumeOrders.order_date.desc())

    c_orders = db.session.execute(query).scalars().all()

    if current_user.id == 1:
        return render_template("orders.html", c_orders=c_orders,
                               logged_in=True, u_id=current_user.id,
                               u_mail=current_user.email, date_range=date_range)
    else:
        return render_template("orders.html", c_orders=c_orders,
                               logged_in=True, u_id=current_user.id,
                               u_mail=current_user.email, date_range=date_range)


@app.route("/user-orders/<u_email>")
@admin_only
def show_user_orders(u_email):
    date_range = request.args.get('range', 'all')
    query = db.select(PerfumeOrders).filter_by(email=u_email)

    if date_range != 'all':
        days_map = {
            '2weeks': 14,
            '1month': 30,
            '2months': 60,
        }
        days = days_map.get(date_range)
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(PerfumeOrders.order_date >= cutoff)

    query = query.order_by(PerfumeOrders.order_date.desc())

    c_orders = db.session.execute(query).scalars().all()
    return render_template("user-orders.html", c_orders=c_orders,
                           logged_in=True, u_id=current_user.id, u_mail=u_email)


@app.route("/users")
@admin_only
def show_users():
    global user_pane
    user_pane = True
    if not current_user.is_authenticated or current_user.id != 1:
        abort(403)
    all_users = db.session.execute(db.select(PerfumeUsers)).scalars().all()
    return render_template("users.html", all_users=all_users,
                           logged_in=True, u_id=current_user.id, u_mail=current_user.email)


@app.route("/update-order/<order_id>/<new_status>/<u_mail>")
def update_order_status(order_id, new_status, u_mail):
    global user_pane
    order_to_update = db.get_or_404(PerfumeOrders, order_id)
    order_to_update.status = new_status
    print(new_status)
    db.session.commit()
    if user_pane:
        return redirect(url_for('show_user_orders', u_email=u_mail))
    else:
        return redirect(url_for('show_orders'))


@app.route("/delete/<int:pef_id>")
@admin_only
def delete_perfume(pef_id):
    pef_to_delete = db.get_or_404(Perfume, pef_id)
    db.session.delete(pef_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/edit-pef/<int:pef_id>", methods=["GET", "POST"])
@admin_only
def edit_perfume(pef_id):
    u_name = current_user.name
    u_id = current_user.id
    pef = db.get_or_404(Perfume, pef_id)
    edit_form = PerfumeForm(
        name=pef.name,
        brand=pef.brand,
        price=pef.price,
        units=pef.units,
        description=pef.description,
        category=pef.category,
    )
    if edit_form.validate_on_submit():
        # Only upload + replace if a new file was actually submitted, otherwise keep existing
        web_path = upload_perfume_image(edit_form.image.data) if edit_form.image.data else pef.image_url
        web_path_2 = upload_perfume_image(edit_form.image_2.data) if edit_form.image_2.data else pef.image_url_2
        web_path_3 = upload_perfume_image(edit_form.image_3.data) if edit_form.image_3.data else pef.image_url_3

        pef.name = edit_form.name.data
        pef.brand = edit_form.brand.data
        pef.price = edit_form.price.data
        pef.units = edit_form.units.data
        pef.image_url = web_path
        pef.image_url_2 = web_path_2
        pef.image_url_3 = web_path_3
        pef.description = edit_form.description.data
        pef.order_count = pef.order_count
        pef.category = edit_form.category.data
        db.session.commit()
        return redirect(url_for("show_perfume", pef_id=pef.id))
    return render_template("add-perfume.html", form=edit_form, is_edit=True,
                           logged_in=True, u_id=u_id)



@login_manager.user_loader
def load_user(user_id):
    return db.session.get(PerfumeUsers, user_id)


# TODO: Retrieve a user from the database based on their email.
@app.route('/login', methods=["GET", "POST"])
def login():
    form = forms.login()
    global s_login
    if request.method == "POST":
        l_email = request.form["email"]
        try:
            l_user = db.session.execute(db.select(PerfumeUsers).filter_by(email=l_email)).scalar_one()
            if check_password_hash(l_user.password, request.form["password"]):
                if not l_user.verified:
                    otp_code = str(random.randint(100000, 999999))
                    l_user.otp_code = otp_code
                    l_user.otp_created_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    db.session.commit()
                    send_otp(otp_code, l_user.name, l_user.email)
                    session['pending_email'] = l_user.email
                    flash("Please verify your email to continue. A new code has been sent.")
                    return redirect(url_for('verify_otp'))

                login_user(l_user)
                s_login = True
                return redirect(url_for("home"))
            else:
                # error = 'Password incorrect, please try again.'
                flash("Password incorrect, please try again.")
                return redirect(url_for("login"))
        except NoResultFound:
            flash("That email does not exists, please try again.")
            return redirect(url_for("login"))
    return render_template("login.html", form=form, logged_out=True, not_user=True)


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():
    form = forms.register()
    global s_login
    if request.method == "POST":
        if not form.validate_on_submit():
            return render_template("register.html", form=form, logged_out=True, not_user=True)

        harsh_pass = generate_password_hash(request.form["password"],
                                            method='pbkdf2:sha256:600000', salt_length=8)

        existing_user = db.session.execute(
            db.select(PerfumeUsers).filter_by(email=request.form["email"])
        ).scalar_one_or_none()

        if existing_user and existing_user.verified:
            flash("You already signed up with that email, login instead.")
            return redirect(url_for("login"))

        otp_code = str(random.randint(100000, 999999))

        if existing_user and not existing_user.verified:
            # Stale, never-verified registration attempt — overwrite it
            existing_user.name = request.form["name"]
            existing_user.password = harsh_pass
            existing_user.otp_code = otp_code
            existing_user.otp_created_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()
            send_otp(otp_code, existing_user.name, existing_user.email)
        else:
            new_user = PerfumeUsers(
                name=request.form["name"],
                email=request.form["email"],
                password=harsh_pass,
                otp_code=otp_code,
                otp_created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                verified=False
            )
            db.session.add(new_user)
            db.session.commit()
            send_otp(otp_code, new_user.name, new_user.email)

        session['pending_email'] = request.form["email"]
        return redirect(url_for('verify_otp'))

    return render_template("register.html", form=form, logged_out=True, not_user=True)


@app.route('/verify-otp', methods=["GET", "POST"])
def verify_otp():
    global s_login
    user_email = session.get('pending_email')
    purpose = session.get('otp_purpose', 'register')

    if not user_email:
        return redirect(url_for('register'))

    user = db.session.execute(
        db.select(PerfumeUsers).filter_by(email=user_email)
    ).scalar_one_or_none()

    if not user:
        return redirect(url_for('register'))

    if request.method == "POST":
        submitted_code = request.form.get("otp")

        if not user.otp_code or not user.otp_created_at:
            flash("No verification code found. Please request a new one.")
            return redirect(url_for('verify_otp'))

        expired = datetime.now(timezone.utc).replace(tzinfo=None) - user.otp_created_at > timedelta(minutes=10)

        if expired:
            flash("Your code has expired. Please request a new one.")
            return redirect(url_for('verify_otp'))

        if submitted_code == user.otp_code:
            user.otp_code = None
            user.otp_created_at = None

            if purpose == 'reset':
                db.session.commit()
                session['otp_purpose'] = None
                return redirect(url_for('reset_password'))
            else:
                user.verified = True
                db.session.commit()
                session.pop('pending_email', None)
                session.pop('otp_purpose', None)
                login_user(user)
                s_login = True
                return redirect(url_for('home'))
        else:
            flash("Incorrect code. Please try again.")
            return redirect(url_for('verify_otp'))

    return render_template("verify-otp.html", user_email=user_email)


@app.route('/resend-otp')
def resend_otp():
    user_email = session.get('pending_email')
    if not user_email:
        return redirect(url_for('register'))

    user = db.session.execute(
        db.select(PerfumeUsers).filter_by(email=user_email)
    ).scalar_one_or_none()

    if user:
        new_code = str(random.randint(100000, 999999))
        user.otp_code = new_code
        user.otp_created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        send_otp(new_code, user.name, user.email)
        flash("A new code has been sent to your email.")

    return redirect(url_for('verify_otp'))


@app.route('/forgot-password', methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        f_email = request.form["email"]
        try:
            user = db.session.execute(db.select(PerfumeUsers).filter_by(email=f_email)).scalar_one()
            otp_code = str(random.randint(100000, 999999))
            user.otp_code = otp_code
            user.otp_created_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()
            send_otp(otp_code, user.name, user.email)
            session['pending_email'] = user.email
            session['otp_purpose'] = 'reset'
            return redirect(url_for('verify_otp'))
        except NoResultFound:
            flash("That email does not exist, please try again.")
            return redirect(url_for("forgot_password"))
    return render_template("forgot-password.html", logged_out=True, not_user=True)


@app.route('/reset-password', methods=["GET", "POST"])
def reset_password():
    user_email = session.get('pending_email')
    if not user_email:
        return redirect(url_for('forgot_password'))

    user = db.session.execute(
        db.select(PerfumeUsers).filter_by(email=user_email)
    ).scalar_one_or_none()

    if not user:
        return redirect(url_for('forgot_password'))

    if request.method == "POST":
        new_password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('reset_password'))

        user.password = generate_password_hash(new_password, method='pbkdf2:sha256:600000', salt_length=8)
        db.session.commit()
        session.pop('pending_email', None)
        flash("Password reset successfully. Please log in.")
        return redirect(url_for('login'))

    return render_template("reset-password.html", user_email=user_email)


@app.route('/logout')
def logout():
    global s_login, basket
    logout_user()
    s_login = False
    basket = []
    return redirect(url_for('home'))


@app.route('/test')
def test():
    return render_template("test.html")


@app.template_filter('commas')
def commas_filter(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    return f"{value:,.0f}"


if __name__ == '__main__':
    app.run(debug=True)
