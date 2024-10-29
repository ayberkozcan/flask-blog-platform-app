from flask import Flask, make_response, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = '123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_PP_FOLDER'] = 'static/profile_pics'

db = SQLAlchemy(app)

migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(100), default="User")
    description = db.Column(db.Text)
    liked_post_ids = db.Column(db.Text, default="")
    saved_post_ids = db.Column(db.Text, default="")
    profile_pic_url = db.Column(db.String(255))

    def __repr__(self):
        return f"User('{self.username}')"
    
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text)
    tags = db.Column(db.String(100))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ispublic = db.Column(db.Text)
    like_count = db.Column(db.Integer, default=0)
    save_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(255))

    user = db.relationship('User', backref=db.backref('posts', lazy=True))

    def __repr__(self):
        return f"Post('{self.title}', '{self.created_date}')"

@app.route('/', methods=['GET', 'POST'])
def visitor_homepage():

    posts = Post.query.all()

    return render_template('visitor_homepage.html', posts=posts)

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
        
        response = make_response(redirect(url_for('homepage')))
        response.set_cookie('email', email, max_age=60*60*24*30)
        response.set_cookie('password', password, max_age=60*60*24*30)

        session['user_id'] = user.id

        return response

    saved_email = request.cookies.get('email', '')
    saved_password = request.cookies.get('password', '')
    return render_template('login.html', saved_email=saved_email, saved_password=saved_password)

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
    
    return redirect(url_for('visitor_homepage'))

@app.route('/homepage', methods=['GET', 'POST'])
def homepage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    posts = Post.query.all()

    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    return render_template('homepage.html', posts=posts, liked_posts=liked_posts, saved_posts=saved_posts)

@app.route('/toggle_like', methods=['POST'])
def toggle_like():
    post_id = request.json.get('post_id')
    action = request.json.get('action')

    post = Post.query.get(post_id)
    user = User.query.get(session['user_id'])

    if post and user:
        if action == 'like':
            post.like_count += 1
            if post_id not in user.liked_post_ids.split(','):
                user.liked_post_ids += f"{post_id},"
        elif action == 'unlike':
            post.like_count -= 1
            if post_id in user.liked_post_ids.split(','):
                user.liked_post_ids = ','.join(
                    [id for id in user.liked_post_ids.split(',') if id != post_id]
                )
        elif action == 'save':
            post.save_count += 1
            if post_id not in user.saved_post_ids.split(','):
                user.saved_post_ids += f"{post_id},"
        elif action == 'unsave':
            post.save_count -= 1
            if post_id in user.saved_post_ids.split(','):
                user.saved_post_ids = ','.join(
                    [id for id in user.saved_post_ids.split(',') if id != post_id]
                )

        db.session.commit()
        
        return {
            'status': 'success', 
            'like_count': post.like_count,
            'save_count': post.save_count
        }
    else:
        return {'status': 'error'}, 404

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

@app.route('/uploadpp', methods=['POST'])
def upload_pp():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    profile_pic = request.files['profile_pic']

    if profile_pic:
        filename = secure_filename(profile_pic.filename)
        filepath = os.path.join(app.config['UPLOAD_PP_FOLDER'], filename)
        profile_pic.save(filepath)

        user.profile_pic_url = filename
        db.session.commit()

        flash("Picture Uploaded!")
    
    return render_template('profile.html', user=user)

@app.route('/likedposts', methods=['GET', 'POST'])
def likedposts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    posts = Post.query.all()

    liked_posts = user.liked_post_ids.split(',') if user.liked_post_ids else []
    saved_posts = user.saved_post_ids.split(',') if user.saved_post_ids else []

    return render_template('likedposts.html', user=user, posts=posts, liked_posts=liked_posts, saved_posts=saved_posts)

@app.route('/savedposts', methods=['GET', 'POST'])
def savedposts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    posts = Post.query.all()

    liked_posts = user.liked_post_ids.split(',') if user.liked_post_ids else []
    saved_posts = user.saved_post_ids.split(',') if user.saved_post_ids else []

    return render_template('savedposts.html', user=user, posts=posts, liked_posts=liked_posts, saved_posts=saved_posts)

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
        visibility = request.form['visibility']

        if not title or not content:
            flash("Title and Content cannot be empty!", "error")
            return redirect(url_for('myblog'))

        new_post = Post(title=title, content=content, tags=tags, user_id=user_id, ispublic=visibility)
        db.session.add(new_post)
        db.session.commit()

        flash("Post Created Successfully!")
        return redirect(url_for('myblog'))

    posts = Post.query.all()
    user = User.query.get(session['user_id'])
    
    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    return render_template('myblog.html', posts=posts, liked_posts=liked_posts, saved_posts=saved_posts)

    # return render_template('myblog.html', posts=posts)

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form['titleTextarea']
        post.content = request.form['contentTextarea']
        post.tags = request.form['tagTextarea']
        post.ispublic = request.form['visibility']
        
        db.session.commit()
        flash('Post successfully updated!')
        return redirect(url_for('myblog'))
    
    return render_template('editpost.html', post=post)


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

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    return render_template('settings.html', user=user)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)