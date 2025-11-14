import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import datetime as dt

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


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
    db.execute("DELETE FROM purchases WHERE shares = ?", [0])
    data = db.execute("SELECT symbol, SUM(shares) AS shares FROM purchases WHERE user_id = ? GROUP BY symbol", session["user_id"])
    holding = []
    for row in data:
        stock = lookup(row["symbol"])
        total_value = row["shares"]  *  stock["price"]
        holding.append({"Symbol": row["symbol"],
                        "Shares": row["shares"],
                        "Price": stock["price"],
                        "Total_Value":  total_value})
    grand_total = sum(item["Total_Value"] for item in holding)

    cash_query = db.execute("SELECT cash FROM users WHERE id = ?" , session["user_id"])
    cash = cash_query[0]["cash"]
    final = cash + grand_total
    return render_template("index.html", holding=holding, cash=cash, total=final)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        try:

            symbol = request.form.get("symbol").upper()
            if not symbol:
                return apology("Please Provide Correct Symbol")
            shares = request.form.get("shares")
            if not shares or not shares.strip() or not shares.strip().isdigit() or int(shares.strip()) <= 0:
                return apology("Please choose the number of shares correctly")
            shares = int(shares.strip())
            data = lookup(symbol)
            if not data:
                return apology("Please Provide Correct Symbol")
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            if cash[0]['cash'] < (shares * data["price"]):
                return apology("You don't have enough money to buy that number of shares")
            new_cash = cash[0]['cash'] - (shares * data["price"])
            db.execute("INSERT INTO purchases (user_id, shares, price, symbol) VALUES(?,?,?,?)", session["user_id"], shares, data["price"], data["symbol"])
            db.execute("UPDATE users SET cash = ? WHERE id = ?", new_cash, session["user_id"])
            date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            transaction_type = "Buy"
            price = data["price"]
            db.execute("INSERT INTO transactions (user_id, transaction_type, symbol, shares, price, timestamp) VALUES (?,?,?,?,?,?)",  session["user_id"], transaction_type, data["symbol"], shares, price, date)
            return redirect("/")
        except Exception as e:
            return apology(f"Error: {str(e)}")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    data = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC", session["user_id"])
    return render_template("history.html", data=data)

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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
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

@app.route("/suggest", methods=["POST"])
def sug():
    data = request.get_json()
    username_input = data.get("input")
    print(f"Searching for usernames with: {username_input}")
    
    if username_input: 
        # Proper parameterized query with wildcards
        search_term = f'%{username_input}%'
        result = db.execute("SELECT username FROM users WHERE username LIKE ? ORDER BY username", search_term)
    else:
        result = []
    
    print(f"Found {len(result)} results: {result}")
    return jsonify(result)


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Please provide symbol")
        data = lookup(symbol)
        if not data:
            return apology("Please provide correct symbol")
        return render_template("quoted.html", data=data)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirmation")
        hashed = generate_password_hash(password)
        taken = db.execute("SELECT username FROM users WHERE username = ?", username)
        if not username:
            return apology("Please profide username")
        if len(taken) > 0:
            return apology("Sorry username taken")
        if not password:
            return apology("Please profide password")
        if confirm != password:
            return apology("Sorry Password dont match")
        try:
              db.execute("INSERT INTO users (username, hash) VALUES (?,?)", username, hashed)
        except ValueError:
            return apology("Sorry username taken")

        flash("Registered successfully!")
        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        own_shares = db.execute("SELECT symbol FROM purchases WHERE user_id = ?", session["user_id"])
        shares = request.form.get("shares")

        if not symbol:
            return apology("please choose a symbol")
        if symbol not in [row["symbol"] for row in own_shares]:
            return apology("Sorry you dont own shares from that company")

        if not shares:
            return apology("Please provide shares")
        shares = int(shares)
        if shares <= 0:
            return apology("Sorry shares has to be possitive intgere and greater than 0")

        total_shares = db.execute("SELECT SUM(shares) AS shares FROM purchases WHERE user_id = ? and symbol = ?", session["user_id"], symbol)
        if not total_shares:
            return apology("You don’t own any shares from this company")

        if shares > int(total_shares[0]["shares"]):
            return apology("You don’t have enough shares to sell from this company")
        final_shares = total_shares[0]["shares"] - shares
        db.execute("UPDATE purchases SET shares = ? WHERE user_id = ? and symbol = ?" , final_shares, session["user_id"], symbol)
        data = lookup(symbol)
        price = data["price"]
        final_cash = shares * price
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = cash[0]["cash"] + final_cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
        date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        transaction_type = "Sell"
        db.execute("INSERT INTO transactions (user_id, transaction_type, symbol, shares, price, timestamp) VALUES (?,?,?,?,?,?)", session["user_id"], transaction_type, data["symbol"], shares, price, date)
        return redirect("/")
    else:
        options = db.execute("SELECT symbol FROM purchases WHERE user_id = ?", session["user_id"])
        return render_template("sell.html", options=options)



@app.route("/add_cash", methods= ["GET", "POST"])
@login_required
def cash():
    if request.method == "POST":
        new_cash = request.form.get("add_cash")

        if not new_cash:
            return apology("Pleas add cash")
        new_cash = float(new_cash)
        if new_cash <= 0:
            return apology("Pleas add cash")
        db.execute(" update users set cash = cash + ? where id = ?", new_cash, session["user_id"])
        return redirect("/")
    else:
        return render_template("add_cash.html")

