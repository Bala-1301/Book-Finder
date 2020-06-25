import os, json, requests, hashlib
from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from configKeys import configKey

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
key = configKey["apikey"]
password_key = configKey["password_key"]

@app.route("/", methods=["POST","GET"])
def index():
    if request.method == "POST":
        if(request.method == "POST"):
            email = request.form.get("email")
            if db.execute("SELECT * FROM users WHERE email=:email", {'email': email}).rowcount == 0:
                return render_template("index.html", error_msg="Mail-id doesn't exist.")
            password = request.form.get("password")
            password += password_key
            encodedPassword = hashlib.md5(password.encode())
            hashcode = encodedPassword.hexdigest()
            user = db.execute("SELECT * FROM users WHERE email=:email", {'email': email}).fetchone()
            if(hashcode != user['password']):
                return render_template("index.html", error_msg="Incorrect password.",email=email)
            session['user_id'] = user['id']
        
            return render_template("search_books.html")

    return render_template("index.html")

@app.route("/sign_up", methods=["POST","GET"])
def sign_up():
    if(request.method == "POST"):
        username = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        role = request.form.get("role")
        password += password_key
        encodedPassword = hashlib.md5(password.encode())
        hashcode = encodedPassword.hexdigest()
        if db.execute("SELECT * FROM users WHERE email=:email", {'email': email}).rowcount != 0:
            return render_template("sign_up.html", error_msg="User with the given mail-id already exists")

        db.execute("INSERT INTO users(username,email,password,gender,phone,role) VALUES (:username,:email,:password,:gender,:phone,:role)", 
        {"username" : username, "email": email, "password" : hashcode,"gender":gender, "phone": phone, "role":role})
        db.commit()
        return render_template("index.html", message="Account successfully created!" )
    
    return render_template("sign_up.html")

@app.route("/search", methods=["GET","POST"])
def search():
    title = request.form.get("title")
    auth  = request.form.get("author")
    if auth != None:
        query = title+"+inauthor:"+auth
    else:
        query = title    
    try:
        response = requests.get("https://www.googleapis.com/books/v1/volumes", params={"q" : query, "key": key})
        result = response.json()
        
        items = result['items']
        books=[]
        for book in items:
            if('imageLinks' not in book['volumeInfo']):
                book['volumeInfo']['imageLinks'] = {"thumbnail" : "#"}
            books.append(book['volumeInfo'])
     
    except:
        return render_template("error.html", message="Sorry! An internal server error has occurred. Try again later. ")
    if books == None:
        return render_template("search_books.html", message="Sorry! No books matched your search!")
    
    return render_template("books.html", books=books, title=title, author=auth)



@app.route("/home")
def home():
    return render_template("search_books.html")

