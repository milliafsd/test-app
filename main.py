import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import os
import pytz
import plotly.express as px
import traceback

# -------------------- 1. ڈیٹا بیس سیٹ اپ --------------------
DB_NAME = 'jamia_millia_v1.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # ٹیبلز کی تخلیق
    c.execute('''CREATE TABLE IF NOT EXISTS teachers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT, 
                  phone TEXT, address TEXT, id_card TEXT, photo TEXT, joining_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, mother_name TEXT, 
                  teacher_name TEXT, phone TEXT, address TEXT, id_card TEXT, photo TEXT, 
                  admission_date DATE, class TEXT, section TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                  surah TEXT, a_from TEXT, a_to TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, 
                  m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT, principal_note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT, 
                  actual_arrival TEXT, actual_departure TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, 
                  back_date DATE, status TEXT, request_date DATE, l_type TEXT, days INTEGER, 
                  notification_seen INTEGER DEFAULT 0)''')
    c.execute("""CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, f_name TEXT, para_no INTEGER, start_date TEXT, end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, grade TEXT, status TEXT, exam_type TEXT)""")
    c.execute('''CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, f_name TEXT, month_year TEXT, amount INTEGER, paid INTEGER,
            due_date DATE, payment_date DATE, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, message TEXT, target TEXT, created_at DATETIME, seen INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT, action TEXT, timestamp DATETIME, details TEXT)''')
    conn.commit()
    
    # نئے کالمز کا اضافہ (اگر پہلے سے نہ ہوں)
    cols = [
        ("teachers", "joining_date", "DATE"),
        ("students", "mother_name", "TEXT"), ("students", "class", "TEXT"), ("students", "section", "TEXT"),
        ("exams", "exam_type", "TEXT"),
        ("t_attendance", "actual_arrival", "TEXT"), ("t_attendance", "actual_departure", "TEXT")
    ]
    for t, col, typ in cols:
        try:
            c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except:
            pass
    
    # ڈیفالٹ ایڈمن
    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()
    conn.close()

init_db()

# -------------------- 2. ہیلپر فنکشنز --------------------
def log_audit(user, action, details=""):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO audit_log (user, action, timestamp, details) VALUES (?,?,?,?)",
                  (user, action, datetime.now(), details))
        conn.commit()
        conn.close()
    except:
        pass

def get_pk_time():
    tz = pytz.timezone('Asia/Karachi')
    return datetime.now(tz).strftime("%I:%M %p")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def generate_html_report(df, title, student_name="", start_date="", end_date=""):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>{title}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', Arial; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ</h2>
            <h3>{title}</h3>
            {f"<p><b>طالب علم:</b> {student_name} &nbsp;&nbsp; <b>تاریخ:</b> {start_date} تا {end_date}</p>" if student_name else ""}
        </div>
        {html_table}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط استاذ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

# -------------------- 3. اسٹائلنگ (موبائل فرینڈلی) --------------------
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ | سمارٹ ایجوکیشن پورٹل", layout="wide", initial_sidebar_state="expanded")

# زبان ٹوگل
if 'language' not in st.session_state:
    st.session_state.language = "urdu"

def set_lang(lang):
    st.session_state.language = lang
    st.rerun()

