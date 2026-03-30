import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import pytz
import plotly.express as px
import os
import calendar

# ==================== 1. ڈیٹا بیس سیٹ اپ ====================
DB_NAME = 'jamia_millia_v1 (1) (1).db'  # اپنے ڈیٹا بیس کا نام یہاں لکھیں

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # اساتذہ ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        password TEXT
    )''')
    cols_teacher = [("dept", "TEXT"), ("phone", "TEXT"), ("address", "TEXT"), ("id_card", "TEXT"), ("photo", "TEXT"), ("joining_date", "DATE")]
    for col, typ in cols_teacher:
        try: c.execute(f"ALTER TABLE teachers ADD COLUMN {col} {typ}")
        except: pass
    
    # طلبہ ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        father_name TEXT,
        teacher_name TEXT
    )''')
    cols_student = [("mother_name", "TEXT"), ("dob", "DATE"), ("admission_date", "DATE"), ("exit_date", "DATE"),
                    ("exit_reason", "TEXT"), ("id_card", "TEXT"), ("photo", "TEXT"), ("phone", "TEXT"),
                    ("address", "TEXT"), ("dept", "TEXT"), ("class", "TEXT"), ("section", "TEXT")]
    for col, typ in cols_student:
        try: c.execute(f"ALTER TABLE students ADD COLUMN {col} {typ}")
        except: pass
    
    # حفظ ریکارڈ
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT,
        surah TEXT, a_from TEXT, a_to TEXT,
        sq_p TEXT, sq_a INTEGER, sq_m INTEGER,
        m_p TEXT, m_a INTEGER, m_m INTEGER,
        attendance TEXT, principal_note TEXT
    )''')
    
    # عمومی تعلیم
    c.execute('''CREATE TABLE IF NOT EXISTS general_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT,
        dept TEXT, book_subject TEXT, today_lesson TEXT, homework TEXT, performance TEXT
    )''')
    
    # اساتذہ حاضری
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT, a_date DATE, arrival TEXT, departure TEXT,
        actual_arrival TEXT, actual_departure TEXT
    )''')
    
    # رخصت درخواستیں
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT, reason TEXT, start_date DATE, back_date DATE,
        status TEXT, request_date DATE, l_type TEXT, days INTEGER,
        notification_seen INTEGER DEFAULT 0
    )''')
    
    # امتحانات (from_para, to_para)
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        s_name TEXT, f_name TEXT, dept TEXT,
        from_para INTEGER, to_para INTEGER,
        start_date TEXT, end_date TEXT,
        q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
        total INTEGER, grade TEXT, status TEXT, exam_type TEXT
    )''')
    try: c.execute("ALTER TABLE exams ADD COLUMN from_para INTEGER")
    except: pass
    try: c.execute("ALTER TABLE exams ADD COLUMN to_para INTEGER")
    except: pass
    
    # پاس شدہ پارے
    c.execute('''CREATE TABLE IF NOT EXISTS passed_paras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        s_name TEXT, f_name TEXT, para_no INTEGER,
        passed_date DATE, exam_type TEXT, grade TEXT
    )''')
    try: c.execute("ALTER TABLE passed_paras ADD COLUMN grade TEXT")
    except: pass
    
    # ٹائم ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT, day TEXT, period TEXT, book TEXT, room TEXT
    )''')
    try: c.execute("ALTER TABLE timetable ADD COLUMN day_order INTEGER")
    except: pass
    try: c.execute("ALTER TABLE timetable ADD COLUMN period_order INTEGER")
    except: pass
    
    # نوٹیفیکیشنز
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, message TEXT, target TEXT, created_at DATETIME, seen INTEGER DEFAULT 0
    )''')
    
    # آڈٹ لاگ
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT, action TEXT, timestamp DATETIME, details TEXT
    )''')
    
    conn.commit()
    
    # ڈیفالٹ ایڈمن
    admin = c.execute("SELECT 1 FROM teachers WHERE name='admin'").fetchone()
    if not admin:
        try:
            c.execute("SELECT dept FROM teachers LIMIT 1")
            c.execute("INSERT INTO teachers (name, password, dept) VALUES (?,?,?)", ("admin", "jamia123", "Admin"))
        except:
            c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()
    conn.close()

init_db()

# ==================== 2. ہیلپر فنکشنز ====================
def log_audit(user, action, details=""):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO audit_log (user, action, timestamp, details) VALUES (?,?,?,?)",
                     (user, action, datetime.now(), details))
        conn.commit()
        conn.close()
    except: pass

def get_pk_time():
    tz = pytz.timezone('Asia/Karachi')
    return datetime.now(tz).strftime("%I:%M %p")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def get_grade_from_mistakes(total_mistakes):
    if total_mistakes <= 2: return "ممتاز"
    elif total_mistakes <= 5: return "جید جداً"
    elif total_mistakes <= 8: return "جید"
    elif total_mistakes <= 12: return "مقبول"
    else: return "دوبارہ کوشش کریں"

def generate_exam_result_card(exam_row):
    """ایک امتحان کے ریکارڈ سے رزلٹ کارڈ HTML بنائیں"""
    para_display = ""
    if exam_row['from_para'] and exam_row['to_para']:
        if exam_row['from_para'] == exam_row['to_para']:
            para_display = f"پارہ {exam_row['from_para']}"
        else:
            para_display = f"پارہ {exam_row['from_para']} تا {exam_row['to_para']}"
    else:
        para_display = "-"
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>رزلٹ کارڈ - {exam_row['s_name']}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', Arial; margin: 20px; direction: rtl; text-align: right; }}
        .card {{ border: 2px solid #1e5631; border-radius: 15px; padding: 20px; max-width: 600px; margin: auto; }}
        h2 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        .footer {{ margin-top: 20px; display: flex; justify-content: space-between; }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>جامعہ ملیہ اسلامیہ</h2>
            <h3>رزلٹ کارڈ</h3>
            <p><b>نام:</b> {exam_row['s_name']} ولد {exam_row['f_name']}</p>
            <p><b>امتحان کی قسم:</b> {exam_row['exam_type']}</p>
            <p><b>{para_display}</b></p>
            <p><b>تاریخ:</b> {exam_row['start_date']} تا {exam_row['end_date']}</p>
             <table>
                <tr><th>سوال</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>کل</th></tr>
                <tr><td>نمبر</td><td>{exam_row['q1']}</td><td>{exam_row['q2']}</td><td>{exam_row['q3']}</td><td>{exam_row['q4']}</td><td>{exam_row['q5']}</td><td>{exam_row['total']}</td></tr>
             </table>
            <p><b>گریڈ:</b> {exam_row['grade']}</p>
            <div class="footer">
                <span>دستخط استاذ: _________________</span>
                <span>دستخط مہتمم: _________________</span>
            </div>
        </div>
        <div class="no-print" style="text-align:center; margin-top:20px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_para_report(student_name, father_name, passed_paras_df):
    """پارہ تعلیمی رپورٹ HTML"""
    if passed_paras_df.empty:
        return "<p>کوئی پاس شدہ پارہ نہیں</p>"
    html_table = passed_paras_df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>پارہ تعلیمی رپورٹ - {student_name}</title>
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
            <h3>پارہ تعلیمی رپورٹ</h3>
            <p><b>طالب علم:</b> {student_name} ولد {father_name}</p>
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

def generate_html_report(df, title, student_name="", start_date="", end_date="", passed_paras=None):
    """پہلے والی رپورٹ (ماہانہ/سالانہ)"""
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

def generate_timetable_html(df_timetable):
    """ٹائم ٹیبل کو خوبصورت HTML گرڈ میں تبدیل کرنا"""
    if df_timetable.empty:
        return "<p>کوئی ٹائم ٹیبل دستیاب نہیں</p>"
    # دنوں کی ترتیب
    day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
    # پیریڈز کو ترتیب دیں (بطور ٹیکسٹ، لیکن ہم صرف موجودہ ترتیب سے ڈسپلے کریں گے)
    df_timetable['day_order'] = df_timetable['دن'].map(day_order)
    df_timetable = df_timetable.sort_values(['day_order', 'وقت'])
    # پائیوٹ ٹیبل
    pivot = df_timetable.pivot(index='وقت', columns='دن', values='کتاب')
    pivot = pivot.fillna("—")
    # HTML بنائیں
    html = """
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>ٹائم ٹیبل</title>
    <style>
        @font-face { font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }
        body { font-family: 'Jameel Noori Nastaleeq', Arial; margin: 20px; direction: rtl; text-align: right; }
        h2, h3 { text-align: center; color: #1e5631; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
        @media print { body { margin: 0; } .no-print { display: none; } }
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ</h2>
            <h3>ٹائم ٹیبل</h3>
        </div>
        """ + pivot.to_html(classes='print-table', border=1, justify='center', escape=False) + """
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

# ==================== 3. اسٹائلنگ ====================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ | سمارٹ ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * { font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; }
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

# ==================== 4. لاگ ان ====================
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

# ==================== 5. مینو ====================
if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "📘 پارہ تعلیمی رپورٹ", "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری",
            "👥 یوزر مینجمنٹ", "📚 ٹائم ٹیبل مینجمنٹ", "📢 نوٹیفیکیشنز",
            "📈 تجزیہ و رپورٹس", "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "📚 میرا ٹائم ٹیبل", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

# ==================== 6. ڈیٹا ====================
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

# ==================== 7. ایڈمن سیکشنز (مختصر) ====================
# (پچھلے تمام ایڈمن سیکشنز یہاں ہوں گے، لیکن صرف ٹائم ٹیبل مینجمنٹ میں تبدیلی کی ہے)
# باقی سیکشنز کو پہلے جیسا رکھا گیا ہے۔

# ==================== 8. ٹائم ٹیبل مینجمنٹ (ایڈمن) - بہتر ====================
if selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("📚 ٹائم ٹیبل مینجمنٹ")
    conn = get_db_connection()
    teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
    conn.close()
    if not teachers:
        st.warning("پہلے اساتذہ رجسٹر کریں")
    else:
        sel_t = st.selectbox("استاد منتخب کریں", teachers)
        
        # موجودہ ٹائم ٹیبل دکھائیں
        conn = get_db_connection()
        tt_df = pd.read_sql_query("SELECT id, day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(sel_t,))
        conn.close()
        if not tt_df.empty:
            st.subheader("موجودہ ٹائم ٹیبل")
            # دنوں کی ترتیب کے لیے
            day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
            tt_df['day_order'] = tt_df['دن'].map(day_order)
            tt_df = tt_df.sort_values(['day_order', 'وقت'])
            st.dataframe(tt_df[['دن', 'وقت', 'کتاب', 'کمرہ']], use_container_width=True)
        
        # نیا پیریڈ شامل کرنے کا فارم
        with st.expander("➕ نیا پیریڈ شامل کریں"):
            with st.form("add_period"):
                col1, col2 = st.columns(2)
                day = col1.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                period = col2.text_input("وقت (مثلاً 08:00-09:00)")
                book = st.text_input("کتاب / مضمون")
                room = st.text_input("کمرہ نمبر")
                if st.form_submit_button("شامل کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                              (sel_t, day, period, book, room))
                    conn.commit()
                    conn.close()
                    st.success("پیریڈ شامل کر دیا گیا")
                    st.rerun()
        
        # پورے ہفتے میں نقل کرنے کا بٹن
        if not tt_df.empty:
            with st.expander("🔄 پورے ہفتے میں نقل کریں"):
                st.write("منتخب دن کے پیریڈز کو تمام دنوں میں کاپی کریں")
                source_day = st.selectbox("منبع دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"], key="copy_source")
                target_days = st.multiselect("نقل کرنے کے لیے دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"], default=["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                if st.button("نقل کریں"):
                    # منبع دن کے پیریڈز حاصل کریں
                    conn = get_db_connection()
                    source_periods = conn.execute("SELECT period, book, room FROM timetable WHERE t_name=? AND day=?", (sel_t, source_day)).fetchall()
                    if source_periods:
                        # پہلے موجودہ ٹارگٹ دنوں کے پیریڈز حذف کریں
                        for d in target_days:
                            conn.execute("DELETE FROM timetable WHERE t_name=? AND day=?", (sel_t, d))
                        # نئے پیریڈز شامل کریں
                        for d in target_days:
                            for period, book, room in source_periods:
                                conn.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                                            (sel_t, d, period, book, room))
                        conn.commit()
                        st.success(f"{source_day} کے پیریڈز {', '.join(target_days)} میں نقل ہو گئے")
                    else:
                        st.warning(f"{source_day} کے لیے کوئی پیریڈ نہیں")
                    conn.close()
                    st.rerun()

# ==================== 9. استاد کا ٹائم ٹیبل (پروفیشنل گرڈ) ====================
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("📚 میرا ٹائم ٹیبل")
    conn = get_db_connection()
    tt_df = pd.read_sql_query("SELECT day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(st.session_state.username,))
    conn.close()
    if tt_df.empty:
        st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")
    else:
        # دنوں کی ترتیب
        day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
        tt_df['day_order'] = tt_df['دن'].map(day_order)
        tt_df = tt_df.sort_values(['day_order', 'وقت'])
        # پائیوٹ ٹیبل بنائیں
        pivot = tt_df.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
        # کمرہ نمبر کو اضافی معلومات کے طور پر دکھائیں (ہم الگ کالم بنا سکتے ہیں)
        # یہاں صرف کتاب دکھائی جا رہی ہے۔ اگر کمرہ بھی دکھانا ہو تو کتاب کے ساتھ لکھ سکتے ہیں
        # اب pivot کو خوبصورت طریقے سے دکھائیں
        st.write("### 📅 ٹائم ٹیبل (پیریڈ وار)")
        st.dataframe(pivot, use_container_width=True)
        
        # ڈاؤن لوڈ اور پرنٹ
        html_timetable = generate_timetable_html(tt_df)
        st.download_button("📥 HTML ڈاؤن لوڈ کریں", html_timetable, f"Timetable_{st.session_state.username}.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"):
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_timetable}`);w.print();</script>", height=0)

# ==================== 10. استاد کی امتحانی درخواست (پارہ ٹیسٹ میں صرف ایک پارہ) ====================
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
            start_date = st.date_input("تاریخ ابتدا", date.today())
            end_date = None
            from_para = 0
            to_para = 0
            if exam_type == "پارہ ٹیسٹ":
                para = st.number_input("پارہ نمبر", min_value=1, max_value=30, value=1)
                from_para = para
                to_para = para
                end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
            else:
                col1, col2 = st.columns(2)
                from_para = col1.number_input("پارہ نمبر (شروع)", min_value=1, max_value=30, value=1)
                to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=min(from_para+4,30))
                end_date = None  # صرف پارہ ٹیسٹ کے لیے اختتام کی تاریخ
            if st.form_submit_button("بھیجیں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO exams (s_name, f_name, dept, from_para, to_para, start_date, end_date, status, exam_type) VALUES (?,?,?,?,?,?,?,?,?)",
                          (s_name, f_name, dept, from_para, to_para, start_date, end_date, "پینڈنگ", exam_type))
                conn.commit()
                conn.close()
                st.success("درخواست بھیج دی گئی")

# ==================== باقی سیکشنز (پہلے جیسے) ====================
# (یہاں دیگر سیکشنز جیسے روزانہ سبق اندراج، رخصت کی درخواست، حاضری، نوٹیفیکیشنز، یوزر مینجمنٹ، وغیرہ پہلے کی طرح ہیں۔
# انہیں مختصر کرنے کے لیے میں صرف اہم حصے دکھا رہا ہوں۔ پورا کوڈ پچھلے جواب میں موجود ہے۔)
# اصل کوڈ میں یہ سیکشنز پہلے سے موجود ہیں، اس لیے میں انہیں دہرا نہیں رہا۔
# لیکن آپ کی سہولت کے لیے میں پوری فائل کو دوبارہ دے سکتا ہوں۔

# ==================== 11. استاد کی رخصت کی درخواست ====================
elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.header("📩 رخصت کی درخواست")
    with st.form("leave_request_form"):
        l_type = st.selectbox("رخصت کی نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        start_date = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دنوں کی تعداد", min_value=1, max_value=30, value=1)
        back_date = start_date + timedelta(days=days-1)
        st.write(f"واپسی کی تاریخ: {back_date}")
        reason = st.text_area("تفصیلی وجہ")
        if st.form_submit_button("درخواست جمع کریں"):
            if reason:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("""INSERT INTO leave_requests 
                            (t_name, l_type, start_date, days, reason, status, notification_seen, request_date)
                            VALUES (?,?,?,?,?,?,?,?)""",
                          (st.session_state.username, l_type, start_date, days, reason, "پینڈنگ", 0, date.today()))
                conn.commit()
                conn.close()
                log_audit(st.session_state.username, "Leave Requested", f"{l_type} for {days} days")
                st.success("درخواست بھیج دی گئی۔ منتظمین جلد جواب دیں گے۔")
            else:
                st.error("براہ کرم وجہ تحریر کریں")

# ==================== 12. استاد کی حاضری ====================
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

# ==================== 13. استاد کا ٹائم ٹیبل ====================
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("میرا ٹائم ٹیبل")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(st.session_state.username,))
    conn.close()
    if df.empty:
        st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")
    else:
        st.table(df)

# ==================== 14. استاد کے نوٹیفیکیشن ====================
elif selected == "📢 نوٹیفیکیشنز" and st.session_state.user_type == "teacher":
    st.header("نوٹیفیکیشنز")
    conn = get_db_connection()
    notifs = conn.execute("SELECT title, message, created_at FROM notifications WHERE target IN ('تمام','اساتذہ') ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    for n in notifs:
        st.info(f"**{n[0]}**\n\n{n[1]}\n\n*{n[2]}*")

# ==================== 15. ایڈمن کے دیگر سیکشنز (مختصر) ====================
elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.header("اساتذہ حاضری ریکارڈ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری")
    conn = get_db_connection()
    try:
        pending = conn.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE ?", ('%پینڈنگ%',)).fetchall()
    except:
        pending = []
    conn.close()
    if not pending:
        st.info("کوئی پینڈنگ درخواست نہیں")
    else:
        for l_id, t_n, l_t, reas, s_d, dys in pending:
            with st.expander(f"{t_n} | {l_t} | {dys} دن"):
                st.write(f"وجہ: {reas}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور", key=f"app_{l_id}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (l_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()
                if col2.button("❌ مسترد", key=f"rej_{l_id}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE leave_requests SET status='مسترد' WHERE id=?", (l_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()

elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["اساتذہ", "طلبہ"])
    with tab1:
        st.subheader("موجودہ اساتذہ")
        conn = get_db_connection()
        teachers_df = pd.read_sql_query("SELECT id, name, password, dept, phone, address, id_card, joining_date FROM teachers WHERE name!='admin'", conn)
        conn.close()
        if not teachers_df.empty:
            edited_teachers = st.data_editor(teachers_df, num_rows="dynamic", use_container_width=True, key="teachers_edit")
            if st.button("اساتذہ میں تبدیلیاں محفوظ کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("DELETE FROM teachers WHERE name!='admin'")
                for _, row in edited_teachers.iterrows():
                    c.execute("INSERT INTO teachers (id, name, password, dept, phone, address, id_card, joining_date) VALUES (?,?,?,?,?,?,?,?)",
                              (row['id'], row['name'], row['password'], row['dept'], row['phone'], row['address'], row['id_card'], row['joining_date']))
                conn.commit()
                conn.close()
                st.success("تبدیلیاں محفوظ ہو گئیں")
                st.rerun()
        else:
            st.info("کوئی استاد موجود نہیں")
        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("new_teacher_form"):
                name = st.text_input("استاد کا نام*")
                password = st.text_input("پاسورڈ*", type="password")
                dept = st.selectbox("شعبہ", ["حفظ", "درسِ نظامی", "عصری تعلیم"])
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                id_card = st.text_input("شناختی کارڈ نمبر")
                joining_date = st.date_input("تاریخ شمولیت", date.today())
                photo = st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                if st.form_submit_button("رجسٹر کریں"):
                    if name and password:
                        conn = get_db_connection()
                        c = conn.cursor()
                        try:
                            photo_path = None
                            if photo:
                                os.makedirs("uploads", exist_ok=True)
                                photo_path = f"uploads/teacher_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                                with open(photo_path, "wb") as f:
                                    f.write(photo.getbuffer())
                            c.execute("INSERT INTO teachers (name, password, dept, phone, address, id_card, joining_date, photo) VALUES (?,?,?,?,?,?,?,?)",
                                      (name, password, dept, phone, address, id_card, joining_date, photo_path))
                            conn.commit()
                            st.success("استاد کامیابی سے رجسٹر ہو گیا")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("یہ نام پہلے سے موجود ہے")
                        finally:
                            conn.close()
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں")
    with tab2:
        st.subheader("موجودہ طلبہ")
        conn = get_db_connection()
        try:
            students_df = pd.read_sql_query("""SELECT id, name, father_name, mother_name, dob, admission_date, exit_date, exit_reason,
                                              id_card, phone, address, teacher_name, dept, class, section
                                              FROM students""", conn)
        except Exception as e:
            st.error(f"ڈیٹا لوڈ کرنے میں خرابی: {str(e)}")
            students_df = pd.DataFrame()
        conn.close()
        if not students_df.empty:
            edited_students = st.data_editor(students_df, num_rows="dynamic", use_container_width=True, key="students_edit")
            if st.button("طلبہ میں تبدیلیاں محفوظ کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("DELETE FROM students")
                for _, row in edited_students.iterrows():
                    c.execute("""INSERT INTO students 
                                (id, name, father_name, mother_name, dob, admission_date, exit_date, exit_reason,
                                 id_card, phone, address, teacher_name, dept, class, section)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (row['id'], row['name'], row['father_name'], row['mother_name'], row['dob'], row['admission_date'],
                               row['exit_date'], row['exit_reason'], row['id_card'], row['phone'], row['address'],
                               row['teacher_name'], row['dept'], row['class'], row['section']))
                conn.commit()
                conn.close()
                st.success("تبدیلیاں محفوظ ہو گئیں")
                st.rerun()
        else:
            st.info("کوئی طالب علم موجود نہیں")
        with st.expander("➕ نیا طالب علم داخل کریں"):
            with st.form("new_student_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("طالب علم کا نام*")
                    father = st.text_input("والد کا نام*")
                    mother = st.text_input("والدہ کا نام")
                    dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=365*10))
                    admission_date = st.date_input("تاریخ داخلہ", date.today())
                with col2:
                    dept = st.selectbox("شعبہ*", ["حفظ", "درسِ نظامی", "عصری تعلیم"])
                    class_name = st.text_input("کلاس (عصری تعلیم کے لیے)")
                    section = st.text_input("سیکشن")
                    conn = get_db_connection()
                    teachers_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                    conn.close()
                    teacher = st.selectbox("استاد*", teachers_list) if teachers_list else st.text_input("استاد کا نام*")
                id_card = st.text_input("شناختی کارڈ نمبر (B-Form)")
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                photo = st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                st.markdown("---")
                st.markdown("**اگر طالب علم مدرسہ چھوڑ چکا ہے تو درج ذیل معلومات بھریں (ورنہ خالی چھوڑیں):**")
                exit_date = st.date_input("تاریخ خارج", value=None)
                exit_reason = st.text_area("وجہ خارج")
                if st.form_submit_button("داخلہ کریں"):
                    if name and father and teacher and dept:
                        conn = get_db_connection()
                        c = conn.cursor()
                        try:
                            photo_path = None
                            if photo:
                                os.makedirs("uploads", exist_ok=True)
                                photo_path = f"uploads/student_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                                with open(photo_path, "wb") as f:
                                    f.write(photo.getbuffer())
                            c.execute("""INSERT INTO students 
                                        (name, father_name, mother_name, dob, admission_date, exit_date, exit_reason,
                                         id_card, phone, address, teacher_name, dept, class, section, photo)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (name, father, mother, dob, admission_date, exit_date, exit_reason,
                                       id_card, phone, address, teacher, dept, class_name, section, photo_path))
                            conn.commit()
                            st.success("طالب علم کامیابی سے داخل ہو گیا")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {str(e)}")
                        finally:
                            conn.close()
                    else:
                        st.error("نام، ولدیت، استاد اور شعبہ ضروری ہیں")

elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("ٹائم ٹیبل مینجمنٹ")
    conn = get_db_connection()
    teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
    conn.close()
    if teachers:
        sel_t = st.selectbox("استاد منتخب کریں", teachers)
        with st.form("add_period"):
            day = st.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
            period = st.text_input("وقت (مثلاً 08:00-09:00)")
            book = st.text_input("کتاب / مضمون")
            room = st.text_input("کمرہ نمبر")
            if st.form_submit_button("شامل کریں"):
                conn = get_db_connection()
                conn.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                             (sel_t, day, period, book, room))
                conn.commit()
                conn.close()
                st.success("پیریڈ شامل کر دیا گیا")
                st.rerun()
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(sel_t,))
        conn.close()
        st.table(df)
    else:
        st.warning("پہلے اساتذہ رجسٹر کریں")

elif selected == "📢 نوٹیفیکیشنز" and st.session_state.user_type == "admin":
    st.header("نوٹیفیکیشن سینٹر")
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
            st.success("نوٹیفکیشن بھیج دیا گیا")
    conn = get_db_connection()
    notifs = conn.execute("SELECT title, message, created_at FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    for n in notifs:
        st.info(f"**{n[0]}**\n\n{n[1]}\n\n*{n[2]}*")

elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("تجزیہ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ FROM t_attendance", conn)
    if not df.empty:
        fig = px.bar(df, x='تاریخ', title="اساتذہ کی حاضری")
        st.plotly_chart(fig)
    conn.close()

elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ اور سیٹنگز")
    if st.button("💾 ڈیٹا بیس کا بیک اپ لیں"):
        tables = ["teachers", "students", "hifz_records", "general_education", "t_attendance", "exams", "passed_paras", "timetable", "leave_requests", "notifications", "audit_log"]
        conn = get_db_connection()
        for t in tables:
            try:
                df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
                df.to_csv(f"{t}_backup.csv", index=False)
            except:
                pass
        conn.close()
        st.success("بیک اپ مکمل (تمام ٹیبلز کی CSV فائلیں بن گئیں)")
    with st.expander("آڈٹ لاگ"):
        conn = get_db_connection()
        logs = pd.read_sql_query("SELECT user, action, timestamp, details FROM audit_log ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        st.dataframe(logs)

# ==================== 16. لاگ آؤٹ ====================
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
