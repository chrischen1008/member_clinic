import os
from flask import Flask, request, jsonify
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


# ===== 取得所有會員 =====
@app.route("/members", methods=["GET"])
def get_members():
    res = supabase.table("members").select("*").order("id").execute()
    return jsonify(res.data)


# ===== 新增會員 =====
@app.route("/members", methods=["POST"])
def create_member():
    data = request.json

    res = supabase.table("members").insert({
        "name": data["name"],
        "email": data["email"],
        "password": data["password"]   # ⚠️ demo 用，正式請 hash
    }).execute()

    return jsonify(res.data)


# ===== 更新會員 =====
@app.route("/members/<int:member_id>", methods=["PUT"])
def update_member(member_id):
    data = request.json

    res = supabase.table("members").update({
        "name": data["name"],
        "email": data["email"]
    }).eq("id", member_id).execute()

    return jsonify(res.data)


# ===== 刪除會員 =====
@app.route("/members/<int:member_id>", methods=["DELETE"])
def delete_member(member_id):
    res = supabase.table("members").delete().eq("id", member_id).execute()
    return jsonify(res.data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)