# ================== V5 Smart Madrasa System - Final (Part 1) ==================
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import sqlite3
import os, base64, shutil
import matplotlib.pyplot as plt
import qrcode

# ------------------- Paths and Folders -------------------
DB_NAME = "jamia_millia_v1test.db"
QR_DIR = "qr_codes"
os.makedirs(QR_DIR, exist_ok=True)

# ------------------- Utility Functions -------------------
def get_pkt_time():
    return datetime.utcnow() + timedelta(hours=5)

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    c = conn.cursor()
    # Teachers
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        password TEXT,
        phone TEXT,
        address TEXT,
        id_card TEXT
    )''')
    # Students
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        father_name TEXT,
        teacher_name TEXT,
        phone TEXT,
        address TEXT
    )''')
    # Hifz Records
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        s_name TEXT,
        f_name TEXT,
        t_name TEXT,
        surah TEXT,
        sq_p TEXT,
        sq_a INTEGER,
        sq_m INTEGER,
        m_p TEXT,
        m_a INTEGER,
        m_m INTEGER,
        attendance TEXT
    )''')
    # Teacher Attendance
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        manual_date DATE,
        manual_time TEXT,
        system_timestamp TEXT
    )''')
    # Leave Requests
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        l_type TEXT,
        days INTEGER,
        reason TEXT,
        start_date DATE,
        status TEXT
    )''')
    # Exams
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        s_name TEXT,
        f_name TEXT,
        para_no INTEGER,
        start_date TEXT,
        end_date TEXT,
        total INTEGER,
        grade TEXT,
        status TEXT
    )''')
    # Default Admin
    c.execute("INSERT OR IGNORE INTO teachers (name,password) VALUES (?,?)",("admin","jamia123"))
    conn.commit()
    return conn, c

conn, c = init_db()

