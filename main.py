import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

# ================= 1. ڈیٹا بیس سیٹ اپ (ڈیٹا کے تحفظ کے ساتھ) =================
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

    # کالمز کا اضافہ (اگر پہلے سے نہ ہوں)
    cols = [
        ("students", "phone", "TEXT"), ("teachers", "phone", "TEXT"), 
        ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER"), 
        ("t_attendance", "manual_date", "DATE"), ("t_attendance", "manual_time", "TEXT"),
        ("t_attendance", "system_timestamp", "TEXT")
    ]
    for t, col, typ in cols:
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except: pass
    
    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# ================= فنکشنز (پرنٹ و رپورٹ) =================
def get_report_download_link(html_content, filename="report.html"):
    # اردو سپورٹ کے لیے UTF-8-SIG کا استعمال
    b64 = base64.b64encode(html_content.encode('utf-8-sig')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background-color:#1e5631; color:white; font-weight:bold; padding:12px 20px; border:none; border-radius:8px; cursor:pointer; width:100%; font-family:tahoma;">🖨️ یہ رپورٹ پرنٹ / ڈاؤنلوڈ کریں</button></a>'

# ================= 2. اسٹائلنگ (RTL) =================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    * { direction: rtl; text-align: right; font-family: 'Noto Nastaliq Urdu', serif; }
    .stButton>button { background: #1e5631; color: white; border-radius: 8px; width: 100%; }
    .main-header { text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; border-bottom: 4px solid #1e5631; margin-bottom: 20px; }
    .report-box { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background: #fff; color: #000; }
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

# ================= 3. لاگ ان سسٹم =================
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
            else: st.error("❌ غلط معلومات!")
else:
    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "🖨️ ٹریکنگ و پرنٹ رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری"]
    
    m = st.sidebar.radio("📌 مینو", menu)

    # ---------------- 📊 یومیہ تعلیمی رپورٹ (ایرر فکسڈ) ----------------
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.header("📊 یومیہ تعلیمی رپورٹ")
        col_f1, col_f2 = st.columns(2)
        d_search = col_f1.date_input("تاریخ منتخب کریں", get_pkt_time().date())
        
        # ناموں کی صفائی (weird text fix)
        raw_teachers = c.execute("SELECT DISTINCT name FROM teachers WHERE name != 'admin'").fetchall()
        t_list = ["تمام اساتذہ"] + [str(t[0]) for t in raw_teachers]
        sel_t = col_f2.selectbox("استاد منتخب کریں", t_list)

        query = "SELECT r_date, s_name, f_name, t_name, attendance, surah, sq_p, sq_m, m_p, m_m FROM hifz_records WHERE r_date = ?"
        params = [str(d_search)]
        if sel_t != "تمام اساتذہ":
            query += " AND t_name = ?"
            params.append(sel_t)
        
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty:
            df.columns = ["تاریخ", "طالب علم", "ولدیت", "استاد", "حاضری", "سبق", "سبقی تفصیل", "سبقی غلطی", "منزل تفصیل", "منزل غلطی"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            # پرنٹ آپشن
            h_print = f"<div dir='rtl'><h2>یومیہ تعلیمی رپورٹ - {d_search}</h2>{df.to_html(index=False, border=1)}</div>"
            st.markdown(get_report_download_link(h_print, f"Daily_{d_search}.html"), unsafe_allow_html=True)
        else: st.warning("اس تاریخ کا کوئی ریکارڈ موجود نہیں ہے۔")

    # ---------------- 🖨️ ٹریکنگ و پرنٹ رپورٹ ----------------
    elif m == "🖨️ ٹریکنگ و پرنٹ رپورٹ":
        st.header("🖨️ طالب علم کی تفصیلی ٹریکنگ")
        raw_students = c.execute("SELECT name, father_name FROM students").fetchall()
        if raw_students:
            s_list = [f"{s[0]} ولد {s[1]}" for s in raw_students]
            sel_s = st.selectbox("طالب علم منتخب کریں", s_list)
            sn, fn = sel_s.split(" ولد ")
            
            # ڈیٹا حاصل کریں
            daily = pd.read_sql_query(f"SELECT r_date, attendance, surah, sq_p, sq_m, m_p, m_m FROM hifz_records WHERE s_name='{sn}' AND f_name='{fn}' ORDER BY r_date DESC LIMIT 30", conn)
            st.subheader("حالیہ 30 دن کی کارکردگی")
            st.dataframe(daily, use_container_width=True)
            
            track_html = f"<div dir='rtl'><h1>رپورٹ: {sel_s}</h1>{daily.to_html(border=1)}</div>"
            st.markdown(get_report_download_link(track_html, f"Tracking_{sn}.html"), unsafe_allow_html=True)

    # ---------------- 🕒 اساتذہ کا ریکارڈ (نام اور تاریخ کے ساتھ الگ الگ) ----------------
    elif m == "🕒 اساتذہ کا ریکارڈ":
        st.header("🕒 اساتذہ کی حاضری کا ریکارڈ")
        col_a1, col_a2 = st.columns(2)
        
        # اساتذہ کی لسٹ صاف ستھری
        raw_t = c.execute("SELECT name FROM teachers WHERE name != 'admin'").fetchall()
        t_list_att = ["تمام"] + [str(t[0]) for t in raw_t]
        sel_t_att = col_a1.selectbox("استاد کا نام", t_list_att)
        sel_date_att = col_a2.date_input("تاریخ (اختیاری)", value=None)

        query_att = "SELECT t_name, manual_date, manual_time, system_timestamp FROM t_attendance"
        conditions = []
        if sel_t_att != "تمام": conditions.append(f"t_name = '{sel_t_att}'")
        if sel_date_att: conditions.append(f"manual_date = '{sel_date_att}'")
        
        if conditions: query_att += " WHERE " + " AND ".join(conditions)
        query_att += " ORDER BY manual_date DESC"
        
        df_att = pd.read_sql_query(query_att, conn)
        if not df_att.empty:
            df_att.columns = ["استاد کا نام", "تاریخ", "درج کردہ وقت", "سسٹم ریکارڈ وقت"]
            st.dataframe(df_att, use_container_width=True, hide_index=True)
            # پرنٹ آپشن
            att_print = f"<div dir='rtl'><h2>اساتذہ حاضری رپورٹ</h2>{df_att.to_html(index=False, border=1)}</div>"
            st.markdown(get_report_download_link(att_print, "Teachers_Attendance.html"), unsafe_allow_html=True)
        else: st.info("کوئی ریکارڈ نہیں ملا۔")

    # ---------------- 🕒 میری حاضری (ٹیچر سیکشن - جملہ حذف شدہ) ----------------
    elif m == "🕒 میری حاضری":
        st.header("🕒 اپنی حاضری درج کریں")
        with st.form("my_att_form"):
            m_date = st.date_input("تاریخ", get_pkt_time().date())
            m_time = st.time_input("آمد کا وقت", get_pkt_time().time())
            if st.form_submit_button("حاضری محفوظ کریں"):
                exists = c.execute("SELECT 1 FROM t_attendance WHERE t_name=? AND manual_date=?", (st.session_state.username, str(m_date))).fetchone()
                if exists: st.error("اس تاریخ کی حاضری پہلے ہی موجود ہے۔")
                else:
                    sys_t = get_pkt_time().strftime("%I:%M %p")
                    c.execute("INSERT INTO t_attendance (t_name, manual_date, manual_time, system_timestamp) VALUES (?,?,?,?)",
                              (st.session_state.username, str(m_date), m_time.strftime("%I:%M %p"), sys_t))
                    conn.commit(); st.success("حاضری درج ہوگئی۔")

    # ---------------- 📝 تعلیمی اندراج (مکمل پرانی لاجک کے ساتھ) ----------------
    elif m == "📝 تعلیمی اندراج":
        st.header(f"📝 تعلیمی اندراج (استاد: {st.session_state.username})")
        sel_date = st.date_input("تاریخ", get_pkt_time().date())
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

        if not students: st.info("کوئی طالب علم رجسٹرڈ نہیں ہے۔")
        else:
            for s, f in students:
                with st.expander(f"👤 {s} ولد {f}"):
                    att = st.radio(f"حاضری {s}", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{s}", horizontal=True)
                    if att == "حاضر":
                        surah = st.selectbox("سورت", surahs_urdu, key=f"sr_{s}")
                        c1, c2 = st.columns(2)
                        a_from = c1.text_input("آیت (سے)", key=f"af_{s}")
                        a_to = c2.text_input("آیت (تک)", key=f"at_{s}")
                        
                        st.subheader("سبقی و منزل")
                        col_sq1, col_sq2 = st.columns(2)
                        sq_p = col_sq1.text_input("سبقی (پارہ/صفحہ)", key=f"sqp_{s}")
                        sq_m = col_sq2.number_input("سبقی غلطی", 0, 50, key=f"sqm_{s}")
                        m_p = col_sq1.text_input("منزل (پارہ/صفحہ)", key=f"mp_{s}")
                        m_m = col_sq2.number_input("منزل غلطی", 0, 50, key=f"mm_{s}")

                        if st.button(f"ریکارڈ محفوظ کریں: {s}", key=f"btn_{s}"):
                            sabq = f"{surah}: {a_from}-{a_to}"
                            c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, sq_p, sq_m, m_p, m_m, attendance) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                      (str(sel_date), s, f, st.session_state.username, sabq, sq_p, sq_m, m_p, m_m, att))
                            conn.commit(); st.success(f"{s} کا ریکارڈ محفوظ ہوگیا۔")
                    else:
                        if st.button(f"حاضری لگائیں: {s}", key=f"btn_abs_{s}"):
                            c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance, surah, sq_p, m_p) VALUES (?,?,?,?,?,?,?,?)",
                                      (str(sel_date), s, f, st.session_state.username, att, "ناغہ", "ناغہ", "ناغہ"))
                            conn.commit(); st.success(f"{s} کی حاضری ({att}) لگ گئی۔")

    # ---------------- 🎓 امتحانی تعلیمی رپورٹ ----------------
    elif m == "🎓 امتحانی تعلیمی رپورٹ":
        st.header("🎓 امتحانی نتائج")
        if st.session_state.user_type == "admin":
            with st.form("exam_form"):
                sn_ex = st.text_input("طالب علم نام")
                fn_ex = st.text_input("ولدیت")
                para_ex = st.number_input("پارہ نمبر", 1, 30)
                total_ex = st.number_input("نمبر", 0, 100)
                grade_ex = st.selectbox("درجہ", ["ممتاز", "جید جدا", "جید", "مقبول", "راسب"])
                if st.form_submit_button("امتحان درج کریں"):
                    c.execute("INSERT INTO exams (s_name, f_name, para_no, total, grade, status) VALUES (?,?,?,?,?,?)",
                              (sn_ex, fn_ex, para_ex, total_ex, grade_ex, "کامیاب"))
                    conn.commit(); st.success("کامیاب!")
        
        ex_df = pd.read_sql_query("SELECT s_name, f_name, para_no, total, grade FROM exams", conn)
        if not ex_df.empty:
            st.dataframe(ex_df, use_container_width=True)
            ex_html = f"<div dir='rtl'><h2>امتحانی رپورٹ</h2>{ex_df.to_html(index=False, border=1)}</div>"
            st.markdown(get_report_download_link(ex_html, "Exams.html"), unsafe_allow_html=True)

    # ---------------- 📜 ماہانہ رزلٹ کارڈ ----------------
    elif m == "📜 ماہانہ رزلٹ کارڈ":
        st.header("📜 ماہانہ رزلٹ کارڈ")
        all_s = c.execute("SELECT DISTINCT name FROM students").fetchall()
        sel_res = st.selectbox("طالب علم", [str(s[0]) for s in all_s])
        if st.button("رزلٹ کارڈ تیار کریں"):
            res_data = pd.read_sql_query(f"SELECT r_date, attendance, surah, sq_m, m_m FROM hifz_records WHERE s_name='{sel_res}'", conn)
            st.dataframe(res_data, use_container_width=True)
            res_html = f"<div dir='rtl'><h1>رزلٹ کارڈ: {sel_res}</h1>{res_data.to_html(border=1)}</div>"
            st.markdown(get_report_download_link(res_html, f"Result_{sel_res}.html"), unsafe_allow_html=True)

    # ---------------- 🏛️ مہتمم پینل (رخصت) ----------------
    elif m == "🏛️ مہتمم پینل (رخصت)":
        st.header("🏛️ رخصت کی درخواستیں")
        leaves = pd.read_sql_query("SELECT id, t_name, reason, start_date, status FROM leave_requests WHERE status='پینڈنگ'", conn)
        if not leaves.empty:
            st.dataframe(leaves, use_container_width=True)
            for _, row in leaves.iterrows():
                if st.button(f"منظور کریں: {row['t_name']}", key=f"lv_{row['id']}"):
                    c.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (row['id'],))
                    conn.commit(); st.rerun()
        else: st.info("کوئی نئی درخواست نہیں ہے۔")

    # ---------------- ⚙️ انتظامی کنٹرول ----------------
    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن و کنٹرول")
        tab1, tab2 = st.tabs(["اساتذہ", "طلباء"])
        with tab1:
            with st.form("t_add"):
                tn = st.text_input("نام")
                tp = st.text_input("پاسورڈ")
                if st.form_submit_button("رجسٹر کریں"):
                    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                    conn.commit(); st.success("کامیاب!")
        with tab2:
            with st.form("s_add"):
                sn = st.text_input("طالب علم نام")
                sf = st.text_input("ولدیت")
                teachers_all = c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()
                st_t = st.selectbox("استاد", [str(t[0]) for t in teachers_all])
                if st.form_submit_button("داخلہ کریں"):
                    c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (sn, sf, st_t))
                    conn.commit(); st.success("کامیاب!")

    # لاگ آؤٹ
    if st.sidebar.button("🚪 لاگ آؤٹ"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()
