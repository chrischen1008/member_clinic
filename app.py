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
    # 1. 從 Supabase 撈取未刪除的會員資料
    res = supabase.table("members").select("*").eq("is_delete", False).execute()
    members = res.data

    # 2. 定義安全排序規則：如果是純數字就依數字大小排；有文字的話就當作 0 排在最前面（防止轉換報錯）
    def safe_int_sort(x):
        val = x.get('member_id', '0')
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0  # 如果混入文字（如 "A101"），當作 0 處理，不讓系統崩潰

    # 執行排序
    sorted_members = sorted(members, key=safe_int_sort)

    # 3. 合併處理日期格式（把 ISO 時間字串切成成 YYYY-MM-DD）
    for m in sorted_members:
        if m.get("birth"):
            m["birth"] = m["birth"].split("T")[0]
        if m.get("start_at"):
            m["start_at"] = m["start_at"].split("T")[0]
        if m.get("end_at"):
            m["end_at"] = m["end_at"].split("T")[0]
            
    return render_template(
        "members.html",
        members=sorted_members,
        active="members"
    )


# ===== 新增會員 =====
@app.route("/members", methods=["POST"])
def create_member():
    data = request.json
    
    # 1. 資料清洗：把所有的空字串 "" 轉成 None (等於資料庫的 NULL)
    # 這樣就算有些欄位（如日期或諮詢師）沒填，資料庫也不會報錯
    clean_data = {}
    for key, value in data.items():
        if value == "":
            clean_data[key] = None
        else:
            clean_data[key] = value

    # 2. 執行新增並包裝回傳結果（避免 Flask 因為直接回傳 List 而報錯）
    try:
        res = supabase.table("members").insert(clean_data).execute()
        return {"status": "success", "data": res.data}, 200
    except Exception as e:
        # 如果還是有錯，把錯誤訊息印在終端機，方便我們除錯
        print("新增失敗:", e)
        return {"status": "error", "message": str(e)}, 400

# ===== 更新會員 =====
@app.route("/members/<id>", methods=["PUT"])
def update_member(id):
    data = request.json

    # 一樣把空字串轉成 None
    clean_data = {}
    for key, value in data.items():
        if value == "":
            clean_data[key] = None
        else:
            clean_data[key] = value

    try:
        res = supabase.table("members").update(clean_data).eq("id", id).execute()
        return {"status": "success", "data": res.data}, 200
    except Exception as e:
        print("修改失敗:", e)
        return {"status": "error", "message": str(e)}, 400

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

#========會員內容===========

@app.route("/member_rights") # 假設這是你的會員權益頁面路由
def member_rights():
    member_id = request.args.get('member_id')
    
    # 1. 先找出該會員所有的 gift_header 紀錄
    gift_header = supabase.table("gift_header").select("*").eq("member_id", member_id).execute().data or []

    # 2. 收集這些 header 的 id 變成一個列表 [1, 2, 3...]
    header_ids = [h["id"] for h in gift_header]

    # 3. 用 .in_() 去撈出所有 gift_id 在 header_ids 裡面的 body 資料
    if header_ids:
        gift_body = supabase.table("gift_body").select("*").in_("gift_id", header_ids).order("id").execute().data or []
    else:
        gift_body = []

    # 4. 經典的巢狀資料組合：用 gift_header 的 id 去配對 gift_body 的 gift_id
    for h in gift_header:
        h["bodies"] = [b for b in gift_body if b["gift_id"] == h["id"]]

    # 現在你的 gift_header 結構裡，每個項目都會有一個 "bodies" 列表了！
    print(gift_header)
    # 先檢查 gift_header 是不是空的，有資料才執行
    # 1. 預設先找出 course_name（防呆：如果 header 有資料就抓 header 的，沒有就用寫死的）
    course_name = gift_header[0]["course_name"] if gift_header else "三選一療程"

    # 2. 判斷是否需要去撈資料庫（情況一：header 是空的，或是 情況二：數量為 0）
    if not gift_header or gift_header[0]["gift_qty"] == 0:
        
        # 去 Supabase 查 default_qty
        res_data = supabase.table("course").select("default_qty").eq("course_info", course_name).execute().data
        
        if res_data:
            default_qty = res_data[0]["default_qty"]
            
            # 情況 A：如果 gift_header 有資料（只是數量為 0），就把值寫回 gift_header
            if gift_header:
                gift_header[0]["gift_qty"] = default_qty
                gift_qty = default_qty
            # 情況 B：如果 gift_header 本來就是空的，就把值賦予給變數
            else:
                gift_qty = default_qty
                
            print(f"成功取得預設數量: {gift_qty}")
        else:
            print("資料庫中找不到該療程的預設數量")
            gift_qty = 0  # 查不到資料時的保險預設值

    else:
        # 3. 如果 header 有資料且數量不為 0，就直接沿用原本的數量
        gift_qty = gift_header[0]["gift_qty"]

    print(f"最終的 gift_qty: {gift_qty}")
    # ================= 新增這段 =================
    # 4. 抓取所有的課程資料 (假設你的資料表叫做 courses)
    # 這裡請確認你的 Supabase 裡面有沒有 "courses" 這個資料表
    courses = supabase.table("course").select("*").execute().data or []
    course_item = supabase.table("course_item").select("*").execute().data or []
    print(course_item)
    # ============================================
    member_data = supabase.table("members").select("*").eq("id", member_id).execute().data
    print(member_data)
    if member_data:
        member = member_data[0]
        # 手動截取日期 (如果欄位不為空且長度夠長)
        for field in ['birth', 'start_at', 'end_at']:
            if member.get(field):
                # 取前 10 個字元 (YYYY-MM-DD)
                member[field] = str(member[field])[:10]
    else:
        member = {}
    # 這裡順便把抓出來的 courses 傳進模板
    return render_template("member_rights.html", gift_header=gift_header, gift_body=gift_body,courses=courses,course_item=course_item,member=member,default_qty=gift_qty)

@app.route("/introduction_img")
def image():

    return render_template("introduction_img.html", active='introduction_img')

@app.route("/orders")
def orders():
    return render_template("orders.html", active="orders")

@app.route("/reports")
def reports():
    return render_template("reports.html", active="reports")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)