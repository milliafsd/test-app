
import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from datetime import date
import shutil
import os

# =========================
# FOLDER SETUP
# =========================

if not os.path.exists("student_photos"):
    os.makedirs("student_photos")

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("madrasa_v4.db",check_same_thread=False)
c = conn.cursor()

def init_db():

    c.execute("""
    CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
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
    phone TEXT,
    photo TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS hifz(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student TEXT,
    lesson TEXT,
    sabqi TEXT,
    manzil TEXT,
    para INTEGER,
    mistakes INTEGER,
    date TEXT
    )
    """)

    c.execute("INSERT OR IGNORE INTO teachers(name,password) VALUES('admin','1234')")

    conn.commit()

init_db()

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(page_title="جامعہ ملیہ حفظ سسٹم",layout="wide")

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

    u=st.text_input("صارف نام")
    p=st.text_input("پاسورڈ",type="password")

    if st.button("لاگ ان کریں"):

        r=c.execute("SELECT * FROM teachers WHERE name=? AND password=?",(u,p)).fetchone()

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

menu=st.sidebar.radio("مینو",[
"🏠 ڈیش بورڈ",
"👨‍🎓 طلباء / طالبات",
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

    st.title("📊 مدرسہ ڈیش بورڈ")

    total=c.execute("SELECT COUNT(*) FROM students").fetchone()[0]

    boys=c.execute("SELECT COUNT(*) FROM students WHERE gender='طالب علم'").fetchone()[0]

    girls=c.execute("SELECT COUNT(*) FROM students WHERE gender='طالبہ'").fetchone()[0]

    teachers=c.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]

    c1,c2,c3,c4=st.columns(4)

    c1.metric("کل طلباء",boys)
    c2.metric("کل طالبات",girls)
    c3.metric("کل طلباء و طالبات",total)
    c4.metric("کل اساتذہ",teachers)

# =========================
# STUDENT ENTRY
# =========================

if menu=="👨‍🎓 طلباء / طالبات":

    st.header("طالب علم داخلہ فارم")

    name=st.text_input("نام")
    father=st.text_input("ولدیت")

    gender=st.selectbox("جنس",["طالب علم","طالبہ"])

    teacher=st.text_input("استاد")

    phone=st.text_input("فون")

    photo=st.file_uploader("تصویر اپلوڈ کریں")

    photo_path=""

    if st.button("محفوظ کریں"):

        if photo:

            photo_path=f"student_photos/{name}.jpg"

            with open(photo_path,"wb") as f:
                f.write(photo.getbuffer())

        c.execute("""
        INSERT INTO students(name,father,gender,teacher,phone,photo)
        VALUES(?,?,?,?,?,?)
        """,(name,father,gender,teacher,phone,photo_path))

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

    sabqi=st.text_input("سبقی")

    manzil=st.text_input("منزل")

    para=st.number_input("پارہ نمبر",1,30)

    mistakes=st.number_input("غلطیاں",0)

    if st.button("محفوظ"):

        c.execute("""
        INSERT INTO hifz(student,lesson,sabqi,manzil,para,mistakes,date)
        VALUES(?,?,?,?,?,?,?)
        """,(s,lesson,sabqi,manzil,para,mistakes,str(date.today())))

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

        for i,row in df.iterrows():

            st.subheader(row["name"])

            if row["photo"]:
                st.image(row["photo"],width=120)

            st.write("ولدیت:",row["father"])
            st.write("استاد:",row["teacher"])
            st.write("فون:",row["phone"])

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

        shutil.copy("madrasa_v4.db","backup.db")

        st.success("Backup بن گیا")
