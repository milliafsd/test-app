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

def generate_html_report(df, title, student_name="", start_date="", end_date=""):
    """HTML رپورٹ جس میں ہیڈنگز اردو میں ہیں"""
    # ڈیٹا فریم کے کالم نام اردو میں تبدیل کریں (اگر پہلے سے اردو نہ ہوں)
    # یہاں ہم مفروضہ کالم نام رکھتے ہیں
    # چونکہ df پہلے سے اردو کالم ناموں کے ساتھ آئے گا، اس لیے تبدیل کی ضرورت نہیں
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

# -------------------- 3. اسٹائلنگ (موبائل فرینڈلی اور درست رنگ) --------------------
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ | سمارٹ ایجوکیشن پورٹل", layout="wide", initial_sidebar_state="expanded")

if 'language' not in st.session_state:
    st.session_state.language = "urdu"

def set_lang(lang):
    st.session_state.language = lang
    st.rerun()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * {
        font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', Arial, sans-serif;
    }
    body {
        direction: rtl;
        text-align: right;
        background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
        margin: 0;
        padding: 0;
    }
    /* سائڈبار - رنگ درست */
    .stSidebar {
        background: linear-gradient(180deg, #1e5631 0%, #0b2b1a 100%);
        color: white;
    }
    .stSidebar .stRadio label {
        color: white !important;
        font-weight: bold;
        font-size: 1rem;
    }
    .stSidebar .stRadio div {
        color: white;
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
    /* موبائل */
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

# سائڈبار زبان
st.sidebar.markdown("## 🌐 زبان / Language")
lang_col1, lang_col2 = st.sidebar.columns(2)
if lang_col1.button("اردو", use_container_width=True):
    set_lang("urdu")
if lang_col2.button("English", use_container_width=True):
    set_lang("english")

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
        "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری", "👥 یوزر مینجمنٹ",
        "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس", "⚙️ بیک اپ & سیٹنگز"
    ]
else:
    menu = [
        "📝 تعلیمی اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
        "🕒 میری حاضری", "📢 نوٹیفیکیشنز"
    ]

selected = st.sidebar.radio("📌 مینو", menu)

# -------------------- 6. سورتوں کی فہرست --------------------
surahs_urdu = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
    "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج",
    "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب",
    "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف",
    "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة",
    "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة",
    "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر",
    "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل",
    "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة",
    "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"
]
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
    
    query = "SELECT r_date as تاریخ, s_name as نام, f_name as ولدیت, t_name as استاد, surah as سبق, sq_m as سبقی_غلطی, m_m as منزل_غلطی, attendance as حاضری FROM hifz_records WHERE r_date BETWEEN ? AND ?"
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
        # گریڈ شامل کریں
        df['کل_غلطیاں'] = df['سبقی_غلطی'] + df['منزل_غلطی']
        df['درجہ'] = df['کل_غلطیاں'].apply(get_grade_from_mistakes)
        
        # خلاصہ
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("کل ریکارڈ", len(df))
        col2.metric("حاضر طلباء", len(df[df['حاضری'] == 'حاضر']))
        avg_mistakes = df['کل_غلطیاں'].mean()
        col3.metric("اوسط غلطیاں", round(avg_mistakes, 1))
        col4.metric("مجموعی درجہ", get_grade_from_mistakes(avg_mistakes))
        
        # تاریخ وار گروپ
        dates = sorted(df['تاریخ'].unique())
        for d in dates:
            with st.expander(f"📆 {d}"):
                sub = df[df['تاریخ'] == d]
                edited = st.data_editor(sub, key=f"edit_{d}", use_container_width=True, num_rows="dynamic")
                if st.button(f"💾 محفوظ کریں ({d})"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM hifz_records WHERE r_date=?", (d,))
                    # یہاں ہمیں اصل کالمز کے مطابق ڈیٹا ڈالنا ہوگا
                    # چونکہ edited میں صرف منتخب کالم ہیں، ہم اصل ٹیبل میں ڈالنے کے لیے ڈیٹا تیار کریں
                    for _, row in edited.iterrows():
                        # اصل hifz_records ٹیبل کے کالم: r_date, s_name, f_name, t_name, surah, sq_m, m_m, attendance
                        # ہمارے پاس sq_m اور m_m ہیں، sq_a, m_a وغیرہ 0 ڈال سکتے ہیں
                        c.execute("""INSERT INTO hifz_records 
                                    (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance)
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                  (row['تاریخ'], row['نام'], row['ولدیت'], row['استاد'], row['سبق'], 
                                   "N/A", 0, row['سبقی_غلطی'], "N/A", 0, row['منزل_غلطی'], row['حاضری']))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Edit Daily Report", f"Date: {d}")
                    st.success("محفوظ ہو گیا")
                    st.rerun()
        
        # ڈاؤن لوڈ اور پرنٹ
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
        query = """SELECT 
                    r_date as تاریخ, 
                    attendance as حاضری,
                    surah as 'سبق (آیت تا آیت)', 
                    sq_p as 'سبقی (پارہ)', sq_m as 'سبقی (غلطی)', sq_a as 'سبقی (اٹکن)', 
                    m_p as 'منزل (پارہ)', m_m as 'منزل (غلطی)', m_a as 'منزل (اٹکن)' 
                   FROM hifz_records 
                   WHERE s_name=? AND r_date BETWEEN ? AND ?
                   ORDER BY r_date ASC"""
        try:
            df = pd.read_sql_query(query, conn, params=(sel_s, start, end))
        except Exception as e:
            st.error(f"خرابی: {str(e)}")
            df = pd.DataFrame()
        conn.close()
        
        if df.empty:
            st.warning("کوئی ریکارڈ نہیں")
        else:
            # گریڈ شامل کریں
            df['کل_غلطیاں'] = df['سبقی (غلطی)'] + df['منزل (غلطی)']
            df['درجہ'] = df['کل_غلطیاں'].apply(get_grade_from_mistakes)
            
            st.dataframe(df, use_container_width=True)
            
            # خلاصہ
            avg_mistakes = df['کل_غلطیاں'].mean()
            st.info(f"**اوسط غلطیاں:** {round(avg_mistakes, 1)} | **مجموعی درجہ:** {get_grade_from_mistakes(avg_mistakes)}")
            
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

elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 اساتذہ و طلبہ مینجمنٹ")
    t1, t2 = st.tabs(["اساتذہ", "طلبہ"])
    with t1:
        conn = get_db_connection()
        try:
            teachers = pd.read_sql_query("SELECT id, name, password, phone, address, id_card FROM teachers", conn)
        except Exception as e:
            st.error(f"خرابی: {str(e)}")
            teachers = pd.DataFrame()
        conn.close()
        if not teachers.empty:
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
        try:
            students = pd.read_sql_query("SELECT id, name, father_name, mother_name, teacher_name, phone, address, id_card, admission_date, class, section FROM students", conn)
        except Exception as e:
            st.error(f"خرابی: {str(e)}")
            students = pd.DataFrame()
        conn.close()
        if not students.empty:
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
        rec_df['کل_غلطیاں'] = rec_df['سبقی_غلطی'] + rec_df['منزل_غلطی']
        rec_df['درجہ'] = rec_df['کل_غلطیاں'].apply(get_grade_from_mistakes)
        fig2 = px.scatter(rec_df, x='سبقی_غلطی', y='منزل_غلطی', color='درجہ', title='غلطیوں کا تجزیہ')
        st.plotly_chart(fig2, use_container_width=True)
    conn.close()

elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("⚙️ بیک اپ اور سیٹنگز")
    if st.button("💾 ڈیٹا بیس کا بیک اپ (CSV)"):
        tables = ["teachers", "students", "hifz_records", "t_attendance", "leave_requests", "exams", "notifications", "audit_log"]
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
        with st.form("daily_entry"):
            records = []
            for s, f in students:
                st.markdown(f"### 👤 {s} ولد {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر"], key=f"att_{s}", horizontal=True)
                if att == "حاضر":
                    # سبق
                    surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{s}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{s}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{s}")
                    sabq = f"{surah}: {a_from}-{a_to}"
                    
                    # سبقی - متعدد پاروں کے لیے بٹن کے ذریعے
                    st.write("**سبقی**")
                    if f"sq_parts_{s}" not in st.session_state:
                        st.session_state[f"sq_parts_{s}"] = []
                    if f"sq_mistakes_{s}" not in st.session_state:
                        st.session_state[f"sq_mistakes_{s}"] = []
                    if f"sq_atkan_{s}" not in st.session_state:
                        st.session_state[f"sq_atkan_{s}"] = []
                    
                    # موجودہ پاروں کو دکھائیں
                    for idx, (para, val, atk, mis) in enumerate(zip(st.session_state[f"sq_parts_{s}"],
                                                                   st.session_state.get(f"sq_values_{s}", []),
                                                                   st.session_state.get(f"sq_atkan_{s}", []),
                                                                   st.session_state.get(f"sq_mistakes_{s}", []))):
                        st.write(f"{idx+1}. {para} - مقدار: {val} | اٹکن: {atk} | غلطی: {mis}")
                    
                    # نیا پارہ شامل کرنے کا بٹن
                    col1, col2, col3, col4 = st.columns(4)
                    new_para = col1.selectbox("پارہ", paras, key=f"new_para_{s}")
                    new_val = col2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"new_val_{s}")
                    new_atk = col3.number_input("اٹکن", 0, key=f"new_atk_{s}")
                    new_mis = col4.number_input("غلطی", 0, key=f"new_mis_{s}")
                    if st.button(f"➕ مزید سبقی پارہ ({s})", key=f"add_sq_{s}"):
                        st.session_state[f"sq_parts_{s}"].append(new_para)
                        if f"sq_values_{s}" not in st.session_state:
                            st.session_state[f"sq_values_{s}"] = []
                        st.session_state[f"sq_values_{s}"].append(new_val)
                        if f"sq_atkan_{s}" not in st.session_state:
                            st.session_state[f"sq_atkan_{s}"] = []
                        st.session_state[f"sq_atkan_{s}"].append(new_atk)
                        if f"sq_mistakes_{s}" not in st.session_state:
                            st.session_state[f"sq_mistakes_{s}"] = []
                        st.session_state[f"sq_mistakes_{s}"].append(new_mis)
                        st.rerun()
                    
                    # منزل - اسی طرح
                    st.write("**منزل**")
                    if f"m_parts_{s}" not in st.session_state:
                        st.session_state[f"m_parts_{s}"] = []
                    if f"m_values_{s}" not in st.session_state:
                        st.session_state[f"m_values_{s}"] = []
                    if f"m_atkan_{s}" not in st.session_state:
                        st.session_state[f"m_atkan_{s}"] = []
                    if f"m_mistakes_{s}" not in st.session_state:
                        st.session_state[f"m_mistakes_{s}"] = []
                    
                    for idx, (para, val, atk, mis) in enumerate(zip(st.session_state[f"m_parts_{s}"],
                                                                   st.session_state.get(f"m_values_{s}", []),
                                                                   st.session_state.get(f"m_atkan_{s}", []),
                                                                   st.session_state.get(f"m_mistakes_{s}", []))):
                        st.write(f"{idx+1}. {para} - مقدار: {val} | اٹکن: {atk} | غلطی: {mis}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    new_para_m = col1.selectbox("پارہ", paras, key=f"new_para_m_{s}")
                    new_val_m = col2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"new_val_m_{s}")
                    new_atk_m = col3.number_input("اٹکن", 0, key=f"new_atk_m_{s}")
                    new_mis_m = col4.number_input("غلطی", 0, key=f"new_mis_m_{s}")
                    if st.button(f"➕ مزید منزل پارہ ({s})", key=f"add_m_{s}"):
                        st.session_state[f"m_parts_{s}"].append(new_para_m)
                        st.session_state[f"m_values_{s}"].append(new_val_m)
                        st.session_state[f"m_atkan_{s}"].append(new_atk_m)
                        st.session_state[f"m_mistakes_{s}"].append(new_mis_m)
                        st.rerun()
                    
                    # ڈیٹا تیار کریں
                    sq_parts_str = " | ".join([f"{p}:{v}" for p, v in zip(st.session_state[f"sq_parts_{s}"], st.session_state.get(f"sq_values_{s}", []))])
                    sq_a_total = sum(st.session_state.get(f"sq_atkan_{s}", []))
                    sq_m_total = sum(st.session_state.get(f"sq_mistakes_{s}", []))
                    m_parts_str = " | ".join([f"{p}:{v}" for p, v in zip(st.session_state[f"m_parts_{s}"], st.session_state.get(f"m_values_{s}", []))])
                    m_a_total = sum(st.session_state.get(f"m_atkan_{s}", []))
                    m_m_total = sum(st.session_state.get(f"m_mistakes_{s}", []))
                else:
                    sabq = "ناغہ"
                    sq_parts_str = "ناغہ"
                    sq_a_total = sq_m_total = 0
                    m_parts_str = "ناغہ"
                    m_a_total = m_m_total = 0
                
                records.append((sel_date, s, f, st.session_state.username, sabq,
                                sq_parts_str, sq_a_total, sq_m_total,
                                m_parts_str, m_a_total, m_m_total, att))
            
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
                    # سیشن صاف کریں
                    for s, f in students:
                        for key in [f"sq_parts_{s}", f"sq_values_{s}", f"sq_atkan_{s}", f"sq_mistakes_{s}",
                                    f"m_parts_{s}", f"m_values_{s}", f"m_atkan_{s}", f"m_mistakes_{s}"]:
                            if key in st.session_state:
                                del st.session_state[key]
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
        if not hist.empty:
            st.dataframe(hist, use_container_width=True)
            st.download_button("ہسٹری ڈاؤن لوڈ", convert_df_to_csv(hist), "exam_history.csv")
        else:
            st.info("کوئی مکمل شدہ امتحان نہیں")

# -------------------- 9. لاگ آؤٹ --------------------
st.sidebar.divider()
if st.sidebar.button("🚪 " + T['logout']):
    st.session_state.logged_in = False
    st.rerun()
