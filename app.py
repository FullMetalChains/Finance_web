import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("stockapi"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    row1 = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    row2 = db.execute("SELECT * FROM stocks WHERE user_id = ? ", session["user_id"])
    stockprice = {}
    stockname = {}
    stocktotal = {}
    total = row1[0]['cash']
    for row in row2 :
        stock = lookup(row["stock"])
        stockprice[row["stock"]] = stock['price']
        stockname[row["stock"]] = stock['name']
        stocktotal[row["stock"]] = (stock['price']*row['number'])
        total += stock['price']*row['number']
    return render_template("index.html", row1 = row1[0]['cash'], row2= row2, stockprice = stockprice, stockname= stockname, total = stocktotal, ttotal = total)


@app.route("/cash", methods =["GET", "POST"])
@login_required
def cash():
    if request.method == "POST":
        user_id = session["user_id"]
        cash = int(request.form.get("cash"))
        og_cash_list = db.execute("SELECT cash FROM users WhERE id = ?", user_id)
        og_cash = int(og_cash_list[0]['cash'])
        new_cash = cash + og_cash
        log = "You added $%d cash to your account"%(cash)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_cash, user_id)
        db.execute("INSERT INTO log (user_id, log) VALUES (?,?)", user_id, log)
        return redirect("/")
    else:
        return render_template("cash.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        stock = lookup(request.form.get("stockname"))
        if not stock:
            return apology("Enter Valid Stock Name", 403)
        number = int(request.form.get("stocknumber"))
        if number <= 0:
            return apology("Enter valid number of stocks")
        price = stock["price"] * number
        user_id = session["user_id"]
        rows = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cash = int(rows[0]["cash"])
        symbol = stock["symbol"]
        if price > cash:
            return apology("You do not have enough money to complete the transaction")
        exist = db.execute("SELECT number FROM stocks WHERE user_id = ? AND stock = ?", user_id, symbol)
        log = "You bought %d stocks of %s"%(number, symbol)
        db.execute("INSERT INTO log (user_id, log) VALUES (?,?)", user_id, log)
        if(not exist):
            db.execute("INSERT INTO stocks (user_id, stock, number) VALUES (?, ?, ?)", user_id, symbol, number)
        else:
            new_num = exist[0]['number'] + number
            db.execute("UPDATE stocks SET number = ? WHERE user_id = ? AND stock = ?", new_num, user_id, symbol)
        new_cash = cash - price
        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_cash, user_id)

        return redirect("/")
    else:
        return render_template("buyform.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    row = db.execute("SELECT log FROM log WHERE user_id = ?", session["user_id"])
    print(row)
    return render_template("history.html", row= row)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        bros = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        stock = lookup(request.form.get("stockname"))
        if not stock:
            return apology("Enter Valid Stock Name", 403)

        name = stock["name"]
        price = stock["price"]
        symbol = stock["symbol"]

        return render_template("quote.html", name = name, price = price, symbol = symbol)
    else:
        return render_template("quoteform.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirmpassword")
     # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

     # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
     # Ensure Password and confirmation was same
        elif password != confirm:
            return apology("Password and Confirm Password doesn't match", 403)
     # Check if given username already exists
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 0:
            return apology("This username already exists. Please try another one", 403)
     # Insert username and password into database as new user
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
     # Remember User logged in
        bros = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
        session["user_id"] = bros[0]["id"]
     # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        user_id = session["user_id"]
        stock = lookup(request.form.get("stockname"))
        print(stock)
        if not stock:
            return apology("Enter Valid Stock Name", 403)
        number = int(request.form.get("stocknumber"))
        nstocklist = db.execute("SELECT number FROM stocks WHERE user_id = ? AND stock = ? ", user_id, stock["symbol"])
        nstock = nstocklist[0]['number']
        print(nstock)
        if number <= 0 or number > nstock:
            return apology("Enter valid number of stocks")
        price = stock["price"] * number
        rows = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cash = int(rows[0]["cash"])
        symbol = stock["symbol"]
        new_cash = cash + price
        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_cash, user_id)
        nstock = nstock - number
        log = "You sold %d stocks of %s"%(number, symbol)
        db.execute("INSERT INTO log (user_id, log) VALUES (?,?)", user_id, log)
        if nstock != 0:
            db.execute("UPDATE stocks SET number = ? WHERE user_id = ? AND stock = ?", nstock, user_id, stock["symbol"])
        else:
            db.execute("DELETE FROM stocks WHERE user_id = ? AND stock = ?", user_id, stock["symbol"])
        return redirect("/")
    else:
        return render_template("sellform.html")
