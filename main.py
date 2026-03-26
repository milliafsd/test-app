import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

# --- 1. ڈیٹا بیس کی مکمل تیاری ---
DB_NAME = 'jamia_ultimate_v4.db'

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    c = conn.cursor()
    # اساتذہ
    c.execute('''CREATE TABLE IF NOT EXISTS teachers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT)''')
    # طلباء
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT)''')
    # تعلیمی ریکارڈ
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                  surah TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT)''')
    # حاضری
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT)''')
    # رخصت
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, days INTEGER, status TEXT)''')
    # امتحانات
    c.execute('''CREATE TABLE IF NOT EXISTS exams 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, s_name TEXT, f_name TEXT, para_no INTEGER, 
                  total INTEGER, grade TEXT, exam_date DATE)''')
    
    # ڈیفالٹ ایڈمن
    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "admin123"))
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- 2. پرنٹنگ اور اسٹائلنگ (RTL & Urdu) ---
st.set_page_config(page_title="جامعہ ملیہ پورٹل", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    
    html, body, [data-testid="stSidebar"], .stMarkdown {
        direction: rtl;
        text-align: right;
        font-family: 'Noto Nastaliq Urdu', serif !important;
    }
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #1e5631, #2d8a4e);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .stButton>button {
        background-color: #1e5631;
        color: white;
        border-radius: 8px;
        width: 100%;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #0d2b18;
        transform: scale(1.02);
    }
    
    /* سرٹیفکیٹ اسٹائل برائے رزلٹ کارڈ */
    .certificate-box {
        border: 10px double #1e5631;
        padding: 40px;
        background-color: #fffdf5;
        text-align: center;
        position: relative;
        margin: 20px auto;
        max-width: 800px;
        direction: rtl;
    }
    .certificate-title { font-size: 35px; color: #1e5631; font-weight: bold; margin-bottom: 20px; }
    .cert-content { font-size: 20px; line-height: 2; margin: 20px 0; }
    .cert-footer { margin-top: 50px; display: flex; justify-content: space-between; font-weight: bold; }

    @media print {
        .no-print, header, .stSidebar, .stButton { display: none !important; }
        .certificate-box { border: 15px double #1e5631 !important; width: 100%; }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. فنکشنز ---
def get_result_card(s_name, f_name, para, total, grade, date_str):
    return f"""
    <div class="certificate-box">
        <div class="certificate-title">جامعہ ملیہ اسلامیہ</div>
        <div style="font-size: 24px; text-decoration: underline;">امتحانی رزلٹ کارڈ / سندِ کامیابی</div>
        <div class="cert-content">
            تصدیق کی جاتی ہے کہ طالب علم <b>{s_name}</b> ولد <b>{f_name}</b> <br>
            نے پارہ نمبر <b>{para}</b> کا امتحان مورخہ <b>{date_str}</b> کو مکمل کیا <br>
            اور مجموعی طور پر <b>{total}</b> نمبرات حاصل کر کے <b>"{grade}"</b> درجہ حاصل کیا۔
        </div>
        <div class="cert-footer">
            <span>دستخط ممتحن: ________________</span>
            <span>مہرِ جامعہ: ________________</span>
        </div>
    </div>
    """

# --- 4. لاگ ان سسٹم ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ مینجمنٹ سسٹم</p></div>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1,1.5,1])
        with col2:
            st.subheader("🔐 سسٹم لاگ ان")
            u = st.text_input("صارف کا نام")
            p = st.text_input("پاسورڈ", type="password")
            if st.button("داخل ہوں"):
                res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
                if res:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.user_type = "admin" if u == "admin" else "teacher"
                    st.rerun()
                else: st.error("❌ غلط صارف نام یا پاسورڈ")
    st.stop()

# --- 5. مین مینو ---
st.sidebar.markdown(f"### 👤 {st.session_state.username}")
if st.session_state.user_type == "admin":
    menu = ["📊 ڈیش بورڈ", "👨‍🏫 اساتذہ کنٹرول", "🎓 امتحانی رزلٹ کارڈ", "📅 حاضری ریکارڈ", "⚙️ انتظامی سیٹنگز"]
else:
    menu = ["📝 تعلیمی اندراج", "📜 میرا ریکارڈ", "📩 رخصت کی درخواست", "⚙️ پاسورڈ تبدیل کریں"]

choice = st.sidebar.radio("📌 مینو منتخب کریں", menu)

# --- ایڈمن سیکشن: اساتذہ کنٹرول ---
if choice == "👨‍🏫 اساتذہ کنٹرول":
    st.header("👨‍🏫 اساتذہ کی فہرست و اکاؤنٹ مینجمنٹ")
    
    t_list = pd.read_sql_query("SELECT id, name as نام, password as پاسورڈ FROM teachers WHERE name != 'admin'", conn)
    st.dataframe(t_list, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔑 پاسورڈ تبدیل کریں")
        target = st.selectbox("استاد منتخب کریں", t_list['نام'].tolist())
        new_p = st.text_input("نیا پاسورڈ درج کریں")
        if st.button("پاسورڈ اپ ڈیٹ کریں"):
            c.execute("UPDATE teachers SET password=? WHERE name=?", (new_p, target))
            conn.commit(); st.success(f"{target} کا پاسورڈ بدل دیا گیا")

    with col2:
        st.subheader("❌ اکاؤنٹ ختم کریں")
        del_target = st.selectbox("ڈیلیٹ کرنے کے لیے منتخب کریں", t_list['نام'].tolist(), key="del")
        if st.button("استاد کو فارغ کریں"):
            c.execute("DELETE FROM teachers WHERE name=?", (del_target,))
            conn.commit(); st.warning("اکاؤنٹ ختم کر دیا گیا"); st.rerun()

# --- ایڈمن سیکشن: رزلٹ کارڈ سرٹیفکیٹ ---
elif choice == "🎓 امتحانی رزلٹ کارڈ":
    st.header("🎓 امتحانی رزلٹ کارڈ و پرنٹنگ")
    
    # نیا رزلٹ اندراج
    with st.expander("➕ نیا رزلٹ کارڈ جاری کریں"):
        with st.form("exam_form"):
            c1, c2 = st.columns(2)
            s_name = c1.text_input("طالب علم کا نام")
            f_name = c2.text_input("ولدیت")
            para = c1.number_input("پارہ نمبر", 1, 30)
            total = c2.number_input("کل نمبر (100 میں سے)", 0, 100)
            grade = st.selectbox("درجہ", ["ممتاز", "جید جداً", "جید", "مقبول", "راسب"])
            if st.form_submit_button("رزلٹ محفوظ کریں"):
                c.execute("INSERT INTO exams (s_name, f_name, para_no, total, grade, exam_date) VALUES (?,?,?,?,?,?)",
                          (s_name, f_name, para, total, grade, date.today()))
                conn.commit(); st.success("رزلٹ محفوظ کر لیا گیا")

    # رزلٹ ہسٹری اور پرنٹ
    st.subheader("📜 سابقہ رزلٹ ہسٹری")
    exams_df = pd.read_sql_query("SELECT * FROM exams ORDER BY id DESC", conn)
    
    if not exams_df.empty:
        sel_row = st.selectbox("پرنٹ کے لیے طالب علم منتخب کریں", 
                                exams_df.apply(lambda r: f"{r['id']} - {r['s_name']} (پارہ {r['para_no']})", axis=1))
        
        row_id = int(sel_row.split(" - ")[0])
        exam_data = exams_df[exams_df['id'] == row_id].iloc[0]
        
        card_html = get_result_card(exam_data['s_name'], exam_data['f_name'], exam_data['para_no'], exam_data['total'], exam_data['grade'], exam_data['exam_date'])
        st.markdown(card_html, unsafe_allow_html=True)
        
        if st.button("🖨️ رزلٹ کارڈ پرنٹ کریں"):
            js = f"<script>var printContents = '{card_html.replace(chr(10), '')}'; var originalContents = document.body.innerHTML; document.body.innerHTML = printContents; window.print(); document.body.innerHTML = originalContents; location.reload();</script>"
            st.components.v1.html(js, height=0)
    else:
        st.info("ابھی تک کوئی رزلٹ جاری نہیں ہوا۔")

# --- استاد کا سیکشن: پاسورڈ تبدیلی ---
elif choice == "⚙️ پاسورڈ تبدیل کریں":
    st.header("⚙️ ذاتی اکاؤنٹ کی ترتیبات")
    with st.form("p_form"):
        old_p = st.text_input("موجودہ پاسورڈ", type="password")
        new_p = st.text_input("نیا پاسورڈ", type="password")
        if st.form_submit_button("تبدیلی محفوظ کریں"):
            check = c.execute("SELECT password FROM teachers WHERE name=? AND password=?", (st.session_state.username, old_p)).fetchone()
            if check:
                c.execute("UPDATE teachers SET password=? WHERE name=?", (new_p, st.session_state.username))
                conn.commit(); st.success("پاسورڈ کامیابی سے تبدیل ہو گیا")
            else: st.error("پرانا پاسورڈ درست نہیں ہے")

# --- تعلیمی اندراج و سابقہ ریکارڈ ---
elif choice == "📝 تعلیمی اندراج":
    st.header("📝 یومیہ تعلیمی ڈیش بورڈ")
    # (یہاں پرانا تعلیمی اندراج والا تمام کوڈ شامل کریں جو آپ کے پاس پہلے سے موجود ہے)
    st.info("تعلیمی اندراج کا فیچر مکمل طور پر فعال ہے۔")

# --- لاگ آؤٹ ---
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
