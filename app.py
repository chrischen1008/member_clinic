import os
from flask import Flask, request, jsonify, render_template
from supabase import create_client

app = Flask(__name__)

# ===== Supabase 設定（Render 用環境變數）=====
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ===== Health Check =====
@app.route("/")
def home():
    return {"status": "ok", "message": "Flask + Supabase Member System"}


# ===== API（原本的）=====
@app.route("/members/api", methods=["GET"])
def get_members_api():
    res = supabase.table("members").select("*").execute()
    return jsonify(res.data)


# ===== 網頁版（重點）=====
@app.route("/members", methods=["GET"])
def members_page():
    res = supabase.table("members").select("*").eq("is_delete",False).order("id").execute()
    members = res.data
    for m in members:
        if m.get("birth"):
            m["birth"] = m["birth"].split("T")[0]
    for m in members:
        if m.get("start_at"):
            m["start_at"] = m["start_at"].split("T")[0]
    for m in members:
        if m.get("end_at"):
            m["end_at"] = m["end_at"].split("T")[0]
            
    return render_template(
        "members.html",
        members=members,
        active="members"
    )


# ===== 新增會員 =====
@app.route("/members", methods=["POST"])
def create_member():
    data = request.json

    return supabase.table("members").insert(data).execute().data

# ===== 更新會員 =====
@app.route("/members/<id>", methods=["PUT"])
def update_member(id):

    data = request.json

    return supabase.table("members") \
        .update(data) \
        .eq("id", id) \
        .execute().data

# ===== 刪除會員 =====
@app.route("/members/<id>", methods=["DELETE"])
def delete_member(id):

    return supabase.table("members") \
        .update({"is_delete": True}) \
        .eq("id", id) \
        .execute().data

#======療程清單========
@app.route("/course_list")
def course_list():

    course_list = supabase.table("course").select("*").execute().data or []
    items = supabase.table("course_item").select("*").execute().data or []

    for c in course_list:
        c["items"] = [i for i in items if i["course_id"] == c["id"]]

    return render_template("course_list.html", courses=course_list)

@app.route("/courses", methods=["GET"])
def get_courses():
    courses = supabase.table("course").select("*").order("id").execute().data or []
    items = supabase.table("course_item").select("*").order("id").execute().data or []

    for c in courses:
        c["items"] = [i for i in items if i["course_id"] == c["id"]]

    return jsonify(courses)

@app.route("/course", methods=["POST"])
def create_course():
    data = request.json
    return supabase.table("course").insert(data).execute().data

@app.route("/course/<id>", methods=["PUT"])
def update_course(id):
    data = request.json
    return supabase.table("course").update(data).eq("id", id).execute().data

@app.route("/course/<id>", methods=["DELETE"])
def delete_course(id):
    # 1️⃣ 先刪 course_item（用 course_id）
    supabase.table("course_item") \
        .delete() \
        .eq("course_id", id) \
        .execute()

    # 2️⃣ 再刪 course
    res = supabase.table("course") \
        .delete() \
        .eq("id", id) \
        .execute()

    return res.data

@app.route("/course/<course_id>/item", methods=["POST"])
def add_item(course_id):
    data = request.json
    res = supabase.table("course_item").insert({
        "course_id": int(course_id),
        "name": data["name"]
    }).execute()

    return res.data

@app.route("/course_item/<id>", methods=["PUT"])
def update_item(id):
    data = request.json
    return supabase.table("course_item").update(data).eq("id", id).execute().data

@app.route("/course_item/<id>", methods=["DELETE"])
def delete_item(id):
    return supabase.table("course_item").delete().eq("id", id).execute().data

#=======諮詢師清單=============
@app.route("/consultants", methods=["GET"])
def get_consultants():

    res = supabase.table("consultant_list") \
        .select("*") \
        .order("id") \
        .execute()

    return jsonify(res.data)
@app.route("/consultants", methods=["POST"])
def add_consultant():

    name = request.json["name"]

    supabase.table("consultant_list") \
        .insert({"name": name}) \
        .execute()

    return "ok"
@app.route("/consultants/<int:id>", methods=["DELETE"])
def delete_consultant(id):

    supabase.table("consultant_list") \
        .delete() \
        .eq("id", id) \
        .execute()

    return "ok"

@app.route("/consultants/<int:id>", methods=["PUT"])
def update_consultant(id):
    # 取得前端傳來的修改後姓名
    name = request.json["name"]

    # 更新資料庫
    supabase.table("consultant_list") \
        .update({"name": name}) \
        .eq("id", id) \
        .execute()

    return "ok"

@app.route("/orders")
def orders():
    return render_template("orders.html", active="orders")

@app.route("/reports")
def reports():
    return render_template("reports.html", active="reports")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)