# ------------------- RTL + Nastaliq Styling -------------------
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide", page_icon="🕌")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
* { font-family: 'Noto Nastaliq Urdu', serif !important; direction: rtl; text-align: right; }
.main-header { text-align:center; color:#1e5631; background-color:#f1f8e9; padding:25px; border-radius:12px; margin-bottom:25px; border-bottom:5px solid #1e5631; box-shadow:0 4px 6px rgba(0,0,0,0.1);}
.date-divider {background-color:#2e7d32;color:white;text-align:center;padding:10px;font-size:20px;border-radius:8px;margin:25px 0 10px 0;}
.stButton>button {background:#1e5631;color:white;border-radius:8px;font-weight:bold;width:100%;transition:0.3s;border:none;}
.stButton>button:hover {background:#143e22;transform:scale(1.02);}
div[data-testid="stExpander"] {border:1px solid #1e5631 !important;border-radius:8px !important;}
</style>
""", unsafe_allow_html=True)

def generate_html_print(df, title):
    html = f"""
    <html dir="rtl" lang="ur">
    <head><meta charset="utf-8">
    <style>
    body {{font-family:'Arial',sans-serif;padding:20px;}}
    h1,h2 {{text-align:center;color:#1e5631;}}
    table {{width:100%;border-collapse:collapse;margin-top:20px;}}
    th,td {{border:1px solid black;padding:8px;text-align:right;}}
    th {{background-color:#f2f2f2;}}
    .footer {{display:flex;justify-content:space-between;margin-top:50px;font-weight:bold;}}
    .footer div {{border-top:1px solid black;width:200px;text-align:center;padding-top:5px;}}
    </style></head>
    <body>
    <h1>جامعہ ملیہ اسلامیہ</h1>
    <h2>{title}</h2>
    <p>تاریخِ پرنٹ: {get_pkt_time().strftime('%Y-%m-%d %H:%M')}</p>
    {df.to_html(index=False)}
    <div class="footer"><div>دستخط مہتمم</div><div>دستخط مدرس</div></div>
    </body></html>
    """
    b64 = base64.b64encode(html.encode('utf-8-sig')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{title}.html" style="text-decoration:none;"><button style="background-color:#008CBA;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;width:100%;font-weight:bold;">🖨️ پرنٹ / ڈاؤنلوڈ: {title}</button></a>'
    # ================== V5 Smart Madrasa System - Final (Part 2) ==================

# ------------------- Login System -------------------
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("🔐 لاگ ان کریں")
        u = st.text_input("صارف کا نام (Username)")
        p = st.text_input("پاسورڈ (Password)", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u=="admin" else "teacher"
                st.rerun()
            else: st.error("❌ غلط معلومات! دوبارہ کوشش کریں۔")
    st.stop()

# ------------------- Sidebar Menu -------------------
if st.session_state.user_type=="admin":
    menu = ["📊 یومیہ تعلیمی رپورٹ","🖨️ ٹریکنگ و پرنٹ رپورٹ","🎓 امتحانات و نتائج",
            "📜 ماہانہ رزلٹ کارڈ","🕒 استاذہ کا ریکارڈ","🏛️ مہتمم پینل (رخصت)","⚙️ انتظامی کنٹرول"]
else:
    menu = ["📝 تعلیمی اندراج","🎓 امتحان کے لیے نامزدگی","📩 درخواستِ رخصت","🕒 میری حاضری"]

m = st.sidebar.radio("📌 مینو منتخب کریں", menu)
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()

# ------------------- Delete Utility -------------------
def execute_delete(table_name, record_id):
    c.execute(f"DELETE FROM {table_name} WHERE id=?", (record_id,))
    conn.commit()
    st.success(f"ریکارڈ نمبر {record_id} کامیابی سے حذف کر دیا گیا!")
    st.rerun()

# ------------------- Surahs and Paras -------------------
surahs_urdu = ["الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة","يونس",
"هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه","الأنبياء","الحج","المؤمنون",
"النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم","لقمان","السجدة","الأحزاب","سبأ","فاطر",
"يس","الصافات","ص","الزمر","غافر","فصلت","الشورى","الزخرف","الدخان","الجاثية","الأحقاف","محمد","الفتح",
"الحجرات","ق","الذاريات","الطور","النجم","القمر","الرحمن","الواقعة","الحديد","المجادلة","الحشر","الممتحنة",
"الصف","الجمعة","المنافقون","التغابن","الطلاق","التحریم","الملک","القلم","الحاقة","المعارج","نوح","الجن",
"المزمل","المدثر","القیامة","الإنسان","المرسلات","النبأ","النازعات","عبس","التکویر","الإنفطار","المطففین",
"الإنشقاق","البروج","الطارق","الأعلى","الغاشیة","الفجر","البلد","الشمس","اللیل","الضحى","الشرح","التین",
"العلق","القدر","البینة","الزلزلة","العادیات","القارعة","التکاثر","العصر","الهمزة","الفیل","قریش","الماعون",
"الکوثر","الکافرون","النصر","المسد","الإخلاص","الفلق","الناس"]
paras = [f"پارہ {i}" for i in range(1,31)]

# =====================================================================
# Admin: Manage Teachers/Students
# =====================================================================
if m=="⚙️ انتظامی کنٹرول":
    st.header("⚙️ انتظامی کنٹرول (رجسٹریشن، ترمیم اور حذف)")
    tab1, tab2 = st.tabs(["👥 استاذہ کا انتظام","🎓 طالبات کا انتظام"])
    
    # --- Teachers Management ---
    with tab1:
        st.subheader("نئی استانی شامل کریں")
        with st.form("add_teacher"):
            t_name = st.text_input("استاذہ کا نام")
            t_pass = st.text_input("پاسورڈ")
            t_phone = st.text_input("فون نمبر")
            if st.form_submit_button("محفوظ کریں"):
                c.execute("INSERT OR IGNORE INTO teachers (name,password,phone) VALUES (?,?,?)",(t_name,t_pass,t_phone))
                conn.commit()
                st.success("استانی کامیابی سے رجسٹر ہو گئی!")
                st.rerun()
        st.subheader("موجودہ استاذہ (ترمیم / حذف)")
        df_t = pd.read_sql_query("SELECT id,name,phone FROM teachers WHERE name!='admin'",conn)
        st.dataframe(df_t,use_container_width=True)
        del_t_id = st.number_input("حذف کرنے کے لیے استانی کی ID درج کریں",min_value=0,step=1,key="del_t")
        if st.button("استانی کو حذف کریں"): execute_delete("teachers",del_t_id)

    # --- Students Management ---
    with tab2:
        st.subheader("نئی طالبہ شامل کریں")
        with st.form("add_student"):
            s_name = st.text_input("نام طالبہ")
            f_name = st.text_input("ولدیت")
            t_list = [row[0] for row in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
            t_assign = st.selectbox("متعلقہ استانی",t_list) if t_list else None
            if st.form_submit_button("محفوظ کریں") and t_assign:
                c.execute("INSERT INTO students (name,father_name,teacher_name) VALUES (?,?,?)",(s_name,f_name,t_assign))
                conn.commit()
                st.success("طالبہ کامیابی سے رجسٹر ہو گئی!")
                st.rerun()
        st.subheader("موجودہ طالبات (ترمیم / حذف)")
        df_s = pd.read_sql_query("SELECT id,name,father_name,teacher_name FROM students",conn)
        st.dataframe(df_s,use_container_width=True)
        del_s_id = st.number_input("حذف کرنے کے لیے طالبہ کی ID درج کریں",min_value=0,step=1,key="del_s")
        if st.button("طالبہ کو حذف کریں"): execute_delete("students",del_s_id)

# =====================================================================
# Teacher: Daily Hifz Entry (حفظ اندراج)
# =====================================================================
elif m=="📝 تعلیمی اندراج":
    st.header("📝 یومیہ تعلیمی اندراج")
    sel_date = st.date_input("تاریخ منتخب کریں", get_pkt_time().date())
    students = c.execute("SELECT name,father_name FROM students WHERE teacher_name=?",(st.session_state.username,)).fetchall()
    
    if not students: st.warning("آپ کی کلاس میں کوئی طالبہ نہیں ہے۔ منتظمہ سے رابطہ کریں۔")
    else:
        for s,f in students:
            with st.expander(f"👤 {s} بنت {f}"):
                att = st.radio("حاضری", ["حاضر","غیر حاضر","رخصت"], key=f"att_{s}", horizontal=True)
                if att=="حاضر":
                    # سبق
                    s_nagha = st.checkbox("سبق کا ناغہ", key=f"sn_{s}")
                    if not s_nagha:
                        c1,c2,c3 = st.columns([2,1,1])
                        surah = c1.selectbox("سورت", surahs_urdu,key=f"surah_{s}")
                        a_from = c2.text_input("آیت سے",key=f"af_{s}")
                        a_to = c3.text_input("آیت تک",key=f"at_{s}")
                        sabq_final = f"{surah}: {a_from}-{a_to}"
                    else: sabq_final="ناغہ"

                    # سبقی
                    sq_nagha = st.checkbox("سبقی کا ناغہ",key=f"sqn_{s}")
                    sq_list,sq_err,sq_atk=[],0,0
                    if not sq_nagha:
                        if f"sq_c_{s}" not in st.session_state: st.session_state[f"sq_c_{s}"]=1
                        for i in range(st.session_state[f"sq_c_{s}"]):
                            c1,c2,c3,c4 = st.columns([2,2,1,1])
                            p = c1.selectbox(f"پارہ",paras,key=f"sqp_{s}_{i}")
                            v = c2.selectbox(f"مقدار",["مکمل","آدھا","پون","پاؤ"],key=f"sqv_{s}_{i}")
                            a = c3.number_input(f"اٹکن",0,key=f"sqa_{s}_{i}")
                            e = c4.number_input(f"غلطی",0,key=f"sqe_{s}_{i}")
                            sq_list.append(f"{p}:{v}"); sq_atk+=a; sq_err+=e
                        if st.button("➕ مزید سبقی",key=f"add_sq_{s}"): st.session_state[f"sq_c_{s}"]+=1; st.rerun()
                    else: sq_list=["ناغہ"]

                    # منزل
                    m_nagha = st.checkbox("منزل کا ناغہ",key=f"mn_{s}")
                    m_list,m_err,m_atk=[],0,0
                    if not m_nagha:
                        if f"m_c_{s}" not in st.session_state: st.session_state[f"m_c_{s}"]=1
                        for i in range(st.session_state[f"m_c_{s}"]):
                            c1,c2,c3,c4 = st.columns([2,2,1,1])
                            p = c1.selectbox(f"پارہ",paras,key=f"mp_{s}_{i}")
                            v = c2.selectbox(f"مقدار",["مکمل","آدھا","پون","پاؤ"],key=f"mv_{s}_{i}")
                            a = c3.number_input(f"اٹکن",0,key=f"ma_{s}_{i}")
                            e = c4.number_input(f"غلطی",0,key=f"me_{s}_{i}")
                            m_list.append(f"{p}:{v}"); m_atk+=a; m_err+=e
                        if st.button("➕ مزید منزل",key=f"add_m_{s}"): st.session_state[f"m_c_{s}"]+=1; st.rerun()
                    else: m_list=["ناغہ"]

                    if st.button("محفوظ کریں",key=f"save_{s}"):
                        c.execute("INSERT INTO hifz_records (r_date,s_name,f_name,t_name,surah,sq_p,sq_a,sq_m,m_p,m_a,m_m,attendance) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (str(sel_date),s,f,st.session_state.username,sabq_final," | ".join(sq_list),sq_atk,sq_err," | ".join(m_list),m_atk,m_err,att))
                        conn.commit()
                        st.toast("ریکارڈ کامیابی سے محفوظ ہو گیا! ✅")
                else:
                    if st.button("حاضری لگائیں",key=f"save_absent_{s}"):
                        c.execute("INSERT INTO hifz_records (r_date,s_name,f_name,t_name,attendance,surah,sq_p,m_p) VALUES (?,?,?,?,?,?,?,?)",
                # ================== V5 Smart Madrasa System - Final (Part 3) ==================

# ------------------- Exams & Results -------------------
                elif m in ["🎓 امتحان کے لیے نامزدگی","🎓 امتحانات و نتائج"]:
                    st.header("🎓 امتحانی تعلیمی نظام")
                    if st.session_state.user_type=="teacher":
                    st.subheader("طالبہ کو امتحان کے لیے بھیجیں")
                    my_students = [f"{s[0]} بنت {s[1]}" for s in c.execute("SELECT name,father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()]
                if my_students:
                    sel_s = st.selectbox("طالبہ منتخب کریں", my_students)
            para_no = st.number_input("پارہ نمبر", 1, 30)
            if st.button("امتحان کی درخواست بھیجیں"):
                sn, fn = sel_s.split(" بنت ")
                c.execute("INSERT INTO exams (s_name,f_name,para_no,start_date,status) VALUES (?,?,?,?,?)",(sn,fn,para_no,str(date.today()),"پینڈنگ"))
                conn.commit()
                st.success("امتحان کی درخواست کامیابی سے بھیج دی گئی!")
        else: st.warning("آپ کی کلاس میں کوئی طالبہ نہیں ہے۔")
    else:
        tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات","📜 امتحانی ریکارڈ (پرنٹ/ترمیم)"])
        with tab1:
            pending = c.execute("SELECT id,s_name,f_name,para_no FROM exams WHERE status='پینڈنگ'").fetchall()
            if not pending: st.info("اس وقت کوئی پینڈنگ امتحان نہیں ہے۔")
            for eid,sn,fn,pn in pending:
                with st.expander(f"📝 {sn} بنت {fn} - پارہ {pn}"):
                    c1,c2,c3,c4,c5 = st.columns(5)
                    q1 = c1.number_input("سوال 1",0,20,key=f"q1_{eid}")
                    q2 = c2.number_input("سوال 2",0,20,key=f"q2_{eid}")
                    q3 = c3.number_input("سوال 3",0,20,key=f"q3_{eid}")
                    q4 = c4.number_input("سوال 4",0,20,key=f"q4_{eid}")
                    q5 = c5.number_input("سوال 5",0,20,key=f"q5_{eid}")
                    tot = q1+q2+q3+q4+q5
                    st.write(f"**کل نمبر:** {tot} / 100")
                    if st.button("نتیجہ محفوظ کریں",key=f"sv_{eid}"):
                        g = "ممتاز" if tot>=90 else "جید جداً" if tot>=80 else "جید" if tot>=70 else "مقبول" if tot>=60 else "فیل"
                        c.execute("UPDATE exams SET total=?,grade=?,status='مکمل',end_date=? WHERE id=?",(tot,g,str(date.today()),eid))
                        conn.commit()
                        st.success("نتیجہ محفوظ ہو گیا!")
                        st.rerun()
        with tab2:
            df_exams = pd.read_sql_query("SELECT id as 'ID', s_name as 'نام', f_name as 'ولدیت', para_no as 'پارہ', total as 'نمبر', grade as 'گریڈ', end_date as 'تاریخ' FROM exams WHERE status='مکمل'",conn)
            st.dataframe(df_exams,use_container_width=True)
            if not df_exams.empty: st.markdown(generate_html_print(df_exams.drop(columns=['ID']),"امتحانی ریکارڈ"),unsafe_allow_html=True)
            st.divider()
            del_ex = st.number_input("حذف کرنے کے لیے امتحان کی ID درج کریں",min_value=0,step=1,key="del_ex")
            if st.button("امتحان حذف کریں"): execute_delete("exams",del_ex)

# ------------------- Teacher Attendance -------------------
elif m=="🕒 میری حاضری":
    st.header("🕒 میری یومیہ حاضری")
    c1,c2 = st.columns(2)
    m_date = c1.date_input("تاریخ", date.today())
    m_time = c2.time_input("آمد کا وقت", get_pkt_time().time())
    if st.button("حاضری درج کریں"):
        sys_t = get_pkt_time().strftime("%Y-%m-%d %H:%M:%S")
        chk = c.execute("SELECT 1 FROM t_attendance WHERE t_name=? AND manual_date=?",(st.session_state.username,str(m_date))).fetchone()
        if chk: st.error("اس تاریخ کی حاضری پہلے ہی لگ چکی ہے۔")
        else:
            c.execute("INSERT INTO t_attendance (t_name,manual_date,manual_time,system_timestamp) VALUES (?,?,?,?)",(st.session_state.username,str(m_date),str(m_time),sys_t))
            conn.commit()
            st.success("حاضری کامیابی سے درج ہو گئی!")

elif m=="🕒 استاذہ کا ریکارڈ":
    st.header("🕒 استاذہ کی حاضری کا ریکارڈ")
    df_att = pd.read_sql_query("SELECT id as 'ID', t_name as 'استاد', manual_date as 'تاریخ', manual_time as 'وقتِ آمد' FROM t_attendance ORDER BY manual_date DESC",conn)
    st.dataframe(df_att,use_container_width=True)
    if not df_att.empty: st.markdown(generate_html_print(df_att.drop(columns=['ID']),"اساتذہ کی حاضری رپورٹ"),unsafe_allow_html=True)
    st.divider()
    del_att = st.number_input("حذف کرنے کے لیے حاضری کی ID درج کریں",min_value=0,step=1,key="del_att")
    if st.button("حاضری حذف کریں"): execute_delete("t_attendance",del_att)

# ------------------- Leave Requests -------------------
elif m=="📩 درخواستِ رخصت":
    st.header("📩 چھٹی کی درخواست بھیجیں")
    with st.form("leave"):
        l_type = st.selectbox("نوعیت",["بیماری","ضروری کام","دیگر"])
        days = st.number_input("کتنے دن کے لیے؟",1,30)
        rsn = st.text_area("تفصیلی وجہ")
        if st.form_submit_button("ارسال کریں"):
            c.execute("INSERT INTO leave_requests (t_name,l_type,days,reason,start_date,status) VALUES (?,?,?,?,?,?)",
                      (st.session_state.username,l_type,days,rsn,str(date.today()),"پینڈنگ"))
            conn.commit()
            st.success("درخواست مہتممہ کو بھیج دی گئی!")

elif m=="🏛️ مہتممہ پینل (رخصت)":
    st.header("🏛️ مہتممہ پینل - درخواستِ رخصت")
    reqs = c.execute("SELECT id,t_name,l_type,days,reason,start_date FROM leave_requests WHERE status='پینڈنگ'").fetchall()
    if not reqs: st.info("اس وقت چھٹی کی کوئی نئی درخواست نہیں ہے۔")
    for rid,tn,lt,d,rsn,sd in reqs:
        with st.expander(f"درخواست: {tn} ({lt} - {d} دن)"):
            st.write(f"**تفصیل:** {rsn}")
            st.write(f"**تاریخِ آغاز:** {sd}")
            c1,c2 = st.columns(2)
            if c1.button("✅ منظور کریں",key=f"app_{rid}"):
                c.execute("UPDATE leave_requests SET status='منظور' WHERE id=?",(rid,))
                conn.commit()
                st.rerun()
            if c2.button("❌ مسترد کریں",key=f"rej_{rid}"):
                c.execute("UPDATE leave_requests SET status='مسترد' WHERE id=?",(rid,))
                conn.commit()
                st.rerun()
    st.divider()
    st.subheader("سابقہ رخصت کا ریکارڈ")
    df_lv = pd.read_sql_query("SELECT t_name as 'استاد', l_type as 'نوعیت', days as 'دن', start_date as 'تاریخ', status as 'سٹیٹس' FROM leave_requests WHERE status!='پینڈنگ'",conn)
    st.dataframe(df_lv,use_container_width=True)
    if not df_lv.empty: st.markdown(generate_html_print(df_lv,"اساتذہ کی رخصت کا ریکارڈ"),unsafe_allow_html=True)

# ------------------- Monthly Report -------------------
elif m=="📜 ماہانہ رزلٹ کارڈ":
    st.header("📜 ماہانہ رزلٹ کارڈ (Generate & Print)")
    c1,c2,c3 = st.columns(3)
    m_year = c1.selectbox("سال",[2024,2025,2026])
    m_month = c2.selectbox("مہینہ",range(1,13))
    t_list = ["تمام"] + [row[0] for row in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
    sel_t = c3.selectbox("استاذہ",t_list)
    if st.button("رپورٹ تیار کریں"):
        start_dt = f"{m_year}-{m_month:02d}-01"
        end_dt = f"{m_year}-{m_month:02d}-31"
        q = "SELECT s_name as 'نام', COUNT(*) as 'کل دن', SUM(CASE WHEN attendance='حاضر' THEN 1 ELSE 0 END) as 'حاضریاں', SUM(CASE WHEN attendance!='حاضر' THEN 1 ELSE 0 END) as 'چھٹیاں', SUM(sq_m) as 'کل سبقی غلطیاں', SUM(m_m) as 'کل منزل غلطیاں' FROM hifz_records WHERE r_date BETWEEN ? AND ?"
        p = [start_dt,end_dt]
        if sel_t!="تمام": q+=" AND t_name=?"; p.append(sel_t)
        q+=" GROUP BY s_name"
        df_month = pd.read_sql_query(q,conn,params=p)
        if df_month.empty: st.warning("اس مہینے کا کوئی ریکارڈ نہیں ملا۔")
        else: st.dataframe(df_month,use_container_width=True)
        st.markdown(generate_html_print(df_month,f"ماہانہ رزلٹ کارڈ ({m_year}-{m_month:02d})"),unsafe_allow_html=True)
                                  (str(sel_date),s,f,st.session_state.username,att,"-","-","-"))
                        conn.commit()
                        st.toast(f"{att} لگ گئی! ✅")
