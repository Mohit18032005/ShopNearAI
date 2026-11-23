import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, initialize_database
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)

app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production"
)

initialize_database()

# Temporary product data
products = [
    {
        "name": "Wireless Mouse",
        "category": "Electronics",
        "price": 599,
        "shop": "Tech World",
        "location": "Kolkata",
        "stock": 12,
        "image": "mouse.jpg"
    },
    {
        "name": "Mechanical Keyboard",
        "category": "Electronics",
        "price": 1499,
        "shop": "Computer Hub",
        "location": "Kolkata",
        "stock": 5
    },
    {
        "name": "Cotton T-Shirt",
        "category": "Fashion",
        "price": 399,
        "shop": "Fashion Point",
        "location": "Kolkata",
        "stock": 20
    },
    {
        "name": "Notebook",
        "category": "Stationery",
        "price": 60,
        "shop": "Student Stationers",
        "location": "Kolkata",
        "stock": 30
    },
    {
        "name": "Football",
        "category": "Sports",
        "price": 799,
        "shop": "Sports Corner",
        "location": "Kolkata",
        "stock": 8
    }
]

# Temporary reservation storage
reservations = []


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not name or not username or not email or not password:
            flash("Please fill in all fields.")
            return redirect(url_for("register"))

        if role not in ["customer", "shopkeeper"]:
            flash("Invalid account type.")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("Username must contain at least 3 characters.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email = ? OR username = ?",
            (email, username)
        )

        if cursor.fetchone():
            connection.close()
            flash("Email or username is already registered.")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users
            (name, username, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            username,
            email,
            password_hash,
            role,
            datetime.now().strftime("%d-%m-%Y %I:%M %p")
        ))

        connection.commit()
        connection.close()

        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")