# جدید اسٹائل
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * {
        font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', Arial, sans-serif;
        box-sizing: border-box;
    }
    body {
        direction: rtl;
        text-align: right;
        background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
        margin: 0;
        padding: 0;
    }
    /* سائڈبار */
    .stSidebar {
        background: linear-gradient(180deg, #1e5631 0%, #0b2b1a 100%);
        color: white;
    }
    .stSidebar .stRadio label {
        color: white;
        font-weight: bold;
        font-size: 1rem;
    }
    /* بٹن */
    .stButton > button {
        background: linear-gradient(90deg, #1e5631, #2e7d32);
        color: white;
        border-radius: 30px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        width: 100%;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        background: linear-gradient(90deg, #2e7d32, #1e5631);
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    /* ہیڈر */
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #f1f8e9, #d4e0c9);
        padding: 1rem;
        border-radius: 20px;
        margin-bottom: 1rem;
        border-bottom: 4px solid #1e5631;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    /* کارڈ */
    .report-card {
        background: white;
        border-radius: 15px;
        padding: 1rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    /* ٹیبز */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 30px;
        padding: 0.5rem 1rem;
        background-color: #e0e0e0;
        transition: 0.2s;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #1e5631, #2e7d32);
        color: white;
    }
    /* ایکسپینڈر */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 10px;
        font-weight: bold;
    }
    /* موبائل کے لیے میڈیا کوئری */
    @media (max-width: 768px) {
        .stButton > button {
            padding: 0.4rem 0.8rem;
            font-size: 0.8rem;
        }
        .main-header h1 {
            font-size: 1.5rem;
        }
        .main-header p {
            font-size: 0.8rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0.3rem 0.8rem;
            font-size: 0.8rem;
        }
        .report-card {
            padding: 0.8rem;
        }
    }
    /* ڈیٹا فریم */
    .dataframe {
        direction: rtl;
        text-align: right;
        font-size: 0.9rem;
    }
    .stDataFrame {
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)

# سائڈبار میں زبان کا انتخاب
st.sidebar.markdown("## 🌐 زبان / Language")
lang_col1, lang_col2 = st.sidebar.columns(2)
if lang_col1.button("اردو", use_container_width=True):
    set_lang("urdu")
if lang_col2.button("English", use_container_width=True):
    set_lang("english")

# متن کی ترجمہ ڈکشنری
text = {
    "urdu": {
        "title": "جامعہ ملیہ اسلامیہ",
        "subtitle": "اسمارٹ تعلیمی و انتظامی پورٹل",
        "login": "لاگ ان پینل",
        "username": "صارف کا نام",
        "password": "پاسورڈ",
        "login_btn": "داخل ہوں",
        "error": "❌ غلط معلومات",
        "logout": "لاگ آؤٹ کریں",
    },
    "english": {
        "title": "Jamia Millia Islamia",
        "subtitle": "Smart Education & Management Portal",
        "login": "Login Panel",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "error": "❌ Invalid credentials",
        "logout": "Logout",
    }
}
lang = st.session_state.language
T = text[lang]

# ہیڈر
st.markdown(f"<div class='main-header'><h1>🕌 {T['title']}</h1><p>{T['subtitle']}</p></div>", unsafe_allow_html=True)

# -------------------- 4. لاگ ان --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown(f"<div class='report-card'><h3>🔐 {T['login']}</h3>", unsafe_allow_html=True)
        u = st.text_input(T['username'])
        p = st.text_input(T['password'], type="password")
        if st.button(T['login_btn']):
            conn = get_db_connection()
            c = conn.cursor()
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            conn.close()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                log_audit(u, "Login", f"User logged in as {st.session_state.user_type}")
                st.rerun()
            else:
                st.error(T['error'])
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -------------------- 5. مینو --------------------
if st.session_state.user_type == "admin":
    menu = [
        "📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
        "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری", "💰 فیس مینجمنٹ",
        "👥 یوزر مینجمنٹ", "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس",
        "⚙️ بیک اپ & سیٹنگز"
    ]
else:
    menu = [
        "📝 تعلیمی اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
        "🕒 میری حاضری", "💰 میرے طلبہ کی فیس", "📢 نوٹیفیکیشنز"
    ]

selected = st.sidebar.radio("📌 مینو", menu)

# -------------------- 6. مختلف سیکشنز (ایڈمن) --------------------
if selected == "📊 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.markdown("<h2 style='text-align: center;'>📊 ماسٹر تعلیمی رپورٹ</h2>", unsafe_allow_html=True)
    with st.sidebar:
        d1 = st.date_input("آغاز", date.today().replace(day=1))
        d2 = st.date_input("اختتام", date.today())
        conn = get_db_connection()
        t_list = ["تمام"] + [t[0] for t in conn.execute("SELECT DISTINCT t_name FROM hifz_records").fetchall()]
        s_list = ["تمام"] + [s[0] for s in conn.execute("SELECT DISTINCT s_name FROM hifz_records").fetchall()]
        conn.close()
        sel_t = st.selectbox("استاد", t_list)
        sel_s = st.selectbox("طالب علم", s_list)
    query = "SELECT * FROM hifz_records WHERE r_date BETWEEN ? AND ?"
    params = [d1, d2]
    if sel_t != "تمام":
        query += " AND t_name = ?"
        params.append(sel_t)
    if sel_s != "تمام":
        query += " AND s_name = ?"
        params.append(sel_s)
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error(f"ڈیٹا لوڈ کرنے میں خرابی: {str(e)}")
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        # خلاصہ
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("کل ریکارڈ", len(df))
        col2.metric("حاضر طلباء", len(df[df['attendance'] == 'حاضر']))
        col3.metric("اوسط سبقی غلطی", round(df['sq_m'].mean(), 1))
        col4.metric("اوسط منزل غلطی", round(df['m_m'].mean(), 1))
        # تاریخ وار گروپ
        dates = sorted(df['r_date'].unique())
        for d in dates:
            with st.expander(f"📆 {d}"):
                sub = df[df['r_date'] == d]
                edited = st.data_editor(sub, key=f"edit_{d}", use_container_width=True, num_rows="dynamic")
                if st.button(f"💾 محفوظ کریں ({d})"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM hifz_records WHERE r_date=?", (d,))
                    edited.to_sql('hifz_records', conn, if_exists='append', index=False)
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Edit Daily Report", f"Date: {d}")
                    st.success("محفوظ ہو گیا")
                    st.rerun()
        # ڈاؤن لوڈ
        csv = convert_df_to_csv(df)
        st.download_button("📥 CSV ڈاؤن لوڈ", csv, "daily_report.csv")
        if st.button("🖨️ پرنٹ رپورٹ"):
            html = generate_html_report(df, "یومیہ تعلیمی رپورٹ", start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

elif selected == "📜 ماہانہ رزلٹ کارڈ":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    conn = get_db_connection()
    students_list = [s[0] for s in conn.execute("SELECT DISTINCT name FROM students").fetchall()]
    conn.close()
    if not students_list:
        st.warning("کوئی طالب علم نہیں")
    else:
        sel_s = st.selectbox("طالب علم", students_list)
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        conn = get_db_connection()
        query = """SELECT r_date as تاریخ, attendance as حاضری,
                   surah as 'سبق (آیت تا آیت)',
                   sq_p as 'سبقی (پارہ)', sq_m as 'سبقی (غلطی)', sq_a as 'سبقی (اٹکن)',
                   m_p as 'منزل (پارہ)', m_m as 'منزل (غلطی)', m_a as 'منزل (اٹکن)'
                   FROM hifz_records WHERE s_name=? AND r_date BETWEEN ? AND ?
                   ORDER BY r_date ASC"""
        try:
            df = pd.read_sql_query(query, conn, params=(sel_s, start, end))
        except Exception as e:
            st.error(f"ڈیٹا لوڈ کرنے میں خرابی: {str(e)}")
            df = pd.DataFrame()
        conn.close()
        if df.empty:
            st.warning("کوئی ریکارڈ نہیں")
        else:
            st.dataframe(df, use_container_width=True)
            html = generate_html_report(df, "ماہانہ رزلٹ کارڈ", student_name=sel_s, start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
            st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{sel_s}_result.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.header("🕒 اساتذہ کی حاضری کا ریکارڈ")
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    except Exception as e:
        st.error(f"خرابی: {str(e)}")
        df = pd.DataFrame()
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 CSV ڈاؤن لوڈ", convert_df_to_csv(df), "teacher_attendance.csv")
    else:
        st.info("کوئی ریکارڈ نہیں")

elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("🏛️ رخصت کی منظوری")
    conn = get_db_connection()
    c = conn.cursor()
    pending = c.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE ?", ('%پینڈنگ%',)).fetchall()
    conn.close()
    if not pending:
        st.info("کوئی نئی درخواست نہیں")
    else:
        for l_id, t_n, l_t, reas, s_d, dys in pending:
            with st.expander(f"📌 {t_n} | {l_t} | {dys} دن"):
                st.write(f"وجہ: {reas}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور", key=f"app_{l_id}"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("UPDATE leave_requests SET status=? WHERE id=?", ("منظور شدہ ✅", l_id))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Leave Approved", f"Teacher: {t_n}")
                    st.success("منظور کر دی گئی")
                    st.rerun()
                if col2.button("❌ مسترد", key=f"rej_{l_id}"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("UPDATE leave_requests SET status=? WHERE id=?", ("مسترد شدہ ❌", l_id))
                    conn.commit()
                    conn.close()
                    st.success("مسترد کر دی گئی")
                    st.rerun()

elif selected == "💰 فیس مینجمن트":
    st.header("💰 فیس مینجمنٹ")
    tab1, tab2 = st.tabs(["💰 فیس جمع کریں", "📊 بقایا جات"])
    with tab1:
        conn = get_db_connection()
        students = conn.execute("SELECT name, father_name FROM students").fetchall()
        conn.close()
        if not students:
            st.warning("کوئی طالب علم نہیں")
        else:
            s_list = [f"{s[0]} ولد {s[1]}" for s in students]
            sel = st.selectbox("طالب علم", s_list)
            s_name, f_name = sel.split(" ولد ")
            month_year = st.selectbox("ماہ / سال", [f"{m}/{datetime.now().year}" for m in range(1,13)] + [f"{m}/{datetime.now().year-1}" for m in range(1,13)])
            amount = st.number_input("ماہانہ فیس", min_value=0, value=500)
            due_date = st.date_input("آخری تاریخ", date.today() + timedelta(days=15))
            if st.button("🎯 فیس جمع کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO fees (s_name, f_name, month_year, amount, paid, due_date, status) VALUES (?,?,?,?,?,?,?)",
                          (s_name, f_name, month_year, amount, 0, due_date, "بقایا"))
                conn.commit()
                conn.close()
                st.success("فیس ریکارڈ شامل کر دی گئی")
                log_audit(st.session_state.username, "Fee Added", f"{s_name} - {month_year}")
    with tab2:
        conn = get_db_connection()
        try:
            df = pd.read_sql_query("SELECT s_name as نام, f_name as ولدیت, month_year as ماہ, amount as رقم, paid as ادا, due_date as آخری_تاریخ, status as حالت FROM fees", conn)
        except Exception as e:
            st.error(f"خرابی: {str(e)}")
            df = pd.DataFrame()
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.download_button("بقایا جات کی رپورٹ ڈاؤن لوڈ کریں", convert_df_to_csv(df), "fees_report.csv")
        else:
            st.info("کوئی فیس ریکارڈ نہیں")

elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 اساتذہ و طلبہ مینجمنٹ")
    t1, t2 = st.tabs(["اساتذہ", "طلبہ"])
    with t1:
        conn = get_db_connection()
        teachers = pd.read_sql_query("SELECT id, name, password, phone, address, id_card FROM teachers", conn)
        conn.close()
        edited = st.data_editor(teachers, num_rows="dynamic", use_container_width=True, key="teachers_edit")
        if st.button("اساتذہ کی تبدیلیاں محفوظ کریں"):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("DELETE FROM teachers")
            for _, row in edited.iterrows():
                c.execute("INSERT INTO teachers (id, name, password, phone, address, id_card) VALUES (?,?,?,?,?,?)",
                          (row['id'], row['name'], row['password'], row['phone'], row['address'], row['id_card']))
            conn.commit()
            conn.close()
            log_audit(st.session_state.username, "Teachers Updated")
            st.success("محفوظ ہو گیا")
            st.rerun()
        with st.expander("نیا استاد شامل کریں"):
            with st.form("new_teacher"):
                name = st.text_input("نام")
                pwd = st.text_input("پاسورڈ")
                phone = st.text_input("فون")
                address = st.text_input("پتہ")
                idcard = st.text_input("شناختی کارڈ")
                submitted = st.form_submit_button("شامل کریں")
                if submitted:
                    if name and pwd:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("INSERT INTO teachers (name, password, phone, address, id_card) VALUES (?,?,?,?,?)",
                                  (name, pwd, phone, address, idcard))
                        conn.commit()
                        conn.close()
                        st.success("استاد شامل ہو گیا")
                        st.rerun()
    with t2:
        conn = get_db_connection()
        students = pd.read_sql_query("SELECT id, name, father_name, mother_name, teacher_name, phone, address, id_card, admission_date, class, section FROM students", conn)
        conn.close()
        edited = st.data_editor(students, num_rows="dynamic", use_container_width=True, key="students_edit")
        if st.button("طلبہ کی تبدیلیاں محفوظ کریں"):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("DELETE FROM students")
            for _, row in edited.iterrows():
                c.execute("INSERT INTO students (id, name, father_name, mother_name, teacher_name, phone, address, id_card, admission_date, class, section) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (row['id'], row['name'], row['father_name'], row['mother_name'], row['teacher_name'], row['phone'], row['address'], row['id_card'], row['admission_date'], row['class'], row['section']))
            conn.commit()
            conn.close()
            st.success("محفوظ ہو گیا")
            st.rerun()
        with st.expander("نیا طالب علم شامل کریں"):
            with st.form("new_student"):
                s_name = st.text_input("نام")
                s_father = st.text_input("والد کا نام")
                s_mother = st.text_input("والدہ کا نام")
                conn = get_db_connection()
                teacher_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                conn.close()
                s_teacher = st.selectbox("استاد", teacher_list) if teacher_list else None
                s_phone = st.text_input("فون")
                s_address = st.text_input("پتہ")
                s_idcard = st.text_input("شناختی کارڈ (B-Form)")
                s_admission = st.date_input("داخلہ تاریخ", date.today())
                s_class = st.text_input("کلاس")
                s_section = st.text_input("سیکشن")
                submitted = st.form_submit_button("داخل کریں")
                if submitted:
                    if s_name and s_father and s_teacher:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("INSERT INTO students (name, father_name, mother_name, teacher_name, phone, address, id_card, admission_date, class, section) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                  (s_name, s_father, s_mother, s_teacher, s_phone, s_address, s_idcard, s_admission, s_class, s_section))
                        conn.commit()
                        conn.close()
                        st.success("داخلہ کامیاب")
                        st.rerun()

elif selected == "📢 نوٹیفیکیشنز":
    st.header("📢 نوٹیفیکیشن سینٹر")
    if st.session_state.user_type == "admin":
        with st.form("new_notification"):
            title = st.text_input("عنوان")
            message = st.text_area("پیغام")
            target = st.selectbox("بھیجیں", ["تمام", "اساتذہ", "طلبہ"])
            submitted = st.form_submit_button("نوٹیفکیشن بھیجیں")
            if submitted:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO notifications (title, message, target, created_at) VALUES (?,?,?,?)",
                          (title, message, target, datetime.now()))
                conn.commit()
                conn.close()
                st.success("بھیج دیا گیا")
    # دکھائیں
    conn = get_db_connection()
    if st.session_state.user_type == "admin":
        notifs = conn.execute("SELECT title, message, created_at FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()
    else:
        notifs = conn.execute("SELECT title, message, created_at FROM notifications WHERE target IN ('تمام','اساتذہ') ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    for n in notifs:
        st.info(f"**{n[0]}**\n\n{n[1]}\n\n*{n[2]}*")

elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("📈 ڈیٹا تجزیہ")
    conn = get_db_connection()
    att_df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد FROM t_attendance", conn)
    if not att_df.empty:
        fig = px.bar(att_df, x='تاریخ', title='اساتذہ کی حاضری')
        st.plotly_chart(fig, use_container_width=True)
    rec_df = pd.read_sql_query("SELECT s_name as نام, sq_m as سبقی_غلطی, m_m as منزل_غلطی FROM hifz_records", conn)
    if not rec_df.empty:
        fig2 = px.scatter(rec_df, x='سبقی_غلطی', y='منزل_غلطی', color='نام', title='غلطیوں کا تجزیہ')
        st.plotly_chart(fig2, use_container_width=True)
    conn.close()

elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("⚙️ بیک اپ اور سیٹنگز")
    if st.button("💾 ڈیٹا بیس کا بیک اپ (CSV)"):
        tables = ["teachers", "students", "hifz_records", "t_attendance", "leave_requests", "exams", "fees", "notifications", "audit_log"]
        conn = get_db_connection()
        for t in tables:
            try:
                df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
                df.to_csv(f"{t}_backup.csv", index=False)
            except:
                pass
        conn.close()
        st.success("بیک اپ مکمل! (ہر ٹیبل کی CSV فائل بن گئی)")
    with st.expander("آڈٹ لاگ"):
        conn = get_db_connection()
        logs = pd.read_sql_query("SELECT user, action, timestamp, details FROM audit_log ORDER BY timestamp DESC LIMIT 100", conn)
        conn.close()
        st.dataframe(logs, use_container_width=True)

# -------------------- 7. استاد کے سیکشن --------------------
elif selected == "📝 تعلیمی اندراج" and st.session_state.user_type == "teacher":
    st.header("🚀 تعلیمی اندراج")
    sel_date = st.date_input("تاریخ", date.today())
    conn = get_db_connection()
    students = conn.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
    conn.close()
    if not students:
        st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
    else:
        with st.form("daily_entry"):
            records = []
            for s, f in students:
                st.markdown(f"### 👤 {s} ولد {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر"], key=f"att_{s}", horizontal=True)
                if att == "حاضر":
                    surah = st.selectbox("سورت", ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"], key=f"surah_{s}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{s}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{s}")
                    sabq = f"{surah}: {a_from}-{a_to}"
                    
                    # سبقی
                    sq_count = st.number_input("سبقی پاروں کی تعداد", 1, 5, 1, key=f"sqc_{s}")
                    sq_parts = []
                    sq_a = sq_m = 0
                    for i in range(sq_count):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", [f"پارہ {j}" for j in range(1,31)], key=f"sqp_{s}_{i}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{s}_{i}")
                        a = cols[2].number_input("اٹکن", 0, key=f"sqa_{s}_{i}")
                        e = cols[3].number_input("غلطی", 0, key=f"sqe_{s}_{i}")
                        sq_parts.append(f"{p}:{v}")
                        sq_a += a
                        sq_m += e
                    
                    # منزل
                    m_count = st.number_input("منزل پاروں کی تعداد", 1, 5, 1, key=f"mc_{s}")
                    m_parts = []
                    m_a = m_m = 0
                    for j in range(m_count):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", [f"پارہ {j}" for j in range(1,31)], key=f"mp_{s}_{j}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{s}_{j}")
                        a = cols[2].number_input("اٹکن", 0, key=f"ma_{s}_{j}")
                        e = cols[3].number_input("غلطی", 0, key=f"me_{s}_{j}")
                        m_parts.append(f"{p}:{v}")
                        m_a += a
                        m_m += e
                else:
                    sabq = "ناغہ"
                    sq_parts = ["ناغہ"]
                    sq_a = sq_m = 0
                    m_parts = ["ناغہ"]
                    m_a = m_m = 0
                records.append((sel_date, s, f, st.session_state.username, sabq,
                                " | ".join(sq_parts), sq_a, sq_m,
                                " | ".join(m_parts), m_a, m_m, att))
            submitted = st.form_submit_button("محفوظ کریں")
            if submitted:
                conn = get_db_connection()
                c = conn.cursor()
                duplicate = False
                for rec in records:
                    chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND f_name=?", (rec[0], rec[1], rec[2])).fetchone()
                    if chk:
                        st.error(f"{rec[1]} کا ریکارڈ پہلے سے موجود ہے")
                        duplicate = True
                        break
                if not duplicate:
                    for rec in records:
                        c.execute("""INSERT INTO hifz_records 
                                    (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", rec)
                    conn.commit()
                    log_audit(st.session_state.username, "Daily Entry", f"Date: {sel_date}")
                    st.success("محفوظ ہو گیا")
                    st.rerun()
                conn.close()

elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("🎓 امتحان کے لیے طالب علم نامزد کریں")
    conn = get_db_connection()
    students = conn.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
    conn.close()
    if not students:
        st.warning("کوئی طالب علم نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s[0]} ولد {s[1]}" for s in students]
            sel = st.selectbox("طالب علم", s_list)
            para = st.number_input("پارہ نمبر", 1, 30)
            exam_type = st.selectbox("امتحان کی قسم", ["ماہانہ", "سہ ماہی", "سالانہ"])
            submitted = st.form_submit_button("بھیجیں")
            if submitted:
                s_name, f_name = sel.split(" ولد ")
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status, exam_type) VALUES (?,?,?,?,?,?)",
                          (s_name, f_name, para, date.today(), "پینڈنگ", exam_type))
                conn.commit()
                conn.close()
                st.success("درخواست بھیج دی گئی")

elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.header("📩 رخصت کی درخواست")
    with st.form("leave"):
        l_type = st.selectbox("نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        s_date = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دن", 1, 15, 1)
        e_date = s_date + timedelta(days=days-1)
        st.write(f"واپسی: {e_date}")
        reason = st.text_area("وجہ")
        submitted = st.form_submit_button("درخواست کریں")
        if submitted:
            if reason:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO leave_requests (t_name, l_type, start_date, days, reason, status, notification_seen) VALUES (?,?,?,?,?,?,?)",
                          (st.session_state.username, l_type, s_date, days, reason, "پینڈنگ", 0))
                conn.commit()
                conn.close()
                st.success("درخواست بھیج دی گئی")

elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    conn = get_db_connection()
    c = conn.cursor()
    rec = c.execute("SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?", (st.session_state.username, today)).fetchone()
    conn.close()
    if not rec:
        col1, col2 = st.columns(2)
        arr_date = col1.date_input("تاریخ", today)
        arr_time = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں"):
            time_str = arr_time.strftime("%I:%M %p")
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO t_attendance (t_name, a_date, arrival, actual_arrival) VALUES (?,?,?,?)",
                      (st.session_state.username, arr_date, time_str, get_pk_time()))
            conn.commit()
            conn.close()
            st.success("آمد درج ہو گئی")
            st.rerun()
    elif rec and rec[1] is None:
        st.success(f"آمد: {rec[0]}")
        dep_time = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("رخصت درج کریں"):
            time_str = dep_time.strftime("%I:%M %p")
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("UPDATE t_attendance SET departure=?, actual_departure=? WHERE t_name=? AND a_date=?",
                      (time_str, get_pk_time(), st.session_state.username, today))
            conn.commit()
            conn.close()
            st.success("رخصت درج ہو گئی")
            st.rerun()
    else:
        st.success(f"آمد: {rec[0]} | رخصت: {rec[1]}")

elif selected == "💰 میرے طلبہ کی فیس" and st.session_state.user_type == "teacher":
    st.header("💰 میرے طلبہ کی فیس")
    conn = get_db_connection()
    students = conn.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
    conn.close()
    if not students:
        st.info("کوئی طالب علم نہیں")
    else:
        for s, f in students:
            with st.expander(f"{s} ولد {f}"):
                conn = get_db_connection()
                fees = conn.execute("SELECT month_year, amount, paid, status FROM fees WHERE s_name=? AND f_name=?", (s, f)).fetchall()
                conn.close()
                if fees:
                    df = pd.DataFrame(fees, columns=["ماہ", "رقم", "ادا", "حالت"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.write("کوئی فیس ریکارڈ نہیں")

# -------------------- 8. امتحانی نظام (ایڈمن) --------------------
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام")
    tab1, tab2 = st.tabs(["پینڈنگ امتحانات", "مکمل شدہ"])
    with tab1:
        conn = get_db_connection()
        pending = conn.execute("SELECT id, s_name, f_name, para_no, start_date, exam_type FROM exams WHERE status=?", ("پینڈنگ",)).fetchall()
        conn.close()
        if not pending:
            st.info("کوئی پینڈنگ امتحان نہیں")
        else:
            for eid, sn, fn, pn, sd, etype in pending:
                with st.expander(f"{sn} ولد {fn} | پارہ {pn} | {etype}"):
                    cols = st.columns(5)
                    q1 = cols[0].number_input("س1", 0, 20, key=f"q1_{eid}")
                    q2 = cols[1].number_input("س2", 0, 20, key=f"q2_{eid}")
                    q3 = cols[2].number_input("س3", 0, 20, key=f"q3_{eid}")
                    q4 = cols[3].number_input("س4", 0, 20, key=f"q4_{eid}")
                    q5 = cols[4].number_input("س5", 0, 20, key=f"q5_{eid}")
                    total = q1+q2+q3+q4+q5
                    if total >= 90: g = "ممتاز"
                    elif total >= 80: g = "جید جداً"
                    elif total >= 70: g = "جید"
                    elif total >= 60: g = "مقبول"
                    else: g = "ناکام"
                    st.write(f"کل: {total} | گریڈ: {g}")
                    if st.button("کلیئر کریں", key=f"save_{eid}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? WHERE id=?",
                                  (q1,q2,q3,q4,q5,total,g,"مکمل", date.today(), eid))
                        conn.commit()
                        conn.close()
                        st.success("محفوظ ہو گیا")
                        st.rerun()
    with tab2:
        conn = get_db_connection()
        hist = pd.read_sql_query("SELECT s_name, f_name, para_no, total, grade, status FROM exams WHERE status!='پینڈنگ'", conn)
        conn.close()
        st.dataframe(hist, use_container_width=True)
        st.download_button("ہسٹری ڈاؤن لوڈ", convert_df_to_csv(hist), "exam_history.csv")

# -------------------- 9. لاگ آؤٹ --------------------
st.sidebar.divider()
if st.sidebar.button("🚪 " + T['logout']):
    st.session_state.logged_in = False
    st.rerun()
