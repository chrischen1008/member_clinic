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
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
@app.route("/member_rights")
def member_rights():
    member_id = request.args.get('member_id')
    
    # 💡 優先撈取會員基本資料與日期格式化（因後續自動生成每月贈送需要 start_at）
    member_data = supabase.table("members").select("*").eq("id", member_id).execute().data
    if member_data:
        member = member_data[0]
        for field in ['birth', 'start_at', 'end_at']:
            if member.get(field):
                member[field] = str(member[field])[:10]
    else:
        member = {}

    # 1. 先找出該會員所有的 gift_header 紀錄
    gift_header = supabase.table("gift_header").select("*").eq("member_id", member_id).execute().data or []

    # 2. 收集這些 header 的 id 變成一個列表
    header_ids = [h["id"] for h in gift_header]

    # 3. 撈出 body 資料
    if header_ids:
        gift_body = supabase.table("gift_body").select("*").in_("gift_id", header_ids).order("id").execute().data or []
    else:
        gift_body = []

    # 4. 巢狀資料組合
    for h in gift_header:
        h["bodies"] = [b for b in gift_body if b["gift_id"] == h["id"]]

    # 🔄 新增：撈取每月贈送主從表（✨ 導入 12 個月自動初始化機制）
    monthly_header = supabase.table("monthly_header").select("*").eq("member_id", member_id).order('id').execute().data or []
    
    # 🚀 如果該會員還沒有每月贈送的主單，初始化 Header 與對應的 Body
    if not monthly_header and member and member.get("start_at"):
        base_date = datetime.strptime(member["start_at"], "%Y-%m-%d")
        header_insert_batch = []
        
        # 1. 準備 12 筆 Header 資料
        # (第 1 筆: 當月~下個月底)
        next_month = base_date + relativedelta(months=1)
        last_day_next_month = calendar.monthrange(next_month.year, next_month.month)[1]
        header_insert_batch.append({
            "member_id": member_id,
            "start_date": base_date.strftime("%Y-%m-%d"),
            "end_date": datetime(next_month.year, next_month.month, last_day_next_month).strftime("%Y-%m-%d")
        })
        
        # (第 2-12 筆: 接續月份)
        for i in range(2, 13):
            target_month = base_date + relativedelta(months=i)
            last_day = calendar.monthrange(target_month.year, target_month.month)[1]
            header_insert_batch.append({
                "member_id": member_id,
                "start_date": datetime(target_month.year, target_month.month, 1).strftime("%Y-%m-%d"),
                "end_date": datetime(target_month.year, target_month.month, last_day).strftime("%Y-%m-%d")
            })
        
        # 2. 執行 Header Insert 並取得回傳的資料 (包含新的 ID)
        res = supabase.table("monthly_header").insert(header_insert_batch).execute()
        monthly_header = res.data # 取得包含新 ID 的 header list

        # 3. 根據新的 Header ID，自動幫每一個月建立「1 個空行」的 body
        # 這樣前端在顯示時，每個月份至少都會有一行資料是可以被 Update 的
        body_insert_batch = []
        for h in monthly_header:
            # 這裡改成跑兩次，確保每個月份都有兩列可以輸入
            for _ in range(2):
                body_insert_batch.append({
                    "benefit_id": h["id"], # 連結到剛剛建立的 header
                    "used_date": None,
                    "user_name": "",
                    "treatment": "",
                    "remark": ""
                })
        
        # 執行 Body Insert
        supabase.table("monthly_body").insert(body_insert_batch).execute()
        
        # 重新撈取一次以取得資料庫真實生成的 12 筆完整列表（含資料庫自動產生的 id）
        monthly_header = supabase.table("monthly_header").select("*").eq("member_id", member_id).order("id").execute().data

    # 🔄 新增：撈取每月贈送明細表 (使用對應資料庫的 benefit_id 欄位)
    monthly_header_ids = [m["id"] for m in monthly_header]
    monthly_body = supabase.table("monthly_body").select("*").in_("benefit_id", monthly_header_ids).order("id").execute().data or [] if monthly_header_ids else []
    
    for m in monthly_header:
        m["bodies"] = [b for b in monthly_body if b["benefit_id"] == m["id"]]

    # 5. 精準計算與防呆 gift_qty 的數量
    gift_qty = 0 
    course_name = "三選一療程" # 預設安全牌

    if gift_header:
        header = gift_header[0]
        db_qty = header.get("gift_qty")
        if header.get("course_name"):
            course_name = header["course_name"]

        # 如果資料庫欄位是 None 或 0，則向外查詢預設值
        if db_qty is None or db_qty == 0:
            res_data = supabase.table("course").select("default_qty").eq("course_info", course_name).execute().data
            if res_data and res_data[0].get("default_qty") is not None:
                gift_qty = res_data[0]["default_qty"]
                header["gift_qty"] = gift_qty  # 同步寫回結構，讓前端 JS 拿得到
            else:
                # 保底機制：如果 course 表也查不到，直接拿現有的 bodies 數量當作總堂數
                gift_qty = len(header["bodies"]) if len(header["bodies"]) > 0 else 0
                header["gift_qty"] = gift_qty
        else:
            gift_qty = db_qty
    else:
        # 如果根本沒有 header，去撈 course 表的預設數量
        res_data = supabase.table("course").select("default_qty").eq("course_info", course_name).execute().data
        if res_data:
            gift_qty = res_data[0]["default_qty"]

    # 6. 抓取所有的課程資料與項目資料供下拉選單使用
    courses = supabase.table("course").select("*").execute().data or []
    course_item = supabase.table("course_item").select("*").execute().data or []
        
    return render_template(
        "member_rights.html", 
        gift_header=gift_header, 
        gift_body=gift_body,
        monthly_header=monthly_header,  # ↩ 傳給前端
        monthly_body=monthly_body,      # ↩ 傳給前端
        courses=courses,
        course_item=course_item,
        member=member,
        default_qty=gift_qty,
        member_id=member_id
    )