@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )

        user = cursor.fetchone()
        connection.close()

        if user and check_password_hash(user["password_hash"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return render_template("login.html")



@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE username = ? AND role = 'admin'
        """, (username,))

        user = cursor.fetchone()
        connection.close()

        if user and check_password_hash(user["password_hash"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin username or password.")
        return redirect(url_for("admin_login"))

    return render_template("admin_login.html")



@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    role = session.get("user_role")

    if role == "admin":
        return redirect(url_for("admin_dashboard"))

    elif role == "customer":
        return redirect(url_for("customer_dashboard"))

    elif role == "shopkeeper":
        return redirect(url_for("shopkeeper_dashboard"))

    session.clear()
    flash("Invalid account role.")
    return redirect(url_for("login"))

@app.route("/customer/dashboard")
def customer_dashboard():

    if "user_id" not in session or session.get("user_role") != "customer":
        flash("Customer access required.")
        return redirect(url_for("login"))

    return render_template("customer_dashboard.html")


@app.route("/shopkeeper/dashboard")
def shopkeeper_dashboard():

    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    return render_template("shopkeeper_dashboard.html")


@app.route("/shopkeeper/products/add", methods=["GET", "POST"])
def add_product():

    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        price = request.form.get("price", "").strip()
        shop = request.form.get("shop", "").strip()
        location = request.form.get("location", "").strip()
        stock = request.form.get("stock", "").strip()
        description = request.form.get("description", "").strip()
        image = request.form.get("image", "").strip()

        if not all([name, category, price, shop, location, stock]):
            flash("Please fill in all required fields.")
            return redirect(url_for("add_product"))

        try:
            price = float(price)
            stock = int(stock)

            if price <= 0 or stock < 0:
                raise ValueError

        except ValueError:
            flash("Enter a valid price and stock quantity.")
            return redirect(url_for("add_product"))

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
    INSERT INTO products
    (name, category, price, shop, location, stock,
     description, image, owner_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    name,
    category,
    price,
    shop,
    location,
    stock,
    description,
    image,
    session["user_id"]
))
        connection.commit()
        connection.close()

        flash("Product added successfully!")
        return redirect(url_for("shopkeeper_dashboard"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT shop_name, location
        FROM shops
        WHERE owner_id = ?
    """, (session["user_id"],))

    shop = cursor.fetchone()
    connection.close()

    return render_template("add_product.html", shop=shop)



@app.route("/shopkeeper/products")
def my_products():
    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM products
        WHERE owner_id = ?
        ORDER BY id DESC
    """, (session["user_id"],))

    products = cursor.fetchall()
    connection.close()

    return render_template(
        "my_products.html",
        products=products
    )



@app.route("/shopkeeper/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM products
        WHERE id = ? AND owner_id = ?
    """, (product_id, session["user_id"]))

    product = cursor.fetchone()

    if product is None:
        connection.close()
        flash("Product not found or access denied.")
        return redirect(url_for("my_products"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        shop = request.form.get("shop", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        image = request.form.get("image", "").strip()

        try:
            price = float(request.form.get("price", ""))
            stock = int(request.form.get("stock", ""))

            if not all([name, category, shop, location]):
                raise ValueError

            if price <= 0 or stock < 0:
                raise ValueError

        except ValueError:
            connection.close()
            flash("Please enter valid product details.")
            return redirect(url_for("edit_product", product_id=product_id))

        cursor.execute("""
    UPDATE products
    SET name = ?, category = ?, price = ?,
        shop = ?, location = ?, stock = ?,
        description = ?, image = ?
    WHERE id = ? AND owner_id = ?
""", (
    name, category, price, shop, location,
    stock, description, image, product_id, session["user_id"]
))

        connection.commit()
        connection.close()

        flash("Product updated successfully!")
        return redirect(url_for("my_products"))

    connection.close()

    return render_template("edit_product.html", product=product)

@app.route("/shopkeeper/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):

    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM products
        WHERE id = ? AND owner_id = ?
    """, (product_id, session["user_id"]))

    if cursor.rowcount > 0:
        connection.commit()
        flash("Product deleted successfully.")
    else:
        flash("Product not found or access denied.")

    connection.close()

    return redirect(url_for("my_products"))




@app.route("/shopkeeper/shop", methods=["GET", "POST"])
def shop_management():

    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM shops
        WHERE owner_id = ?
    """, (session["user_id"],))

    shop = cursor.fetchone()

    if request.method == "POST":

        shop_name = request.form.get("shop_name", "").strip()
        location = request.form.get("location", "").strip()
        address = request.form.get("address", "").strip()
        description = request.form.get("description", "").strip()

        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()

        if not shop_name or not location or not address:
            connection.close()
            flash("Please fill in all required fields.")
            return redirect(url_for("shop_management"))

        # Validate optional map coordinates
        if bool(latitude) != bool(longitude):
            connection.close()
            flash("Please enter both latitude and longitude.")
            return redirect(url_for("shop_management"))

        try:
            latitude = float(latitude) if latitude else None
            longitude = float(longitude) if longitude else None

            if latitude is not None and not -90 <= latitude <= 90:
                raise ValueError

            if longitude is not None and not -180 <= longitude <= 180:
                raise ValueError

        except ValueError:
            connection.close()
            flash("Please enter valid latitude and longitude values.")
            return redirect(url_for("shop_management"))

        if shop:
            cursor.execute("""
                UPDATE shops
                SET shop_name = ?, location = ?,
                    address = ?, description = ?,
                    latitude = ?, longitude = ?
                WHERE owner_id = ?
            """, (
                shop_name, location, address,
                description, latitude, longitude,
                session["user_id"]
            ))

        else:
            cursor.execute("""
                INSERT INTO shops
                (owner_id, shop_name, address, location,
                 description, latitude, longitude, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                session["user_id"], shop_name, address,
                location, description, latitude, longitude
            ))

        connection.commit()
        connection.close()

        flash("Shop details saved successfully!")
        return redirect(url_for("shop_management"))

    connection.close()

    return render_template("shop_management.html", shop=shop)



@app.route("/admin/dashboard")
def admin_dashboard():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'shopkeeper'")
    total_shopkeepers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reservations")
    total_reservations = cursor.fetchone()[0]

    connection.close()

    return render_template(
        "admin_dashboard.html",
        total_customers=total_customers,
        total_shopkeepers=total_shopkeepers,
        total_products=total_products,
        total_reservations=total_reservations
    )



@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out successfully.")

    return redirect(url_for("login"))




@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    recommended_products = []
    recommendation_reason = "Popular choices among ShopNear AI customers."

    # Generate recommendations for customers
    if session.get("user_role") == "customer":
        preferred_category = None

        # Find the customer's most frequently reserved category
        cursor.execute("""
            SELECT products.category, COUNT(*) AS category_count
            FROM reservations
            JOIN products
                ON reservations.product_id = products.id
            WHERE reservations.user_id = ?
              AND reservations.status = 'Confirmed'
            GROUP BY products.category
            ORDER BY category_count DESC
            LIMIT 1
        """, (session["user_id"],))

        preference = cursor.fetchone()

        if preference:
            preferred_category = preference["category"]

        
        # Recommend products based on similar customers' reservation histories
        if preferred_category:
            cursor.execute("""
                WITH similar_customers AS (
                    SELECT DISTINCT other_reservations.user_id
                    FROM reservations AS other_reservations
                    JOIN products AS other_products
                        ON other_reservations.product_id = other_products.id
                    WHERE other_reservations.status = 'Confirmed'
                      AND other_reservations.user_id != ?
                      AND other_products.category = ?
                ),
                related_categories AS (
                    SELECT
                        related_products.category,
                        COUNT(*) AS category_score
                    FROM reservations AS related_reservations
                    JOIN products AS related_products
                        ON related_reservations.product_id = related_products.id
                    JOIN similar_customers
                        ON similar_customers.user_id = related_reservations.user_id
                    WHERE related_reservations.status = 'Confirmed'
  AND NOT EXISTS (
      SELECT 1
      FROM reservations AS customer_category_reservations
      JOIN products AS customer_category_products
          ON customer_category_reservations.product_id = customer_category_products.id
      WHERE customer_category_reservations.user_id = ?
        AND customer_category_reservations.status = 'Confirmed'
        AND customer_category_products.category = related_products.category
  )
GROUP BY related_products.category
                )
                SELECT
                    products.*,
                    shops.address AS shop_address,
                    COUNT(DISTINCT popularity_reservations.id) AS popularity,
                    related_categories.category_score
                FROM products
                LEFT JOIN shops
                    ON products.owner_id = shops.owner_id
                    AND products.shop = shops.shop_name
                JOIN related_categories
                    ON related_categories.category = products.category
                LEFT JOIN reservations AS popularity_reservations
                    ON products.id = popularity_reservations.product_id
                    AND popularity_reservations.status = 'Confirmed'
                WHERE products.stock > 0
                  AND products.id = (
                      SELECT MAX(p2.id)
                      FROM products AS p2
                      WHERE LOWER(TRIM(p2.name)) = LOWER(TRIM(products.name))
                        AND p2.category = products.category
                        AND p2.stock > 0
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM reservations AS customer_reservations
                      JOIN products AS reserved_products
                          ON customer_reservations.product_id = reserved_products.id
                      WHERE customer_reservations.user_id = ?
                        AND customer_reservations.status = 'Confirmed'
                        AND LOWER(TRIM(reserved_products.name)) =
                            LOWER(TRIM(products.name))
                  )
                GROUP BY products.id
                ORDER BY
                    related_categories.category_score DESC,
                    popularity DESC,
                    products.id DESC
                LIMIT 4
            """, (
    session["user_id"],
    preferred_category,
    session["user_id"],
    session["user_id"]
))

            recommended_products = cursor.fetchall()

            if recommended_products:
                recommendation_reason = (
                    "Recommended using reservation patterns from customers "
                    "with similar interests."
                )


        # Show popular products if there is no personalized recommendation
        if not recommended_products:
            
            cursor.execute("""
                WITH product_popularity AS (
                    SELECT
                        p.id,
                        COUNT(DISTINCT r.id) AS popularity
                    FROM products AS p
                    LEFT JOIN reservations AS r
                        ON p.id = r.product_id
                        AND r.status = 'Confirmed'
                    WHERE p.stock > 0
                      AND p.id = (
                          SELECT MAX(p2.id)
                          FROM products AS p2
                          WHERE LOWER(TRIM(p2.name)) = LOWER(TRIM(p.name))
                            AND p2.category = p.category
                            AND p2.stock > 0
                      )
                      AND NOT EXISTS (
                          SELECT 1
                          FROM reservations AS customer_reservations
                          JOIN products AS reserved_products
                              ON customer_reservations.product_id = reserved_products.id
                          WHERE customer_reservations.user_id = ?
                            AND customer_reservations.status = 'Confirmed'
                            AND LOWER(TRIM(reserved_products.name)) =
                                LOWER(TRIM(p.name))
                      )
                    GROUP BY p.id
                ),
                ranked_products AS (
                    SELECT
                        p.*,
                        s.address AS shop_address,
                        pp.popularity,
                        ROW_NUMBER() OVER (
                            PARTITION BY p.category
                            ORDER BY pp.popularity DESC, p.id DESC
                        ) AS category_rank
                    FROM product_popularity AS pp
                    JOIN products AS p
                        ON p.id = pp.id
                    LEFT JOIN shops AS s
                        ON p.owner_id = s.owner_id
                        AND p.shop = s.shop_name
                )
                SELECT *
                FROM ranked_products
                WHERE category_rank = 1
                ORDER BY popularity DESC, id DESC
                LIMIT 4
            """, (session["user_id"],))
            recommended_products = cursor.fetchall()
            recommendation_reason = "Popular choices among ShopNear AI customers."

    connection.close()

    return render_template(
        "index.html",
        recommended_products=recommended_products,
        recommendation_reason=recommendation_reason
    )




@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()

    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    selected_location = request.args.get("location", "").strip()
    in_stock_only = request.args.get("in_stock", "").strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL AND category != ''
        ORDER BY category
    """)
    categories = [row["category"] for row in cursor.fetchall()]

    # Fetch available product locations
    cursor.execute("""
        SELECT DISTINCT location
        FROM products
        WHERE location IS NOT NULL AND location != ''
        ORDER BY location
    """)
    locations = [row["location"] for row in cursor.fetchall()]

    sql = """
    SELECT
        products.*,
        shops.address AS shop_address,
        shops.latitude AS shop_latitude,
        shops.longitude AS shop_longitude
    FROM products
    LEFT JOIN shops
        ON products.owner_id = shops.owner_id
        AND products.shop = shops.shop_name
    WHERE (products.name LIKE ? OR products.category LIKE ?)
"""

    params = [f"%{query}%", f"%{query}%"]

    # Category filter
    if selected_category:
        sql += " AND category = ?"
        params.append(selected_category)

    # Location filter
    if selected_location:
        sql += " AND location = ?"
        params.append(selected_location)

    # Availability filter
    if in_stock_only == "1":
        sql += " AND stock > 0"

    # Minimum price filter
    if min_price:
        try:
            minimum = float(min_price)
            if minimum < 0:
                raise ValueError
        except ValueError:
            connection.close()
            flash("Please enter a valid minimum price.")
            return redirect(url_for("search"))

        sql += " AND price >= ?"
        params.append(minimum)

    # Maximum price filter
    if max_price:
        try:
            maximum = float(max_price)
            if maximum < 0:
                raise ValueError
        except ValueError:
            connection.close()
            flash("Please enter a valid maximum price.")
            return redirect(url_for("search"))

        sql += " AND price <= ?"
        params.append(maximum)

    # Check that the price range is valid
    if min_price and max_price and minimum > maximum:
        connection.close()
        flash("Minimum price cannot exceed maximum price.")
        return redirect(url_for("search"))

    cursor.execute(sql, params)

    
    results = cursor.fetchall()

        # AI-powered product recommendations
    recommended_products = []

    # Only show recommendations on the main marketplace page,
    # not when the customer searches or selects a category.
    if not selected_category and not query:

        preferred_category = None

        # Find the customer's most frequently reserved category
        if session.get("user_role") == "customer":

            cursor.execute("""
                SELECT products.category, COUNT(*) AS category_count
                FROM reservations
                JOIN products
                    ON reservations.product_id = products.id
                WHERE reservations.user_id = ?
                GROUP BY products.category
                ORDER BY category_count DESC
                LIMIT 1
            """, (session["user_id"],))

            preference = cursor.fetchone()

            if preference:
                preferred_category = preference["category"]

        # Personalized recommendations
        if preferred_category:

            cursor.execute("""
                SELECT
                    products.*,
                    shops.address AS shop_address,
                    COUNT(reservations.id) AS popularity
                FROM products
                LEFT JOIN shops
                    ON products.owner_id = shops.owner_id
                    AND products.shop = shops.shop_name
                LEFT JOIN reservations
                    ON products.id = reservations.product_id
                WHERE products.category = ?
                  AND products.stock > 0
                GROUP BY products.id
                ORDER BY popularity DESC, products.id DESC
                LIMIT 4
            """, (preferred_category,))

            recommended_products = cursor.fetchall()

        # Popular products for customers without reservation history
        else:

            cursor.execute("""
                SELECT
                    products.*,
                    shops.address AS shop_address,
                    COUNT(reservations.id) AS popularity
                FROM products
                LEFT JOIN shops
                    ON products.owner_id = shops.owner_id
                    AND products.shop = shops.shop_name
                LEFT JOIN reservations
                    ON products.id = reservations.product_id
                WHERE products.stock > 0
                GROUP BY products.id
                ORDER BY popularity DESC, products.id DESC
                LIMIT 4
            """)

            recommended_products = cursor.fetchall()

    connection.close()


    return render_template(
    "search.html",
    query=query,
    results=results,
    recommended_products=recommended_products,
    categories=categories,
    selected_category=selected_category,
    min_price=min_price,
    max_price=max_price,
    locations=locations,
    selected_location=selected_location,
    in_stock_only=in_stock_only
)




@app.route("/reserve/<int:product_id>", methods=["POST"])
def reserve_product(product_id):
    if "user_id" not in session or session.get("user_role") != "customer":
        flash("Please log in as a customer to reserve products.")
        return redirect(url_for("login"))
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM products
        WHERE id = ?
    """, (product_id,))

    product = cursor.fetchone()

    if product is None:
        connection.close()
        return "Product not found."

    if product["stock"] <= 0:
        connection.close()
        return "Sorry, this product is out of stock."

    cursor.execute("""
        UPDATE products
        SET stock = stock - 1
        WHERE id = ? AND stock > 0
    """, (product["id"],))

    if cursor.rowcount == 0:
        connection.close()
        return "Sorry, this product is out of stock."

    reservation_date = datetime.now().strftime(
        "%d-%m-%Y %I:%M %p"
    )

    cursor.execute("""
        INSERT INTO reservations
        (user_id, product_id, product, price, shop, location, status, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        product["id"],
        product["name"],
        product["price"],
        product["shop"],
        product["location"],
        "Confirmed",
        reservation_date
    ))

    reservation_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return redirect(
        url_for(
            "reservation_details",
            reservation_id=reservation_id
        )
    )



@app.route("/bargain/<int:product_id>", methods=["POST"])
def submit_bargain(product_id):

    if "user_id" not in session or session.get("user_role") != "customer":
        flash("Please log in as a customer to make an offer.")
        return redirect(url_for("login"))

    try:
        offered_price = float(request.form.get("offered_price", ""))
        if offered_price <= 0:
            raise ValueError
    except ValueError:
        flash("Please enter a valid offer price.")
        return redirect(url_for("search"))

    message = request.form.get("message", "").strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, price, owner_id, stock
FROM products
WHERE id = ?
    """, (product_id,))

    product = cursor.fetchone()

    if product is None or product["owner_id"] is None:
        connection.close()
        flash("This product is not available for bargaining.")
        return redirect(url_for("search"))

    if product["stock"] <= 0:
        connection.close()
        flash("Sorry, this product is out of stock and cannot receive offers.")
        return redirect(url_for("search"))

    if offered_price >= product["price"]:
        connection.close()
        flash("Your offer must be lower than the listed price.")
        return redirect(url_for("search"))

    created_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    cursor.execute("""
        INSERT INTO bargaining_requests
        (product_id, customer_id, shopkeeper_id, offered_price,
         message, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        product_id,
        session["user_id"],
        product["owner_id"],
        offered_price,
        message,
        "Pending",
        created_at
    ))

    connection.commit()
    connection.close()

    flash("Your price offer has been sent to the shopkeeper.")
    return redirect(url_for("search"))



@app.route("/reservation/<int:reservation_id>")
def reservation_details(reservation_id):
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    if session.get("user_role") == "admin":
        cursor.execute("""
            SELECT * FROM reservations
            WHERE id = ?
        """, (reservation_id,))
    elif session.get("user_role") == "customer":
        cursor.execute("""
            SELECT * FROM reservations
            WHERE id = ? AND user_id = ?
        """, (reservation_id, session["user_id"]))
    else:
        connection.close()
        return "Access denied.", 403

    reservation = cursor.fetchone()
    connection.close()

    if reservation is None:
        return "Reservation not found or access denied.", 404

    return render_template(
        "reservation.html",
        reservation=reservation
    )


@app.route("/my-reservations")
def my_reservations():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if session.get("user_role") not in ("customer", "admin"):
        return "Access denied.", 403

    connection = get_connection()
    cursor = connection.cursor()

    if session.get("user_role") == "admin":
        cursor.execute("""
            SELECT * FROM reservations
            ORDER BY id DESC
        """)
    else:
        cursor.execute("""
            SELECT * FROM reservations
            WHERE user_id = ?
            ORDER BY id DESC
        """, (session["user_id"],))

    reservations = cursor.fetchall()
    connection.close()

    return render_template(
        "reservations.html",
        reservations=reservations
    )




@app.route("/admin/customers")
def admin_customers():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    # Search and pagination settings
    search_query = request.args.get("search", "").strip()

    per_page = 10

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    connection = get_connection()
    cursor = connection.cursor()

    # Count matching customers
    if search_query:
        search_term = f"%{search_query}%"

        cursor.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'customer'
            AND (
                name LIKE ?
                OR username LIKE ?
                OR email LIKE ?
            )
        """, (search_term, search_term, search_term))

    else:
        cursor.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'customer'
        """)

    total_customers = cursor.fetchone()[0]

    # Calculate total pages
    total_pages = max(1, (total_customers + per_page - 1) // per_page)

    # Keep requested page within valid range
    page = min(page, total_pages)

    offset = (page - 1) * per_page

    # Fetch customers for the current page
    if search_query:
        cursor.execute("""
            SELECT id, name, username, email, created_at
            FROM users
            WHERE role = 'customer'
            AND (
                name LIKE ?
                OR username LIKE ?
                OR email LIKE ?
            )
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (
            search_term,
            search_term,
            search_term,
            per_page,
            offset
        ))

    else:
        cursor.execute("""
            SELECT id, name, username, email, created_at
            FROM users
            WHERE role = 'customer'
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

    customers = cursor.fetchall()

    connection.close()

    return render_template(
        "admin_customers.html",
        customers=customers,
        search_query=search_query,
        total_customers=total_customers,
        page=page,
        total_pages=total_pages
    )






@app.route("/admin/shopkeepers")
def admin_shopkeepers():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    # Search and pagination
    search_query = request.args.get("search", "").strip()

    per_page = 10

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    connection = get_connection()
    cursor = connection.cursor()

    # Count matching shopkeepers
    if search_query:
        search_term = f"%{search_query}%"

        cursor.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'shopkeeper'
            AND (
                name LIKE ?
                OR username LIKE ?
                OR email LIKE ?
            )
        """, (search_term, search_term, search_term))

    else:
        cursor.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'shopkeeper'
        """)

    total_shopkeepers = cursor.fetchone()[0]

    # Calculate pagination
    total_pages = max(
        1,
        (total_shopkeepers + per_page - 1) // per_page
    )

    page = min(page, total_pages)

    offset = (page - 1) * per_page

    # Fetch current page
    if search_query:
        cursor.execute("""
            SELECT id, name, username, email, created_at
            FROM users
            WHERE role = 'shopkeeper'
            AND (
                name LIKE ?
                OR username LIKE ?
                OR email LIKE ?
            )
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (
            search_term,
            search_term,
            search_term,
            per_page,
            offset
        ))

    else:
        cursor.execute("""
            SELECT id, name, username, email, created_at
            FROM users
            WHERE role = 'shopkeeper'
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

    shopkeepers = cursor.fetchall()

    connection.close()

    return render_template(
        "admin_shopkeepers.html",
        shopkeepers=shopkeepers,
        search_query=search_query,
        total_shopkeepers=total_shopkeepers,
        page=page,
        total_pages=total_pages
    )


@app.route("/admin/shopkeepers/delete/<int:shopkeeper_id>", methods=["POST"])
def delete_shopkeeper(shopkeeper_id):

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Verify that the account exists and is a shopkeeper
        cursor.execute("""
            SELECT id FROM users
            WHERE id = ? AND role = 'shopkeeper'
        """, (shopkeeper_id,))

        shopkeeper = cursor.fetchone()

        if not shopkeeper:
            flash("Shopkeeper account not found.")
            connection.rollback()
            return redirect(url_for("admin_shopkeepers"))

        # Find products owned by this shopkeeper
        cursor.execute("""
            SELECT id FROM products
            WHERE owner_id = ?
        """, (shopkeeper_id,))

        products = cursor.fetchall()
        product_ids = [product["id"] for product in products]

        # Delete reservations associated with those products
        if product_ids:
            placeholders = ",".join("?" for _ in product_ids)

            cursor.execute(f"""
                DELETE FROM reservations
                WHERE product_id IN ({placeholders})
            """, product_ids)

        # Delete shopkeeper's products
        cursor.execute("""
            DELETE FROM products
            WHERE owner_id = ?
        """, (shopkeeper_id,))

        # Delete shopkeeper's shops
        cursor.execute("""
            DELETE FROM shops
            WHERE owner_id = ?
        """, (shopkeeper_id,))

        # Delete the shopkeeper account
        cursor.execute("""
            DELETE FROM users
            WHERE id = ? AND role = 'shopkeeper'
        """, (shopkeeper_id,))

        connection.commit()
        flash("Shopkeeper account deleted successfully.")

    except Exception as e:
        connection.rollback()
        print("Shopkeeper deletion error:", e)
        flash("Unable to delete shopkeeper account.")

    finally:
        connection.close()

    return redirect(url_for("admin_shopkeepers"))



@app.route("/admin/shops")
def admin_shops():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    # Search and pagination settings
    search_query = request.args.get("search", "").strip()
    per_page = 5

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    connection = get_connection()
    cursor = connection.cursor()

    # Count matching shops
    if search_query:
        search_term = f"%{search_query}%"

        cursor.execute("""
            SELECT COUNT(*)
            FROM shops
            LEFT JOIN users ON shops.owner_id = users.id
            WHERE shops.shop_name LIKE ?
               OR users.name LIKE ?
               OR users.email LIKE ?
               OR shops.location LIKE ?
        """, (search_term, search_term, search_term, search_term))

    else:
        cursor.execute("SELECT COUNT(*) FROM shops")

    total_shops = cursor.fetchone()[0]

    # Calculate pagination
    total_pages = max(1, (total_shops + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    # Fetch shops for the current page
    if search_query:
        cursor.execute("""
            SELECT
                shops.id,
                shops.shop_name,
                shops.address,
                shops.location,
                shops.description,
                users.name AS owner_name,
                users.email AS owner_email
            FROM shops
            LEFT JOIN users ON shops.owner_id = users.id
            WHERE shops.shop_name LIKE ?
               OR users.name LIKE ?
               OR users.email LIKE ?
               OR shops.location LIKE ?
            ORDER BY shops.id DESC
            LIMIT ? OFFSET ?
        """, (
            search_term, search_term, search_term, search_term,
            per_page, offset
        ))

    else:
        cursor.execute("""
            SELECT
                shops.id,
                shops.shop_name,
                shops.address,
                shops.location,
                shops.description,
                users.name AS owner_name,
                users.email AS owner_email
            FROM shops
            LEFT JOIN users ON shops.owner_id = users.id
            ORDER BY shops.id DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

    shops = cursor.fetchall()
    connection.close()

    return render_template(
        "admin_shops.html",
        shops=shops,
        total_shops=total_shops,
        search_query=search_query,
        page=page,
        total_pages=total_pages
    )







@app.route("/admin/products")
def admin_products():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    search_query = request.args.get("search", "").strip()
    selected_category = request.args.get("category", "").strip()
    stock_filter = request.args.get("stock", "all").strip()

    if stock_filter not in ["all", "in_stock", "out_of_stock"]:
        stock_filter = "all"

    per_page = 5

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    connection = get_connection()
    cursor = connection.cursor()

    # Build filters
    conditions = []
    params = []

    if search_query:
        search_term = f"%{search_query}%"

        conditions.append("""
            (
                products.name LIKE ?
                OR products.category LIKE ?
                OR products.shop LIKE ?
                OR products.location LIKE ?
                OR users.name LIKE ?
            )
        """)

        params.extend([
            search_term, search_term, search_term,
            search_term, search_term
        ])

    if selected_category:
        conditions.append("products.category = ?")
        params.append(selected_category)

    if stock_filter == "in_stock":
        conditions.append("products.stock > 0")

    elif stock_filter == "out_of_stock":
        conditions.append("products.stock = 0")

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Count matching products
    cursor.execute(f"""
        SELECT COUNT(*)
        FROM products
        LEFT JOIN users ON products.owner_id = users.id
        {where_clause}
    """, params)

    total_products = cursor.fetchone()[0]

    total_pages = max(1, (total_products + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    # Fetch matching products
    cursor.execute(f"""
        SELECT
            products.id,
            products.name,
            products.category,
            products.price,
            products.shop,
            products.location,
            products.stock,
            users.name AS owner_name
        FROM products
        LEFT JOIN users ON products.owner_id = users.id
        {where_clause}
        ORDER BY products.id DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    products = cursor.fetchall()

    # Get available categories
    cursor.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL AND category != ''
        ORDER BY category
    """)

    categories = [row[0] for row in cursor.fetchall()]

    connection.close()

    return render_template(
        "admin_products.html",
        products=products,
        total_products=total_products,
        search_query=search_query,
        selected_category=selected_category,
        stock_filter=stock_filter,
        categories=categories,
        page=page,
        total_pages=total_pages
    )



@app.route("/admin/categories")
def admin_categories():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name
        FROM categories
        ORDER BY name
    """)

    categories = cursor.fetchall()

    connection.close()

    return render_template(
        "admin_categories.html",
        categories=categories
    )



@app.route("/admin/analytics")
def admin_analytics():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'shopkeeper'")
    total_shopkeepers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shops")
    total_shops = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reservations")
    total_reservations = cursor.fetchone()[0]

    cursor.execute("""
        SELECT status, COUNT(*) AS total
        FROM reservations
        GROUP BY status
    """)
    reservation_stats = cursor.fetchall()

    cursor.execute("""
        SELECT category, COUNT(*) AS total
        FROM products
        GROUP BY category
        ORDER BY total DESC
    """)
    category_stats = cursor.fetchall()

    connection.close()

    return render_template(
        "admin_analytics.html",
        total_customers=total_customers,
        total_shopkeepers=total_shopkeepers,
        total_shops=total_shops,
        total_products=total_products,
        total_reservations=total_reservations,
        reservation_stats=reservation_stats,
        category_stats=category_stats
    )



@app.route("/admin/categories/add", methods=["POST"])
def add_category():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    category_name = request.form.get("category_name", "").strip()

    if not category_name:
        flash("Category name cannot be empty.")
        return redirect(url_for("admin_categories"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO categories (name)
            VALUES (?)
        """, (category_name,))

        connection.commit()
        flash("Category added successfully.")

    except sqlite3.IntegrityError:
        flash("This category already exists.")

    finally:
        connection.close()

    return redirect(url_for("admin_categories"))



@app.route("/admin/categories/edit/<int:category_id>", methods=["POST"])
def edit_category(category_id):

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    new_name = request.form.get("category_name", "").strip()

    if not new_name:
        flash("Category name cannot be empty.")
        return redirect(url_for("admin_categories"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT name FROM categories WHERE id = ?",
        (category_id,)
    )
    category = cursor.fetchone()

    if category is None:
        connection.close()
        flash("Category not found.")
        return redirect(url_for("admin_categories"))

    old_name = category["name"]

    try:
        cursor.execute(
            "UPDATE categories SET name = ? WHERE id = ?",
            (new_name, category_id)
        )

        cursor.execute(
            "UPDATE products SET category = ? WHERE category = ?",
            (new_name, old_name)
        )

        connection.commit()
        flash("Category updated successfully.")

    except sqlite3.IntegrityError:
        connection.rollback()
        flash("This category name already exists.")

    finally:
        connection.close()

    return redirect(url_for("admin_categories"))



@app.route("/admin/categories/delete/<int:category_id>", methods=["POST"])
def delete_category(category_id):

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT name FROM categories WHERE id = ?",
        (category_id,)
    )
    category = cursor.fetchone()

    if category is None:
        flash("Category not found.")
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM products WHERE category = ?",
            (category["name"],)
        )
        product_count = cursor.fetchone()[0]

        if product_count > 0:
            flash("Cannot delete this category because products are using it.")
        else:
            cursor.execute(
                "DELETE FROM categories WHERE id = ?",
                (category_id,)
            )
            connection.commit()
            flash("Category deleted successfully.")

    connection.close()
    return redirect(url_for("admin_categories"))


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
def delete_admin_product(product_id):

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    # Check whether the product exists
    cursor.execute(
        "SELECT id FROM products WHERE id = ?",
        (product_id,)
    )
    product = cursor.fetchone()

    if product is None:
        connection.close()
        flash("Product not found.")
        return redirect(url_for("admin_products"))

    # Delete reservations linked to this product
    cursor.execute(
        "DELETE FROM reservations WHERE product_id = ?",
        (product_id,)
    )

    # Delete the product
    cursor.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    connection.commit()
    connection.close()

    flash("Product and its related reservations deleted successfully.")

    return redirect(url_for("admin_products"))



@app.route("/admin/reservations/update/<int:reservation_id>", methods=["POST"])
def update_reservation_status(reservation_id):

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    new_status = request.form.get("status", "").strip()

    allowed_statuses = ["Confirmed", "Cancelled"]

    if new_status not in allowed_statuses:
        flash("Invalid reservation status.")
        return redirect(url_for("admin_reservations"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE reservations
        SET status = ?
        WHERE id = ?
    """, (new_status, reservation_id))

    connection.commit()
    connection.close()

    flash("Reservation status updated successfully.")

    return redirect(url_for("admin_reservations"))



@app.route("/admin/reservations")
def admin_reservations():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    search_query = request.args.get("search", "").strip()

    connection = get_connection()
    cursor = connection.cursor()

    if search_query:
        search_term = f"%{search_query}%"

        cursor.execute("""
            SELECT COUNT(*)
            FROM reservations
            LEFT JOIN users ON reservations.user_id = users.id
            WHERE users.name LIKE ?
               OR users.email LIKE ?
               OR reservations.product LIKE ?
               OR reservations.shop LIKE ?
               OR reservations.location LIKE ?
               OR reservations.status LIKE ?
        """, (
            search_term, search_term, search_term,
            search_term, search_term, search_term
        ))
    else:
        cursor.execute("SELECT COUNT(*) FROM reservations")

    total_reservations = cursor.fetchone()[0]

    if search_query:
        cursor.execute("""
            SELECT
                reservations.id,
                reservations.product,
                reservations.price,
                reservations.shop,
                reservations.location,
                reservations.status,
                reservations.date,
                users.name AS customer_name,
                users.email AS customer_email
            FROM reservations
            LEFT JOIN users ON reservations.user_id = users.id
            WHERE users.name LIKE ?
               OR users.email LIKE ?
               OR reservations.product LIKE ?
               OR reservations.shop LIKE ?
               OR reservations.location LIKE ?
               OR reservations.status LIKE ?
            ORDER BY reservations.id DESC
        """, (
            search_term, search_term, search_term,
            search_term, search_term, search_term
        ))
    else:
        cursor.execute("""
            SELECT
                reservations.id,
                reservations.product,
                reservations.price,
                reservations.shop,
                reservations.location,
                reservations.status,
                reservations.date,
                users.name AS customer_name,
                users.email AS customer_email
            FROM reservations
            LEFT JOIN users ON reservations.user_id = users.id
            ORDER BY reservations.id DESC
        """)

    reservations = cursor.fetchall()
    connection.close()

    return render_template(
        "admin_reservations.html",
        reservations=reservations,
        total_reservations=total_reservations,
        search_query=search_query
    )




@app.route("/admin/shops/delete/<int:shop_id>", methods=["POST"])
def delete_shop(shop_id):

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Find the selected shop
        cursor.execute("""
            SELECT id, shop_name, owner_id
            FROM shops
            WHERE id = ?
        """, (shop_id,))

        shop = cursor.fetchone()

        if not shop:
            flash("Shop not found.")
            return redirect(url_for("admin_shops"))

        # Find products belonging to this shop and owner
        cursor.execute("""
            SELECT id FROM products
            WHERE owner_id = ? AND shop = ?
        """, (shop["owner_id"], shop["shop_name"]))

        products = cursor.fetchall()
        product_ids = [product["id"] for product in products]

        # Delete reservations associated with those products
        if product_ids:
            placeholders = ",".join("?" for _ in product_ids)

            cursor.execute(f"""
                DELETE FROM reservations
                WHERE product_id IN ({placeholders})
            """, product_ids)

        # Delete the shop's products
        cursor.execute("""
            DELETE FROM products
            WHERE owner_id = ? AND shop = ?
        """, (shop["owner_id"], shop["shop_name"]))

        # Delete only the selected shop
        cursor.execute("""
            DELETE FROM shops
            WHERE id = ?
        """, (shop_id,))

        connection.commit()
        flash("Shop and its associated products and reservations deleted successfully.")

    except Exception as e:
        connection.rollback()
        print("Shop deletion error:", e)
        flash("Unable to delete shop.")

    finally:
        connection.close()

    return redirect(url_for("admin_shops"))




@app.route("/admin/customers/delete/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM users
        WHERE id = ? AND role = 'customer'
    """, (customer_id,))

    if cursor.rowcount > 0:
        flash("Customer account deleted successfully.")
    else:
        flash("Customer account not found.")

    connection.commit()
    connection.close()

    return redirect(url_for("admin_customers"))



@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():

    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("admin_login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS platform_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            platform_name TEXT NOT NULL,
            contact_email TEXT,
            support_phone TEXT
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO platform_settings
        (id, platform_name, contact_email, support_phone)
        VALUES (1, 'ShopNear AI', '', '')
    """)

    if request.method == "POST":
        platform_name = request.form.get("platform_name", "").strip()
        contact_email = request.form.get("contact_email", "").strip()
        support_phone = request.form.get("support_phone", "").strip()

        if not platform_name:
            flash("Platform name cannot be empty.")
        else:
            cursor.execute("""
                UPDATE platform_settings
                SET platform_name = ?,
                    contact_email = ?,
                    support_phone = ?
                WHERE id = 1
            """, (platform_name, contact_email, support_phone))

            connection.commit()
            flash("Settings updated successfully.")

    cursor.execute("""
        SELECT * FROM platform_settings WHERE id = 1
    """)
    settings = cursor.fetchone()

    connection.close()

    return render_template(
        "admin_settings.html",
        settings=settings
    )


@app.route("/shopkeeper/offers")
def shopkeeper_offers():

    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            bargaining_requests.*,
            products.name AS product_name,
            products.price AS listed_price,
            users.name AS customer_name,
            users.email AS customer_email
        FROM bargaining_requests
        JOIN products
            ON bargaining_requests.product_id = products.id
        JOIN users
            ON bargaining_requests.customer_id = users.id
        WHERE bargaining_requests.shopkeeper_id = ?
        ORDER BY bargaining_requests.id DESC
    """, (session["user_id"],))

    offers = cursor.fetchall()

    connection.close()

    return render_template(
        "shopkeeper_offers.html",
        offers=offers
    )




@app.route("/shopkeeper/offers/<int:offer_id>/update", methods=["POST"])
def update_bargaining_offer(offer_id):

    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    new_status = request.form.get("status")

    if new_status not in ["Accepted", "Rejected"]:
        flash("Invalid offer status.")
        return redirect(url_for("shopkeeper_offers"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        connection.execute("BEGIN IMMEDIATE")

        cursor.execute("""
            SELECT
                bargaining_requests.*,
                products.name AS product_name,
                products.price AS listed_price,
                products.shop,
                products.location,
                products.stock
            FROM bargaining_requests
            JOIN products
                ON bargaining_requests.product_id = products.id
            WHERE bargaining_requests.id = ?
              AND bargaining_requests.shopkeeper_id = ?
              AND bargaining_requests.status = 'Pending'
        """, (offer_id, session["user_id"]))

        offer = cursor.fetchone()

        if offer is None:
            connection.rollback()
            flash("Offer not found or already processed.")
            return redirect(url_for("shopkeeper_offers"))

        if new_status == "Accepted":

            if offer["stock"] <= 0:
                connection.rollback()
                flash("This product is out of stock.")
                return redirect(url_for("shopkeeper_offers"))

            cursor.execute("""
                UPDATE products
                SET stock = stock - 1
                WHERE id = ? AND stock > 0
            """, (offer["product_id"],))

            if cursor.rowcount == 0:
                connection.rollback()
                flash("Product is out of stock.")
                return redirect(url_for("shopkeeper_offers"))

            cursor.execute("""
                INSERT INTO reservations
                (user_id, product_id, product, price, shop,
                 location, status, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                offer["customer_id"],
                offer["product_id"],
                offer["product_name"],
                offer["offered_price"],
                offer["shop"],
                offer["location"],
                "Confirmed",
                datetime.now().strftime("%d-%m-%Y %I:%M %p")
            ))

        cursor.execute("""
            UPDATE bargaining_requests
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            datetime.now().strftime("%d-%m-%Y %I:%M %p"),
            offer_id
        ))

        connection.commit()

        flash(
            "Offer accepted and reservation confirmed!"
            if new_status == "Accepted"
            else "Offer rejected successfully."
        )

    except Exception:
        connection.rollback()
        flash("Something went wrong while processing the offer.")

    finally:
        connection.close()

    return redirect(url_for("shopkeeper_offers"))


@app.route("/customer/offers")
def customer_offers():

    if "user_id" not in session or session.get("user_role") != "customer":
        flash("Customer access required.")
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            bargaining_requests.*,
            products.name AS product_name,
            products.price AS listed_price,
            shopkeepers.name AS shopkeeper_name
        FROM bargaining_requests
        JOIN products
            ON bargaining_requests.product_id = products.id
        JOIN users AS shopkeepers
            ON bargaining_requests.shopkeeper_id = shopkeepers.id
        WHERE bargaining_requests.customer_id = ?
        ORDER BY bargaining_requests.id DESC
    """, (session["user_id"],))

    offers = cursor.fetchall()

    connection.close()

    return render_template(
        "customer_offers.html",
        offers=offers
    )



@app.route("/customer/offers/<int:offer_id>/respond", methods=["POST"])
def respond_to_counteroffer(offer_id):

    if "user_id" not in session or session.get("user_role") != "customer":
        flash("Customer access required.")
        return redirect(url_for("login"))

    response = request.form.get("response", "").strip()

    if response not in ["Accepted", "Rejected"]:
        flash("Invalid response.")
        return redirect(url_for("customer_offers"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("""
            SELECT
                bargaining_requests.id,
                bargaining_requests.product_id,
                bargaining_requests.customer_id,
                bargaining_requests.counter_price,
                bargaining_requests.status,
                products.name AS product_name,
                products.shop,
                products.location,
                products.stock
            FROM bargaining_requests
            JOIN products
                ON bargaining_requests.product_id = products.id
            WHERE bargaining_requests.id = ?
              AND bargaining_requests.customer_id = ?
        """, (offer_id, session["user_id"]))

        offer = cursor.fetchone()

        if offer is None or offer["status"] != "Countered" or offer["counter_price"] is None:
            connection.rollback()
            flash("Counteroffer not found or already processed.")
            return redirect(url_for("customer_offers"))

        updated_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")

        if response == "Rejected":

            cursor.execute("""
                UPDATE bargaining_requests
                SET status = 'Rejected by Customer',
                    updated_at = ?
                WHERE id = ? AND customer_id = ? AND status = 'Countered'
            """, (updated_at, offer_id, session["user_id"]))

            connection.commit()
            flash("You rejected the shopkeeper's counteroffer.")

        else:

            cursor.execute("""
                UPDATE products
                SET stock = stock - 1
                WHERE id = ? AND stock > 0
            """, (offer["product_id"],))

            if cursor.rowcount == 0:
                connection.rollback()
                flash("Sorry, this product is out of stock.")
                return redirect(url_for("customer_offers"))

            reservation_date = updated_at

            cursor.execute("""
                INSERT INTO reservations
                (user_id, product_id, product, price, shop, location, status, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session["user_id"],
                offer["product_id"],
                offer["product_name"],
                offer["counter_price"],
                offer["shop"],
                offer["location"],
                "Confirmed",
                reservation_date
            ))

            cursor.execute("""
                UPDATE bargaining_requests
                SET status = 'Agreed',
                    updated_at = ?
                WHERE id = ? AND customer_id = ? AND status = 'Countered'
            """, (updated_at, offer_id, session["user_id"]))

            connection.commit()
            flash("Counteroffer accepted! Your reservation is confirmed.")

    except Exception:
        connection.rollback()
        flash("Something went wrong. Please try again.")

    finally:
        connection.close()

    return redirect(url_for("customer_offers"))


@app.route("/shopkeeper/offers/<int:offer_id>/counter", methods=["POST"])
def submit_counteroffer(offer_id):

    if "user_id" not in session or session.get("user_role") != "shopkeeper":
        flash("Shopkeeper access required.")
        return redirect(url_for("login"))

    try:
        counter_price = float(request.form.get("counter_price", ""))

        if counter_price <= 0:
            raise ValueError

    except ValueError:
        flash("Please enter a valid counteroffer price.")
        return redirect(url_for("shopkeeper_offers"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            bargaining_requests.offered_price,
            bargaining_requests.status,
            products.price AS listed_price
        FROM bargaining_requests
        JOIN products
            ON bargaining_requests.product_id = products.id
        WHERE bargaining_requests.id = ?
          AND bargaining_requests.shopkeeper_id = ?
    """, (offer_id, session["user_id"]))

    offer = cursor.fetchone()

    if offer is None or offer["status"] != "Pending":
        connection.close()
        flash("Offer not found or no longer pending.")
        return redirect(url_for("shopkeeper_offers"))

    if not offer["offered_price"] < counter_price < offer["listed_price"]:
        connection.close()
        flash("Counteroffer must be higher than the customer's offer and lower than the listed price.")
        return redirect(url_for("shopkeeper_offers"))

    updated_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    cursor.execute("""
        UPDATE bargaining_requests
        SET counter_price = ?,
            status = 'Countered',
            updated_at = ?
        WHERE id = ?
          AND shopkeeper_id = ?
          AND status = 'Pending'
    """, (
        counter_price,
        updated_at,
        offer_id,
        session["user_id"]
    ))

    connection.commit()
    connection.close()

    flash("Your counteroffer has been sent to the customer.")
    return redirect(url_for("shopkeeper_offers"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
