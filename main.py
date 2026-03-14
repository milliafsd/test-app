import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from datetime import date
import shutil

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("madrasa.db",check_same_thread=False)
c = conn.cursor()

def init_db():

    c.execute("""
    CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    father TEXT,
    gender TEXT,
    teacher TEXT,
    phone TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS hifz(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    s_name TEXT,
    lesson TEXT,
    mistake INTEGER,
    date TEXT
    )
    """)

    c.execute("INSERT OR IGNORE INTO teachers(name,password) VALUES('admin','1234')")

    conn.commit()

init_db()

# =========================
# STYLE
# =========================

st.set_page_config(page_title="جامعہ ملیہ سسٹم",layout="wide")

st.markdown("""
<style>

.stApp{
background:#e8f5e9;
direction:rtl;
text-align:right;
}

h1,h2,h3{
color:#1e5631;
}

.stButton button{
background:#1e5631;
color:white;
border-radius:8px;
}

</style>
""",unsafe_allow_html=True)

# =========================
# LOGIN
# =========================

if "login" not in st.session_state:
    st.session_state.login=False

if not st.session_state.login:

    st.title("🕌 جامعہ ملیہ اسلامیہ")

    u = st.text_input("صارف نام")
    p = st.text_input("پاسورڈ",type="password")

    if st.button("لاگ ان"):

        r = c.execute("SELECT * FROM teachers WHERE name=? AND password=?",(u,p)).fetchone()

        if r:
            st.session_state.login=True
            st.session_state.user=u
            st.rerun()

        else:
            st.error("غلط معلومات")

    st.stop()

# =========================
# MENU
# =========================

menu = st.sidebar.radio("مینو",[
"🏠 ڈیش بورڈ",
"👨‍🎓 طلباء/طالبات",
"📝 سبق اندراج",
"📊 رپورٹ",
"🔎 تلاش",
"🪪 QR کارڈ",
"💾 بیک اپ"
])

# =========================
# DASHBOARD
# =========================

if menu=="🏠 ڈیش بورڈ":

    st.title("📊 ڈیش بورڈ")

    s_total=c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    t_total=c.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]

    today=date.today()

    today_lesson=c.execute("SELECT COUNT(*) FROM hifz WHERE date=?",(str(today),)).fetchone()[0]

    c1,c2,c3=st.columns(3)

    c1.metric("کل طلباء و طالبات",s_total)
    c2.metric("کل اساتذہ",t_total)
    c3.metric("آج کے اسباق",today_lesson)

# =========================
# STUDENT ADD
# =========================

if menu=="👨‍🎓 طلباء/طالبات":

    st.header("طالب علم داخلہ")

    name=st.text_input("نام")
    father=st.text_input("ولدیت")

    gender=st.selectbox("جنس",["طالب علم","طالبہ"])

    teacher=st.text_input("استاد")

    phone=st.text_input("فون")

    if st.button("محفوظ کریں"):

        c.execute("""
        INSERT INTO students(name,father,gender,teacher,phone)
        VALUES(?,?,?,?,?)
        """,(name,father,gender,teacher,phone))

        conn.commit()

        st.success("طالب علم شامل ہوگیا")

    st.divider()

    df=pd.read_sql_query("SELECT * FROM students",conn)

    st.dataframe(df,use_container_width=True)

# =========================
# LESSON ENTRY
# =========================

if menu=="📝 سبق اندراج":

    st.header("سبق اندراج")

    students=[i[0] for i in c.execute("SELECT name FROM students").fetchall()]

    s=st.selectbox("طالب علم",students)

    lesson=st.text_input("سبق")

    mistake=st.number_input("غلطیاں",0)

    if st.button("محفوظ"):

        c.execute("""
        INSERT INTO hifz(s_name,lesson,mistake,date)
        VALUES(?,?,?,?)
        """,(s,lesson,mistake,str(date.today())))

        conn.commit()

        st.success("سبق محفوظ ہوگیا")

# =========================
# REPORT
# =========================

if menu=="📊 رپورٹ":

    st.header("تعلیمی رپورٹ")

    df=pd.read_sql_query("SELECT * FROM hifz",conn)

    st.dataframe(df,use_container_width=True)

# =========================
# SEARCH
# =========================

if menu=="🔎 تلاش":

    st.header("طالب علم تلاش کریں")

    s=st.text_input("نام لکھیں")

    if s:

        df=pd.read_sql_query(f"""
        SELECT * FROM students
        WHERE name LIKE '%{s}%'
        """,conn)

        st.dataframe(df)

# =========================
# QR CARD
# =========================

if menu=="🪪 QR کارڈ":

    st.header("QR کارڈ")

    students=[i[0] for i in c.execute("SELECT name FROM students").fetchall()]

    s=st.selectbox("طالب علم",students)

    if st.button("QR بنائیں"):

        img=qrcode.make(s)

        img.save("qr.png")

        st.image("qr.png")

# =========================
# BACKUP
# =========================

if menu=="💾 بیک اپ":

    st.header("ڈیٹا بیس بیک اپ")

    if st.button("Backup بنائیں"):

        shutil.copy("madrasa.db","backup.db")

        st.success("Backup بن گیا")