#========會員同行者=======
@app.route("/member_party", methods=["GET"])
def get_member_party():
    member_id = request.args.get('member_id')
    if not member_id:
        return jsonify({"error": "缺少 member_id 參數"}), 400

    # 撈出該會員底下的所有同行者名單
    res = supabase.table("member_party") \
        .select("*") \
        .eq("member_id", member_id) \
        .order("id") \
        .execute()
        
    return jsonify(res.data)

@app.route("/member_party", methods=["POST"])
def add_member_party():
    # 接收前端傳來的 name 與 member_id
    name = request.json.get("name")
    member_id = request.json.get("member_id")

    # 寫入資料庫
    supabase.table("member_party") \
        .insert({
            "name": name, 
            "member_id": member_id
        }) \
        .execute()
        
    return "ok"

@app.route("/member_party/<int:id>", methods=["DELETE"])
def delete_member_party(id):
    # 根據資料表的主鍵 (id) 來刪除特定的一筆同行者紀錄
    supabase.table("member_party") \
        .delete() \
        .eq("id", id) \
        .execute()
        
    return "ok"

@app.route("/member_party/<int:id>", methods=["PUT"])
def update_member_party(id):
    # 接收前端傳來的新姓名
    name = request.json.get("name")

    # 根據資料表的主鍵 (id) 來更新該筆紀錄的 name
    supabase.table("member_party") \
        .update({"name": name}) \
        .eq("id", id) \
        .execute()
        
    return "ok"


import traceback

