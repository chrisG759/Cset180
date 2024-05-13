from datetime import timedelta, datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://chris:sirhc@172.16.180.214/fp180'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'accounts'
    User_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(45), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(255), nullable=False)

class Product(db.Model):
    __tablename__ = 'products'
    Product_ID = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.Text, nullable=False)
    Description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)

    def __init__(self, Title, Description, price, image_url, Quantity):
        self.Title = Title
        self.Description = Description
        self.price = price
        self.image_url = image_url
        self.Quantity = Quantity

class Review(db.Model):
    review_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.Product_ID'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.Text)
    reviewer_name = db.Column(db.String(255), nullable=False)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('accounts.User_ID'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.Product_ID'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Add a price column
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

class OrderStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_num = db.Column(db.Integer, nullable=False)
    items = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False)

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        account = User.query.filter_by(username=username, password=password).first()
        
        if User and User.password == password:
            session['user_id'] = User.User_ID
            session.permanent = True
            if User.type == 'admin':
                return redirect(url_for('admin'))
            elif User.type == 'vendor':
                return redirect(url_for('vendor'))
            elif User.type == 'customer':
                return redirect(url_for('products'))
            else:
                flash('Invalid account type', 'error')
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    cart_items = user.carts  
    
    total_price = 0
    
    for item in cart_items:
    # Check if price is None or zero
        if item.product.price is None or item.product.price == 0:
            flash(f'Price for item "{item.product.Title}" is not set or zero. Please contact support.', 'error')
            return redirect(url_for('home'))
        
        # Calculate the total price for each item in the cart
        item.total_price = item.quantity * item.product.price
        total_price += item.total_price
    
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/proceed_to_payment', methods=['GET', 'POST'])
def proceed_to_payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        user = User.query.get(user_id)
        cart_items = user.carts  

        items = []
        total_price = 0

        for item in cart_items:
            product = item.product
            if product.price is None:
                flash(f'Price for item "{product.Title}" is not set. Please contact support.', 'error')
                return redirect(url_for('cart'))

            total_price += product.price * item.quantity
            items.append(f"{product.Title} (Quantity: {item.quantity})")

        # Create order status object
        order = OrderStatus(order_num=generate_order_number(), items=', '.join(items), total_price=f"${total_price:.2f}", status='Pending')
        db.session.add(order)
        db.session.commit()

        # Clear the cart after order placement
        Cart.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        flash('Payment processed successfully. Your order has been placed.', 'success')
        return redirect(url_for('order_receipt', order_num=order.order_num))

    return render_template('payment_form.html')

def generate_order_number():
    # Generate a unique order number (you can implement your own logic)
    # For example, you can use a combination of timestamp and user ID
    return int(datetime.now().timestamp())

@app.route('/order_receipt/<int:order_num>')
def order_receipt(order_num):
    order = OrderStatus.query.filter_by(order_num=order_num).first()
    if order:
        return render_template('order_receipt.html', order=order)
    else:
        flash('Invalid order number', 'error')
        return redirect(url_for('home'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))  

    user_id = session['user_id']  

    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])  

    product = Product.query.get(product_id)
    if product:
        # Check if the product price is None or not properly set
        if product.price is None:
            flash(f'Price for product "{product.Title}" is not set. Please contact support.', 'error')
            return redirect(url_for('home'))

        cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity, price=product.price)
        db.session.add(cart_item)
        db.session.commit()

        flash('Product added to cart successfully', 'success')
    else:
        flash('Product not found', 'error')
    
    return redirect(url_for('cart'))  # Redirect to the cart page after adding the item

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        account_type = request.form['account_type']
        
        # Check if email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'error')
            return redirect(url_for('register'))  # Redirect back to registration form
        
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,  # Adjust field name
            last_name=last_name,    # Adjust field name
            password=password,
            type=account_type
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.User_ID
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    products = Product.query.all()
    return render_template('products.html', user=user, products=products)

@app.route('/product/<int:product_id>')
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).all()
    return render_template('product_details.html', product=product, reviews=reviews)

@app.route('/product/<int:product_id>/write_review', methods=['GET', 'POST'])
def write_review(product_id):
    if request.method == 'POST':
        rating = int(request.form['rating'])
        description = request.form['description']
        image = request.form['image']
        reviewer_name = request.form['reviewer_name']
        review = Review(product_id=product_id, rating=rating, description=description, image=image, reviewer_name=reviewer_name)
        db.session.add(review)
        db.session.commit()
        flash('Review added successfully', 'success')
        return redirect(url_for('product_details', product_id=product_id))
    return render_template('write_review.html', product_id=product_id)






@app.route('/product/<int:product_id>/reviews')
def product_reviews(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).all()
    return render_template('product_reviews.html', product=product, reviews=reviews)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))  

    cart_item_id = request.form['cart_item_id']
    
    cart_item = Cart.query.get(cart_item_id)

    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Product removed from cart successfully', 'success')
    else:
        flash('Failed to remove product from cart', 'error')

    return redirect(url_for('cart'))

if __name__ == '__main__':
    app.run(debug=True)