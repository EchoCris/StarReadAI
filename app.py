from flask import Flask, render_template, request, redirect, session, url_for
import pymysql
from config import *

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM `user` WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()
        db.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "parent":
                return redirect(url_for("parent_home"))
            else:
                return redirect(url_for("child_home"))

        return "用户名或密码错误"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        nickname = request.form.get("nickname")
        age = request.form.get("age")
        role = request.form.get("role")

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO `user` (username, password, nickname, age, role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (username, password, nickname, age, role)
        )
        db.commit()
        db.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/child_home")
def child_home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("child_home.html")


@app.route("/parent_home")
def parent_home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("parent_home.html")


@app.route("/generate_story", methods=["GET", "POST"])
def generate_story():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        theme = request.form.get("theme")
        age = request.form.get("age")
        keyword = request.form.get("keyword")

        title = f"{keyword}的奇妙故事"
        content = f"从前，有一个喜欢{keyword}的小朋友。他进入了一个关于{theme}的世界，在那里学会了勇敢、友爱和坚持。最后，他带着快乐和知识回到了家。"

        cover_url = "/static/uploads/covers/default_cover.jpg"

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO story (title, content, theme, suitable_age, cover_url, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (title, content, theme, age, cover_url, session["user_id"])
        )
        db.commit()
        db.close()

        return redirect(url_for("story_list"))

    return render_template("generate_story.html")


@app.route("/stories")
def story_list():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM story ORDER BY create_time DESC")
    stories = cursor.fetchall()
    db.close()

    return render_template("story_list.html", stories=stories)


@app.route("/story/<int:story_id>")
def story_detail(story_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM story WHERE id=%s", (story_id,))
    story = cursor.fetchone()

    cursor.execute(
        """
        INSERT INTO read_record (user_id, story_id, spend_time)
        VALUES (%s, %s, %s)
        """,
        (session["user_id"], story_id, 5)
    )

    db.commit()
    db.close()

    return render_template("story_detail.html", story=story)


@app.route("/add_favorite/<int:story_id>")
def add_favorite(story_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT * FROM collect
        WHERE user_id=%s AND story_id=%s
        """,
        (session["user_id"], story_id)
    )
    existing = cursor.fetchone()

    if not existing:
        cursor.execute(
            """
            INSERT INTO collect (user_id, story_id)
            VALUES (%s, %s)
            """,
            (session["user_id"], story_id)
        )
        db.commit()

    db.close()
    return redirect(url_for("favorites"))


@app.route("/favorites")
def favorites():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT s.*
        FROM collect c
        JOIN story s ON c.story_id = s.id
        WHERE c.user_id=%s
        ORDER BY c.collect_time DESC
        """,
        (session["user_id"],)
    )
    favorites = cursor.fetchall()
    db.close()

    return render_template("favorites.html", favorites=favorites)


@app.route("/records")
def read_records():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT r.*, s.title
        FROM read_record r
        JOIN story s ON r.story_id = s.id
        WHERE r.user_id=%s
        ORDER BY r.read_time DESC
        """,
        (session["user_id"],)
    )
    records = cursor.fetchall()
    db.close()

    return render_template("read_records.html", records=records)


@app.route("/view_child_records")
def view_child_records():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT r.*, s.title, u.nickname AS child_name
        FROM parent_control pc
        JOIN `user` u ON pc.child_id = u.id
        JOIN read_record r ON pc.child_id = r.user_id
        JOIN story s ON r.story_id = s.id
        WHERE pc.parent_id=%s
        ORDER BY r.read_time DESC
        """,
        (session["user_id"],)
    )
    records = cursor.fetchall()
    db.close()

    return render_template("read_records.html", records=records)


@app.route("/set_daily_limit", methods=["GET", "POST"])
def set_daily_limit():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        child_id = request.form.get("child_id")
        daily_time = request.form.get("daily_time")

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO parent_control (parent_id, child_id, daily_time)
            VALUES (%s, %s, %s)
            """,
            (session["user_id"], child_id, daily_time)
        )

        db.commit()
        db.close()

        return redirect(url_for("parent_home"))

    return """
    <h1>Set Daily Time Limit</h1>
    <form method="post">
        <input name="child_id" placeholder="Child ID">
        <input name="daily_time" placeholder="Daily Time">
        <button type="submit">Submit</button>
    </form>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)