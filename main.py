import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64
import re

# ==========================================
# 1. ڈیٹا بیس سیٹ اپ اور آٹو اپ گریڈ
# ==========================================
DB_NAME = 'jamia_millia_v1.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def get_pkt_time():
    return datetime.utcnow() + timedelta(hours=5)

def clean_text(val):
    if not val: return ""
    cleaned = re.sub(r"[()\'\",]", "", str(val))
    return cleaned.strip()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT, phone TEXT, address TEXT, id_card TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT, phone TEXT, address TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, surah TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, manual_date DATE, manual_time TEXT, system_timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, l_type TEXT, days INTEGER, reason TEXT, start_date DATE, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exams (id INTEGER PRIMARY KEY AUTOINCREMENT, s_name TEXT, f_name TEXT, para_no INTEGER, start_date TEXT, end_date TEXT, total INTEGER, grade TEXT, status TEXT)''')
    
    # آٹو اپ گریڈر (Crash-Proof System)
    cols_to_add = [
        ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER"),
        ("leave_requests", "reason", "TEXT"), ("leave_requests", "start_date", "DATE"),
        ("leave_requests", "status", "TEXT"), ("t_attendance", "manual_date", "DATE"),
        ("t_attendance", "manual_time", "TEXT"), ("t_attendance", "system_timestamp", "TEXT"),
        ("hifz_records", "sq_a", "INTEGER"), ("hifz_records", "sq_m", "INTEGER"),
        ("hifz_records", "m_a", "INTEGER"), ("hifz_records", "m_m", "INTEGER")
    ]
    for table, col, typ in cols_to_add:
        try: c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        except: pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# ==========================================
# 2. پروفیشنل اسٹائلنگ (CSS) اور پرنٹ فنکشنز
# ==========================================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ | Educationist", layout="wide", page_icon="🕌")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    * { font-family: 'Noto Nastaliq Urdu', serif !important; direction: rtl; text-align: right; }
    
    /* ڈیش بورڈ کارڈز کی اسٹائلنگ */
    .dashboard-card { background: linear-gradient(135deg, #ffffff 0%, #f1f8e9 100%); padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); text-align: center; border-bottom: 5px solid #1e5631; margin-bottom: 20px; transition: 0.3s; }
    .dashboard-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
    .card-title { color: #555; font-size: 18px; font-weight: bold; }
    .card-value { color: #1e5631; font-size: 38px; font-weight: bold; margin: 10px 0; }
    
    /* نوٹس بورڈ اور ہیڈر */
    .notice-board { background: #fff3cd; padding: 20px; border-radius: 10px; border-right: 6px solid #ffc107; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .main-header { text-align: center; color: white; background: linear-gradient(to right, #1e5631, #2e7d32); padding: 25px; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .date-divider { background-color: #2e7d32; color: white; text-align: center; padding: 10px; font-size: 20px; border-radius: 8px; margin: 25px 0 10px 0; }
    
    /* بٹنز */
    .stButton>button { background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background: #2e7d32; color: white; border-color: #1e5631; }
</style>
""", unsafe_allow_html=True)

def generate_html_print(dataframe, title):
    html = f"""
    <html dir="rtl" lang="ur">
    <head><meta charset="utf-8"><style>body{{font-family: 'Arial', sans-serif; padding: 20px;}} h1, h2{{text-align: center; color: #1e5631;}} table{{width: 100%; border-collapse: collapse; margin-top: 20px;}} th, td{{border: 1px solid black; padding: 8px; text-align: right;}} th{{background-color: #f2f2f2;}} .footer{{display: flex; justify-content: space-between; margin-top: 50px; font-weight: bold;}} .footer div{{border-top: 1px solid black; width: 200px; text-align: center; padding-top: 5px;}}</style></head>
    <body><h1>جامعہ ملیہ اسلامیہ</h1><h2>{title}</h2><p>تاریخِ پرنٹ: {get_pkt_time().strftime("%Y-%m-%d %H:%M")}</p>
    {dataframe.to_html(index=False)}<div class="footer"><div>دستخط مہتمم</div><div>دستخط مدرس</div></div></body></html>
    """
    b64 = base64.b64encode(html.encode('utf-8-sig')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{title}.html" style="text-decoration:none;"><button style="background-color:#008CBA; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; width:100%;">🖨️ پرنٹ / ڈاؤنلوڈ: {title}</button></a>'

def execute_delete(table_name, record_id):
    c.execute(f"DELETE FROM {table_name} WHERE id=?", (record_id,))
    conn.commit()
    st.success(f"ریکارڈ کامیابی سے حذف کر دیا گیا!")
    st.rerun()

# ==========================================
# 3. لاگ ان سسٹم
# ==========================================
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ (Educationist ERP)</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("🔐 پورٹل میں داخل ہوں")
        u = st.text_input("صارف کا نام (Username)")
        p = st.text_input("پاسورڈ (Password)", type="password")
        if st.button("لاگ ان"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("❌ غلط معلومات!")
    st.stop()

# ==========================================
# 4. مینوز اور نیویگیشن
# ==========================================
if st.session_state.user_type == "admin":
    menu = ["📊 ڈیش بورڈ (Overview)", "📝 یومیہ تعلیمی رپورٹ", "🖨️ ٹریکنگ و پرنٹ رپورٹ", "🎓 امتحانات و نتائج", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
else:
    menu = ["📝 تعلیمی اندراج", "🎓 امتحان کے لیے نامزدگی", "📩 درخواستِ رخصت", "🕒 میری حاضری"]

m = st.sidebar.radio("📌 مرکزی مینو", menu)
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# ==========================================
# ماڈیول 1: گرافیکل ڈیش بورڈ (Plotly کے ساتھ)
# ==========================================
if m == "📊 ڈیش بورڈ (Overview)":
    st.header("📊 جامعہ اینالیٹکس ڈیش بورڈ")
    today_str = str(date.today())
    
    # ڈیٹا بیس سے لائیو اعداد و شمار
    total_students = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = c.execute("SELECT COUNT(*) FROM teachers WHERE name != 'admin'").fetchone()[0]
    
    # آج کی حاضری کا ڈیٹا (پائی چارٹ کے لیے)
    att_data = pd.read_sql_query(f"SELECT attendance, COUNT(*) as count FROM hifz_records WHERE r_date='{today_str}' GROUP BY attendance", conn)
    
    # میٹرکس کارڈز
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("کل طلباء", total_students)
    with col2: st.metric("کل اساتذہ", total_teachers)
    with col3:
        p_count = c.execute(f"SELECT COUNT(*) FROM hifz_records WHERE r_date='{today_str}' AND attendance='حاضر'").fetchone()[0]
        st.metric("آج حاضر طلباء", p_count)
    with col4:
        t_present = c.execute(f"SELECT COUNT(DISTINCT t_name) FROM t_attendance WHERE manual_date='{today_str}'").fetchone()[0]
        st.metric("حاضر اساتذہ", t_present)

    st.divider()

    # --- گراف سیکشن ---
    g1, g2 = st.columns(2)

    with g1:
        st.subheader("🎯 آج کی حاضری کا تناسب")
        if not att_data.empty:
            fig_pie = px.pie(att_data, values='count', names='attendance', 
                             color='attendance',
                             color_discrete_map={'حاضر':'#1e5631', 'غیر حاضر':'#d32f2f', 'رخصت':'#ffa000'},
                             hole=0.4)
            fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("آج کی حاضری کا ڈیٹا دستیاب نہیں ہے۔")

    with g2:
        st.subheader("📉 پچھلے 7 دن کی تعلیمی رپورٹ")
        # پچھلے 7 دن کی غلطیوں کا ڈیٹا
        week_ago = str(date.today() - timedelta(days=7))
        err_df = pd.read_sql_query(f"""
            SELECT r_date, SUM(sq_m) as 'سبقی غلطی', SUM(m_m) as 'منزل غلطی' 
            FROM hifz_records 
            WHERE r_date >= '{week_ago}' 
            GROUP BY r_date 
            ORDER BY r_date ASC
        """, conn)
        
        if not err_df.empty:
            fig_line = px.line(err_df, x='r_date', y=['سبقی غلطی', 'منزل غلطی'], 
                               markers=True,
                               color_discrete_sequence=['#2e7d32', '#1565c0'])
            fig_line.update_layout(xaxis_title="تاریخ", yaxis_title="تعدادِ غلطی", legend_title="نوعیت")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("گزشتہ ہفتے کا تعلیمی ریکارڈ موجود نہیں ہے۔")

    st.markdown("---")
    # کوئیک ایکشنز (پہلے والے)
    st.subheader("⚡ فوری انتظامی کنٹرول")
    c1, c2, c3 = st.columns(3)
    if c1.button("🎓 نیا داخلہ"): st.info("انتظامی کنٹرول مینو میں جائیں")
    if c2.button("📜 ماہانہ رپورٹ"): st.info("ماہانہ رزلٹ کارڈ مینو میں جائیں")
    if c3.button("📢 تمام اساتذہ کو الرٹ"): st.warning("یہ فیچر جلد آرہا ہے")
# ==========================================
# ماڈیول 2: تعلیمی اندراج (محفوظ اور کلین)
# ==========================================
elif m == "📝 تعلیمی اندراج":
    st.header("📝 یومیہ تعلیمی اندراج")
    sel_date = st.date_input("تاریخ منتخب کریں", get_pkt_time().date())
    raw_students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

    if not raw_students: st.warning("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
    else:
        for s_raw, f_raw in raw_students:
            s, f = clean_text(s_raw), clean_text(f_raw)
            with st.expander(f"👤 {s} ولد {f}"):
                att = st.radio(f"حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{s}", horizontal=True)
                if att == "حاضر":
                    s_nagha = st.checkbox("سبق کا ناغہ", key=f"sn_{s}")
                    if not s_nagha:
                        c1, c2, c3 = st.columns([2, 1, 1])
                        surah = c1.selectbox("سورت", surahs_urdu, key=f"surah_{s}")
                        a_from = c2.text_input("آیت سے", key=f"af_{s}")
                        a_to = c3.text_input("آیت تک", key=f"at_{s}")
                        sabq_final = f"{surah}: {a_from}-{a_to}"
                    else: sabq_final = "ناغہ"

                    sq_nagha = st.checkbox("سبقی کا ناغہ", key=f"sqn_{s}")
                    sq_list, sq_err, sq_atk = [], 0, 0
                    if not sq_nagha:
                        if f"sq_c_{s}" not in st.session_state: st.session_state[f"sq_c_{s}"] = 1
                        for i in range(st.session_state[f"sq_c_{s}"]):
                            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                            p = c1.selectbox(f"پارہ", paras, key=f"sqp_{s}_{i}")
                            v = c2.selectbox(f"مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{s}_{i}")
                            a = c3.number_input(f"اٹکن", 0, key=f"sqa_{s}_{i}")
                            e = c4.number_input(f"غلطی", 0, key=f"sqe_{s}_{i}")
                            sq_list.append(f"{p}:{v}"); sq_atk += a; sq_err += e
                        if st.button("➕ مزید سبقی", key=f"add_sq_{s}"): st.session_state[f"sq_c_{s}"] += 1; st.rerun()
                    else: sq_list = ["ناغہ"]

                    m_nagha = st.checkbox("منزل کا ناغہ", key=f"mn_{s}")
                    m_list, m_err, m_atk = [], 0, 0
                    if not m_nagha:
                        if f"m_c_{s}" not in st.session_state: st.session_state[f"m_c_{s}"] = 1
                        for i in range(st.session_state[f"m_c_{s}"]):
                            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                            p = c1.selectbox(f"پارہ", paras, key=f"mp_{s}_{i}")
                            v = c2.selectbox(f"مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{s}_{i}")
                            a = c3.number_input(f"اٹکن", 0, key=f"ma_{s}_{i}")
                            e = c4.number_input(f"غلطی", 0, key=f"me_{s}_{i}")
                            m_list.append(f"{p}:{v}"); m_atk += a; m_err += e
                        if st.button("➕ مزید منزل", key=f"add_m_{s}"): st.session_state[f"m_c_{s}"] += 1; st.rerun()
                    else: m_list = ["ناغہ"]

                    if st.button("محفوظ کریں", key=f"save_{s}"):
                        c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (str(sel_date), s, f, st.session_state.username, sabq_final, " | ".join(sq_list), sq_atk, sq_err, " | ".join(m_list), m_atk, m_err, att))
                        conn.commit(); st.success("محفوظ ہو گیا!")
                else:
                    if st.button("حاضری لگائیں", key=f"save_absent_{s}"):
                        c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance, surah, sq_p, m_p) VALUES (?,?,?,?,?,?,?,?)", (str(sel_date), s, f, st.session_state.username, att, "-", "-", "-"))
                        conn.commit(); st.success(f"{att} لگ گئی!")

# ==========================================
# دیگر تمام ماڈیولز (بغیر کسی کمی کے)
# ==========================================
elif m == "📝 یومیہ تعلیمی رپورٹ":
    st.header("📊 یومیہ تعلیمی رپورٹ")
    d1, d2 = st.date_input("آغاز", date.today()), st.date_input("اختتام", get_pkt_time().date())
    t_list = ["تمام اساتذہ"] + [clean_text(row[0]) for row in c.execute("SELECT name FROM teachers WHERE name != 'admin'").fetchall()]
    sel_t = st.selectbox("استاد منتخب کریں", t_list)

    query = "SELECT id as 'ID', r_date as 'تاریخ', s_name as 'نام', f_name as 'ولدیت', t_name as 'استاد', attendance as 'حاضری', surah as 'سبق', sq_p as 'سبقی', sq_m as 'سبقی غلطی', m_p as 'منزل', m_m as 'منزل غلطی' FROM hifz_records WHERE r_date BETWEEN ? AND ?"
    params = [str(d1), str(d2)]
    if sel_t != "تمام اساتذہ": query += " AND t_name = ?"; params.append(sel_t)
    df = pd.read_sql_query(query + " ORDER BY r_date DESC", conn, params=params)
    
    if df.empty: st.info("کوئی ریکارڈ نہیں ملا۔")
    else:
        st.markdown(generate_html_print(df.drop(columns=['ID']), "یومیہ تعلیمی رپورٹ"), unsafe_allow_html=True)
        for date_val, group_df in df.groupby('تاریخ'):
            st.markdown(f"<div class='date-divider'>📅 تاریخ: {date_val}</div>", unsafe_allow_html=True)
            st.dataframe(group_df.drop(columns=['تاریخ']), use_container_width=True, hide_index=True)
        st.divider()
        del_r_id = st.number_input("غلط درج شدہ ریکارڈ کی ID درج کریں", min_value=0, step=1, key="del_hr")
        if st.button("ریکارڈ حذف کریں"): execute_delete("hifz_records", del_r_id)

elif m == "🖨️ ٹریکنگ و پرنٹ رپورٹ":
    st.header("🖨️ انفرادی ٹریکنگ")
    s_list = [f"{clean_text(s[0])} ولد {clean_text(s[1])}" for s in c.execute("SELECT name, father_name FROM students").fetchall()]
    if s_list:
        sel_s = st.selectbox("طالب علم", s_list)
        sn, fn = sel_s.split(" ولد ")
        df_hist = pd.read_sql_query(f"SELECT r_date as 'تاریخ', attendance as 'حاضری', surah as 'سبق', sq_p as 'سبقی', m_p as 'منزل' FROM hifz_records WHERE s_name='{sn}' AND f_name='{fn}' ORDER BY r_date DESC LIMIT 30", conn)
        st.dataframe(df_hist, use_container_width=True)
        st.markdown(generate_html_print(df_hist, f"رپورٹ: {sel_s}"), unsafe_allow_html=True)

elif m in ["🎓 امتحان کے لیے نامزدگی", "🎓 امتحانات و نتائج"]:
    st.header("🎓 امتحانی نظام")
    if st.session_state.user_type == "teacher":
        my_students = [f"{clean_text(s[0])} ولد {clean_text(s[1])}" for s in c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()]
        if my_students:
            sel_s = st.selectbox("طالب علم", my_students)
            para_no = st.number_input("پارہ نمبر", 1, 30)
            if st.button("امتحان کی درخواست بھیجیں"):
                sn, fn = sel_s.split(" ولد ")
                c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)", (sn, fn, para_no, str(date.today()), "پینڈنگ"))
                conn.commit(); st.success("درخواست بھیج دی گئی!")
    else:
        pending = c.execute("SELECT id, s_name, f_name, para_no FROM exams WHERE status='پینڈنگ'").fetchall()
        for eid, sn, fn, pn in pending:
            with st.expander(f"📝 {sn} - پارہ {pn}"):
                c1, c2, c3, c4, c5 = st.columns(5)
                tot = c1.number_input("س1",0,20,key=f"q1_{eid}") + c2.number_input("س2",0,20,key=f"q2_{eid}") + c3.number_input("س3",0,20,key=f"q3_{eid}") + c4.number_input("س4",0,20,key=f"q4_{eid}") + c5.number_input("س5",0,20,key=f"q5_{eid}")
                if st.button("محفوظ کریں", key=f"sv_{eid}"):
                    g = "ممتاز" if tot>=90 else "جید جداً" if tot>=80 else "جید" if tot>=70 else "مقبول" if tot>=60 else "فیل"
                    c.execute("UPDATE exams SET total=?, grade=?, status='مکمل', end_date=? WHERE id=?", (tot, g, str(date.today()), eid))
                    conn.commit(); st.rerun()
        df_ex = pd.read_sql_query("SELECT id as 'ID', s_name as 'نام', f_name as 'ولدیت', para_no as 'پارہ', total as 'نمبر', grade as 'گریڈ' FROM exams WHERE status='مکمل'", conn)
        st.dataframe(df_ex, use_container_width=True)
        if not df_ex.empty: st.markdown(generate_html_print(df_ex.drop(columns=['ID']), "امتحانی ریکارڈ"), unsafe_allow_html=True)

elif m == "📜 ماہانہ رزلٹ کارڈ":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    m_year, m_month = st.selectbox("سال", [2024, 2025, 2026]), st.selectbox("مہینہ", range(1, 13))
    if st.button("رپورٹ تیار کریں"):
        start_dt, end_dt = f"{m_year}-{m_month:02d}-01", f"{m_year}-{m_month:02d}-31"
        q = "SELECT s_name as 'نام', COUNT(*) as 'کل دن', SUM(CASE WHEN attendance='حاضر' THEN 1 ELSE 0 END) as 'حاضریاں', SUM(sq_m) as 'سبقی غلطیاں', SUM(m_m) as 'منزل غلطیاں' FROM hifz_records WHERE r_date BETWEEN ? AND ? GROUP BY s_name"
        df_month = pd.read_sql_query(q, conn, params=[start_dt, end_dt])
        st.dataframe(df_month, use_container_width=True)
        if not df_month.empty: st.markdown(generate_html_print(df_month, f"ماہانہ رزلٹ کارڈ ({m_year}-{m_month:02d})"), unsafe_allow_html=True)

elif m == "🕒 میری حاضری":
    m_date, m_time = st.date_input("تاریخ", date.today()), st.time_input("آمد", get_pkt_time().time())
    if st.button("حاضری درج کریں"):
        if c.execute("SELECT 1 FROM t_attendance WHERE t_name=? AND manual_date=?", (st.session_state.username, str(m_date))).fetchone(): st.error("پہلے ہی لگ چکی ہے۔")
        else:
            c.execute("INSERT INTO t_attendance (t_name, manual_date, manual_time, system_timestamp) VALUES (?,?,?,?)", (st.session_state.username, str(m_date), str(m_time), get_pkt_time().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); st.success("حاضری درج ہو گئی!")

elif m == "🕒 اساتذہ کا ریکارڈ":
    st.header("🕒 اساتذہ کی حاضری")
    df_att = pd.read_sql_query("SELECT id as 'ID', t_name as 'استاد', manual_date as 'تاریخ', manual_time as 'آمد' FROM t_attendance ORDER BY manual_date DESC", conn)
    st.dataframe(df_att, use_container_width=True)
    if not df_att.empty: st.markdown(generate_html_print(df_att.drop(columns=['ID']), "اساتذہ کی حاضری"), unsafe_allow_html=True)

elif m == "📩 درخواستِ رخصت":
    with st.form("leave"):
        l_type, days, rsn = st.selectbox("نوعیت", ["بیماری", "ضروری کام", "دیگر"]), st.number_input("دن", 1, 30), st.text_area("تفصیل")
        if st.form_submit_button("ارسال کریں"):
            c.execute("INSERT INTO leave_requests (t_name, l_type, days, reason, start_date, status) VALUES (?,?,?,?,?,?)", (st.session_state.username, l_type, days, rsn, str(date.today()), "پینڈنگ"))
            conn.commit(); st.success("درخواست بھیج دی گئی!")

elif m == "🏛️ مہتمم پینل (رخصت)":
    for rid, tn, lt, d, rsn, sd in c.execute("SELECT id, t_name, l_type, days, reason, start_date FROM leave_requests WHERE status='پینڈنگ'").fetchall():
        with st.expander(f"{tn} ({lt} - {d} دن)"):
            st.write(rsn)
            c1, c2 = st.columns(2)
            if c1.button("✅ منظور", key=f"app_{rid}"): c.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (rid,)); conn.commit(); st.rerun()
            if c2.button("❌ مسترد", key=f"rej_{rid}"): c.execute("UPDATE leave_requests SET status='مسترد' WHERE id=?", (rid,)); conn.commit(); st.rerun()
    df_lv = pd.read_sql_query("SELECT t_name as 'استاد', l_type as 'نوعیت', days as 'دن', start_date as 'تاریخ', status as 'سٹیٹس' FROM leave_requests WHERE status!='پینڈنگ'", conn)
    st.dataframe(df_lv, use_container_width=True)

elif m == "⚙️ انتظامی کنٹرول":
    tab1, tab2 = st.tabs(["👥 اساتذہ", "🎓 طلباء"])
    with tab1:
        with st.form("add_teacher"):
            t_name, t_pass, t_phone = st.text_input("نام"), st.text_input("پاسورڈ"), st.text_input("فون")
            if st.form_submit_button("محفوظ کریں"): c.execute("INSERT OR IGNORE INTO teachers (name, password, phone) VALUES (?,?,?)", (t_name, t_pass, t_phone)); conn.commit(); st.success("استاد رجسٹرڈ!")
        df_t = pd.read_sql_query("SELECT id, name, phone FROM teachers WHERE name != 'admin'", conn)
        st.dataframe(df_t, use_container_width=True)
        del_t = st.number_input("ID درج کریں", min_value=0, step=1, key="dt")
        if st.button("حذف", key="btnt"): execute_delete("teachers", del_t)
    with tab2:
        with st.form("add_student"):
            s_name, f_name = st.text_input("نام"), st.text_input("ولدیت")
            t_list = [clean_text(row[0]) for row in c.execute("SELECT name FROM teachers WHERE name != 'admin'").fetchall()]
            t_assign = st.selectbox("متعلقہ استاد", t_list) if t_list else None
            if st.form_submit_button("محفوظ کریں") and t_assign: c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (s_name, f_name, t_assign)); conn.commit(); st.success("طالب علم رجسٹرڈ!")
        df_s = pd.read_sql_query("SELECT id, name, father_name, teacher_name FROM students", conn)
        st.dataframe(df_s, use_container_width=True)
        del_s = st.number_input("ID درج کریں", min_value=0, step=1, key="ds")
        if st.button("حذف", key="btns"): execute_delete("students", del_s)

conn.close()