@app.route("/save_batch", methods=["POST"])
def save_batch():
    try:
        # 1. 接收前端傳來的結構化 JSON 資料
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "儲存失敗：未接收到有效的資料"}), 400

        member_id = data.get('member_id') 
        main_course_name = data.get('main_course_name') 
        
        if not member_id or str(member_id).strip() == "":
            return jsonify({"status": "error", "message": "儲存失敗：未接收到有效的會員編號"}), 400

        print("=== [Debug] 接收到的結構化主表單資料 ===")
        print(f"member_id: {member_id}")
        print(f"main_course_name: {main_course_name}")

        # 🛡️ 權限防護：先去資料庫查出這個 member_id 真正擁有的所有主單 ID
        # 區分為會員贈送與每月贈送兩張表
        real_gift_headers = supabase.table("gift_header").select("id").eq("member_id", member_id).execute().data or []
        allowed_gift_header_ids = [str(rh["id"]) for rh in real_gift_headers if "id" in rh]

        # 這裡假設您的每月贈送主表名稱為 "monthly_header"
        # real_monthly_headers = supabase.table("monthly_header").select("id").eq("member_id", member_id).execute().data or []
        # allowed_monthly_header_ids = [str(rmh["id"]) for rmh in real_monthly_headers if "id" in rmh]

        # ==========================================
        # 2. 處理「會員贈送」 (Membership Rows) -> 維持原表
        # ==========================================
        membership_rows = data.get('membership_rows', [])
        new_header_id_cache = None 

        for item in membership_rows:
            body_id = str(item.get('body_id', '')).strip()
            header_id_from_form = str(item.get('header_id', '')).strip()
            
            if body_id.lower() in ['null', 'none', '']: body_id = None
            if header_id_from_form.lower() in ['null', 'none', '']: header_id_from_form = None

            current_gift_id = None

            if header_id_from_form:
                if header_id_from_form not in allowed_gift_header_ids:
                    return jsonify({"status": "error", "message": f"越權存取：無權使用主帳單編號 {header_id_from_form}"}), 403
                current_gift_id = header_id_from_form
                
                # 👇 [修復這裡] 補上更新主表 (gift_header) 起訖日期的邏輯
                supabase.table('gift_header').update({
                    "start_at": item.get('start_at') if item.get('start_at') else None,
                    "end_at": item.get('end_at') if item.get('end_at') else None
                }).eq('id', current_gift_id).execute()
                # 👆 ----------------------------------------------------

            else:
                if not new_header_id_cache:
                    new_header_data = {
                        "member_id": member_id, 
                        "course_name": main_course_name,
                        "start_at": item.get('start_at') if item.get('start_at') else None,
                        "end_at": item.get('end_at') if item.get('end_at') else None,
                        "gift_qty": 6,
                        # "gift_type": "membership"
                    }
                    header_response = supabase.table('gift_header').insert(new_header_data).execute()
                    if header_response.data:
                        new_header_id_cache = str(header_response.data[0]['id'])
                        allowed_gift_header_ids.append(new_header_id_cache)
                
                current_gift_id = new_header_id_cache

            raw_remaining = item.get('remain_qty', '0')
            body_data = {
                "gift_id": current_gift_id,  
                "use_date": item.get('use_date') if item.get('use_date') else None,
                "user_name": item.get('user_name', ''),
                "use_course": item.get('use_course', ''),
                "remain_qty": int(raw_remaining) if str(raw_remaining).isdigit() else 0,
                "note": item.get('note', '')
            }

            if body_id:
                check_body = supabase.table("gift_body").select("gift_id").eq("id", body_id).execute().data or []
                if check_body:
                    db_gift_id = str(check_body[0].get("gift_id"))
                    if db_gift_id not in allowed_gift_header_ids:
                        return jsonify({"status": "error", "message": f"越權存取：無權修改紀錄編號 {body_id}"}), 403
                
                print(f"[Debug] 會員贈送 -> 執行 UPDATE (body_id: {body_id})")
                supabase.table('gift_body').update(body_data).eq('id', body_id).execute()
            else:
                print(f"[Debug] 會員贈送 -> 執行 INSERT (全新明細欄位)")
                supabase.table('gift_body').insert(body_data).execute()

        # ==========================================================
        # 2. 處理「每月贈送」 (手動分離 Update 與 Insert)
        # ==========================================================
        monthly_rows = data.get('monthly_rows', [])
        
        for item in monthly_rows:
            body_id = str(item.get('body_id', '')).strip()
            header_id = str(item.get('header_id', '')).strip()

            # [嚴格檢查] 進入此函數的每一筆資料都必須要有 body_id
            if not body_id or body_id.lower() in ['null', 'none', '']:
                # 若發現沒有 ID 的資料，這代表前端未正確執行初始化
                return jsonify({"status": "error", "message": "錯誤：檢測到無效的資料行，請確保資料已正確初始化"}), 400

            # 準備資料
            body_data = {
                "benefit_id": header_id,
                "used_date": item.get('use_date') if item.get('use_date') else None,
                "user_name": item.get('user_name', ''),
                "treatment": item.get('use_course', ''),
                "remark": item.get('note', '')
            }

            # [強制 Update]
            # 因為我們假設所有資料皆已初始化，所以這裡只需要 Update
            supabase.table('monthly_body').update(body_data).eq('id', int(body_id)).execute()

        return jsonify({"status": "success", "message": "儲存成功！"})
    
    except Exception as e:
        print(f"[Debug] 發生錯誤 (Exception): {str(e)}")
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": f"發生錯誤：{str(e)}"}), 500

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