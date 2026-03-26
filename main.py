import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

# --- 1. ڈیٹا بیس سیٹ اپ ---
DB_NAME = 'jamia_millia_v1test.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

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
    
    # کالمز کا اضافہ (اگر موجود نہ ہوں)
    cols = [
        ("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), 
        ("teachers", "phone", "TEXT"), ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER")
    ]
    for t, col, typ in cols:
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except: pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# --- مددگار فنکشنز ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def get_certificate_html(s_name, f_name, para, total, grade, date_str):
    """خوبصورت سرٹیفکیٹ اسٹائل رزلٹ کارڈ"""
    return f"""
    <div style="border: 10px double #1e5631; padding: 30px; background-color: #fffdf5; text-align: center; direction: rtl; font-family: 'Arial';">
        <h1 style="color: #1e5631; margin-bottom: 0;">جامعہ ملیہ اسلامیہ</h1>
        <h3 style="text-decoration: underline;">سندِ کامیابی / رزلٹ کارڈ</h3>
        <p style="font-size: 18px; line-height: 1.8;">
            تصدیق کی جاتی ہے کہ طالب علم <b>{s_name}</b> ولد <b>{f_name}</b> نے <br>
            مورخہ <b>{date_str}</b> کو <b>پارہ نمبر {para}</b> کا امتحان مکمل کیا۔ <br>
            حاصل کردہ کل نمبر: <b>{total}/100</b> | درجہ: <b>{grade}</b>
        </p>
        <div style="margin-top: 40px; display: flex; justify-content: space-between;">
            <span style="border-top: 1px solid #000; width: 150px;">دستخط ممتحن</span>
            <span style="border-top: 1px solid #000; width: 150px;">مہرِ جامعہ</span>
        </div>
    </div>
    """

def render_exam_report():
    st.subheader("🎓 امتحانی تعلیمی نظام")
    u_type = st.session_state.user_type

    if u_type == "teacher":
        st.info("📢 **استاد پینل:** یہاں سے آپ طالب علم کا نام امتحان کے لیے بھیج سکتے ہیں۔")
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
        if not students:
            st.warning("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
        else:
            with st.form("exam_request_form"):
                s_list = [f"{s[0]} ولد {s[1]}" for s in students]
                sel_student = st.selectbox("طالب علم منتخب کریں", s_list)
                para_to_test = st.number_input("پارہ نمبر جس کا امتحان لینا ہے", 1, 30)
                s_date = st.date_input("آغازِ امتحان", date.today())
                if st.form_submit_button("امتحان کے لیے نامزد کریں 🚀"):
                    s_name, f_name = sel_student.split(" ولد ")
                    c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)",
                              (s_name, f_name, para_to_test, str(s_date), "پینڈنگ"))
                    conn.commit(); st.success("درخواست بھیج دی گئی۔")

    elif u_type == "admin":
        tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات", "📜 مکمل شدہ ریکارڈ"])
        with tab1:
            pending = c.execute("SELECT id, s_name, f_name, para_no, start_date FROM exams WHERE status='پینڈنگ'").fetchall()
            for eid, sn, fn, pn, sd in pending:
                with st.expander(f"📝 {sn} (پارہ {pn})"):
                    q = st.columns(5)
                    q1 = q[0].number_input("س 1", 0, 20, key=f"q1_{eid}")
                    q2 = q[1].number_input("س 2", 0, 20, key=f"q2_{eid}")
                    q3 = q[2].number_input("س 3", 0, 20, key=f"q3_{eid}")
                    q4 = q[3].number_input("س 4", 0, 20, key=f"q4_{eid}")
                    q5 = q[4].number_input("س 5", 0, 20, key=f"q5_{eid}")
                    total = q1+q2+q3+q4+q5
                    grade = "ممتاز" if total>=90 else "جید جداً" if total>=80 else "جید" if total>=70 else "مقبول" if total>=60 else "ناکام"
                    if st.button("امتحان کلیئر کریں ✅", key=f"save_{eid}"):
                        c.execute("UPDATE exams SET q1=?,q2=?,q3=?,q4=?,q5=?,total=?,grade=?,status='کامیاب',end_date=? WHERE id=?", (q1,q2,q3,q4,q5,total,grade,str(date.today()),eid))
                        conn.commit(); st.rerun()
        with tab2:
            hist = pd.read_sql_query("SELECT * FROM exams WHERE status!='پینڈنگ'", conn)
            st.dataframe(hist, use_container_width=True)