@app.route("/profile")
def profile():
    user_id = session['user_id']
    user_details = db.execute("SELECT username, email, gender, phone, role FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()
    books = db.execute(" SELECT title FROM isbn i JOIN reviews r ON i.id=r.isbn_id WHERE r.user_id=:user_id", {"user_id":user_id})
    reviewed_books=[]
    count=0
    for i in books:
        reviewed_books.append(i)
        count+=1
    return render_template("profile.html", userInfo=user_details, reviewed_books=reviewed_books, count=count) 

@app.route("/edit_profile",methods=["POST","GET"])
def edit_profile():
    user_id = session['user_id']
    message = None
    if request.method=="POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        role = request.form.get("role")
        db.execute("UPDATE users SET username=:name, phone=:phone, role=:role WHERE id=:user_id", {
            "name":name, "phone":phone, "user_id": user_id, "role":role})
        db.commit()
        message="Profile successfully updated!"
    user_details = db.execute("SELECT username, email, gender, phone, role FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()
    return render_template("edit_profile.html", userInfo=user_details, message=message)

@app.route("/change_password", methods=["POST", "GET"])
def change_password():
    if request.method == "POST":
        user_id = session['user_id']
        oldPass = request.form.get("old-password")
        newPass = request.form.get("new-password")
        oldPass += password_key
        encodedOldPass = hashlib.md5(oldPass.encode())
        oldPassCode = encodedOldPass.hexdigest()
        currentPass = db.execute("SELECT password FROM users WHERE id=:user_id", {"user_id":user_id}).fetchone()
        print(currentPass[0])
        if(oldPassCode != currentPass[0]):
            return render_template("change_password.html", err_message="Wrong current password!")
        newPass += password_key
        encodedNewPass = hashlib.md5(newPass.encode())
        newPassCode = encodedNewPass.hexdigest()
        db.execute("UPDATE users SET password=:newPass WHERE id=:user_id", {"newPass":newPassCode, "user_id":user_id})
        db.commit()
        return render_template("change_password.html",message="Password successfully updated!")

    return render_template("change_password.html")

@app.route("/book/<isbn_no>/<title>", methods=["GET", "POST"])
def book(isbn_no, title):
    user_id = session['user_id']

    if request.method == "POST":
    
        rating = int(request.form.get("rating"))
        review = request.form.get("review")
        
        if db.execute("SELECT isbn_no FROM isbn WHERE isbn_no = :isbn_no", {"isbn_no": isbn_no}).rowcount == 0:
            db.execute("INSERT INTO isbn (isbn_no, title) VALUES (:isbn_no, :title)", {"isbn_no": isbn_no,"title": title})
        
        if(db.execute("SELECT * FROM reviews WHERE isbn_id = :isbn_id AND user_id = :user_id", {
        "isbn_id" : db.execute("SELECT id FROM isbn WHERE isbn_no = :isbn_no",{"isbn_no":isbn_no}).fetchone()[0],
            "user_id": user_id}).rowcount == 0):

            db.execute("INSERT INTO reviews(isbn_id, user_id, rating, review) VALUES (:isbn_id, :user_id, :rating, :review)",
            {"isbn_id": db.execute("SELECT id from isbn WHERE isbn_no=:isbn_no", {"isbn_no":isbn_no}).fetchone()[0],
            "user_id": user_id, "rating": rating, "review": review})
        else:
            if(review != None):
                db.execute("UPDATE reviews SET rating=:rating,review=:review WHERE isbn_id = :isbn_id AND user_id = :user_id", {
                "rating": rating,
                "review": review,
                "isbn_id" :db.execute("SELECT id FROM isbn WHERE isbn_no = :isbn_no",{"isbn_no":isbn_no}).fetchone()[0],
                "user_id": user_id
            })
            else:
                db.execute("UPDATE reviews SET rating=:rating WHERE isbn_id = :isbn_id AND user_id = :user_id", {
                "rating": rating,
                "isbn_id" :db.execute("SELECT id FROM isbn WHERE isbn_no = :isbn_no",{"isbn_no":isbn_no}).fetchone()[0],
                "user_id": user_id
            })
        db.commit()
    query = title + "+isbn:" + isbn_no
    response = requests.get("https://www.googleapis.com/books/v1/volumes", params={"q" : query ,"key" : key})
    result = response.json()

    try:
        bookInfo = result['items'][0]['volumeInfo']
    except:
        return render_template("error.html", message = "Sorry! The requested book couldn't be found")

    
    if('imageLinks' not in bookInfo):
        bookInfo['imageLinks'] = {'thumbnail' : '#'}
    if('ratingsCount' not in bookInfo):
        bookInfo['ratingsCount'] = "No ratings Yet"
        bookInfo['averageRating'] = "N/A"
    
    if db.execute("SELECT isbn_no FROM isbn WHERE isbn_no = :isbn_no", {"isbn_no": isbn_no}).rowcount != 0:
        ratings = db.execute("SELECT rating FROM reviews r JOIN isbn i ON i.id=r.isbn_id WHERE isbn_no=:isbn_no",{"isbn_no": isbn_no})        
        total_rating1 = 0
        for rating in ratings.fetchall()[0]:
            total_rating1 += rating
        try:
            
            total_rating2 = bookInfo['averageRating'] * bookInfo['ratingsCount']
            total = total_rating1 + total_rating2
            bookInfo['averageRating'] = round(total/(ratings.rowcount + bookInfo['ratingsCount']),2)
        except:
            bookInfo['averageRating'] = round(total_rating1/ratings.rowcount,2)
        
        try:
            bookInfo['ratingsCount'] += ratings.rowcount
        except:
            bookInfo['ratingsCount'] = ratings.rowcount
        
        feedback = db.execute("SELECT review, rating from reviews r JOIN isbn i ON i.id=r.isbn_id WHERE isbn_no=:isbn_no AND user_id=:user_id",
        {"isbn_no":isbn_no, "user_id": user_id})
        
        if feedback.rowcount != 0:
            feedback = feedback.fetchall()
            bookInfo['your_review'] = feedback[0][0]
            bookInfo['your_rating'] = feedback[0][1]

    return render_template("book_details.html", bookInfo=bookInfo, reviewForm = False)
   

    
@app.route("/deleteReview/<isbn_no>/<title>", methods=["GET"])
def deleteReview(isbn_no,title):
    user_id = session['user_id']
    
    db.execute("DELETE FROM reviews WHERE isbn_id=:isbn_id AND user_id=:user_id", {
        "isbn_id":db.execute("SELECT id FROM isbn WHERE isbn_no=:isbn_no", {"isbn_no": isbn_no}).fetchone()[0],
        "user_id": user_id
    })
   
    if db.execute("SELECT * FROM reviews WHERE isbn_id=:isbn_id", {
        "isbn_id":db.execute("SELECT id FROM isbn WHERE isbn_no=:isbn_no", {"isbn_no": isbn_no}).fetchone()[0],
    }).rowcount == 0:
        db.execute("DELETE FROM isbn WHERE isbn_no=:isbn_no", {"isbn_no":isbn_no}) 
    db.commit()
    return book(isbn_no, title)

@app.route("/logout")
def logout():
    session.clear()
    return render_template("index.html")
