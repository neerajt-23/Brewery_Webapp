from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import uuid


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def get_average_rating(reviews):
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        average_rating = total_rating / len(reviews)
        return average_rating
    else:
        return "No reviews yet"



app.jinja_env.globals.update(get_average_rating=get_average_rating)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    reviews = db.relationship('Review', backref='author', lazy=True)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    brewery_id = db.Column(db.String(36), nullable=False) # Change data type to String(36)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))



# Routes
@app.route('/')
def home():
    return render_template('home.html', current_user=current_user)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        city = request.form['city']
        breweries = get_breweries_by_city(city)
        return render_template('search.html', breweries=breweries)
    return render_template('search.html')


@app.route('/brewery/<string:brewery_id>', methods=['GET', 'POST'])
@login_required
def brewery_details(brewery_id):
    # Check if brewery_id is a valid UUID
    try:
        uuid.UUID(brewery_id, version=4)
    except ValueError:
        flash('Invalid brewery ID.', 'danger')
        return redirect(url_for('home'))

    brewery = get_brewery_by_id(brewery_id)
    
    if brewery:
        # Pass brewery_id as a string when calling the function
        reviews = get_reviews_for_brewery(str(brewery_id))
        return render_template('brewery_details.html', brewery=brewery, reviews=reviews)
    else:
        flash('Brewery not found.', 'danger')
        return redirect(url_for('search'))


@app.route('/add_review/<string:brewery_id>', methods=['GET', 'POST'])
@login_required
def add_review(brewery_id):
    try:
        uuid.UUID(brewery_id, version=4) # Check if brewery_id is a valid UUID
    except ValueError:
        flash('Invalid brewery ID.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        rating = int(request.form['rating'])
        content = request.form['content']
        if 1 <= rating <= 5:
            # Use brewery_id directly as a string
            review = Review(rating=rating, content=content, brewery_id=brewery_id, user_id=current_user.id)
            db.session.add(review)
            db.session.commit()
            flash('Review added successfully!', 'success')
        else:
            flash('Invalid rating. Please choose a rating between 1 and 5.', 'danger')
        return redirect(url_for('brewery_details', brewery_id=brewery_id))
    
    return render_template('add_review.html', brewery_id=brewery_id)

def get_breweries_by_city(city):
    api_url = f'https://api.openbrewerydb.org/v1/breweries?by_city={city}&per_page=6'
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    else:
        flash('Error fetching breweries. Please try again.', 'danger')
        return []


def get_brewery_by_id(brewery_id):
    api_url = f'https://api.openbrewerydb.org/v1/breweries/{brewery_id}'
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_reviews_for_brewery(brewery_id):
    return Review.query.filter_by(brewery_id=brewery_id).all()



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)