# --- 2. اسٹائلنگ ---
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    body, div, p, h1, h2, h3, label { direction: rtl; text-align: right; font-family: 'Noto Nastaliq Urdu', serif; }
    .stButton>button {background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%;}
    .main-header {text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; border-bottom: 4px solid #1e5631;}
    @media print { .stSidebar, header, .stButton, .no-print { display: none !important; } }
</style>
""", unsafe_allow_html=True)

# --- لاگ ان سسٹم ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        u = st.text_input("صارف کا نام")
        p = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("غلط معلومات!")
else:
    # مینو سلیکشن
    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری", "🔑 پاسورڈ تبدیل کریں"]
    
    m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

    # --- ایڈمن: یومیہ رپورٹ ---
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.header("📊 ماسٹر تعلیمی رپورٹ")
        df = pd.read_sql_query("SELECT * FROM hifz_records ORDER BY r_date DESC", conn)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 تبدیلیاں محفوظ کریں"):
            edited_df.to_sql('hifz_records', conn, if_exists='replace', index=False)
            st.success("ریکارڈ اپ ڈیٹ ہو گیا!")

    # --- ایڈمن: رزلٹ کارڈ و سرٹیفکیٹ ---
    elif m == "📜 ماہانہ رزلٹ کارڈ":
        st.header("📜 رزلٹ کارڈ و پرنٹنگ")
        students = [s[0] for s in c.execute("SELECT name FROM students").fetchall()]
        sel_s = st.selectbox("طالب علم منتخب کریں", students)
        
        # امتحانی ریکارڈ سے سرٹیفکیٹ بنانا
        exam_data = pd.read_sql_query(f"SELECT * FROM exams WHERE s_name='{sel_s}' AND status='کامیاب'", conn)
        if not exam_data.empty:
            st.subheader("🏁 امتحانی سرٹیفکیٹ (Certificate)")
            sel_exam = st.selectbox("امتحان منتخب کریں", exam_data['para_no'].tolist())
            row = exam_data[exam_data['para_no'] == sel_exam].iloc[0]
            cert_html = get_certificate_html(row['s_name'], row['f_name'], row['para_no'], row['total'], row['grade'], row['end_date'])
            st.markdown(cert_html, unsafe_allow_html=True)
            if st.button("🖨️ سرٹیفکیٹ پرنٹ کریں"):
                st.components.v1.html(f"<script>window.print();</script>", height=0)
        
        # ماہانہ رپورٹ
        st.divider()
        st.subheader("📅 ماہانہ حاضری و تعلیمی رپورٹ")
        d1, d2 = st.columns(2)
        date1 = d1.date_input("آغاز", date.today().replace(day=1))
        date2 = d2.date_input("اختتام", date.today())
        report_df = pd.read_sql_query(f"SELECT r_date, attendance, surah, sq_m, m_m FROM hifz_records WHERE s_name='{sel_s}' AND r_date BETWEEN '{date1}' AND '{date2}'", conn)
        st.dataframe(report_df, use_container_width=True)

    # --- ایڈمن: انتظامی کنٹرول (Password Management) ---
    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن و پاسورڈ مینجمنٹ")
        t_list = pd.read_sql_query("SELECT id, name as نام, password as پاسورڈ FROM teachers WHERE name != 'admin'", conn)
        st.write("### 👨‍🏫 اساتذہ کی فہرست")
        st.dataframe(t_list, use_container_width=True)
        
        with st.expander("🔑 کسی استاد کا پاسورڈ تبدیل کریں"):
            target_t = st.selectbox("استاد منتخب کریں", t_list['نام'].tolist())
            new_pass = st.text_input("نیا پاسورڈ درج کریں", type="password")
            if st.button("پاسورڈ اپ ڈیٹ کریں"):
                c.execute("UPDATE teachers SET password=? WHERE name=?", (new_pass, target_t))
                conn.commit(); st.success(f"{target_t} کا پاسورڈ تبدیل ہو گیا۔")

        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("reg_t"):
                tn = st.text_input("نام")
                tp = st.text_input("پاسورڈ")
                if st.form_submit_button("رجسٹر کریں"):
                    c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                    conn.commit(); st.rerun()

    # --- استاد: تعلیمی اندراج (With Dynamic Rows) ---
    elif m == "📝 تعلیمی اندراج":
        st.header("🚀 یومیہ تعلیمی اندراج")
        sel_date = st.date_input("تاریخ", date.today())
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
        
        for s, f in students:
            with st.expander(f"👤 {s} ولد {f}"):
                att = st.radio(f"حاضری", ["حاضر", "ناغہ", "رخصت"], key=f"att_{s}", horizontal=True)
                if att == "حاضر":
                    # سبق
                    surah = st.selectbox("سورت", ["الفاتحہ", "البقرہ"], key=f"s_{s}")
                    # سبقی (Dynamic Row Logic)
                    if f"sq_{s}" not in st.session_state: st.session_state[f"sq_{s}"] = 1
                    for i in range(st.session_state[f"sq_{s}"]):
                        c1, c2 = st.columns(2)
                        c1.selectbox(f"پارہ {i+1}", [f"پارہ {x}" for x in range(1,31)], key=f"p_{s}_{i}")
                        c2.number_input(f"غلطی {i+1}", 0, key=f"e_{s}_{i}")
                    if st.button(f"➕ مزید سبقی {s}", key=f"btn_{s}"): 
                        st.session_state[f"sq_{s}"] += 1; st.rerun()
                    
                    if st.button(f"محفوظ کریں {s}"):
                        c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance) VALUES (?,?,?,?,?)", (str(sel_date), s, f, st.session_state.username, att))
                        conn.commit(); st.success("محفوظ!")

    # --- استاد: پاسورڈ تبدیل کریں ---
    elif m == "🔑 پاسورڈ تبدیل کریں":
        st.header("🔑 اپنا پاسورڈ تبدیل کریں")
        with st.form("self_pass"):
            old_p = st.text_input("پرانا پاسورڈ", type="password")
            new_p = st.text_input("نیا پاسورڈ", type="password")
            if st.form_submit_button("تبدیلی محفوظ کریں"):
                check = c.execute("SELECT 1 FROM teachers WHERE name=? AND password=?", (st.session_state.username, old_p)).fetchone()
                if check:
                    c.execute("UPDATE teachers SET password=? WHERE name=?", (new_p, st.session_state.username))
                    conn.commit(); st.success("پاسورڈ بدل گیا!")
                else: st.error("پرانا پاسورڈ غلط ہے")

    # --- دیگر فنکشنز (حاضری، رخصت، امتحانات) ---
    elif m == "🎓 امتحانی تعلیمی رپورٹ": render_exam_report()
    elif m == "🕒 میری حاضری":
        st.header("🕒 اپنی حاضری لگائیں")
        if st.button("Check-in"):
            c.execute("INSERT INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", (st.session_state.username, str(date.today()), datetime.now().strftime("%I:%M %p")))
            conn.commit(); st.success("آمد درج ہوگئی!")

    # لاگ آؤٹ
    st.sidebar.divider()
    if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun()
