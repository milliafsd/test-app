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

    # کالمز کا اضافہ (نئے فیچرز کے لیے)
    cols = [
        ("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), 
        ("students", "photo", "TEXT"), ("teachers", "phone", "TEXT"), ("teachers", "address", "TEXT"), 
        ("teachers", "id_card", "TEXT"), ("teachers", "photo", "TEXT"), 
        ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER"), 
        ("leave_requests", "notification_seen", "INTEGER DEFAULT 0")
    ]
    for t, col, typ in cols:
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except: pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def generate_html_report(df, student_name, start_date, end_date):
    """HTML رپورٹ تیار کریں پرنٹ اور ڈاؤن لوڈ کے لیے"""
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>ماہانہ تعلیمی رپورٹ - {student_name}</title>
        <style>
            body {{ font-family: 'Jameel Noori Nastaleeq', 'Arial', sans-serif; margin: 20px; direction: rtl; text-align: right; }}
            h2 {{ text-align: center; color: #1e5631; }}
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

# --- 2. اسٹائلنگ (بہتر) ---
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    body {direction: rtl; text-align: right;}
    .stButton>button {background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: none; padding: 10px; transition: 0.3s;}
    .stButton>button:hover {background: #143e22;}
    .main-header {text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-bottom: 4px solid #1e5631;}
    .css-1d391kg {background-color: #f5f5f5;}
    .stSidebar .css-1d391kg {background-color: #e8f0e8;}
    .reportview-container .main .block-container {padding-top: 1rem;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {border-radius: 4px; padding: 8px 16px; background-color: #f0f2f6;}
    .stTabs [aria-selected="true"] {background-color: #1e5631; color: white;}
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# --- مرکزی ہیڈر ---
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

# --- لاگ ان ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.subheader("🔐 لاگ ان پینل")
        u = st.text_input("صارف کا نام (Username)")
        p = st.text_input("پاسورڈ (Password)", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("❌ غلط معلومات، براہ کرم دوبارہ کوشش کریں۔")
    st.stop()

# --- مینو (سائیڈبار) ---
if st.session_state.user_type == "admin":
    menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
else:
    menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری"]

m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

# ================= ADMIN SECTION =================
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

    # محفوظ کوئری
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

        st.subheader("🛠️ ڈیٹا کنٹرول (تبدیلی اور حذف)")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)

        if st.button("💾 تمام تبدیلیاں مستقل محفوظ کریں"):
            try:
                # پرانے ریکارڈز کو حذف کریں
                delete_query = "DELETE FROM hifz_records WHERE r_date BETWEEN ? AND ?"
                delete_params = [d1, d2]
                if sel_t != "تمام":
                    delete_query += " AND t_name = ?"
                    delete_params.append(sel_t)
                if sel_s != "تمام":
                    delete_query += " AND s_name = ?"
                    delete_params.append(sel_s)
                c.execute(delete_query, delete_params)
                
                # نئے ڈیٹا کو ڈالیں
                edited_df.to_sql('hifz_records', conn, if_exists='append', index=False)
                st.success("✅ ڈیٹا کامیابی سے اپ ڈیٹ ہو گیا!")
                st.rerun()
            except Exception as e:
                st.error(f"ایرر: {e}")

# ================= ماہانہ رزلٹ کارڈ اور پرنٹ =================
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
            
            # HTML رپورٹ تیار کریں
            html_report = generate_html_report(res_df, sel_s, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            
            # پرنٹ بٹن (نیا ٹیب میں)
            if st.button("🖨️ پرنٹ کریں"):
                # جاوا اسکرپٹ کے ذریعے پرنٹ کھولیں
                js = f"""
                <script>
                    var printWindow = window.open('', '_blank');
                    printWindow.document.write(`{html_report}`);
                    printWindow.document.close();
                    printWindow.print();
                </script>
                """
                st.components.v1.html(js, height=0)
            
            # HTML ڈاؤن لوڈ بٹن
            st.download_button(
                label="📥 HTML رپورٹ ڈاؤن لوڈ کریں",
                data=html_report,
                file_name=f"Result_{sel_s}.html",
                mime="text/html"
            )
            
            # CSV ڈاؤن لوڈ
            st.download_button(
                label="📥 CSV ڈاؤن لوڈ کریں",
                data=convert_df_to_csv(res_df),
                file_name=f"Result_{sel_s}.csv",
                mime="text/csv"
            )

# ================= باقی تمام سیکشنز (منتظم کے لیے) =================
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
        with st.form("t_reg_form"):
            tn = st.text_input("استاد کا نام")
            tp = st.text_input("پاسورڈ")
            if st.form_submit_button("رجسٹر کریں"):
                if tn and tp:
                    try:
                        c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                        conn.commit()
                        st.success("کامیاب!")
                    except sqlite3.IntegrityError:
                        st.error("نام پہلے سے موجود ہے!")
                else:
                    st.error("براہ کرم تمام فیلڈز بھریں۔")
    
    with tab2:
        with st.form("s_reg_form"):
            s_name = st.text_input("طالب علم نام")
            s_father = st.text_input("ولدیت")
            t_list = [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
            if t_list:
                s_teacher = st.selectbox("استاد", t_list)
                if st.form_submit_button("داخل کریں"):
                    if s_name and s_father:
                        c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (s_name, s_father, s_teacher))
                        conn.commit()
                        st.success("داخلہ کامیاب!")
                    else:
                        st.error("تمام فیلڈز بھریں۔")
            else:
                st.warning("پہلے کم از کم ایک استاد رجسٹر کریں۔")

elif m == "🕒 اساتذہ کا ریکارڈ":
    st.header("🕒 اساتذہ کی حاضری کا ریکارڈ")
    att_df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    if not att_df.empty:
        st.dataframe(att_df, use_container_width=True)
        st.download_button("📥 ڈاؤن لوڈ ریکارڈ (CSV)", convert_df_to_csv(att_df), "teachers_attendance.csv", "text/csv")
    else:
        st.info("ابھی کوئی حاضری ریکارڈ نہیں ہے۔")

# ================= TEACHER SECTION =================
elif m == "📝 تعلیمی اندراج":
    st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ")
    sel_date = st.date_input("تاریخ منتخب کریں", date.today())
    students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

    if not students:
        st.info("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
    else:
        # ایک فارم میں تمام طلباء کا ڈیٹا جمع کریں
        with st.form(key="daily_entry_form"):
            st.write(f"**تاریخ:** {sel_date.strftime('%Y-%m-%d')}")
            records = []
            for s_name, f_name in students:
                st.markdown(f"### 👤 {s_name} ولد {f_name}")
                att = st.radio(f"حاضری {s_name}", ["حاضر", "غیر حاضر (ناغہ)", "رخصت"], key=f"att_{s_name}", horizontal=True)
                
                if att == "حاضر":
                    # سبق
                    surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{s_name}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{s_name}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{s_name}")
                    sabq_final = f"{surah}: {a_from}-{a_to}"
                    
                    # سبقی
                    sq_count = st.number_input("سبقی کے لیے پاروں کی تعداد", min_value=1, max_value=5, value=1, key=f"sq_count_{s_name}")
                    sq_parts = []
                    sq_a_total = 0
                    sq_m_total = 0
                    for i in range(sq_count):
                        st.write(f"**سبقی {i+1}**")
                        col1, col2, col3, col4 = st.columns([2,2,1,1])
                        p = col1.selectbox("پارہ", paras, key=f"sqp_{s_name}_{i}")
                        v = col2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{s_name}_{i}")
                        a = col3.number_input("اٹکن", 0, key=f"sqa_{s_name}_{i}")
                        e = col4.number_input("غلطی", 0, key=f"sqe_{s_name}_{i}")
                        sq_parts.append(f"{p}:{v}")
                        sq_a_total += a
                        sq_m_total += e
                    
                    # منزل
                    m_count = st.number_input("منزل کے لیے پاروں کی تعداد", min_value=1, max_value=5, value=1, key=f"m_count_{s_name}")
                    m_parts = []
                    m_a_total = 0
                    m_m_total = 0
                    for j in range(m_count):
                        st.write(f"**منزل {j+1}**")
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
                # پہلے چیک کریں کہ ڈپلیکیٹ تو نہیں
                for rec in records:
                    r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, att = rec
                    check = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND f_name=?", (r_date, s_name, f_name)).fetchone()
                    if check:
                        st.error(f"🛑 {s_name} کا ریکارڈ پہلے سے موجود ہے! دوسرے طلباء کے ریکارڈ محفوظ نہیں ہوئے۔")
                        break
                else:
                    # سبھی نئے ہیں، انسرٹ کریں
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
        my_leaves = pd.read_sql_query(f"SELECT start_date as تاریخ, l_type as نوعیت, days as دن, status as حالت FROM leave_requests WHERE t_name=? ORDER BY start_date DESC", conn, params=(st.session_state.username,))
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
        if st.button("✅ آمد درج کریں"):
            time_now = datetime.now().strftime("%I:%M %p")
            c.execute("INSERT INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", (st.session_state.username, today_date, time_now))
            conn.commit()
            st.success(f"آپ کی آمد کا وقت ({time_now}) ریکارڈ ہو گیا!")
            st.rerun()
    elif record and record[1] is None:
        st.success(f"🟢 آپ کی آمد کا وقت: **{record[0]}**")
        st.warning("آپ نے ابھی تک واپسی (Check-out) درج نہیں کی۔")
        if st.button("🔴 رخصت درج کریں (Check-out)"):
            time_now = datetime.now().strftime("%I:%M %p")
            c.execute("UPDATE t_attendance SET departure=? WHERE t_name=? AND a_date=?", (time_now, st.session_state.username, today_date))
            conn.commit()
            st.success(f"آپ کی واپسی کا وقت ({time_now}) ریکارڈ ہو گیا!")
            st.rerun()
    else:
        st.success(f"🎉 آپ کی آج کی حاضری مکمل ہو چکی ہے!")
        st.markdown(f"**آمد کا وقت:** {record[0]}  \n**واپسی کا وقت:** {record[1]}")

# ================= امتحانی نظام =================
elif m == "🎓 امتحانی تعلیمی رپورٹ":
    # امتحان کا فنکشن پہلے سے موجود ہے، اسے بھی جدید بنایا جا سکتا ہے
    # لیکن brevity کے لیے اسے یہاں شامل نہیں کیا جا رہا، مگر آپ اسے اوپر دیے گئے اصل فنکشن کی طرح رکھ سکتے ہیں
    # اس مثال میں ہم render_exam_report کو بہتر کر کے یہاں استعمال کر سکتے ہیں
    # (اصل کوڈ میں render_exam_report تھا، اسے یہاں ڈال دیں)
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
