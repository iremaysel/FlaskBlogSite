from os import name
import re
from MySQLdb import cursors
from flask import Flask, render_template,flash,redirect,url_for,session,logging,request
from flask.typing import ResponseReturnValue
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:           
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın!","danger")
            return redirect(url_for("login"))
    return decorated_function

class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.DataRequired(message="Lütfen 4 karakterden büyük ve 16 karakterden küçük giriniz!"),validators.Length(min = 4, max = 16)])
    username = StringField("Kullanıcı Adı", validators=[validators.DataRequired(),validators.Length(min = 5, max = 10)])
    email = StringField("e-mail", validators=[validators.Email(message="Lütfen Geçerli Bir Email Adresi Girin!")])
    password = PasswordField("Parola", validators = [
        validators.DataRequired(message="Lütfen Bir parola Belirleyin!"),
        validators.EqualTo(fieldname="confirm",message="Parolalar Uyuşmuyor")
    ])
    confirm = PasswordField("Parola Doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.Length(min=5,max=100)])
    content = TextAreaField("Makale İçeriği",validators = [validators.Length(min=10)])

app = Flask(__name__)                  
app.secret_key = "blog"
app.config["MYSQL_HOST"] = "localhost" 
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"        
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)   

@app.route("/")             

def index():
    return render_template("index.html")      

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM articles")   
    
    if result > 0:     
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

@app.route("/article/<string:id>")
def detail(id):
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM articles where id = %s", (id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

@app.route("/dashboard")
@login_required
def dashboard(): 
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM articles WHERE author = %s", (session["username"],))
    if result > 0: 
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else: 
        return render_template("dashboard.html")

@app.route("/register", methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)           
    if request.method == "POST" and form.validate():                 
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)   
        
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users(name,email,username,password) VALUES (%s,%s,%s,%s)", (name,email,username,password))    
        mysql.connection.commit()  
        cursor.close()

        flash("Başarıyla Kayıt oldunuz...","success")
        return redirect(url_for("login"))        
    else:                     
        return render_template("register.html" ,form = form)

@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_enter = form.password.data
        cursor = mysql.connection.cursor()
        result = cursor.execute("SELECT * FROM users WHERE username = %s",(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]

            if sha256_crypt.verify(password_enter, real_password):
                flash("Başarıyla Giriş Yaptınız", "success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))

            else:
                flash("Girilen Parola Bilgisi Yanlış!", "danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor!","danger")
            return redirect(url_for("login"))

    return render_template("login.html", form=form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/addarticle", methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO articles(title, author, content) VALUES (%s,%s,%s)",(title, session["username"], content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Kaydedildi.","success")
        return redirect(url_for("dashboard"))

    return render_template("addarticle.html", form = form)

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE author = %s and id = %s"
    result = cursor.execute(query, (session["username"],id))
    
    if result > 0:
        query2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(query2, (id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok yada bu makaleyi silme yetkiniz yok", "danger")
        return redirect(url_for("index"))

@app.route("/edit/<string:id>",methods = ["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        result = cursor.execute("SELECT * FROM articles WHERE id = %s and author = %s", (id, session["username"]))
        if result == 0:
            flash("Böyle bir makale yok veya böyle bir işleme yetkiniz yok!")
            return redirect(url_for("index"))

        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)

    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE articles SET title = %s, content = %s WHERE id = %s",(newTitle, newContent, id))
        mysql.connection.commit()

        flash("Makaleniz Başarıyla Güncellendi!", "success")
        return redirect(url_for("dashboard"))

@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))

    else:
        keyword = request.form.get("keyword")   
        cursor = mysql.connection.cursor()
        result = cursor.execute("SELECT * FROM articles WHERE title like '%" + keyword + "%'")

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı!", "warning")
            return redirect(url_for("articles"))

        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)

if __name__ == "__main__":
    app.run(debug = True)   

