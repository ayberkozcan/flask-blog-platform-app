from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)

app.secret_key = '123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(100))
    description = db.Column(db.Text)

    def __repr__(self):
        return f"User('{self.username}')"
    
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text)
    tags = db.Column(db.String(100))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('posts', lazy=True))

    def __repr__(self):
        return f"Post('{self.title}', '{self.created_date}')"

@app.route('/', methods=['GET', 'POST'])
def visitor_base():
    return render_template('visitor_base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user is None:
            flash("Email not found!")
            return render_template('login.html')
        
        if not check_password_hash(user.password, password):
            flash("Incorrect Password!")
            return render_template('login.html')
        
        session['user_id'] = user.id

        return redirect(url_for('homepage'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        age = request.form.get('age')

        existing_user_email = User.query.filter_by(email=email).first()
        existing_user_username = User.query.filter_by(username=username).first()

        if existing_user_email:
            flash("This e-mail already exists!")
            return render_template('register.html')
        
        if existing_user_username:
            flash("This username already exists!")
            return render_template('register.html')

        if len(username) < 6:
            flash("Username must be at least 6 characters long!")
            return render_template('register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long!")
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        new_user = User(email=email, username=username, password=password_hash, age=age)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    
    return redirect(url_for('visitor_base'))

@app.route('/homepage', methods=['GET', 'POST'])
def homepage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    posts = Post.query.all()

    return render_template('homepage.html', posts=posts)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        new_description = request.form.get('description')

        user.description = new_description
        db.session.commit()

        flash("Description Updated Successfully!")
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/changepassword', methods=['GET', 'POST'])
def changepassword():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')

        if not check_password_hash(user.password, current_password):
            flash("Wrong Password!")
            return render_template('changepassword.html', user=user)

        if len(new_password) < 6:
            flash("Password must be at least 6 characters long!")
            return render_template('changepassword.html')
        
        user.password = generate_password_hash(new_password)
        db.session.commit()

        flash("Password Updated Successfully!")
        return redirect(url_for('profile'))
    
    return render_template('changepassword.html')

@app.route('/myblog', methods=['GET', 'POST'])
def myblog():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['titleTextarea']
        content = request.form['contentTextarea']
        tags = request.form['tagTextarea']
        user_id = request.form['user_id']

        new_post = Post(title=title, content=content, tags=tags, user_id=user_id)
        db.session.add(new_post)
        db.session.commit()

        flash("Post Created Successfully!")
        return redirect(url_for('myblog'))

    posts = Post.query.all()
    return render_template('myblog.html', posts=posts)

@app.route('/delete_post/<int:post_id>', methods=['GET', 'POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.user_id != session['user_id']:
        flash('You do not have permission to delete this post.')
        return redirect(url_for('myblog'))
    
    db.session.delete(post)
    db.session.commit()
    flash('Post Deleted Successfully!')

    return redirect(url_for('myblog'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)