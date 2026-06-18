from flask import Flask, render_template, request, redirect
import pymysql
from config import *

app = Flask(__name__)

@app.route("/")
def home():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    # 今日推荐：取3个故事做轮播
    cursor.execute("""
        SELECT story_id, title, theme, cover_image
        FROM story
        WHERE cover_image IS NOT NULL
        ORDER BY RAND()
        LIMIT 3
    """)
    recommended = cursor.fetchall()

    # 热门故事：按阅读次数排序，取8个
    cursor.execute("""
        SELECT story_id, title, theme, age_group, cover_image, read_count
        FROM story
        WHERE cover_image IS NOT NULL
        ORDER BY read_count DESC
        LIMIT 8
    """)
    hot_stories = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        recommended=recommended,
        hot_stories=hot_stories
    )

@app.route("/story_library")
def story_library():

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT story_id, title, theme, age_group, read_count
        FROM story
    """)

    stories = cursor.fetchall()

    conn.close()

    return render_template(
        "story_library.html",
        stories=stories
    )

@app.route("/generate_story", methods=["GET", "POST"])
def generate_story():

    story = None
    selected_theme = "动物"
    selected_age = "3-5岁"

    if request.method == "POST":
        selected_theme = request.form["theme"]
        selected_age = request.form["age_group"]
        keywords = request.form["keywords"]

        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4"
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT title,content,theme,age_group
            FROM story
            WHERE theme=%s AND age_group=%s
            ORDER BY RAND()
            LIMIT 1
        """, (selected_theme, selected_age))

        story = cursor.fetchone()
        if story:
            cursor.execute("""
                INSERT INTO story_generate_record
                (user_id, theme, age_group, keywords, story_id, generate_time)
                SELECT 1, %s, %s, %s, story_id, NOW()
                FROM story
                WHERE title = %s 
                LIMIT 1
            """, (selected_theme, selected_age, keywords, story[0]))

            conn.commit()

        conn.close()

    return render_template(
        "generate_story.html",
        story=story,
        selected_theme=selected_theme,
        selected_age=selected_age
    )

@app.route("/reading_record")
def reading_record():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.title, r.read_time, r.duration
        FROM read_record r
        JOIN story s ON r.story_id = s.story_id
        WHERE r.user_id = 1
        ORDER BY r.read_time DESC
    """)

    records = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*), IFNULL(SUM(duration),0)
        FROM read_record
        WHERE user_id = 1
    """)

    total = cursor.fetchone()

    conn.close()

    return render_template(
        "reading_record.html",
        records=records,
        total_count=total[0],
        total_minutes=total[1]
    )

@app.route("/parent_center")
def parent_center():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*), IFNULL(SUM(duration),0), COUNT(DISTINCT story_id)
        FROM read_record
        WHERE user_id = 1
    """)
    total = cursor.fetchone()

    cursor.execute("""
        SELECT IFNULL(SUM(duration),0)
        FROM read_record
        WHERE user_id = 1 AND DATE(read_time) = CURDATE()
    """)
    today_minutes = cursor.fetchone()[0]

    cursor.execute("""
        SELECT max_minutes
        FROM daily_limit
        WHERE user_id = 1
        LIMIT 1
    """)
    limit_result = cursor.fetchone()
    max_minutes = limit_result[0] if limit_result else 60

    conn.close()

    return render_template(
        "parent_center.html",
        today_minutes=today_minutes,
        total_count=total[0],
        total_minutes=total[1],
        story_count=total[2],
        max_minutes=max_minutes
    )

@app.route("/story/<int:story_id>")
def story_detail(story_id):

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, theme, age_group, content, cover_image
        FROM story
        WHERE story_id=%s
    """, (story_id,))

    story = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM favorite
        WHERE user_id=1 AND story_id=%s
    """, (story_id,))

    favorite = cursor.fetchone()

    conn.close()

    favorite_success = request.args.get("favorite")

    return render_template(
        "story_detail.html",
        story=story,
        story_id=story_id,
        favorite=favorite,
        favorite_success=favorite_success
    )

@app.route("/favorite/<int:story_id>")
def add_favorite(story_id):
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO favorite (user_id, story_id, favorite_time)
        VALUES (1, %s, NOW())
    """, (story_id,))

    conn.commit()
    conn.close()

    return redirect("/story/" + str(story_id) + "?favorite=success")

@app.route("/favorite_list")
def favorite_list():

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            s.story_id,
            s.title,
            s.theme,
            s.age_group,
            s.cover_image
        FROM favorite f
        JOIN story s
            ON f.story_id = s.story_id
        WHERE f.user_id = 1
        ORDER BY f.favorite_time DESC
    """)

    stories = cursor.fetchall()

    conn.close()

    return render_template(
        "favorite_list.html",
        stories=stories
    )

@app.route("/unfavorite/<int:story_id>")
def unfavorite(story_id):

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM favorite
        WHERE user_id=1
        AND story_id=%s
    """, (story_id,))

    conn.commit()

    conn.close()

    return redirect("/story/" + str(story_id))

@app.route("/read/<int:story_id>")
def read_story(story_id):

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO read_record
        (user_id, story_id, read_time, duration)
        VALUES
        (1, %s, NOW(), 5)
    """, (story_id,))

    conn.commit()

    cursor.execute("""
        SELECT title,
               content,
               cover_image
        FROM story
        WHERE story_id=%s
    """, (story_id,))

    story = cursor.fetchone()

    conn.close()

    return render_template(
        "reading_page.html",
        story=story
    )

@app.route("/set_limit", methods=["POST"])
def set_limit():
    max_minutes = request.form["max_minutes"]

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE daily_limit
        SET max_minutes=%s, updated_at=NOW()
        WHERE user_id=1
    """, (max_minutes,))

    conn.commit()
    conn.close()

    return redirect("/parent_center")

if __name__ == "__main__":
    app.run(debug=True)