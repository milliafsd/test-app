import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

# ================= 1. ڈیٹا بیس سیٹ اپ =================
DB_NAME = 'jamia_millia_v1.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def get_pkt_time():
    return datetime.utcnow() + timedelta(hours=5)

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS teachers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                  surah TEXT, a_from TEXT, a_to TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, 
                  m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT, principal_note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, manual_date DATE, manual_time TEXT, system_timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, days INTEGER, status TEXT, l_type TEXT)''')
    c.execute("""CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, f_name TEXT, para_no INTEGER, start_date TEXT, end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, grade TEXT, status TEXT)""")
    conn.commit()
    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# ================= 2. پرنٹ ایبل رپورٹ فنکشن =================
def get_report_download_link(html_content, filename="report.html"):
    b64 = base64.b64encode(html_content.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background-color:#27ae60; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer; width:100%;">رپورٹ ڈاؤنلوڈ کریں اور پرنٹ نکالیں 🖨️</button></a>'

# ================= 3. اسٹائلنگ (RTL اور نستعلیق) =================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    html, body, [data-testid="stSidebar"], .main, p, h1, h2, h3, h4, h5, h6, div, span, label, td, th {
        font-family: 'Noto Nastaliq Urdu', serif !important;
        direction: rtl !important;
        text-align: right !important;
    }
    .stButton>button {background: #1e5631; color: white; border-radius: 8px; width: 100%; padding: 10px;}
    .main-header {text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-bottom: 4px solid #1e5631;}
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# --- ہیڈر ---
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state.logged_in = False

# ================= 4. لاگ ان لاجک =================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.subheader("🔐 لاگ ان پینل")
        u = st.text_input("صارف کا نام")
        p = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("❌ غلط معلومات")
else:
    # مینو کی ترتیب
    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 پارہ ٹریکنگ و سابقہ ریکارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری"]
    
    m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

    # ================= 5. پارہ ٹریکنگ اور سابقہ امتحانات (NEW) =================
    if m == "📜 پارہ ٹریکنگ و سابقہ ریکارڈ":
        st.header("📜 طالب علم کا مکمل تعلیمی ریکارڈ")
        students = c.execute("SELECT name, father_name FROM students").fetchall()
        if students:
            s_list = [f"{s[0]} ولد {s[1]}" for s in students]
            sel_student = st.selectbox("طالب علم منتخب کریں", s_list)
            sn, fn = sel_student.split(" ولد ")

            # ڈیٹا حاصل کریں
            exam_history = pd.read_sql_query(f"SELECT para_no as 'پارہ', start_date as 'آغاز', end_date as 'اختتام', total as 'نمبر', grade as 'درجہ' FROM exams WHERE s_name='{sn}' AND f_name='{fn}'", conn)
            daily_history = pd.read_sql_query(f"SELECT r_date as 'تاریخ', surah as 'سورت', sq_m as 'سبقی غلطی', m_m as 'منزل غلطی' FROM hifz_records WHERE s_name='{sn}' AND f_name='{fn}' ORDER BY r_date DESC LIMIT 15", conn)

            st.subheader(f"رپورٹ: {sel_student}")
            st.write("### 1. پارہ ٹریکنگ و سابقہ امتحانات")
            st.dataframe(exam_history, use_container_width=True, hide_index=True)

            st.write("### 2. حالیہ روزانہ کارکردگی")
            st.dataframe(daily_history, use_container_width=True, hide_index=True)

            # پرنٹ آپشن
            report_html = f"""
            <div dir="rtl" style="font-family:Arial; padding:30px; border:2px solid #000;">
                <h1 style="text-align:center;">جامعہ ملیہ اسلامیہ - تعلیمی رپورٹ</h1>
                <p><strong>نام طالب علم:</strong> {sn} &nbsp;&nbsp;&nbsp; <strong>ولدیت:</strong> {fn}</p>
                <hr>
                <h3>پارہ ٹریکنگ و امتحانات</h3>
                {exam_history.to_html(index=False, border=1)}
                <br>
                <h3>حالیہ کارکردگی</h3>
                {daily_history.to_html(index=False, border=1)}
                <br><br>
                <div style="display:flex; justify-content:space-between; margin-top:50px;">
                    <p style="border-top:1px solid #000; width:200px; text-align:center;">دستخط استاد</p>
                    <p style="border-top:1px solid #000; width:200px; text-align:center;">دستخط ناظم / ایڈمن</p>
                </div>
            </div>
            """
            st.markdown(get_report_download_link(report_html, f"{sn}_report.html"), unsafe_allow_html=True)

    # ================= 6. امتحانی رپورٹ (Original Logic) =================
    elif m == "🎓 امتحانی تعلیمی رپورٹ":
        st.subheader("🎓 امتحانی تعلیمی نظام")
        if st.session_state.user_type == "teacher":
            students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
            if students:
                with st.form("exam_request"):
                    s_list = [f"{s[0]} ولد {s[1]}" for s in students]
                    sel_s = st.selectbox("طالب علم", s_list)
                    p_no = st.number_input("پارہ نمبر", 1, 30)
                    if st.form_submit_button("امتحان کے لیے نامزد کریں"):
                        sn_part, fn_part = sel_s.split(" ولد ")
                        c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)", (sn_part, fn_part, p_no, str(date.today()), "پینڈنگ"))
                        conn.commit(); st.success("درخواست بھیج دی گئی۔")
        else:
            pending = c.execute("SELECT id, s_name, f_name, para_no FROM exams WHERE status='پینڈنگ'").fetchall()
            for eid, sn, fn, pn in pending:
                with st.expander(f"📝 {sn} (پارہ {pn})"):
                    q = st.columns(5)
                    q1 = q[0].number_input("س 1", 0, 20, key=f"q1_{eid}")
                    q2 = q[1].number_input("س 2", 0, 20, key=f"q2_{eid}")
                    total = q1 + q2 # آپ مزید سوالات یہاں شامل کر سکتے ہیں
                    if st.button("پاس کریں", key=f"p_{eid}"):
                        c.execute("UPDATE exams SET total=?, status='کامیاب', end_date=? WHERE id=?", (total, str(date.today()), eid))
                        conn.commit(); st.rerun()

    # ================= 7. تعلیمی اندراج (Original Teacher Logic) =================
    elif m == "📝 تعلیمی اندراج":
        st.header("📝 یومیہ تعلیمی ریکارڈ")
        sel_date = st.date_input("تاریخ", get_pkt_time().date())
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
        for s, f in students:
            with st.expander(f"👤 {s} ولد {f}"):
                att = st.radio(f"حاضری {s}", ["حاضر", "ناغہ", "رخصت"], key=f"att_{s}", horizontal=True)
                if att == "حاضر":
                    surah = st.selectbox("سورت", surahs_urdu, key=f"sur_{s}")
                    sq_m = st.number_input("سبقی غلطی", 0, 50, key=f"sqm_{s}")
                    m_m = st.number_input("منزل غلطی", 0, 50, key=f"mm_{s}")
                    if st.button(f"محفوظ کریں {s}", key=f"save_{s}"):
                        c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, sq_m, m_m, attendance) VALUES (?,?,?,?,?,?,?,?)", (sel_date, s, f, st.session_state.username, surah, sq_m, m_m, att))
                        conn.commit(); st.success("محفوظ ہو گیا۔")

    # ================= 8. میری حاضری (Fixed) =================
    elif m == "🕒 میری حاضری":
        st.header("🕒 حاضری اساتذہ")
        st.info("اپنی آمد کا وقت درج کریں")
        with st.form("att_form"):
            d = st.date_input("تاریخ", date.today())
            t = st.time_input("وقت", get_pkt_time().time())
            if st.form_submit_button("حاضری لگائیں"):
                c.execute("INSERT INTO t_attendance (t_name, manual_date, manual_time) VALUES (?,?,?)", (st.session_state.username, d, str(t)))
                conn.commit(); st.success("حاضری درج ہو گئی۔")

    # ================= 9. یومیہ رپورٹ (Admin) =================
    elif m == "📊 یومیہ تعلیمی رپورٹ":
        st.header("📊 یومیہ تعلیمی رپورٹ")
        df = pd.read_sql_query("SELECT r_date as تاریخ, s_name as طالب_علم, surah as سورت, sq_m as سبقی_غلطی, m_m as منزل_غلطی FROM hifz_records ORDER BY r_date DESC", conn)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ================= 10. انتظامی کنٹرول (Admin) =================
    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن")
        tab1, tab2 = st.tabs(["👨‍🏫 اساتذہ", "👨‍🎓 طلباء"])
        with tab1:
            with st.form("t_reg"):
                tn = st.text_input("استاد کا نام")
                tp = st.text_input("پاسورڈ")
                if st.form_submit_button("رجسٹر کریں"):
                    c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                    conn.commit(); st.success("استاد رجسٹر ہو گئے۔")
        with tab2:
            with st.form("s_reg"):
                sn = st.text_input("طالب علم کا نام")
                fn = st.text_input("ولدیت")
                tl = [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                st_teacher = st.selectbox("استاد منتخب کریں", tl)
                if st.form_submit_button("داخلہ کریں"):
                    c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (sn, fn, st_teacher))
                    conn.commit(); st.success("داخلہ مکمل ہو گیا۔")

    # لاگ آؤٹ
    if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun()
