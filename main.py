import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
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

def get_grade_from_mistakes(total_mistakes):
    """غلطیوں کی تعداد کے مطابق گریڈ"""
    if total_mistakes <= 2: return "ممتاز"
    elif total_mistakes <= 5: return "جید جداً"
    elif total_mistakes <= 8: return "جید"
    elif total_mistakes <= 12: return "مقبول"
    else: return "دوبارہ کوشش کریں"

def generate_html_report(df, title, student_name="", start_date="", end_date=""):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
        body {{ font-family: 'Noto Nastaliq Urdu', Arial; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
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
            <button onclick="window.print()" style="padding:10px 20px; background:#1e5631; color:white; border:none; border-radius:5px;">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

# -------------------- 3. اسٹائلنگ --------------------
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ | پورٹل", layout="wide", initial_sidebar_state="expanded")

if 'language' not in st.session_state:
    st.session_state.language = "urdu"

def set_lang(lang):
    st.session_state.language = lang
    st.rerun()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * { font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', Arial, sans-serif; }
    body { direction: rtl; text-align: right; background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%); }
    .stSidebar { background: linear-gradient(180deg, #1e5631 0%, #0b2b1a 100%); color: white; }
    .stSidebar .stRadio label { color: white !important; font-weight: bold; }
    .stButton > button { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; border-radius: 30px; border: none; font-weight: bold; width: 100%; transition: 0.3s; }
    .stButton > button:hover { transform: scale(1.02); }
    .main-header { text-align: center; background: linear-gradient(135deg, #f1f8e9, #d4e0c9); padding: 1rem; border-radius: 20px; margin-bottom: 1rem; border-bottom: 4px solid #1e5631; }
    .report-card { background: white; border-radius: 15px; padding: 1.5rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; border-radius: 30px; }
    .dataframe { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# سائڈبار زبان
st.sidebar.markdown("## 🌐 زبان / Language")
lang_col1, lang_col2 = st.sidebar.columns(2)
if lang_col1.button("اردو", use_container_width=True): set_lang("urdu")
if lang_col2.button("English", use_container_width=True): set_lang("english")

T = {
    "urdu": {"title": "جامعہ ملیہ اسلامیہ", "subtitle": "اسمارٹ تعلیمی و انتظامی پورٹل", "login": "لاگ ان پینل", "username": "صارف کا نام", "password": "پاسورڈ", "login_btn": "داخل ہوں", "error": "❌ غلط معلومات", "logout": "لاگ آؤٹ کریں"},
    "english": {"title": "Jamia Millia Islamia", "subtitle": "Smart Education & Management Portal", "login": "Login Panel", "username": "Username", "password": "Password", "login_btn": "Login", "error": "❌ Invalid credentials", "logout": "Logout"}
}[st.session_state.language]

st.markdown(f"<div class='main-header'><h1>🕌 {T['title']}</h1><p>{T['subtitle']}</p></div>", unsafe_allow_html=True)

# -------------------- 4. لاگ ان --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown(f"<div class='report-card'><h3 style='text-align:center;'>🔐 {T['login']}</h3>", unsafe_allow_html=True)
        u = st.text_input(T['username'])
        p = st.text_input(T['password'], type="password")
        if st.button(T['login_btn']):
            conn = get_db_connection()
            res = conn.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            conn.close()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                log_audit(u, "Login", f"Logged in as {st.session_state.user_type}")
                st.rerun()
            else:
                st.error(T['error'])
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -------------------- 5. مینو --------------------
if st.session_state.user_type == "admin":
    menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری", "👥 یوزر مینجمنٹ", "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس", "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 تعلیمی اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست", "🕒 میری حاضری", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

# -------------------- 6. سورتوں کی فہرست --------------------
surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# -------------------- 7. ایڈمن سیکشن --------------------
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
    
    query = "SELECT id, r_date as تاریخ, s_name as نام, f_name as ولدیت, t_name as استاد, surah as سبق, sq_m as سبقی_غلطی, m_m as منزل_غلطی, attendance as حاضری FROM hifz_records WHERE r_date BETWEEN ? AND ?"
    params = [d1, d2]
    if sel_t != "تمام":
        query += " AND t_name = ?"
        params.append(sel_t)
    if sel_s != "تمام":
        query += " AND s_name = ?"
        params.append(sel_s)
    
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        df['کل_غلطیاں'] = df['سبقی_غلطی'] + df['منزل_غلطی']
        df['درجہ'] = df['کل_غلطیاں'].apply(get_grade_from_mistakes)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("کل ریکارڈ", len(df))
        col2.metric("حاضر طلباء", len(df[df['حاضری'] == 'حاضر']))
        col3.metric("اوسط غلطیاں", round(df['کل_غلطیاں'].mean(), 1))
        col4.metric("مجموعی درجہ", get_grade_from_mistakes(df['کل_غلطیاں'].mean()))
        
        dates = sorted(df['تاریخ'].unique())
        for d in dates:
            with st.expander(f"📆 {d}"):
                sub = df[df['تاریخ'] == d].copy()
                edited = st.data_editor(sub, key=f"edit_{d}", use_container_width=True, hide_index=True, disabled=["id", "تاریخ", "نام", "ولدیت", "استاد", "کل_غلطیاں", "درجہ"])
                if st.button(f"💾 تبدیلیاں محفوظ کریں ({d})"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for _, row in edited.iterrows():
                        c.execute("UPDATE hifz_records SET surah=?, sq_m=?, m_m=?, attendance=? WHERE id=?", 
                                  (row['سبق'], row['سبقی_غلطی'], row['منزل_غلطی'], row['حاضری'], row['id']))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Edit Report", f"Date: {d}")
                    st.success("تبدیلیاں کامیابی سے محفوظ ہو گئیں۔")
                    st.rerun()
        
        csv = convert_df_to_csv(df.drop(columns=['id']))
        st.download_button("📥 CSV ڈاؤن لوڈ", csv, "daily_report.csv")
        if st.button("🖨️ پرنٹ رپورٹ"):
            html = generate_html_report(df.drop(columns=['id']), "یومیہ تعلیمی رپورٹ", start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

elif selected == "📜 ماہانہ رزلٹ کارڈ":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    conn = get_db_connection()
    students_list = [s[0] for s in conn.execute("SELECT DISTINCT name FROM students").fetchall()]
    conn.close()
    if not students_list: st.warning("کوئی طالب علم نہیں")
    else:
        sel_s = st.selectbox("طالب علم", students_list)
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        
        conn = get_db_connection()
        query = """SELECT r_date as تاریخ, attendance as حاضری, surah as 'سبق', sq_p as 'سبقی (پارہ)', sq_m as 'سبقی (غلطی)', m_p as 'منزل (پارہ)', m_m as 'منزل (غلطی)' 
                   FROM hifz_records WHERE s_name=? AND r_date BETWEEN ? AND ? ORDER BY r_date ASC"""
        df = pd.read_sql_query(query, conn, params=(sel_s, start, end))
        conn.close()
        
        if df.empty: st.warning("کوئی ریکارڈ نہیں")
        else:
            df['کل_غلطیاں'] = df['سبقی (غلطی)'] + df['منزل (غلطی)']
            df['درجہ'] = df['کل_غلطیاں'].apply(get_grade_from_mistakes)
            st.dataframe(df, use_container_width=True)
            html = generate_html_report(df, "ماہانہ رزلٹ کارڈ", student_name=sel_s, start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.header("🕒 اساتذہ کی حاضری")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    conn.close()
    if not df.empty: st.dataframe(df, use_container_width=True)
    else: st.info("کوئی ریکارڈ نہیں")

elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("🏛️ رخصت کی منظوری")
    conn = get_db_connection()
    pending = conn.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE '%پینڈنگ%'").fetchall()
    conn.close()
    if not pending: st.info("کوئی نئی درخواست نہیں")
    for l_id, t_n, l_t, reas, s_d, dys in pending:
        with st.expander(f"📌 {t_n} | {l_t} | {dys} دن"):
            st.write(f"وجہ: {reas}")
            c1, c2 = st.columns(2)
            if c1.button("✅ منظور", key=f"app_{l_id}"):
                conn = get_db_connection()
                conn.execute("UPDATE leave_requests SET status='منظور شدہ ✅' WHERE id=?", (l_id,))
                conn.commit(); conn.close(); st.rerun()
            if c2.button("❌ مسترد", key=f"rej_{l_id}"):
                conn = get_db_connection()
                conn.execute("UPDATE leave_requests SET status='مسترد شدہ ❌' WHERE id=?", (l_id,))
                conn.commit(); conn.close(); st.rerun()

elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 اساتذہ و طلبہ مینجمنٹ")
    t1, t2 = st.tabs(["اساتذہ", "طلبہ"])
    with t1:
        conn = get_db_connection()
        teachers = pd.read_sql_query("SELECT id, name, password, phone, address, id_card FROM teachers", conn)
        conn.close()
        edited = st.data_editor(teachers, num_rows="dynamic", use_container_width=True)
        if st.button("تبدیلیاں محفوظ کریں (اساتذہ)"):
            conn = get_db_connection(); c = conn.cursor()
            c.execute("DELETE FROM teachers")
            for _, r in edited.iterrows():
                c.execute("INSERT INTO teachers (id, name, password, phone, address, id_card) VALUES (?,?,?,?,?,?)", (r['id'], r['name'], r['password'], r['phone'], r['address'], r['id_card']))
            conn.commit(); conn.close(); st.success("محفوظ ہو گیا"); st.rerun()

    with t2:
        conn = get_db_connection()
        students = pd.read_sql_query("SELECT id, name, father_name, teacher_name, phone, class FROM students", conn)
        conn.close()
        edited_s = st.data_editor(students, num_rows="dynamic", use_container_width=True)
        if st.button("تبدیلیاں محفوظ کریں (طلبہ)"):
            conn = get_db_connection(); c = conn.cursor()
            c.execute("DELETE FROM students")
            for _, r in edited_s.iterrows():
                c.execute("INSERT INTO students (id, name, father_name, teacher_name, phone, class) VALUES (?,?,?,?,?,?)", (r['id'], r['name'], r['father_name'], r['teacher_name'], r['phone'], r['class']))
            conn.commit(); conn.close(); st.success("محفوظ ہو گیا"); st.rerun()

        with st.expander("نیا طالب علم شامل کریں"):
            s_name = st.text_input("نام")
            s_father = st.text_input("والد کا نام")
            conn = get_db_connection()
            teacher_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
            conn.close()
            s_teacher = st.selectbox("استاد", teacher_list) if teacher_list else None
            if st.button("داخل کریں"):
                conn = get_db_connection()
                conn.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (s_name, s_father, s_teacher))
                conn.commit(); conn.close(); st.success("داخلہ کامیاب"); st.rerun()

elif selected == "📢 نوٹیفیکیشنز":
    st.header("📢 نوٹیفیکیشن سینٹر")
    if st.session_state.user_type == "admin":
        title = st.text_input("عنوان")
        message = st.text_area("پیغام")
        target = st.selectbox("بھیجیں", ["تمام", "اساتذہ", "طلبہ"])
        if st.button("نوٹیفکیشن بھیجیں"):
            conn = get_db_connection()
            conn.execute("INSERT INTO notifications (title, message, target, created_at) VALUES (?,?,?,?)", (title, message, target, datetime.now()))
            conn.commit(); conn.close(); st.success("بھیج دیا گیا")
    
    conn = get_db_connection()
    if st.session_state.user_type == "admin": notifs = conn.execute("SELECT title, message, created_at FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()
    else: notifs = conn.execute("SELECT title, message, created_at FROM notifications WHERE target IN ('تمام','اساتذہ') ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    for n in notifs: st.info(f"**{n[0]}**\n\n{n[1]}\n\n*{n[2]}*")

elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("📈 ڈیٹا تجزیہ")
    st.info("مزید گرافکس پر کام جاری ہے...")

elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("⚙️ بیک اپ اور سیٹنگز")
    if st.button("💾 ڈیٹا بیس کا بیک اپ (CSV)"):
        tables = ["teachers", "students", "hifz_records", "t_attendance", "leave_requests", "exams"]
        conn = get_db_connection()
        for t in tables:
            try: pd.read_sql_query(f"SELECT * FROM {t}", conn).to_csv(f"{t}_backup.csv", index=False)
            except: pass
        conn.close()
        st.success("بیک اپ مکمل!")

# -------------------- 8. استاد کے سیکشن --------------------
elif selected == "📝 تعلیمی اندراج" and st.session_state.user_type == "teacher":
    st.header("🚀 تعلیمی اندراج")
    sel_date = st.date_input("تاریخ", date.today())
    conn = get_db_connection()
    students = conn.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
    conn.close()
    
    if not students:
        st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
    else:
        # ہم نے اس حصے کو st.form سے نکال دیا ہے تاکہ st.button درست کام کرے
        records = []
        for s, f in students:
            with st.container():
                st.markdown(f"### 👤 {s} ولد {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر"], key=f"att_{s}", horizontal=True)
                
                if att == "حاضر":
                    # سبق
                    c1, c2, c3 = st.columns(3)
                    surah = c1.selectbox("سورت", surahs_urdu, key=f"surah_{s}")
                    a_from = c2.text_input("آیت (سے)", key=f"af_{s}")
                    a_to = c3.text_input("آیت (تک)", key=f"at_{s}")
                    sabq = f"{surah}: {a_from}-{a_to}"
                    
                    st.write("---")
                    col_sq, col_m = st.columns(2)
                    
                    # سبقی کا حصہ
                    with col_sq:
                        st.markdown("**📖 سبقی**")
                        if f"sq_parts_{s}" not in st.session_state: st.session_state[f"sq_parts_{s}"] = []
                        if f"sq_values_{s}" not in st.session_state: st.session_state[f"sq_values_{s}"] = []
                        if f"sq_atkan_{s}" not in st.session_state: st.session_state[f"sq_atkan_{s}"] = []
                        if f"sq_mistakes_{s}" not in st.session_state: st.session_state[f"sq_mistakes_{s}"] = []
                        
                        for idx, (p, v, a, m) in enumerate(zip(st.session_state[f"sq_parts_{s}"], st.session_state[f"sq_values_{s}"], st.session_state[f"sq_atkan_{s}"], st.session_state[f"sq_mistakes_{s}"])):
                            st.caption(f"{idx+1}. {p} - مقدار: {v} | اٹکن: {a} | غلطی: {m}")
                        
                        nc1, nc2, nc3, nc4 = st.columns(4)
                        new_para = nc1.selectbox("پارہ", paras, key=f"n_p_{s}")
                        new_val = nc2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"n_v_{s}")
                        new_atk = nc3.number_input("اٹکن", 0, key=f"n_a_{s}")
                        new_mis = nc4.number_input("غلطی", 0, key=f"n_m_{s}")
                        if st.button(f"➕ شامل کریں", key=f"add_sq_{s}"):
                            st.session_state[f"sq_parts_{s}"].append(new_para)
                            st.session_state[f"sq_values_{s}"].append(new_val)
                            st.session_state[f"sq_atkan_{s}"].append(new_atk)
                            st.session_state[f"sq_mistakes_{s}"].append(new_mis)
                            st.rerun()

                    # منزل کا حصہ
                    with col_m:
                        st.markdown("**📚 منزل**")
                        if f"m_parts_{s}" not in st.session_state: st.session_state[f"m_parts_{s}"] = []
                        if f"m_values_{s}" not in st.session_state: st.session_state[f"m_values_{s}"] = []
                        if f"m_atkan_{s}" not in st.session_state: st.session_state[f"m_atkan_{s}"] = []
                        if f"m_mistakes_{s}" not in st.session_state: st.session_state[f"m_mistakes_{s}"] = []
                        
                        for idx, (p, v, a, m) in enumerate(zip(st.session_state[f"m_parts_{s}"], st.session_state[f"m_values_{s}"], st.session_state[f"m_atkan_{s}"], st.session_state[f"m_mistakes_{s}"])):
                            st.caption(f"{idx+1}. {p} - مقدار: {v} | اٹکن: {a} | غلطی: {m}")
                        
                        mc1, mc2, mc3, mc4 = st.columns(4)
                        new_para_m = mc1.selectbox("پارہ", paras, key=f"m_p_{s}")
                        new_val_m = mc2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"m_v_{s}")
                        new_atk_m = mc3.number_input("اٹکن", 0, key=f"m_a_{s}")
                        new_mis_m = mc4.number_input("غلطی", 0, key=f"m_m_{s}")
                        if st.button(f"➕ شامل کریں", key=f"add_m_{s}"):
                            st.session_state[f"m_parts_{s}"].append(new_para_m)
                            st.session_state[f"m_values_{s}"].append(new_val_m)
                            st.session_state[f"m_atkan_{s}"].append(new_atk_m)
                            st.session_state[f"m_mistakes_{s}"].append(new_mis_m)
                            st.rerun()

                    sq_parts_str = " | ".join([f"{p}:{v}" for p, v in zip(st.session_state[f"sq_parts_{s}"], st.session_state[f"sq_values_{s}"])]) if st.session_state[f"sq_parts_{s}"] else "کوئی نہیں"
                    sq_a_total = sum(st.session_state[f"sq_atkan_{s}"])
                    sq_m_total = sum(st.session_state[f"sq_mistakes_{s}"])
                    
                    m_parts_str = " | ".join([f"{p}:{v}" for p, v in zip(st.session_state[f"m_parts_{s}"], st.session_state[f"m_values_{s}"])]) if st.session_state[f"m_parts_{s}"] else "کوئی نہیں"
                    m_a_total = sum(st.session_state[f"m_atkan_{s}"])
                    m_m_total = sum(st.session_state[f"m_mistakes_{s}"])
                else:
                    sabq = sq_parts_str = m_parts_str = "ناغہ"
                    sq_a_total = sq_m_total = m_a_total = m_m_total = 0
                
                records.append((sel_date, s, f, st.session_state.username, sabq, sq_parts_str, sq_a_total, sq_m_total, m_parts_str, m_a_total, m_m_total, att))
                st.markdown("<hr style='margin:10px 0; border: 1px dashed #ccc;'>", unsafe_allow_html=True)

        # ماسٹر سیو بٹن (فارم سے باہر)
        if st.button("💾 مکمل کلاس کا ڈیٹا محفوظ کریں", type="primary"):
            conn = get_db_connection()
            c = conn.cursor()
            duplicate = False
            for rec in records:
                if c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND f_name=?", (rec[0], rec[1], rec[2])).fetchone():
                    st.error(f"❌ {rec[1]} کا آج کا ریکارڈ پہلے سے موجود ہے!")
                    duplicate = True
                    break
            if not duplicate:
                for rec in records:
                    c.execute("""INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", rec)
                conn.commit()
                # Clear session state for dynamic fields
                for s, f in students:
                    for key in [f"sq_parts_{s}", f"sq_values_{s}", f"sq_atkan_{s}", f"sq_mistakes_{s}", f"m_parts_{s}", f"m_values_{s}", f"m_atkan_{s}", f"m_mistakes_{s}"]:
                        st.session_state.pop(key, None)
                st.success("✅ تمام طلباء کا ڈیٹا کامیابی سے محفوظ ہو گیا!")
                st.rerun()
            conn.close()

elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("🎓 امتحانی درخواست")
    # ... (باقی کوڈ پہلے جیسا ہے) ...

elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    conn = get_db_connection()
    rec = conn.execute("SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?", (st.session_state.username, today)).fetchone()
    
    if not rec:
        if st.button("آمد درج کریں (Check-In)"):
            conn.execute("INSERT INTO t_attendance (t_name, a_date, arrival, actual_arrival) VALUES (?,?,?,?)", (st.session_state.username, today, get_pk_time(), get_pk_time()))
            conn.commit(); conn.close(); st.success("آمد درج ہو گئی"); st.rerun()
    elif rec and rec[1] is None:
        st.info(f"آمد کا وقت: {rec[0]}")
        if st.button("رخصت درج کریں (Check-Out)"):
            conn.execute("UPDATE t_attendance SET departure=?, actual_departure=? WHERE t_name=? AND a_date=?", (get_pk_time(), get_pk_time(), st.session_state.username, today))
            conn.commit(); conn.close(); st.success("رخصت درج ہو گئی"); st.rerun()
    else:
        st.success(f"آج کی ڈیوٹی مکمل: آمد ({rec[0]}) | رخصت ({rec[1]})")

# -------------------- 9. لاگ آؤٹ --------------------
st.sidebar.divider()
if st.sidebar.button("🚪 " + T['logout']):
    st.session_state.logged_in = False
    st.rerun()
