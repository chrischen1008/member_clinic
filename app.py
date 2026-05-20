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
    res = supabase.table("members").select("*").order("id").execute()
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
    return render_template("members.html", members=members)


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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)