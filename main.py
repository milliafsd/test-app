import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import pytz
import plotly.express as px

# -------------------- 1. ڈیٹا بیس سیٹ اپ --------------------
DB_NAME = 'jamia_erp_v3.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS teachers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT, 
                  dept TEXT, phone TEXT, address TEXT, id_card TEXT, photo TEXT, joining_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, mother_name TEXT, 
                  teacher_name TEXT, dept TEXT, class TEXT, section TEXT,
                  phone TEXT, address TEXT, id_card TEXT, photo TEXT, admission_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                  surah TEXT, a_from TEXT, a_to TEXT, 
                  sq_p TEXT, sq_a INTEGER, sq_m INTEGER, 
                  m_p TEXT, m_a INTEGER, m_m INTEGER, 
                  attendance TEXT, principal_note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS general_education 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT,
                  dept TEXT, book_subject TEXT, today_lesson TEXT, homework TEXT, performance TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT, 
                  actual_arrival TEXT, actual_departure TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, 
                  back_date DATE, status TEXT, request_date DATE, l_type TEXT, days INTEGER, 
                  notification_seen INTEGER DEFAULT 0)''')
    c.execute("""CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, f_name TEXT, dept TEXT, para_no INTEGER, start_date TEXT, end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, grade TEXT, status TEXT, exam_type TEXT)""")
    # پاس شدہ پارے
    c.execute("""CREATE TABLE IF NOT EXISTS passed_paras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, f_name TEXT, para_no INTEGER, passed_date DATE, exam_type TEXT)""")
    c.execute('''CREATE TABLE IF NOT EXISTS timetable 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, day TEXT, period TEXT, book TEXT, room TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notifications 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT, created_at DATETIME, seen INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, timestamp DATETIME, details TEXT)''')
    conn.commit()
    
    # نئے کالمز کا اضافہ
    cols = [
        ("teachers", "dept", "TEXT"), ("teachers", "phone", "TEXT"), ("teachers", "address", "TEXT"), 
        ("teachers", "id_card", "TEXT"), ("teachers", "photo", "TEXT"), ("teachers", "joining_date", "DATE"),
        ("students", "mother_name", "TEXT"), ("students", "dept", "TEXT"), ("students", "class", "TEXT"), 
        ("students", "section", "TEXT"), ("students", "phone", "TEXT"), ("students", "address", "TEXT"), 
        ("students", "id_card", "TEXT"), ("students", "photo", "TEXT"), ("students", "admission_date", "DATE"),
        ("exams", "dept", "TEXT"),
        ("t_attendance", "actual_arrival", "TEXT"), ("t_attendance", "actual_departure", "TEXT")
    ]
    for t, col, typ in cols:
        try:
            c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except:
            pass
    
    c.execute("INSERT OR IGNORE INTO teachers (name, password, dept) VALUES (?,?,?)", ("admin", "jamia123", "Admin"))
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
    if total_mistakes <= 2:
        return "ممتاز"
    elif total_mistakes <= 5:
        return "جید جداً"
    elif total_mistakes <= 8:
        return "جید"
    elif total_mistakes <= 12:
        return "مقبول"
    else:
        return "دوبارہ کوشش کریں"

def generate_html_report(df, title, student_name="", start_date="", end_date="", passed_paras=None):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    passed_html = ""
    if passed_paras:
        passed_html = f"<div style='margin-top:20px'><b>پاس شدہ پارے:</b> {', '.join(map(str, passed_paras))}</div>"
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
        {passed_html}
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

# -------------------- 3. اسٹائلنگ --------------------
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ | سمارٹ ERP", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * { font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', Arial, sans-serif; }
    body { direction: rtl; text-align: right; background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%); }
    .stSidebar { background: linear-gradient(180deg, #1e5631 0%, #0b2b1a 100%); color: white; }
    .stSidebar .stRadio label { color: white !important; font-weight: bold; }
    .stButton > button { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; border-radius: 30px; border: none; padding: 0.5rem 1rem; font-weight: bold; transition: 0.3s; width: 100%; }
    .stButton > button:hover { transform: scale(1.02); background: linear-gradient(90deg, #2e7d32, #1e5631); }
    .main-header { text-align: center; background: linear-gradient(135deg, #f1f8e9, #d4e0c9); padding: 1rem; border-radius: 20px; margin-bottom: 1rem; border-bottom: 4px solid #1e5631; }
    .report-card { background: white; border-radius: 15px; padding: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 30px; padding: 0.5rem 1rem; background-color: #e0e0e0; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; }
    @media (max-width: 768px) { .stButton > button { padding: 0.4rem 0.8rem; font-size: 0.8rem; } .main-header h1 { font-size: 1.5rem; } }
</style>
""", unsafe_allow_html=True)

# -------------------- 4. لاگ ان --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>حفظ | درسِ نظامی | عصری تعلیم</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.container():
            st.markdown("<div class='report-card'><h3>🔐 لاگ ان</h3>", unsafe_allow_html=True)
            u = st.text_input("صارف نام")
            p = st.text_input("پاسورڈ", type="password")
            if st.button("داخل ہوں"):
                conn = get_db_connection()
                res = conn.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
                conn.close()
                if res:
                    st.session_state.logged_in, st.session_state.username = True, u
                    st.session_state.user_type = "admin" if u == "admin" else "teacher"
                    log_audit(u, "Login", f"User type: {st.session_state.user_type}")
                    st.rerun()
                else:
                    st.error("غلط معلومات")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -------------------- 5. مینو --------------------
if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری", "👥 یوزر مینجمنٹ",
            "📚 ٹائم ٹیبل مینجمنٹ", "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس",
            "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "📚 میرا ٹائم ٹیبل", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

# -------------------- 6. ڈیٹا --------------------
surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
               "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج",
               "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب",
               "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف",
               "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة",
               "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة",
               "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر",
               "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل",
               "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة",
               "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# ================= ایڈمن سیکشنز (پہلے والے) =================
# (یہاں تمام پچھلے ایڈمن سیکشنز کو مختصراً رکھا گیا ہے، لیکن آپ چاہیں تو مکمل شامل کر سکتے ہیں)
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = conn.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
    st.metric("کل طلباء", total_students)
    st.metric("کل اساتذہ", total_teachers)
    conn.close()

elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    conn = get_db_connection()
    students_list = conn.execute("SELECT name, father_name, dept FROM students").fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی طالب علم نہیں")
    else:
        student_names = [f"{s[0]} ولد {s[1]} ({s[2]})" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        s_name, rest = sel.split(" ولد ")
        f_name, dept = rest.split(" (")
        dept = dept.replace(")", "")
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        
        if dept == "حفظ":
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, attendance as حاضری, surah as 'سبق (آیت تا آیت)',
                                      sq_p as 'سبقی (پارہ)', sq_m as 'سبقی (غلطی)', sq_a as 'سبقی (اٹکن)',
                                      m_p as 'منزل (پارہ)', m_m as 'منزل (غلطی)', m_a as 'منزل (اٹکن)'
                                      FROM hifz_records WHERE s_name=? AND f_name=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(s_name, f_name, start, end))
            conn.close()
            if not df.empty:
                df['کل_غلطیاں'] = df['سبقی (غلطی)'] + df['منزل (غلطی)']
                df['درجہ'] = df['کل_غلطیاں'].apply(get_grade_from_mistakes)
                avg_mistakes = df['کل_غلطیاں'].mean()
                st.info(f"**اوسط غلطیاں:** {round(avg_mistakes, 1)} | **مجموعی درجہ:** {get_grade_from_mistakes(avg_mistakes)}")
        else:
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, book_subject as 'کتاب/مضمون', today_lesson as 'آج کا سبق',
                                      homework as 'ہوم ورک', performance as کارکردگی
                                      FROM general_education WHERE s_name=? AND f_name=? AND dept=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(s_name, f_name, dept, start, end))
            conn.close()
        
        if df.empty:
            st.warning("کوئی ریکارڈ نہیں")
        else:
            st.dataframe(df, use_container_width=True)
            # پاس شدہ پارے (صرف حفظ کے لیے)
            passed = []
            if dept == "حفظ":
                conn = get_db_connection()
                passed = [row[0] for row in conn.execute("SELECT para_no FROM passed_paras WHERE s_name=? AND f_name=? ORDER BY para_no", (s_name, f_name)).fetchall()]
                conn.close()
            html = generate_html_report(df, "ماہانہ رزلٹ کارڈ", student_name=f"{s_name} ولد {f_name}",
                                        start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"),
                                        passed_paras=passed if passed else None)
            st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# ================= امتحانی نظام (پارہ ٹیسٹ + پاس شدہ پارے) =================
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام")
    tab1, tab2 = st.tabs(["پینڈنگ امتحانات", "مکمل شدہ"])
    with tab1:
        conn = get_db_connection()
        pending = conn.execute("SELECT id, s_name, f_name, dept, para_no, start_date, exam_type FROM exams WHERE status=?", ("پینڈنگ",)).fetchall()
        conn.close()
        if not pending:
            st.info("کوئی پینڈنگ امتحان نہیں")
        else:
            for eid, sn, fn, dept, pn, sd, etype in pending:
                with st.expander(f"{sn} ولد {fn} | {dept} | {etype} | پارہ {pn if pn else 'N/A'}"):
                    st.write(f"**تاریخ ابتدا:** {sd}")
                    end_date = st.date_input("تاریخ اختتام", date.today(), key=f"end_{eid}")
                    if etype == "پارہ ٹیسٹ" and pn > 0:
                        st.info(f"پارہ نمبر {pn} کا امتحان")
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
                        c.execute("""UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? WHERE id=?""",
                                  (q1,q2,q3,q4,q5,total,g,"مکمل", end_date, eid))
                        # اگر پارہ ٹیسٹ ہے اور گریڈ ناکام نہیں ہے تو پاس شدہ پاروں میں شامل کریں
                        if etype == "پارہ ٹیسٹ" and g != "ناکام" and pn > 0:
                            # چیک کریں کہ یہ پارہ پہلے سے پاس شدہ تو نہیں
                            existing = c.execute("SELECT 1 FROM passed_paras WHERE s_name=? AND f_name=? AND para_no=?", (sn, fn, pn)).fetchone()
                            if not existing:
                                c.execute("INSERT INTO passed_paras (s_name, f_name, para_no, passed_date, exam_type) VALUES (?,?,?,?,?)",
                                          (sn, fn, pn, date.today(), etype))
                        conn.commit()
                        conn.close()
                        log_audit(st.session_state.username, "Exam Cleared", f"{sn} {fn} {etype} para {pn}")
                        st.success("امتحان کلیئر کر دیا گیا")
                        st.rerun()
    with tab2:
        conn = get_db_connection()
        hist = pd.read_sql_query("SELECT s_name, f_name, dept, para_no, total, grade, exam_type, end_date FROM exams WHERE status='مکمل' ORDER BY end_date DESC", conn)
        conn.close()
        if not hist.empty:
            st.dataframe(hist, use_container_width=True)
            st.download_button("ہسٹری CSV", convert_df_to_csv(hist), "exam_history.csv")
        else:
            st.info("کوئی مکمل شدہ امتحان نہیں")

# ================= استاد کا سیکشن: روزانہ سبق اندراج (حفظ کے لیے + بٹن) =================
elif selected == "📝 روزانہ سبق اندراج" and st.session_state.user_type == "teacher":
    st.header("📝 روزانہ سبق اندراج")
    dept = st.selectbox("شعبہ منتخب کریں", ["حفظ", "درسِ نظامی", "عصری تعلیم"])
    today = date.today()
    
    if dept == "حفظ":
        st.subheader("حفظ کا اندراج (➕ بٹن سے مزید پارے شامل کریں)")
        conn = get_db_connection()
        students = conn.execute("SELECT name, father_name FROM students WHERE teacher_name=? AND dept='حفظ'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
        else:
            for s, f in students:
                key = f"{s}_{f}"
                # سیشن میں صف کی تعداد
                if f"sq_rows_{key}" not in st.session_state:
                    st.session_state[f"sq_rows_{key}"] = 1
                if f"m_rows_{key}" not in st.session_state:
                    st.session_state[f"m_rows_{key}"] = 1
                
                st.markdown(f"### 👤 {s} ولد {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر"], key=f"att_{key}", horizontal=True)
                
                if att == "حاضر":
                    surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{key}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{key}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{key}")
                    sabq = f"{surah}: {a_from}-{a_to}"
                    
                    st.write("**سبقی**")
                    sq_parts = []; sq_a = 0; sq_m = 0
                    for i in range(st.session_state[f"sq_rows_{key}"]):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", paras, key=f"sqp_{key}_{i}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{key}_{i}")
                        a = cols[2].number_input("اٹکن", 0, key=f"sqa_{key}_{i}")
                        e = cols[3].number_input("غلطی", 0, key=f"sqe_{key}_{i}")
                        sq_parts.append(f"{p}:{v}")
                        sq_a += a; sq_m += e
                    if st.button("➕ مزید سبقی پارہ", key=f"add_sq_{key}"):
                        st.session_state[f"sq_rows_{key}"] += 1
                        st.rerun()
                    
                    st.write("**منزل**")
                    m_parts = []; m_a = 0; m_m = 0
                    for j in range(st.session_state[f"m_rows_{key}"]):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", paras, key=f"mp_{key}_{j}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{key}_{j}")
                        a = cols[2].number_input("اٹکن", 0, key=f"ma_{key}_{j}")
                        e = cols[3].number_input("غلطی", 0, key=f"me_{key}_{j}")
                        m_parts.append(f"{p}:{v}")
                        m_a += a; m_m += e
                    if st.button("➕ مزید منزل پارہ", key=f"add_m_{key}"):
                        st.session_state[f"m_rows_{key}"] += 1
                        st.rerun()
                    
                    if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND f_name=?", (today, s, f)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے")
                        else:
                            c.execute("""INSERT INTO hifz_records 
                                        (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (today, s, f, st.session_state.username, sabq,
                                       " | ".join(sq_parts), sq_a, sq_m,
                                       " | ".join(m_parts), m_a, m_m, att))
                            conn.commit()
                            log_audit(st.session_state.username, "Hifz Entry", f"{s} {today}")
                            st.success("محفوظ ہو گیا")
                        conn.close()
                else:
                    if st.button(f"غیر حاضر محفوظ کریں ({s})", key=f"absent_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND f_name=?", (today, s, f)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے")
                        else:
                            c.execute("""INSERT INTO hifz_records 
                                        (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (today, s, f, st.session_state.username, "ناغہ", "ناغہ", 0, 0, "ناغہ", 0, 0, att))
                            conn.commit()
                            st.success("محفوظ ہو گیا")
                        conn.close()
                st.markdown("---")
    
    elif dept == "درسِ نظامی":
        st.subheader("درسِ نظامی سبق ریکارڈ")
        conn = get_db_connection()
        students = conn.execute("SELECT name, father_name FROM students WHERE teacher_name=? AND dept='درسِ نظامی'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("کوئی طالب علم نہیں")
        else:
            with st.form("dars_form"):
                records = []
                for s, f in students:
                    st.markdown(f"### {s} ولد {f}")
                    book = st.text_input("کتاب کا نام", key=f"book_{s}")
                    lesson = st.text_area("آج کا سبق", key=f"lesson_{s}")
                    perf = st.select_slider("کارکردگی", ["بہت بہتر", "بہتر", "مناسب", "کمزور"], key=f"perf_{s}")
                    records.append((today, s, f, st.session_state.username, "درسِ نظامی", book, lesson, "", perf))
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, s_name, f_name, t_name, dept, book_subject, today_lesson, performance) VALUES (?,?,?,?,?,?,?,?)", rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")
    
    elif dept == "عصری تعلیم":
        st.subheader("عصری تعلیم ڈائری")
        conn = get_db_connection()
        students = conn.execute("SELECT name, father_name FROM students WHERE teacher_name=? AND dept='عصری تعلیم'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("کوئی طالب علم نہیں")
        else:
            with st.form("school_form"):
                records = []
                for s, f in students:
                    st.markdown(f"### {s} ولد {f}")
                    subject = st.selectbox("مضمون", ["اردو", "انگلش", "ریاضی", "سائنس", "اسلامیات"], key=f"sub_{s}")
                    topic = st.text_input("عنوان", key=f"topic_{s}")
                    hw = st.text_area("ہوم ورک", key=f"hw_{s}")
                    records.append((today, s, f, st.session_state.username, "عصری تعلیم", subject, topic, hw, ""))
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, s_name, f_name, t_name, dept, book_subject, today_lesson, homework) VALUES (?,?,?,?,?,?,?,?)", rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")

# ================= استاد کی امتحانی درخواست (پارہ ٹیسٹ کی سہولت) =================
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("امتحان کے لیے طالب علم نامزد کریں")
    conn = get_db_connection()
    students = conn.execute("SELECT name, father_name, dept FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
    conn.close()
    if not students:
        st.warning("کوئی طالب علم نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s[0]} ولد {s[1]} ({s[2]})" for s in students]
            sel = st.selectbox("طالب علم", s_list)
            s_name, rest = sel.split(" ولد ")
            f_name, dept = rest.split(" (")
            dept = dept.replace(")", "")
            exam_type = st.selectbox("امتحان کی قسم", ["ماہانہ", "سہ ماہی", "سالانہ", "پارہ ٹیسٹ"])
            para_no = 0
            if exam_type == "پارہ ٹیس्ट":
                para_no = st.number_input("پارہ نمبر", 1, 30)
            start_date = st.date_input("تاریخ ابتدا", date.today())
            if st.form_submit_button("بھیجیں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO exams (s_name, f_name, dept, para_no, start_date, status, exam_type) VALUES (?,?,?,?,?,?,?)",
                          (s_name, f_name, dept, para_no, start_date, "پینڈنگ", exam_type))
                conn.commit()
                conn.close()
                st.success("درخواست بھیج دی گئی")

# ================= باقی سیکشنز (پہلے والے) =================
elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    conn = get_db_connection()
    rec = conn.execute("SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?", (st.session_state.username, today)).fetchone()
    conn.close()
    if not rec:
        col1, col2 = st.columns(2)
        arr_date = col1.date_input("تاریخ", today)
        arr_time = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں"):
            time_str = arr_time.strftime("%I:%M %p")
            conn = get_db_connection()
            conn.execute("INSERT INTO t_attendance (t_name, a_date, arrival, actual_arrival) VALUES (?,?,?,?)",
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
            conn.execute("UPDATE t_attendance SET departure=?, actual_departure=? WHERE t_name=? AND a_date=?",
                         (time_str, get_pk_time(), st.session_state.username, today))
            conn.commit()
            conn.close()
            st.success("رخصت درج ہو گئی")
            st.rerun()
    else:
        st.success(f"آمد: {rec[0]} | رخصت: {rec[1]}")

elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("میرا ٹائم ٹیبل")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(st.session_state.username,))
    conn.close()
    if df.empty:
        st.info("ٹائم ٹیبل ابھی ترتیب نہیں دیا گیا")
    else:
        st.table(df)

elif selected == "📢 نوٹیفیکیشنز":
    st.header("نوٹیفیکیشن سینٹر")
    if st.session_state.user_type == "admin":
        with st.form("new_notif"):
            title = st.text_input("عنوان")
            msg = st.text_area("پیغام")
            target = st.selectbox("بھیجیں", ["تمام", "اساتذہ", "طلبہ"])
            if st.form_submit_button("بھیجیں"):
                conn = get_db_connection()
                conn.execute("INSERT INTO notifications (title, message, target, created_at) VALUES (?,?,?,?)",
                             (title, msg, target, datetime.now()))
                conn.commit()
                conn.close()
                st.success("بھیج دیا گیا")
    conn = get_db_connection()
    if st.session_state.user_type == "admin":
        notifs = conn.execute("SELECT title, message, created_at FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()
    else:
        notifs = conn.execute("SELECT title, message, created_at FROM notifications WHERE target IN ('تمام','اساتذہ') ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    for n in notifs:
        st.info(f"**{n[0]}**\n\n{n[1]}\n\n*{n[2]}*")

elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.header("اساتذہ حاضری ریکارڈ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری")
    conn = get_db_connection()
    pending = conn.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE ?", ('%پینڈنگ%',)).fetchall()
    conn.close()
    for l_id, t_n, l_t, reas, s_d, dys in pending:
        with st.expander(f"{t_n} | {l_t} | {dys} دن"):
            st.write(reas)
            col1, col2 = st.columns(2)
            if col1.button("منظور", key=f"app_{l_id}"):
                conn = get_db_connection()
                conn.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (l_id,))
                conn.commit()
                conn.close()
                st.rerun()
            if col2.button("مسترد", key=f"rej_{l_id}"):
                conn = get_db_connection()
                conn.execute("UPDATE leave_requests SET status='مسترد' WHERE id=?", (l_id,))
                conn.commit()
                conn.close()
                st.rerun()

elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["اساتذہ", "طلبہ"])
    with tab1:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT id, name, password, dept, phone FROM teachers", conn)
        conn.close()
        edited = st.data_editor(df, num_rows="dynamic", key="teachers_edit")
        if st.button("اساتذہ محفوظ کریں"):
            conn = get_db_connection()
            conn.execute("DELETE FROM teachers")
            for _, row in edited.iterrows():
                conn.execute("INSERT INTO teachers (id, name, password, dept, phone) VALUES (?,?,?,?,?)",
                             (row['id'], row['name'], row['password'], row['dept'], row['phone']))
            conn.commit()
            conn.close()
            st.success("محفوظ")
            st.rerun()
    with tab2:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT id, name, father_name, teacher_name, dept, class FROM students", conn)
        conn.close()
        edited = st.data_editor(df, num_rows="dynamic", key="students_edit")
        if st.button("طلبہ محفوظ کریں"):
            conn = get_db_connection()
            conn.execute("DELETE FROM students")
            for _, row in edited.iterrows():
                conn.execute("INSERT INTO students (id, name, father_name, teacher_name, dept, class) VALUES (?,?,?,?,?,?)",
                             (row['id'], row['name'], row['father_name'], row['teacher_name'], row['dept'], row['class']))
            conn.commit()
            conn.close()
            st.success("محفوظ")
            st.rerun()

elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("ٹائم ٹیبل مینجمنٹ")
    conn = get_db_connection()
    teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
    conn.close()
    if teachers:
        sel_t = st.selectbox("استاد", teachers)
        with st.form("add_period"):
            day = st.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
            period = st.text_input("وقت")
            book = st.text_input("کتاب")
            room = st.text_input("کمرہ")
            if st.form_submit_button("شامل کریں"):
                conn = get_db_connection()
                conn.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                             (sel_t, day, period, book, room))
                conn.commit()
                conn.close()
                st.success("شامل")
                st.rerun()
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT day, period, book, room FROM timetable WHERE t_name=?", conn, params=(sel_t,))
        conn.close()
        st.table(df)

elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("تجزیہ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ FROM t_attendance", conn)
    if not df.empty:
        fig = px.bar(df, x='تاریخ', title="اساتذہ حاضری")
        st.plotly_chart(fig)
    conn.close()

elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ")
    if st.button("بیک اپ لیں"):
        tables = ["teachers", "students", "hifz_records", "general_education", "t_attendance", "exams", "passed_paras", "timetable"]
        conn = get_db_connection()
        for t in tables:
            df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
            df.to_csv(f"{t}_backup.csv", index=False)
        conn.close()
        st.success("بیک اپ مکمل")
    with st.expander("آڈٹ لاگ"):
        conn = get_db_connection()
        logs = pd.read_sql_query("SELECT user, action, timestamp, details FROM audit_log ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        st.dataframe(logs)

# ================= لاگ آؤٹ =================
st.sidebar.divider()
if st.sidebar.button("لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
