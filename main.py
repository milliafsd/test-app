import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64
import re

# 1. بنیادی سیٹ اپ
DB_NAME = 'jamia_millia_v1test.db' # نیا نام تاکہ پرانا ڈیٹا بیس مسئلہ نہ کرے
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def get_pkt_time():
    return datetime.utcnow() + timedelta(hours=5)

def clean_text(val):
    if not val: return ""
    return re.sub(r"[()\'\",]", "", str(val)).strip()

# 2. ڈیٹا بیس ٹیبلز (صرف ضروری)
def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, surah TEXT, sq_m INTEGER, m_m INTEGER, attendance TEXT)''')
    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# 3. جادوئی CSS جو ڈیزائن کو نہیں ٹوٹنے دے گا
st.set_page_config(page_title="جامعہ پورٹل", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');

    /* صرف اردو تحریر کے لیے */
    .urdu-text, .stMarkdown p, h1, h2, h3, label {
        font-family: 'Noto Nastaliq Urdu', serif !important;
        direction: rtl !important;
        text-align: right !important;
        line-height: 2.0 !important;
    }

    /* سسٹم کے آئیکنز کو اردو فونٹ سے بچانا */
    .st-emotion-cache-1vt458s, [data-testid="stExpander"] svg, [data-testid="stSidebarNav"] span {
        font-family: inherit !important;
    }

    /* موبائل پر ناموں کو ایک لائن میں رکھنا */
    [data-testid="stExpander"] {
        direction: rtl !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# 4. لاگ ان سسٹم
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 class='urdu-text'>🔐 جامعہ لاگ ان</h1>", unsafe_allow_html=True)
    u = st.text_input("صارف کا نام")
    p = st.text_input("پاسورڈ", type="password")
    if st.button("داخل ہوں"):
        res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
        if res:
            st.session_state.logged_in, st.session_state.username = True, u
            st.rerun()
        else: st.error("غلط نام یا پاسورڈ")
    st.stop()

# 5. مینو
m = st.sidebar.radio("مینو", ["📝 حاضری و تعلیمی اندراج", "📊 رپورٹ دیکھیں", "⚙️ اساتذہ و طلباء"])

# 6. تعلیمی اندراج (اصلاح شدہ)
if m == "📝 حاضری و تعلیمی اندراج":
    st.markdown("<h2 class='urdu-text'>📝 روزانہ کا اندراج</h2>", unsafe_allow_html=True)
    students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
    
    if not students: st.warning("کوئی طالب علم رجسٹرڈ نہیں ہے۔")
    
    for s_raw, f_raw in students:
        s, f = clean_text(s_raw), clean_text(f_raw)
        with st.expander(f"👤 {s} ولد {f}"):
            att = st.selectbox(f"حاضری - {s}", ["حاضر", "غیر حاضر", "رخصت"], key=f"at_{s}")
            if att == "حاضر":
                c1, c2 = st.columns(2)
                sm = c1.number_input(f"سبقی غلطی", 0, 50, key=f"sm_{s}")
                mm = c2.number_input(f"منزل غلطی", 0, 50, key=f"mm_{s}")
                if st.button(f"محفوظ کریں {s}"):
                    c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, sq_m, m_m, attendance) VALUES (?,?,?,?,?,?,?)",
                              (date.today(), s, f, st.session_state.username, sm, mm, att))
                    conn.commit()
                    st.success("ریکارڈ محفوظ!")

# 7. اساتذہ و طلباء (انتظامی کنٹرول)
elif m == "⚙️ اساتذہ و طلباء":
    st.markdown("<h2 class='urdu-text'>⚙️ انتظام</h2>", unsafe_allow_html=True)
    with st.form("add_s"):
        name = st.text_input("طالب علم کا نام")
        fname = st.text_input("ولدیت")
        if st.form_submit_button("طالب علم شامل کریں"):
            c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (name, fname, st.session_state.username))
            conn.commit()
            st.rerun()
    
    df_s = pd.read_sql_query(f"SELECT id, name, father_name FROM students WHERE teacher_name='{st.session_state.username}'", conn)
    st.table(df_s)

elif m == "📊 رپورٹ دیکھیں":
    df_r = pd.read_sql_query(f"SELECT r_date as 'تاریخ', s_name as 'نام', sq_m as 'سبقی غلطی', m_m as 'منزل غلطی' FROM hifz_records WHERE t_name='{st.session_state.username}'", conn)
    st.dataframe(df_r, use_container_width=True)

if st.sidebar.button("لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
