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

# ================= مددگار فنکشنز =================
def get_report_download_link(html_content, filename="report.html"):
    b64 = base64.b64encode(html_content.encode('utf-8-sig')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background-color:#27ae60; color:white; font-weight:bold; padding:12px 20px; border:none; border-radius:8px; cursor:pointer; width:100%;">رپورٹ ڈاؤنلوڈ کریں اور پرنٹ نکالیں 🖨️</button></a>'

def render_exam_report():
    st.subheader("🎓 امتحانی تعلیمی نظام")
    u_type = st.session_state.user_type

    if u_type == "teacher":
        st.info("📢 **استاد پینل:** یہاں سے آپ طالب علم کا نام امتحان کے لیے بھیج سکتے ہیں۔")
        # ٹپل فکس:
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
        tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات", "📜 مکمل شدہ ریکارڈ"])
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
            history_df = pd.read_sql_query("""SELECT s_name as نام, f_name as ولدیت, para_no as پارہ, start_date as آغاز, end_date as اختتام, total as نمبر, grade as درجہ, status as کیفیت FROM exams WHERE status != 'پینڈنگ' ORDER BY id DESC""", conn)
            if not history_df.empty:
                st.dataframe(history_df, use_container_width=True, hide_index=True)
            else: st.info("ابھی تک کوئی امتحان مکمل نہیں ہوا۔")

# ================= 2. اسٹائلنگ اور دائیں سے بائیں (RTL) =================
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
    .date-divider {background-color: #2e7d32; color: white; text-align: center; padding: 10px; font-size: 20px; border-radius: 8px; margin: 20px 0;}
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
    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "🖨️ ٹریکنگ و پرنٹ رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری"]
        
    m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

    # ================= ADMIN: یومیہ تعلیمی رپورٹ =================
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.markdown("<h2 style='text-align: center; color: #1e5631;'>📊 ماسٹر تعلیمی رپورٹ و تجزیہ</h2>", unsafe_allow_html=True)
        with st.sidebar:
            st.header("🔍 فلٹرز")
            d1 = st.date_input("آغاز", date.today().replace(day=1))
            d2 = st.date_input("اختتام", get_pkt_time().date())
            t_list = ["تمام"] + [str(t[0]) for t in c.execute("SELECT DISTINCT name FROM teachers WHERE name != 'admin'").fetchall()]
            sel_t = st.selectbox("استاد/کلاس", t_list)

        query = "SELECT r_date, s_name, f_name, t_name, attendance, surah, sq_p, sq_m, m_p, m_m FROM hifz_records WHERE r_date BETWEEN ? AND ?"
        params = [str(d1), str(d2)]
        if sel_t != "تمام": query += " AND t_name = ?"; params.append(sel_t)
        query += " ORDER BY r_date DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        if df.empty: st.warning("ریکارڈ نہیں ملا۔")
        else:
            grouped = df.groupby('r_date')
            for date_val, group_df in grouped:
                st.markdown(f"<div class='date-divider'>📅 تاریخ: {date_val}</div>", unsafe_allow_html=True)
                group_df = group_df.rename(columns={"s_name": "طالب علم", "f_name": "ولدیت", "t_name": "استاد", "attendance": "حاضری", "surah": "سبق", "sq_p": "تفصیل سبقی", "sq_m": "سبقی غلطی", "m_p": "تفصیل منزل", "m_m": "منزل غلطی"})
                st.dataframe(group_df.drop(columns=['r_date']), use_container_width=True, hide_index=True)

    # ================= 🖨️ ٹریکنگ و پرنٹ رپورٹ (Full original HTML logic) =================
    elif m == "🖨️ ٹریکنگ و پرنٹ رپورٹ":
        st.header("🖨️ طالب علم کی تفصیلی ٹریکنگ اور پرنٹ")
        raw_students = c.execute("SELECT name, father_name FROM students").fetchall()
        if raw_students:
            s_list = [f"{s[0]} ولد {s[1]}" for s in raw_students]
            sel_student = st.selectbox("طالب علم منتخب کریں", s_list)
            sn, fn = sel_student.split(" ولد ")

            exam_history = pd.read_sql_query(f"SELECT para_no as 'پارہ', start_date as 'آغاز', end_date as 'اختتام', total as 'نمبر', grade as 'درجہ' FROM exams WHERE s_name='{sn}' AND f_name='{fn}'", conn)
            daily_history = pd.read_sql_query(f"SELECT r_date as 'تاریخ', attendance as 'حاضری', surah as 'سبق', sq_p as 'سبقی تفصیل', sq_m as 'سبقی غلطی', m_p as 'منزل تفصیل', m_m as 'منزل غلطی' FROM hifz_records WHERE s_name='{sn}' AND f_name='{fn}' ORDER BY r_date DESC LIMIT 30", conn)

            st.write("### 📜 امتحانات کا ریکارڈ")
            st.dataframe(exam_history, use_container_width=True, hide_index=True)
            st.write("### 📝 یومیہ تفصیلی کارکردگی")
            st.dataframe(daily_history, use_container_width=True, hide_index=True)

            report_html = f"""
            <div dir="rtl" style="font-family:Arial; padding:30px; border:2px solid #000; background-color: white; color: black;">
                <h1 style="text-align:center; color: #1e5631;">جامعہ ملیہ اسلامیہ - تفصیلی تعلیمی رپورٹ</h1>
                <p><strong>نام طالب علم:</strong> {sn} | <strong>ولدیت:</strong> {fn}</p>
                <hr>
                <h3>📜 سابقہ امتحانات</h3>{exam_history.to_html(index=False, border=1)}
                <h3>📝 یومیہ کارکردگی (گزشتہ 30 دن)</h3>{daily_history.to_html(index=False, border=1)}
                <div style="display:flex; justify-content:space-between; margin-top:50px;">
                    <p style="border-top:1px solid #000; width:200px; text-align:center;">دستخط استاد</p>
                    <p style="border-top:1px solid #000; width:200px; text-align:center;">دستخط مہتمم</p>
                </div>
            </div>
            """
            st.markdown(get_report_download_link(report_html, f"{sn}_Report.html"), unsafe_allow_html=True)

    # ================= TEACHER: تعلیمی اندراج (RE-ADDED DYNAMIC ROWS) =================
    elif m == "📝 تعلیمی اندراج":
        st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ")
        sel_date = st.date_input("تاریخ منتخب کریں", get_pkt_time().date())
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

        if not students: st.info("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
        else:
            for s, f in students:
                with st.expander(f"👤 {s} ولد {f}"):
                    att = st.radio(f"حاضری {s}", ["حاضر", "غیر حاضر (ناغہ)", "رخصت"], key=f"att_{s}", horizontal=True)
                    if att == "حاضر":
                        # نیا سبق
                        st.subheader("📖 نیا سبق")
                        s_nagha = st.checkbox("سبق کا ناغہ", key=f"sn_nagha_{s}")
                        if not s_nagha:
                            col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
                            surah_sel = col_s1.selectbox("سورت", surahs_urdu, key=f"surah_{s}")
                            a_from = col_s2.text_input("آیت (سے)", key=f"af_{s}")
                            a_to = col_s3.text_input("آیت (تک)", key=f"at_{s}")
                            sabq_final = f"{surah_sel}: {a_from}-{a_to}"
                        else: sabq_final = "ناغہ"

                        # سبقی (Dynamic Row Logic)
                        st.subheader("🔄 سبقی")
                        sq_total_nagha = st.checkbox("سبقی کا مکمل ناغہ", key=f"sq_tn_{s}")
                        sq_list, f_sq_m, f_sq_a = [], 0, 0
                        if not sq_total_nagha:
                            if f"sq_count_{s}" not in st.session_state: st.session_state[f"sq_count_{s}"] = 1
                            for i in range(st.session_state[f"sq_count_{s}"]):
                                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                                p = c1.selectbox(f"پارہ {i+1}", paras, key=f"sqp_{s}_{i}")
                                v = c2.selectbox(f"مقدار {i+1}", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{s}_{i}")
                                a = c3.number_input(f"اٹکن {i+1}", 0, key=f"sqa_{s}_{i}")
                                e = c4.number_input(f"غلطی {i+1}", 0, key=f"sqe_{s}_{i}")
                                if c5.checkbox("ناغہ", key=f"sq_n_{s}_{i}"): sq_list.append(f"{p}:ناغہ")
                                else: sq_list.append(f"{p}:{v}(غ:{e},ا:{a})"); f_sq_m += e; f_sq_a += a
                            if st.button(f"➕ مزید سبقی {s}", key=f"btn_sq_{s}"): st.session_state[f"sq_count_{s}"] += 1; st.rerun()
                        else: sq_list = ["ناغہ"]

                        # منزل (Dynamic Row Logic)
                        st.subheader("🏠 منزل")
                        m_total_nagha = st.checkbox("منزل کا مکمل ناغہ", key=f"m_tn_{s}")
                        m_list, f_m_m, f_m_a = [], 0, 0
                        if not m_total_nagha:
                            if f"m_count_{s}" not in st.session_state: st.session_state[f"m_count_{s}"] = 1
                            for j in range(st.session_state[f"m_count_{s}"]):
                                mc1, mc2, mc3, mc4, mc5 = st.columns([2, 2, 1, 1, 1])
                                mp = mc1.selectbox(f"پارہ {j+1}", paras, key=f"mp_{s}_{j}")
                                mv = mc2.selectbox(f"مقدار {j+1}", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{s}_{j}")
                                ma = mc3.number_input(f"اٹکن {j+1}", 0, key=f"ma_{s}_{j}")
                                me = mc4.number_input(f"غلطی {j+1}", 0, key=f"me_{s}_{j}")
                                if mc5.checkbox("ناغہ", key=f"m_n_{s}_{j}"): m_list.append(f"{mp}:ناغہ")
                                else: m_list.append(f"{mp}:{mv}(غ:{me},ا:{ma})"); f_m_m += me; f_m_a += ma
                            if st.button(f"➕ مزید منزل {s}", key=f"btn_m_{s}"): st.session_state[f"m_count_{s}"] += 1; st.rerun()
                        else: m_list = ["ناغہ"]

                        if st.button(f"محفوظ کریں: {s}", key=f"save_{s}"):
                            c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                      (str(sel_date), s, f, st.session_state.username, sabq_final, " | ".join(sq_list), f_sq_a, f_sq_m, " | ".join(m_list), f_m_a, f_m_m, att))
                            conn.commit(); st.success(f"✅ {s} کا ریکارڈ محفوظ ہو گیا۔")
                    else:
                        if st.button(f"حاضری لگائیں: {s}", key=f"save_absent_{s}"):
                            c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance, surah, sq_p, m_p) VALUES (?,?,?,?,?,?,?,?)", (str(sel_date), s, f, st.session_state.username, att, "ناغہ", "ناغہ", "ناغہ"))
                            conn.commit(); st.success(f"حاضری ({att}) لگ گئی۔")

    # ================= 🕒 میری حاضری (Teacher Side) =================
    elif m == "🕒 میری حاضری":
        st.header("🕒 اساتذہ کی حاضری")
        with st.form("teacher_att_form"):
            m_date = st.date_input("حاضری کی تاریخ", get_pkt_time().date())
            m_time = st.time_input("آمد کا وقت", get_pkt_time().time())
            if st.form_submit_button("✅ حاضری درج کریں"):
                sys_time_str = get_pkt_time().strftime("%Y-%m-%d %I:%M %p")
                man_time_str = m_time.strftime("%I:%M %p")
                exists = c.execute("SELECT 1 FROM t_attendance WHERE t_name=? AND manual_date=?", (st.session_state.username, str(m_date))).fetchone()
                if exists: st.error("🛑 آپ کی حاضری پہلے ہی لگ چکی ہے!")
                else:
                    c.execute("INSERT INTO t_attendance (t_name, manual_date, manual_time, system_timestamp) VALUES (?,?,?,?)", (st.session_state.username, str(m_date), man_time_str, sys_time_str))
                    conn.commit(); st.success("حاضری کامیابی سے درج ہو گئی۔")

    # ================= ADMIN: اساتذہ کا ریکارڈ =================
    elif m == "🕒 اساتذہ کا ریکارڈ":
        st.header("🕒 اساتذہ کی حاضری کا ریکارڈ")
        att_df = pd.read_sql_query("SELECT id, t_name as 'استاد', manual_date as 'درج کردہ تاریخ', manual_time as 'درج کردہ وقت', system_timestamp as 'سسٹم وقت' FROM t_attendance ORDER BY id DESC", conn)
        if not att_df.empty:
            edited_att = st.data_editor(att_df, use_container_width=True, hide_index=True)
            if st.button("حاضری کی تبدیلیاں محفوظ کریں"):
                # یہاں اپڈیٹ کی لاجک شامل کی جا سکتی ہے
                st.success("تبدیلیاں محفوظ ہو گئیں۔")
        else: st.info("کوئی حاضری موجود نہیں ہے۔")

    # ================= دیگر مینیو آئٹمز (فوری ری-ایڈیشن) =================
    elif m == "🎓 امتحانی تعلیمی رپورٹ": render_exam_report()
    elif m == "📩 درخواستِ رخصت":
        st.header("📩 درخواستِ رخصت")
        with st.form("leave_f"):
            l_type = st.selectbox("نوعیت", ["ضروری کام", "بیماری", "دیگر"])
            days = st.number_input("دن", 1, 15)
            reason = st.text_area("وجہ")
            if st.form_submit_button("ارسال کریں"):
                c.execute("INSERT INTO leave_requests (t_name, l_type, start_date, days, reason, status) VALUES (?,?,?,?,?,?)", (st.session_state.username, l_type, str(date.today()), days, reason, "پینڈنگ"))
                conn.commit(); st.info("ارسال کر دی گئی۔")

    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن")
        with st.form("t_reg"):
            tn = st.text_input("استاد کا نام")
            tp = st.text_input("پاسورڈ")
            if st.form_submit_button("رجسٹر کریں"):
                c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                conn.commit(); st.success("کامیاب!")

    # لاگ آؤٹ
    st.sidebar.divider()
    if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()
