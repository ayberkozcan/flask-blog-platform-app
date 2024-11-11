from flask import Flask, make_response, render_template, request, redirect, url_for, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = '123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_PP_FOLDER'] = 'static/profile_pics'
app.config['UPLOAD_IMAGE_FOLDER'] = 'static/image'

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
    followed_user_ids = db.Column(db.Text, default="")

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
    
class Comment(db.Model):
    comment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    content = db.Column(db.String(200))

    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    post = db.relationship('Post', backref=db.backref('comments', lazy=True))

    def __repr__(self):
        return f"Comment('{self.content[:20]}', '{self.created_at}')"

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
        
        if user.role == 'User':
            response = make_response(redirect(url_for('homepage')))
        else:
            response = make_response(redirect(url_for('admin_homepage')))

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

@app.before_request
def load_user():
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])
    else:
        g.user = None

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    
    return redirect(url_for('visitor_homepage'))

@app.route('/admin_homepage', methods=['GET', 'POST'])
def admin_homepage():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if user.role != 'Admin':
        return redirect(url_for('login'))

    users = User.query.all()
    posts = Post.query.all()
    comments = Comment.query.all()

    user_count = len(users)
    post_count = len(posts)
    comment_count = len(comments)

    one_month_ago = datetime.now() - timedelta(days=30)
    one_week_ago = datetime.now() - timedelta(days=7)
    user_count_last_month = User.query.filter(User.join_date >= one_month_ago).count()
    user_count_last_week = User.query.filter(User.join_date >= one_week_ago).count()

    return render_template(
        'admin_homepage.html',
        user=user,
        user_count=user_count,
        post_count=post_count,
        comment_count=comment_count,
        user_count_last_month=user_count_last_month,
        user_count_last_week=user_count_last_week
    )

@app.route('/userlist', methods=['GET', 'POST'])
def userlist():
    if 'user_id' not in session and user.role != 'Admin':
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    if user.role != 'Admin':
        return redirect(url_for('login'))

    search_term = request.form.get('usersearch', '').strip()

    if search_term:
        users = User.query.filter(User.username.ilike(f'%{search_term}%')).all()
    else:
        users = User.query.all()

    return render_template('userlist.html', user=user, users=users)

@app.route('/adduser', methods=['GET', 'POST'])
def adduser():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        age = request.form.get('age')
        role = request.form.get('role')

        existing_user_email = User.query.filter_by(email=email).first()
        existing_user_username = User.query.filter_by(username=username).first()

        if existing_user_email:
            flash("This e-mail already exists!")
            return render_template('adduser.html')
        
        if existing_user_username:
            flash("This username already exists!")
            return render_template('adduser.html')

        if len(username) < 6:
            flash("Username must be at least 6 characters long!")
            return render_template('adduser.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long!")
            return render_template('adduser.html')

        password_hash = generate_password_hash(password)
        new_user = User(email=email, username=username, password=password_hash, age=age, role=role)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('userlist'))
        
    return render_template('adduser.html')

