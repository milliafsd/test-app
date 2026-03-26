import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import os
from PIL import Image
import pytz
import base64

# --- 1. ڈیٹا بیس سیٹ اپ ---
DB_NAME = 'jamia_millia_v1test.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def init_db():
    # موجودہ ٹیبلز
    c.execute('''CREATE TABLE IF NOT EXISTS teachers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT, 
                  phone TEXT, address TEXT, id_card TEXT, photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT,
                  phone TEXT, address TEXT, id_card TEXT, photo TEXT, admission_date DATE)''')
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
            s_name TEXT, 
            f_name TEXT, 
            para_no INTEGER, 
            start_date TEXT, 
            end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, 
            grade TEXT,
            status TEXT)""")
    conn.commit()

    # نئے کالمز کا اضافہ (اگر پہلے سے نہ ہوں)
    cols = [
        ("teachers", "phone", "TEXT"), ("teachers", "address", "TEXT"), ("teachers", "id_card", "TEXT"), ("teachers", "photo", "TEXT"),
        ("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), ("students", "photo", "TEXT"), ("students", "admission_date", "DATE"),
        ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER"), ("leave_requests", "notification_seen", "INTEGER DEFAULT 0")
    ]
    for t, col, typ in cols:
        try:
            c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except:
            pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# --- 2. ہیلپر فنکشنز ---
def get_pk_time():
    """پاکستان کا موجودہ وقت"""
    tz = pytz.timezone('Asia/Karachi')
    return datetime.now(tz).strftime("%I:%M %p")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def generate_html_report(df, student_name, start_date, end_date):
    """HTML رپورٹ تیار کریں (پرنٹ اور ڈاؤن لوڈ کے لیے)"""
    # ڈیٹا فریم کو ٹیبل میں بدلیں
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>ماہانہ تعلیمی رپورٹ - {student_name}</title>
        <style>
            @font-face {{
                font-family: 'Jameel Noori Nastaleeq';
                src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq') format('woff2');
                font-weight: normal;
                font-style: normal;
            }}
            body {{
                font-family: 'Jameel Noori Nastaleeq', 'Arial', sans-serif;
                margin: 20px;
                direction: rtl;
                text-align: right;
                font-size: 14px;
            }}
            h2, h3 {{ text-align: center; color: #1e5631; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .signatures {{ display: flex; justify-content: space-between; margin-top: 50px; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; }}
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ</h2>
            <h3>ماہانہ تعلیمی رپورٹ</h3>
            <p><b>طالب علم کا نام:</b> {student_name} &nbsp;&nbsp;&nbsp; <b>تاریخ:</b> {start_date} تا {end_date}</p>
        </div>
        {html_table}
        <div class="signatures">
            <span>دستخط استاذ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align: center; margin-top: 30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

# --- 3. اسٹائلنگ (جدید اور رنگین) ---
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* گلوبل اسٹائل */
    body {
        direction: rtl;
        text-align: right;
        font-family: 'Jameel Noori Nastaleeq', 'Arial', sans-serif;
        background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
    }
    /* سائڈبار */
    .stSidebar {
        background: linear-gradient(180deg, #1e5631 0%, #143e22 100%);
        color: white;
    }
    .stSidebar .css-1d391kg {
        background: transparent;
    }
    .stSidebar .stRadio label {
        color: white;
        font-weight: bold;
    }
    .stSidebar .stButton>button {
        background: #ffc107;
        color: #1e5631;
        border-radius: 30px;
    }
    /* بٹنز */
    .stButton>button {
        background: linear-gradient(90deg, #1e5631, #2e7d32);
        color: white;
        border-radius: 25px;
        font-weight: bold;
        border: none;
        padding: 8px 20px;
        transition: 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        transform: scale(1.02);
        background: linear-gradient(90deg, #2e7d32, #1e5631);
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    /* کارڈز */
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #f1f8e9, #d4e0c9);
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 20px;
        border-bottom: 4px solid #1e5631;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .report-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    /* ٹیبز */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 30px;
        padding: 8px 20px;
        background-color: #e0e0e0;
        transition: 0.2s;
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
    /* فونٹ */
    * {
        font-family: 'Jameel Noori Nastaleeq', 'Arial', sans-serif;
    }
    /* ڈیٹا فریم */
    .dataframe {
        direction: rtl;
        text-align: right;
    }
    .stDataFrame {
        direction: rtl;
    }
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# --- 4. مرکزی ہیڈر ---
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

# --- 5. لاگ ان ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("<div class='report-card'><h3>🔐 لاگ ان پینل</h3>", unsafe_allow_html=True)
        u = st.text_input("صارف کا نام (Username)")
        p = st.text_input("پاسورڈ (Password)", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else:
                st.error("❌ غلط معلومات، براہ کرم دوبارہ کوشش کریں۔")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 6. مینو (سائیڈبار) ---
if st.session_state.user_type == "admin":
    menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
else:
    menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری"]

m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

# --- 7. مختلف سیکشنز ---
if m == "📊 یومیہ تعلیمی رپورٹ":
    st.markdown("<h2 style='text-align: center; color: #1e5631;'>📊 ماسٹر تعلیمی رپورٹ و تجزیہ</h2>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("🔍 فلٹرز")
        d1 = st.date_input("آغاز", date.today().replace(day=1))
        d2 = st.date_input("اختتام", date.today())
        t_list = ["تمام"] + [t[0] for t in c.execute("SELECT DISTINCT t_name FROM hifz_records").fetchall()]
        sel_t = st.selectbox("استاد/کلاس", t_list)
        s_list = ["تمام"] + [s[0] for s in c.execute("SELECT DISTINCT s_name FROM hifz_records").fetchall()]
        sel_s = st.selectbox("طالب علم", s_list)

    query = "SELECT * FROM hifz_records WHERE r_date BETWEEN ? AND ?"
    params = [d1, d2]
    if sel_t != "تمام":
        query += " AND t_name = ?"
        params.append(sel_t)
    if sel_s != "تمام":
        query += " AND s_name = ?"
        params.append(sel_s)
    
    df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        st.warning("منتخب کردہ فلٹرز کے مطابق کوئی ریکارڈ نہیں ملا۔")
    else:
        # خلاصہ میٹرکس
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("کل ریکارڈ", len(df))
        col2.metric("حاضر طلباء", len(df[df['attendance'] == 'حاضر']))
        col3.metric("اوسط سبقی غلطی", round(df['sq_m'].mean(), 1))
        col4.metric("اوسط منزل غلطی", round(df['m_m'].mean(), 1))

        st.subheader("📅 تاریخ کے لحاظ سے ریکارڈ")
        # تاریخ کے لحاظ سے گروپ کریں
        dates = sorted(df['r_date'].unique())
        for d in dates:
            with st.expander(f"📆 تاریخ: {d}"):
                sub_df = df[df['r_date'] == d]
                # ایڈٹ کرنے کے لیے ڈیٹا ایڈیٹر
                edited = st.data_editor(sub_df, key=f"edit_{d}", use_container_width=True, hide_index=True, num_rows="dynamic")
                if st.button(f"💾 تبدیلیاں محفوظ کریں ({d})", key=f"save_{d}"):
                    # پہلے اس تاریخ کے پرانے ریکارڈز حذف کریں
                    c.execute("DELETE FROM hifz_records WHERE r_date=?", (d,))
                    # نئے ڈیٹا ڈالیں
                    edited.to_sql('hifz_records', conn, if_exists='append', index=False)
                    st.success("تبدیلیاں محفوظ ہو گئیں!")
                    st.rerun()
        
        # ڈاؤن لوڈ اور پرنٹ
        col_dl, col_print = st.columns(2)
        csv = convert_df_to_csv(df)
        col_dl.download_button("📥 رپورٹ ڈاؤن لوڈ کریں (CSV)", csv, "daily_report.csv", "text/csv")
        if col_print.button("🖨️ پرنٹ کریں"):
            # پرنٹ کے لیے HTML بنائیں
            html = generate_html_report(df, "تمام طلباء", d1.strftime("%Y-%m-%d"), d2.strftime("%Y-%m-%d"))
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

elif m == "📜 ماہانہ رزلٹ کارڈ":
    st.header("📜 ماہانہ رزلٹ کارڈ و پرنٹ")
    students_list = [s[0] for s in c.execute("SELECT DISTINCT name FROM students").fetchall()]
    
    if not students_list:
        st.warning("کوئی طالب علم رجسٹرڈ نہیں ہے۔")
    else:
        col1, col2, col3 = st.columns([2,1,1])
        sel_s = col1.selectbox("طالب علم منتخب کریں", students_list)
        start_date = col2.date_input("تاریخ آغاز", date.today().replace(day=1))
        end_date = col3.date_input("تاریخ اختتام", date.today())

        query = """SELECT 
                    r_date as تاریخ, 
                    attendance as حاضری,
                    surah as 'سبق (آیت تا آیت)', 
                    sq_p as 'سبقی (پارہ)', sq_m as 'سبقی (غلطی)', sq_a as 'سبقی (اٹکن)', 
                    m_p as 'منزل (پارہ)', m_m as 'منزل (غلطی)', m_a as 'منزل (اٹکن)' 
                   FROM hifz_records 
                   WHERE s_name=? AND r_date BETWEEN ? AND ?
                   ORDER BY r_date ASC"""
        res_df = pd.read_sql_query(query, conn, params=(sel_s, start_date, end_date))

        if res_df.empty:
            st.warning("اس طالب علم کا ان تاریخوں میں کوئی ریکارڈ نہیں ملا۔")
        else:
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            
            html_report = generate_html_report(res_df, sel_s, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)
            st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, f"Result_{sel_s}.html", "text/html")
            st.download_button("📥 CSV ڈاؤن لوڈ کریں", convert_df_to_csv(res_df), f"Result_{sel_s}.csv", "text/csv")

elif m == "🏛️ مہتمم پینل (رخصت)":
    st.header("🏛️ مہتمم پینل (رخصت کی منظوری)")
    pending = c.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE ?", ('%پینڈنگ%',)).fetchall()
    if not pending:
        st.info("کوئی نئی درخواست نہیں ہے۔")
    else:
        for l_id, t_n, l_t, reas, s_d, dys in pending:
            with st.expander(f"📌 استاد: {t_n} | دن: {dys} | نوعیت: {l_t}"):
                st.write(f"**وجہ:** {reas}")
                col_app, col_rej = st.columns(2)
                if col_app.button("✅ منظور", key=f"app_{l_id}"):
                    c.execute("UPDATE leave_requests SET status=?, notification_seen=0 WHERE id=?", ("منظور شدہ ✅", l_id))
                    conn.commit()
                    st.success("درخواست منظور کر لی گئی۔")
                    st.rerun()
                if col_rej.button("❌ مسترد", key=f"rej_{l_id}"):
                    c.execute("UPDATE leave_requests SET status=?, notification_seen=0 WHERE id=?", ("مسترد شدہ ❌", l_id))
                    conn.commit()
                    st.success("درخواست مسترد کر دی گئی۔")
                    st.rerun()

elif m == "⚙️ انتظامی کنٹرول":
    st.header("⚙️ رجسٹریشن اور انتظامی کنٹرول")
    tab1, tab2 = st.tabs(["👨‍🏫 اساتذہ مینجمنٹ", "👨‍🎓 طلباء مینجمنٹ"])
    
    with tab1:
        st.subheader("اساتذہ کی فہرست")
        teachers_df = pd.read_sql_query("SELECT id, name, password, phone, address, id_card FROM teachers", conn)
        if not teachers_df.empty:
            # ایڈٹ اور ڈیلیٹ
            edited_teachers = st.data_editor(teachers_df, num_rows="dynamic", use_container_width=True, hide_index=True, key="teachers_edit")
            if st.button("اساتذہ کی تبدیلیاں محفوظ کریں"):
                # حذف کرنا: پہلے موجودہ ڈیٹا کو حذف کریں، پھر نیا ڈالیں (سادہ طریقہ)
                c.execute("DELETE FROM teachers")
                for _, row in edited_teachers.iterrows():
                    c.execute("INSERT INTO teachers (id, name, password, phone, address, id_card) VALUES (?,?,?,?,?,?)",
                              (row['id'], row['name'], row['password'], row['phone'], row['address'], row['id_card']))
                conn.commit()
                st.success("تبدیلیاں محفوظ ہو گئیں!")
                st.rerun()
        else:
            st.info("کوئی استاد نہیں ہے۔")
        
        with st.expander("نیا استاد رجسٹر کریں"):
            with st.form("new_teacher"):
                tn = st.text_input("نام")
                tp = st.text_input("پاسورڈ")
                tphone = st.text_input("فون")
                taddr = st.text_input("پتہ")
                tcard = st.text_input("شناختی کارڈ نمبر")
                # تصویر اپ لوڈ (اختیاری)
                tphoto = st.file_uploader("تصویر", type=["jpg", "png"])
                if st.form_submit_button("رجسٹر کریں"):
                    if tn and tp:
                        try:
                            photo_path = None
                            if tphoto:
                                os.makedirs("uploads", exist_ok=True)
                                photo_path = f"uploads/{tn}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                                with open(photo_path, "wb") as f:
                                    f.write(tphoto.getbuffer())
                            c.execute("INSERT INTO teachers (name, password, phone, address, id_card, photo) VALUES (?,?,?,?,?,?)",
                                      (tn, tp, tphone, taddr, tcard, photo_path))
                            conn.commit()
                            st.success("استاد رجسٹر ہو گیا!")
                        except sqlite3.IntegrityError:
                            st.error("نام پہلے سے موجود ہے!")
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں۔")
    
    with tab2:
        st.subheader("طلباء کی فہرست")
        students_df = pd.read_sql_query("SELECT id, name, father_name, teacher_name, phone, address, id_card, admission_date FROM students", conn)
        if not students_df.empty:
            edited_students = st.data_editor(students_df, num_rows="dynamic", use_container_width=True, hide_index=True, key="students_edit")
            if st.button("طلباء کی تبدیلیاں محفوظ کریں"):
                c.execute("DELETE FROM students")
                for _, row in edited_students.iterrows():
                    c.execute("INSERT INTO students (id, name, father_name, teacher_name, phone, address, id_card, admission_date) VALUES (?,?,?,?,?,?,?,?)",
                              (row['id'], row['name'], row['father_name'], row['teacher_name'], row['phone'], row['address'], row['id_card'], row['admission_date']))
                conn.commit()
                st.success("تبدیلیاں محفوظ ہو گئیں!")
                st.rerun()
        else:
            st.info("کوئی طالب علم نہیں ہے۔")
        
        with st.expander("نیا طالب علم داخل کریں"):
            with st.form("new_student"):
                s_name = st.text_input("نام")
                s_father = st.text_input("ولدیت")
                teacher_list = [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                if teacher_list:
                    s_teacher = st.selectbox("استاد", teacher_list)
                else:
                    st.warning("پہلے استاد رجسٹر کریں۔")
                    s_teacher = None
                s_phone = st.text_input("فون")
                s_address = st.text_input("پتہ")
                s_idcard = st.text_input("شناختی کارڈ نمبر (B-Form)")
                s_admission = st.date_input("داخلہ کی تاریخ", date.today())
                s_photo = st.file_uploader("تصویر", type=["jpg", "png"])
                if st.form_submit_button("داخل کریں"):
                    if s_name and s_father and s_teacher:
                        photo_path = None
                        if s_photo:
                            os.makedirs("uploads", exist_ok=True)
                            photo_path = f"uploads/{s_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                            with open(photo_path, "wb") as f:
                                f.write(s_photo.getbuffer())
                        c.execute("INSERT INTO students (name, father_name, teacher_name, phone, address, id_card, admission_date, photo) VALUES (?,?,?,?,?,?,?,?)",
                                  (s_name, s_father, s_teacher, s_phone, s_address, s_idcard, s_admission, photo_path))
                        conn.commit()
                        st.success("داخلہ کامیاب!")
                    else:
                        st.error("نام، ولدیت اور استاد ضروری ہیں۔")

elif m == "🕒 اساتذہ کا ریکارڈ":
    st.header("🕒 اساتذہ کی حاضری کا ریکارڈ")
    att_df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    if not att_df.empty:
        st.dataframe(att_df, use_container_width=True)
        st.download_button("📥 ڈاؤن لوڈ ریکارڈ (CSV)", convert_df_to_csv(att_df), "teachers_attendance.csv", "text/csv")
    else:
        st.info("ابھی کوئی حاضری ریکارڈ نہیں ہے۔")

elif m == "📝 تعلیمی اندراج":
    st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ")
    sel_date = st.date_input("تاریخ منتخب کریں", date.today())
    students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

    if not students:
        st.info("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
    else:
        # فارم میں تمام طلباء کا ڈیٹا جمع کریں
        with st.form(key="daily_entry_form"):
            records = []
            for s_name, f_name in students:
                st.markdown(f"### 👤 {s_name} ولد {f_name}")
                att = st.radio(f"حاضری {s_name}", ["حاضر", "غیر حاضر (ناغہ)", "رخصت"], key=f"att_{s_name}", horizontal=True)
                
                if att == "حاضر":
                    # سبق (سورت اور آیات)
                    surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{s_name}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{s_name}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{s_name}")
                    sabq_final = f"{surah}: {a_from}-{a_to}"
                    
                    # سبقی - متعدد پاروں کے لیے
                    st.write("**سبقی**")
                    sq_count = st.number_input("سبقی کے لیے پاروں کی تعداد", min_value=1, max_value=5, value=1, key=f"sq_count_{s_name}")
                    sq_parts = []
                    sq_a_total = 0
                    sq_m_total = 0
                    for i in range(sq_count):
                        st.write(f"سبقی پارہ {i+1}")
                        col1, col2, col3, col4 = st.columns([2,2,1,1])
                        p = col1.selectbox("پارہ", paras, key=f"sqp_{s_name}_{i}")
                        v = col2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{s_name}_{i}")
                        a = col3.number_input("اٹکن", 0, key=f"sqa_{s_name}_{i}")
                        e = col4.number_input("غلطی", 0, key=f"sqe_{s_name}_{i}")
                        sq_parts.append(f"{p}:{v}")
                        sq_a_total += a
                        sq_m_total += e
                    
                    # منزل - متعدد پاروں کے لیے
                    st.write("**منزل**")
                    m_count = st.number_input("منزل کے لیے پاروں کی تعداد", min_value=1, max_value=5, value=1, key=f"m_count_{s_name}")
                    m_parts = []
                    m_a_total = 0
                    m_m_total = 0
                    for j in range(m_count):
                        st.write(f"منزل پارہ {j+1}")
                        col1, col2, col3, col4 = st.columns([2,2,1,1])
                        mp = col1.selectbox("پارہ", paras, key=f"mp_{s_name}_{j}")
                        mv = col2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{s_name}_{j}")
                        ma = col3.number_input("اٹکن", 0, key=f"ma_{s_name}_{j}")
                        me = col4.number_input("غلطی", 0, key=f"me_{s_name}_{j}")
                        m_parts.append(f"{mp}:{mv}")
                        m_a_total += ma
                        m_m_total += me
                else:
                    sabq_final = "ناغہ"
                    sq_parts = ["ناغہ"]
                    sq_a_total = 0
                    sq_m_total = 0
                    m_parts = ["ناغہ"]
                    m_a_total = 0
                    m_m_total = 0
                
                records.append((sel_date, s_name, f_name, st.session_state.username, sabq_final,
                                " | ".join(sq_parts), sq_a_total, sq_m_total,
                                " | ".join(m_parts), m_a_total, m_m_total, att))
            
            if st.form_submit_button("تمام ریکارڈ محفوظ کریں"):
                # ڈپلیکیٹ چیک
                duplicate = False
                for rec in records:
                    r_date, s_name, f_name, _, _, _, _, _, _, _, _, _ = rec
                    check = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND f_name=?", (r_date, s_name, f_name)).fetchone()
                    if check:
                        st.error(f"🛑 {s_name} کا ریکارڈ پہلے سے موجود ہے! دوسرے طلباء کے ریکارڈ محفوظ نہیں ہوئے۔")
                        duplicate = True
                        break
                if not duplicate:
                    for rec in records:
                        c.execute("""INSERT INTO hifz_records 
                                    (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", rec)
                    conn.commit()
                    st.success("✅ تمام طلباء کا ریکارڈ کامیابی سے محفوظ ہو گیا۔")
                    st.rerun()

elif m == "📩 درخواستِ رخصت":
    st.header("📩 اسمارٹ رخصت و نوٹیفیکیشن")
    
    tab_apply, tab_status = st.tabs(["✍️ نئی درخواست", "📜 میری رخصتوں کی تاریخ"])
    
    with tab_apply:
        with st.form("teacher_leave_form", clear_on_submit=True):
            l_type = st.selectbox("رخصت کی نوعیت", ["ضروری کام", "بیماری", "ہنگامی رخصت", "دیگر"])
            s_date = st.date_input("تاریخ آغاز", date.today())
            days = st.number_input("کتنے دن؟", min_value=1, max_value=15, value=1)
            e_date = s_date + timedelta(days=days-1)
            st.write(f"واپسی کی تاریخ: **{e_date}**")
            reason = st.text_area("تفصیلی وجہ درج کریں")
            
            if st.form_submit_button("درخواست ارسال کریں 🚀"):
                if reason:
                    c.execute("""INSERT INTO leave_requests 
                              (t_name, l_type, start_date, days, reason, status, notification_seen) 
                              VALUES (?,?,?,?,?,?,?)""", 
                              (st.session_state.username, l_type, s_date, days, reason, "پینڈنگ (زیرِ غور)", 0))
                    conn.commit()
                    st.success("✅ درخواست مہتمم کو بھیج دی گئی ہے۔")
                else:
                    st.warning("براہ کرم وجہ ضرور لکھیں۔")
    
    with tab_status:
        st.subheader("📊 میری رخصتوں کا ریکارڈ")
        my_leaves = pd.read_sql_query("SELECT start_date as تاریخ, l_type as نوعیت, days as دن, status as حالت FROM leave_requests WHERE t_name=? ORDER BY start_date DESC", conn, params=(st.session_state.username,))
        if not my_leaves.empty:
            st.dataframe(my_leaves, use_container_width=True, hide_index=True)
        else:
            st.info("کوئی ریکارڈ نہیں ملا۔")

elif m == "🕒 میری حاضری":
    st.header("🕒 آمد و رخصت (حاضری)")
    today_date = date.today()
    record = c.execute("SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?", (st.session_state.username, today_date)).fetchone()
    
    if not record:
        st.info("آپ نے آج کی آمد (Check-in) درج نہیں کی۔")
        # تاریخ اور وقت منتخب کریں
        col1, col2 = st.columns(2)
        arr_date = col1.date_input("تاریخ", today_date)
        arr_time = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("✅ آمد درج کریں"):
            time_str = arr_time.strftime("%I:%M %p")
            c.execute("INSERT INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", (st.session_state.username, arr_date, time_str))
            conn.commit()
            st.success(f"آپ کی آمد کا وقت ({time_str}) ریکارڈ ہو گیا!")
            st.rerun()
    elif record and record[1] is None:
        st.success(f"🟢 آپ کی آمد کا وقت: **{record[0]}**")
        st.warning("آپ نے ابھی تک واپسی (Check-out) درج نہیں کی۔")
        dep_time = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("🔴 رخصت درج کریں (Check-out)"):
            time_str = dep_time.strftime("%I:%M %p")
            c.execute("UPDATE t_attendance SET departure=? WHERE t_name=? AND a_date=?", (time_str, st.session_state.username, today_date))
            conn.commit()
            st.success(f"آپ کی واپسی کا وقت ({time_str}) ریکارڈ ہو گیا!")
            st.rerun()
    else:
        st.success(f"🎉 آپ کی آج کی حاضری مکمل ہو چکی ہے!")
        st.markdown(f"**آمد کا وقت:** {record[0]}  \n**واپسی کا وقت:** {record[1]}")

elif m == "🎓 امتحانی تعلیمی رپورٹ":
    # امتحانی نظام (پہلے کی طرح)
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
                    s_date = st.date_input("آغازِ امتحان (تاریخِ درخواست)", date.today())
                    
                    if st.form_submit_button("امتحان کے لیے نامزد کریں 🚀"):
                        s_name, f_name = sel_student.split(" ولد ")
                        exists = c.execute("SELECT 1 FROM exams WHERE s_name=? AND f_name=? AND para_no=? AND status=?", 
                                           (s_name, f_name, para_to_test, "پینڈنگ")).fetchone()
                        if exists:
                            st.error("🛑 اس طالب علم کی اس پارے کے لیے درخواست پہلے سے مہتمم صاحب کے پاس موجود ہے۔")
                        else:
                            c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)",
                                      (s_name, f_name, para_to_test, str(s_date), "پینڈنگ"))
                            conn.commit()
                            st.success(f"✅ {s_name} (پارہ {para_to_test}) کی درخواست بھیج دی گئی ہے۔")
        
        elif u_type == "admin":
            tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات (مہتمم پینل)", "📜 مکمل شدہ ریکارڈ (ہسٹری)"])
            with tab1:
                st.markdown("### 🖋️ ممتحن (مہتمم صاحب) کے نمبرات")
                pending = c.execute("SELECT id, s_name, f_name, para_no, start_date FROM exams WHERE status=?", ("پینڈنگ",)).fetchall()
                if not pending:
                    st.info("فی الحال کوئی طالب علم امتحان کے لیے نامزد نہیں ہے۔")
                else:
                    for eid, sn, fn, pn, sd in pending:
                        with st.expander(f"📝 امتحان: {sn} ولد {fn} (پارہ {pn}) - درخواست تاریخ: {sd}"):
                            st.write("پانچ سوالات کے نمبر درج کریں (ہر سوال 20 نمبر کا ہے):")
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
                            if st.button("امتحان کلیئر کریں اور محفوظ کریں ✅", key=f"save_{eid}"):
                                e_date = str(date.today())
                                c.execute("""UPDATE exams SET 
                                          q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? 
                                          WHERE id=?""", (q1, q2, q3, q4, q5, total, g, s_msg, e_date, eid))
                                conn.commit()
                                st.success(f"✅ {sn} کا پارہ {pn} کلیئر کر دیا گیا ہے۔")
                                st.rerun()
            with tab2:
                st.markdown("### 📜 امتحانی ہسٹری")
                history_df = pd.read_sql_query("""SELECT s_name as نام, f_name as ولدیت, para_no as پارہ, 
                                               start_date as آغاز, end_date as اختتام, 
                                               total as نمبر, grade as درجہ, status as کیفیت 
                                               FROM exams WHERE status != 'پینڈنگ' ORDER BY id DESC""", conn)
                if not history_df.empty:
                    st.dataframe(history_df, use_container_width=True, hide_index=True)
                    st.download_button("رپورٹ ڈاؤن لوڈ کریں (CSV)", convert_df_to_csv(history_df), "exam_history.csv", "text/csv")
                else:
                    st.info("ابھی تک کوئی امتحان مکمل نہیں ہوا۔")
    
    render_exam_report()

# --- لاگ آؤٹ ---
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
    st.session_state.logged_in = False
    st.rerun()
