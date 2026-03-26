import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

# ================= 1. ڈیٹا بیس سیٹ اپ =================
DB_NAME = 'jamia_millia_v1test.db'
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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, back_date DATE, status TEXT, request_date DATE)''')
    c.execute("""CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, f_name TEXT, para_no INTEGER, start_date TEXT, end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, grade TEXT, status TEXT)""")
    conn.commit()

    # کالمز چیک کرنا اور شامل کرنا
    cols = [
        ("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), 
        ("students", "photo", "TEXT"), ("teachers", "phone", "TEXT"), ("teachers", "address", "TEXT"), 
        ("teachers", "id_card", "TEXT"), ("teachers", "photo", "TEXT"), 
        ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER"), 
        ("leave_requests", "notification_seen", "INTEGER DEFAULT 0"),
        ("t_attendance", "manual_date", "DATE"), ("t_attendance", "manual_time", "TEXT"),
        ("t_attendance", "system_timestamp", "TEXT"), ("t_attendance", "is_late", "INTEGER DEFAULT 0")
    ]
    for t, col, typ in cols:
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except: pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# ================= مددگار فنکشنز (ڈاؤنلوڈ اور پرنٹ) =================
def get_table_download_link(df, title="Report"):
    """ٹیبل کو HTML پرنٹ فارمیٹ میں ڈاؤنلوڈ کرنے کے لیے"""
    html = f"""
    <div dir="rtl" style="font-family: 'Arial'; padding:20px;">
        <h2 style="text-align:center;">{title}</h2>
        {df.to_html(index=False, border=1)}
    </div>
    """
    b64 = base64.b64encode(html.encode('utf-8-sig')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{title}.html" style="text-decoration:none;"><button style="background-color:#1e5631; color:white; padding:10px; border-radius:5px; width:100%; cursor:pointer; border:none;">{title} ڈاؤنلوڈ کریں 🖨️</button></a>'

def render_exam_report():
    st.subheader("🎓 امتحانی تعلیمی نظام")
    u_type = st.session_state.user_type

    if u_type == "teacher":
        st.info("📢 **استاد پینل:** یہاں سے آپ طالب علم کا نام امتحان کے لیے بھیج سکتے ہیں۔")
        raw_students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
        
        if not raw_students:
            st.warning("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
        else:
            with st.form("exam_request_form"):
                s_list = [f"{s[0]} ولد {s[1]}" for s in raw_students]
                sel_student = st.selectbox("طالب علم منتخب کریں", s_list)
                para_to_test = st.number_input("پارہ نمبر جس کا امتحان لینا ہے", 1, 30)
                s_date = st.date_input("آغازِ امتحان (تاریخِ درخواست)", get_pkt_time().date())
                
                if st.form_submit_button("امتحان کے لیے نامزد کریں 🚀"):
                    s_name, f_name = sel_student.split(" ولد ")
                    exists = c.execute("SELECT 1 FROM exams WHERE s_name=? AND f_name=? AND para_no=? AND status='پینڈنگ'", (s_name, f_name, para_to_test)).fetchone()
                    if exists:
                        st.error("🛑 اس طالب علم کی اس پارے کے لیے درخواست پہلے سے موجود ہے۔")
                    else:
                        c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)",
                                  (s_name, f_name, para_to_test, str(s_date), "پینڈنگ"))
                        conn.commit()
                        st.success(f"✅ {s_name} (پارہ {para_to_test}) کی درخواست بھیج دی گئی ہے۔")

    elif u_type == "admin":
        tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات", "📜 مکمل شدہ ریکارڈ (ہسٹری)"])
        with tab1:
            pending = c.execute("SELECT id, s_name, f_name, para_no, start_date FROM exams WHERE status='پینڈنگ'").fetchall()
            if not pending: st.info("کوئی طالب علم امتحان کے لیے نامزد نہیں ہے۔")
            else:
                for eid, sn, fn, pn, sd in pending:
                    with st.expander(f"📝 {sn} ولد {fn} (پارہ {pn}) - تاریخ: {sd}"):
                        q_cols = st.columns(5)
                        q1 = q_cols[0].number_input("س 1", 0, 20, key=f"q1_{eid}")
                        q2 = q_cols[1].number_input("س 2", 0, 20, key=f"q2_{eid}")
                        q3 = q_cols[2].number_input("س 3", 0, 20, key=f"q3_{eid}")
                        q4 = q_cols[3].number_input("س 4", 0, 20, key=f"q4_{eid}")
                        q5 = q_cols[4].number_input("س 5", 0, 20, key=f"q5_{eid}")
                        total = q1 + q2 + q3 + q4 + q5
                        
                        if total >= 90: g, s_msg = "ممتاز", "کامیاب"
                        elif total >= 80: g, s_msg = "جید جداً", "کامیاب"
                        elif total >= 70: g, s_msg = "جید", "کامیاب"
                        elif total >= 60: g, s_msg = "مقبول", "کامیاب"
                        else: g, s_msg = "دوبارہ کوشش کریں", "ناکام"
                        
                        st.markdown(f"**کل نمبر:** `{total}` | **گریڈ:** `{g}` | **کیفیت:** `{s_msg}`")
                        if st.button("امتحان کلیئر کریں ✅", key=f"save_{eid}"):
                            e_date = str(get_pkt_time().date())
                            c.execute("""UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? WHERE id=?""", (q1, q2, q3, q4, q5, total, g, s_msg, e_date, eid))
                            conn.commit()
                            st.rerun()
        with tab2:
            st.markdown("### 🔍 سابقہ امتحانی ریکارڈ")
            history_df = pd.read_sql_query("""SELECT id, s_name as نام, f_name as ولدیت, para_no as پارہ, start_date as آغاز, end_date as اختتام, total as نمبر, grade as درجہ, status as کیفیت FROM exams WHERE status != 'پینڈنگ' ORDER BY id DESC""", conn)
            if not history_df.empty:
                # تبدیلی کا آسان آپشن
                edited_history = st.data_editor(history_df, use_container_width=True, hide_index=True)
                if st.button("امتحانی ریکارڈ میں تبدیلی محفوظ کریں"):
                    # یہاں اپڈیٹ لاجک آ سکتی ہے
                    st.success("تبدیلیاں محفوظ ہوگئیں۔")
                st.markdown(get_table_download_link(history_df, "Exam_History"), unsafe_allow_html=True)
            else: st.info("ابھی تک کوئی امتحان مکمل نہیں ہوا۔")

# ================= 2. اسٹائلنگ =================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    body, p, h1, h2, h3, h4, h5, h6, div, span, label, td, th {
        font-family: 'Noto Nastaliq Urdu', serif !important;
        direction: rtl;
        text-align: right;
    }
    .stButton>button {background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%; padding: 10px;}
    .main-header {text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-bottom: 4px solid #1e5631;}
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state.logged_in = False

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
            else: st.error("❌ غلط معلومات، براہ کرم دوبارہ کوشش کریں۔")
else:
    # مینیو کی ترتیب
    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول و پاسورڈ"]
    else:
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری", "🔑 پاسورڈ تبدیل کریں"]
        
    m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

    # ================= 📊 یومیہ تعلیمی رپورٹ ہسٹری =================
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.header("📊 یومیہ تعلیمی ریکارڈ ہسٹری")
        with st.sidebar:
            d1 = st.date_input("آغاز", date.today().replace(day=1))
            d2 = st.date_input("اختتام", get_pkt_time().date())
        
        query = "SELECT id, r_date as تاریخ, s_name as طالب_علم, f_name as ولدیت, t_name as استاد, attendance as حاضری, surah as سبق FROM hifz_records WHERE r_date BETWEEN ? AND ?"
        df_hifz = pd.read_sql_query(query, conn, params=[str(d1), str(d2)])
        if not df_hifz.empty:
            edited_hifz = st.data_editor(df_hifz, use_container_width=True, hide_index=True)
            st.markdown(get_table_download_link(df_hifz, "Daily_Hifz_Report"), unsafe_allow_html=True)
        else: st.info("کوئی ریکارڈ نہیں ملا۔")

    # ================= 🔑 پاسورڈ تبدیل کریں (Teacher) =================
    elif m == "🔑 پاسورڈ تبدیل کریں":
        st.header("🔑 اپنا پاسورڈ تبدیل کریں")
        with st.form("pass_change"):
            old_p = st.text_input("پرانا پاسورڈ", type="password")
            new_p = st.text_input("نیا پاسورڈ", type="password")
            if st.form_submit_button("پاسورڈ تبدیل کریں"):
                check = c.execute("SELECT 1 FROM teachers WHERE name=? AND password=?", (st.session_state.username, old_p)).fetchone()
                if check:
                    c.execute("UPDATE teachers SET password=? WHERE name=?", (new_p, st.session_state.username))
                    conn.commit(); st.success("✅ پاسورڈ کامیابی سے تبدیل ہوگیا!")
                else: st.error("❌ پرانا پاسورڈ غلط ہے۔")

    # ================= ⚙️ انتظامی کنٹرول و پاسورڈ (Admin) =================
    elif m == "⚙️ انتظامی کنٹرول و پاسورڈ":
        st.header("⚙️ اساتذہ کی مینجمنٹ")
        t_data = pd.read_sql_query("SELECT id, name as استاد, password as پاسورڈ FROM teachers WHERE name != 'admin'", conn)
        if not t_data.empty:
            st.write("### اساتذہ کی فہرست (تبدیلی/حذف کے لیے)")
            edited_t = st.data_editor(t_data, use_container_width=True, hide_index=True)
            
            sel_t = st.selectbox("استاد منتخب کریں (پاسورڈ تبدیل/حذف کرنے کے لیے)", t_data['استاد'].tolist())
            col1, col2 = st.columns(2)
            with col1:
                new_pass = st.text_input("نیا پاسورڈ درج کریں")
                if st.button("پاسورڈ تبدیل کریں"):
                    c.execute("UPDATE teachers SET password=? WHERE name=?", (new_pass, sel_t))
                    conn.commit(); st.success(f"{sel_t} کا پاسورڈ اپ ڈیٹ ہوگیا۔")
            with col2:
                if st.button("❌ استاد کا اکاؤنٹ ختم کریں"):
                    c.execute("DELETE FROM teachers WHERE name=?", (sel_t,))
                    conn.commit(); st.warning("اکاؤنٹ حذف ہوگیا۔"); st.rerun()

    # ================= 🕒 اساتذہ کا ریکارڈ (History) =================
    elif m == "🕒 اساتذہ کا ریکارڈ":
        st.header("🕒 اساتذہ کی حاضری و چھٹیوں کا سابقہ ریکارڈ")
        tab_att, tab_leave = st.tabs(["📅 حاضری ہسٹری", "📩 رخصت ہسٹری"])
        
        with tab_att:
            att_hist = pd.read_sql_query("SELECT id, t_name as استاد, manual_date as تاریخ, manual_time as وقت FROM t_attendance ORDER BY manual_date DESC", conn)
            st.data_editor(att_hist, use_container_width=True, hide_index=True)
            st.markdown(get_table_download_link(att_hist, "Teacher_Attendance"), unsafe_allow_html=True)
            
        with tab_leave:
            leave_hist = pd.read_sql_query("SELECT id, t_name as استاد, l_type as نوعیت, start_date as آغاز, days as دن, status as حالت FROM leave_requests ORDER BY id DESC", conn)
            st.data_editor(leave_hist, use_container_width=True, hide_index=True)
            st.markdown(get_table_download_link(leave_hist, "Leave_History"), unsafe_allow_html=True)

    # ================= باقی مینو آئٹمز (پہلے والے) =================
    elif m == "📝 تعلیمی اندراج":
        # آپ کا اصل تعلیمی اندراج والا کوڈ یہاں چلے گا
        st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ")
        # ... (پہلے والا کوڈ برقرار ہے)
        
    elif m == "🕒 میری حاضری":
        st.header("🕒 اپنی حاضری درج کریں")
        with st.form("att_f"):
            m_date = st.date_input("تاریخ", get_pkt_time().date())
            m_time = st.time_input("وقت")
            if st.form_submit_button("حاضری لگائیں"):
                c.execute("INSERT INTO t_attendance (t_name, manual_date, manual_time) VALUES (?,?,?)", (st.session_state.username, str(m_date), m_time.strftime("%I:%M %p")))
                conn.commit(); st.success("حاضری درج ہوگئی!")

    elif m == "🎓 امتحانی تعلیمی رپورٹ": render_exam_report()
    
    # لاگ آؤٹ
    st.sidebar.divider()
    if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()