@app.route('/deleteuser/<int:user_id>', methods=['GET', 'POST'])
def deleteuser(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User has been deleted successfully!")

    return redirect(url_for('userlist'))

@app.route('/postlist', methods=['GET', 'POST'])
def postlist():
    if 'user_id' not in session and user.role != 'Admin':
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    if user.role != 'Admin':
        return redirect(url_for('login'))

    search_term = request.form.get('postsearch', '').strip()

    if search_term:
        posts = Post.query.filter(Post.title.ilike(f'%{search_term}%')).all()
    else:
        posts = Post.query.all()

    return render_template('postlist.html', user=user, posts=posts)

@app.route('/deletepost/<int:post_id>', methods=['GET', 'POST'])
def deletepost(post_id):
    post = Post.query.get_or_404(post_id)

    Comment.query.filter_by(post_id=post_id).delete()

    db.session.delete(post)
    db.session.commit()
    
    flash("Post has been deleted successfully!")

    return redirect(url_for('postlist'))

@app.route('/homepage', methods=['GET', 'POST'])
def homepage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    search_term = request.form.get('postsearch', '').strip()
    sort_option = request.form.get('sort', 'Newest')

    if search_term:
        posts = Post.query.filter(Post.title.ilike(f'%{search_term}%'), Post.ispublic == 'public').all()
    else:
        posts = Post.query.filter(Post.ispublic == 'public')

    if sort_option == 'Newest':
        posts = posts.order_by(Post.created_date.desc())
    elif sort_option == 'Most Liked':
        posts = posts.order_by(Post.like_count.desc())

    posts = posts.all()

    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    return render_template('homepage.html', posts=posts, liked_posts=liked_posts, saved_posts=saved_posts)

@app.route('/user/<string:username>', methods=['GET', 'POST'])
def user(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    target_user = User.query.filter_by(username=username).first()
    target_user_posts = Post.query.filter(Post.user_id==target_user.id).all()

    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    return render_template('user.html', user=user,target_user=target_user, target_user_posts=target_user_posts, liked_posts=liked_posts, saved_posts=saved_posts)

@app.route('/taggedposts/<string:post_tag>', methods=['GET', 'POST'])
def taggedposts(post_tag):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    search_term = request.form.get('postsearch', '').strip()

    if search_term:
        posts = Post.query.filter(Post.title.ilike(f'%{search_term}%'), Post.ispublic == 'public').all()
    else:
        posts = Post.query.all()

    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    tag = post_tag

    return render_template('homepage.html', posts=posts, liked_posts=liked_posts, saved_posts=saved_posts, tag=tag)

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

@app.route('/followingposts', methods=['GET', 'POST'])
def followingposts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    search_term = request.form.get('postsearch', '').strip()
    sort_option = request.form.get('sort', 'Newest')

    if search_term:
        posts = Post.query.filter(Post.title.ilike(f'%{search_term}%'), Post.ispublic == 'public').all()
    else:
        posts = Post.query.filter(Post.ispublic == 'public')

    if sort_option == 'Newest':
        posts = posts.order_by(Post.created_date.desc())
    elif sort_option == 'Most Liked':
        posts = posts.order_by(Post.like_count.desc())

    posts = posts.all()

    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    followed_user_ids = user.followed_user_ids.split(',') if user.followed_user_ids else []
    followed_users = User.query.filter(User.id.in_(followed_user_ids)).all()

    return render_template('followingposts.html', user=user, posts=posts, liked_posts=liked_posts, saved_posts=saved_posts, followed_users=followed_users)

@app.route('/follow', methods=['GET', 'POST'])
def follow():
    user = User.query.get(session['user_id'])

    target_user_id = request.form.get('target_user_id')
    target_user = User.query.filter_by(id=target_user_id).first()
    target_user_posts = Post.query.filter(Post.user_id==target_user.id).all()

    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    followed_user_ids = user.followed_user_ids.split(',') if user.followed_user_ids else []
    if str(target_user.id) not in followed_user_ids:
        followed_user_ids.append(str(target_user.id))

    user.followed_user_ids = ','.join(followed_user_ids)
    db.session.commit()

    return render_template(
        'user.html', 
        user=user,
        target_user=target_user, 
        target_user_posts=target_user_posts, 
        liked_posts=liked_posts, 
        saved_posts=saved_posts, 
    )

@app.route('/unfollow', methods=['GET', 'POST'])
def unfollow():
    user = User.query.get(session['user_id'])

    target_user_id = request.form.get('target_user_id')
    target_user = User.query.filter_by(id=target_user_id).first()
    target_user_posts = Post.query.filter(Post.user_id==target_user.id).all()

    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    followed_user_ids = user.followed_user_ids.split(',') if user.followed_user_ids else []
    if str(target_user.id) in followed_user_ids:
        followed_user_ids.remove(str(target_user.id))

    user.followed_user_ids = ','.join(followed_user_ids)
    db.session.commit()

    return render_template(
            'user.html', 
            user=user,
            target_user=target_user, 
            target_user_posts=target_user_posts, 
            liked_posts=liked_posts, 
            saved_posts=saved_posts, 
        )
        
@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    
    user = User.query.get(session['user_id'])
    user_id = user.id

    posts = Post.query.all()
    post = Post.query.get_or_404(post_id)

    comments = Comment.query.filter_by(post_id=post_id).all()

    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    return render_template("post.html", posts=posts, post=post, post_id=post_id, comments=comments, user_id=user_id, liked_posts=liked_posts, saved_posts=saved_posts)

@app.route('/deletecomment/<int:post_id>/<int:comment_id>', methods=['POST'])
def deletecomment(post_id, comment_id):
    comment = Comment.query.get_or_404(comment_id)

    db.session.delete(comment)
    db.session.commit()

    return redirect(url_for('post', post_id=post_id))

@app.route('/comment/<int:post_id>', methods=['GET', 'POST'])
def comment(post_id):
    if request.method == 'POST':
        content = request.form['commentTextarea']

        user_id = session['user_id']
        if not content:
            flash('Content cannot be empty!', "error")
            return redirect(url_for('homepage'))

        post = Post.query.get_or_404(post_id)
        post.comment_count += 1

        new_comment = Comment(content=content, post_id=post_id, user_id=user_id)
        db.session.add(new_comment)
        db.session.commit()

    return redirect(url_for('homepage'))

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
        
        if not os.path.exists(app.config['UPLOAD_PP_FOLDER']):
            os.makedirs(app.config['UPLOAD_PP_FOLDER'])
        
        profile_pic.save(filepath)
        user.profile_pic_url = filename
        db.session.commit()

        flash("Picture Uploaded!")
    
    return render_template('profile.html', user=user)

@app.route('/removepp', methods=['POST'])
def remove_pp():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if user and user.profile_pic_url:
        user.profile_pic_url = None
        db.session.commit()

    return redirect(url_for('profile'))

@app.route('/likedsavedposts/<string:type>', methods=['GET', 'POST'])
def likedsavedposts(type):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    posts = Post.query.all()

    liked_posts = user.liked_post_ids.split(',') if user.liked_post_ids else []
    saved_posts = user.saved_post_ids.split(',') if user.saved_post_ids else []

    page_title = "Liked Posts" if type == "liked" else "Saved Posts"

    if type == "liked":
        filtered_posts = [post for post in posts if str(post.id) in liked_posts]
    else:
        filtered_posts = [post for post in posts if str(post.id) in saved_posts]

    return render_template(
        'likedsavedposts.html', 
        user=user, 
        posts=filtered_posts, 
        liked_posts=liked_posts, 
        saved_posts=saved_posts, 
        page_title=page_title
    )

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
        image = request.files.get('imageUpload')

        image_url = None

        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_IMAGE_FOLDER'], filename)

            if not os.path.exists(app.config['UPLOAD_IMAGE_FOLDER']):
                os.makedirs(app.config['UPLOAD_IMAGE_FOLDER'])

            image.save(filepath)
            image_url = filename

        new_post = Post(
            title=title,
            content=content,
            tags=tags,
            user_id=user_id,
            ispublic=visibility,
            image_url=image_url
        )
        db.session.add(new_post)
        db.session.commit()

        flash("Post Created Successfully!")
        return redirect(url_for('myblog'))

    posts = Post.query.all()
    user = User.query.get(session['user_id'])
    
    liked_posts = user.liked_post_ids.split(',')
    saved_posts = user.saved_post_ids.split(',')

    return render_template('myblog.html', posts=posts, liked_posts=liked_posts, saved_posts=saved_posts)

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form['titleTextarea']
        post.content = request.form['contentTextarea']
        post.tags = request.form['tagTextarea']
        post.ispublic = request.form['visibility']
        
        if 'imageUpload' in request.files:
            image_file = request.files['imageUpload']
            if image_file and image_file.filename != '':
                if post.image_url:
                    old_image_path = os.path.join(app.config['UPLOAD_IMAGE_FOLDER'], post.image_url)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_IMAGE_FOLDER'], filename)
                image_file.save(image_path)

                post.image_url = filename
        
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

@app.route('/deleteaccount', methods=['GET', 'POST'])
def deleteaccount():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if user:
        for liked_post_id in user.liked_post_ids:
            post = Post.query.get(liked_post_id)
            if post and post.like_count > 0:
                post.like_count -= 1

        for comment in Comment.query.filter_by(user_id=user_id).all():
            post = Post.query.get(comment.post_id)
            if post and post.comment_count > 0:
                post.comment_count -= 1

        Post.query.filter_by(user_id=user_id).delete()
        Comment.query.filter_by(user_id=user_id).delete()

        db.session.delete(user)
        db.session.commit()
        session.pop('user_id', None)

    return redirect(url_for('visitor_homepage'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)