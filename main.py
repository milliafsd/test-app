import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

# ==========================================
# 1. ڈیٹا بیس سیٹ اپ اور کنکشن
# ==========================================
DB_NAME = 'jamia_millia_v1test.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def get_pkt_time():
    return datetime.utcnow() + timedelta(hours=5)

def init_db():
    # اساتذہ
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT, phone TEXT, address TEXT, id_card TEXT)''')
    # طلباء
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT, phone TEXT, address TEXT)''')
    # حفظ ریکارڈ
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, surah TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT)''')
    # اساتذہ کی حاضری
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, manual_date DATE, manual_time TEXT, system_timestamp TEXT)''')
    # رخصت کی درخواستیں
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, l_type TEXT, days INTEGER, reason TEXT, start_date DATE, status TEXT)''')
    # امتحانات
    c.execute('''CREATE TABLE IF NOT EXISTS exams (id INTEGER PRIMARY KEY AUTOINCREMENT, s_name TEXT, f_name TEXT, para_no INTEGER, start_date TEXT, end_date TEXT, total INTEGER, grade TEXT, status TEXT)''')
    
    # ایڈمن اکاؤنٹ (اگر نہ ہو)
    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# ==========================================
# 2. اسٹائلنگ (RTL) اور پرنٹ کے فنکشنز
# ==========================================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    * { font-family: 'Noto Nastaliq Urdu', serif !important; direction: rtl; text-align: right; }
    .main-header { text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-bottom: 4px solid #1e5631; }
    .date-divider { background-color: #2e7d32; color: white; text-align: center; padding: 10px; font-size: 20px; border-radius: 8px; margin: 25px 0 10px 0; }
    .stButton>button { background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%; }
    .print-btn>button { background: #008CBA !important; }
    .delete-btn>button { background: #f44336 !important; }
</style>
""", unsafe_allow_html=True)

def generate_html_print(dataframe, title):
    html = f"""
    <html dir="rtl" lang="ur">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Arial', sans-serif; padding: 20px; }}
            h1, h2 {{ text-align: center; color: #1e5631; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid black; padding: 8px; text-align: right; }}
            th {{ background-color: #f2f2f2; }}
            .footer {{ display: flex; justify-content: space-between; margin-top: 50px; font-weight: bold; }}
            .footer div {{ border-top: 1px solid black; width: 200px; text-align: center; padding-top: 5px; }}
        </style>
    </head>
    <body>
        <h1>جامعہ ملیہ اسلامیہ</h1>
        <h2>{title}</h2>
        <p>تاریخِ پرنٹ: {get_pkt_time().strftime("%Y-%m-%d %H:%M")}</p>
        {dataframe.to_html(index=False)}
        <div class="footer"><div>دستخط مہتمم</div><div>دستخط مدرس</div></div>
    </body>
    </html>
    """
    b64 = base64.b64encode(html.encode('utf-8-sig')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{title}.html" style="text-decoration:none;"><button style="background-color:#008CBA; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; width:100%;">🖨️ پرنٹ / ڈاؤنلوڈ: {title}</button></a>'

def execute_delete(table_name, record_id):
    c.execute(f"DELETE FROM {table_name} WHERE id=?", (record_id,))
    conn.commit()
    st.success(f"ریکارڈ نمبر {record_id} کامیابی سے حذف کر دیا گیا!")
    st.rerun()

# ==========================================
# 3. لاگ ان سسٹم
# ==========================================
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("🔐 لاگ ان کریں")
        u = st.text_input("صارف کا نام (Username)")
        p = st.text_input("پاسورڈ (Password)", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("❌ غلط معلومات!")
    st.stop()

# ==========================================
# 4. مینوز (Menus)
# ==========================================
if st.session_state.user_type == "admin":
    menu = ["📊 یومیہ تعلیمی رپورٹ", "🖨️ ٹریکنگ و پرنٹ رپورٹ", "🎓 امتحانات و نتائج", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
else:
    menu = ["📝 تعلیمی اندراج", "🎓 امتحان کے لیے نامزدگی", "📩 درخواستِ رخصت", "🕒 میری حاضری"]

m = st.sidebar.radio("📌 مینو منتخب کریں", menu)
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()

# مستقل متغیرات (Constants)
surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# ==========================================
# ماڈیول: انتظامی کنٹرول (حذف اور ترمیم)
# ==========================================
if m == "⚙️ انتظامی کنٹرول":
    st.header("⚙️ انتظامی کنٹرول (رجسٹریشن، ترمیم اور حذف)")
    tab1, tab2 = st.tabs(["👥 اساتذہ کا انتظام", "🎓 طلباء کا انتظام"])
    
    with tab1:
        st.subheader("نیا استاد شامل کریں")
        with st.form("add_teacher"):
            t_name = st.text_input("استاد کا نام")
            t_pass = st.text_input("پاسورڈ")
            t_phone = st.text_input("فون نمبر")
            if st.form_submit_button("محفوظ کریں"):
                c.execute("INSERT OR IGNORE INTO teachers (name, password, phone) VALUES (?,?,?)", (t_name, t_pass, t_phone))
                conn.commit(); st.success("استاد رجسٹر ہو گیا!")
                st.rerun()
        
        st.subheader("موجودہ اساتذہ (ترمیم / حذف)")
        df_t = pd.read_sql_query("SELECT id, name, phone FROM teachers WHERE name != 'admin'", conn)
        st.dataframe(df_t, use_container_width=True)
        del_t_id = st.number_input("حذف کرنے کے لیے استاد کی ID درج کریں", min_value=0, step=1, key="del_t")
        if st.button("استاد کو حذف کریں"): execute_delete("teachers", del_t_id)

    with tab2:
        st.subheader("نیا طالب علم شامل کریں")
        with st.form("add_student"):
            s_name = st.text_input("نام طالب علم")
            f_name = st.text_input("ولدیت")
            t_list = [row[0] for row in c.execute("SELECT name FROM teachers WHERE name != 'admin'").fetchall()]
            t_assign = st.selectbox("متعلقہ استاد", t_list) if t_list else None
            if st.form_submit_button("محفوظ کریں") and t_assign:
                c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (s_name, f_name, t_assign))
                conn.commit(); st.success("طالب علم رجسٹر ہو گیا!")
                st.rerun()
                
        st.subheader("موجودہ طلباء (ترمیم / حذف)")
        df_s = pd.read_sql_query("SELECT id, name, father_name, teacher_name FROM students", conn)
        st.dataframe(df_s, use_container_width=True)
        del_s_id = st.number_input("حذف کرنے کے لیے طالب علم کی ID درج کریں", min_value=0, step=1, key="del_s")
        if st.button("طالب علم کو حذف کریں"): execute_delete("students", del_s_id)

# ==========================================
# ماڈیول: تعلیمی اندراج (اساتذہ کے لیے)
# ==========================================
elif m == "📝 تعلیمی اندراج":
    st.header("📝 یومیہ تعلیمی اندراج")
    st.markdown("<p style='color: #2e7d32; font-weight: bold;'>طالب علم کی حاضری اور سبق، سبقی، منزل کا اندراج کریں</p>", unsafe_allow_html=True)
    
    sel_date = st.date_input("آج کی تاریخ منتخب کریں", get_pkt_time().date())
    
    # ڈیٹا بیس سے طلباء کا صاف ڈیٹا نکالنا
    students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

    if not students: 
        st.warning("⚠️ آپ کی کلاس میں فی الحال کوئی طالب علم موجود نہیں۔")
    else:
        for s, f in students:
            # ناموں کو بالکل صاف (Clean) اور بریکٹس سے پاک کرنا
            clean_s_name = str(s).strip()
            clean_f_name = str(f).strip()
            display_name = f"{clean_s_name} ولد {clean_f_name}"
            
            with st.expander(f"👤 طالب علم: {display_name}"):
                # حاضری کا ریڈیو بٹن (منفرد Key کے ساتھ تاکہ ایرر نہ آئے)
                att = st.radio(
                    f"📌 {clean_s_name} کی حاضری", 
                    ["حاضر", "غیر حاضر (ناغہ)", "رخصت"], 
                    key=f"att_{clean_s_name}_{sel_date}", 
                    horizontal=True
                )
                
                if att == "حاضر":
                    st.markdown("---")
                    
                    # سبق کا سیکشن
                    st.markdown("### 📖 نیا سبق")
                    s_nagha = st.checkbox("آج سبق کا ناغہ ہے؟", key=f"sn_{clean_s_name}")
                    if not s_nagha:
                        c1, c2, c3 = st.columns([2, 1, 1])
                        surah = c1.selectbox("سورت", surahs_urdu, key=f"surah_{clean_s_name}")
                        a_from = c2.text_input("آیت (سے)", placeholder="مثلاً 1", key=f"af_{clean_s_name}")
                        a_to = c3.text_input("آیت (تک)", placeholder="مثلاً 5", key=f"at_{clean_s_name}")
                        sabq_final = f"{surah}: {a_from}-{a_to}"
                    else: 
                        sabq_final = "ناغہ"

                    # سبقی کا سیکشن
                    st.markdown("### 🔄 سبقی")
                    sq_nagha = st.checkbox("آج سبقی کا ناغہ ہے؟", key=f"sqn_{clean_s_name}")
                    sq_list, sq_err, sq_atk = [], 0, 0
                    if not sq_nagha:
                        if f"sq_c_{clean_s_name}" not in st.session_state: st.session_state[f"sq_c_{clean_s_name}"] = 1
                        for i in range(st.session_state[f"sq_c_{clean_s_name}"]):
                            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                            p = c1.selectbox(f"پارہ (سبقی)", paras, key=f"sqp_{clean_s_name}_{i}")
                            v = c2.selectbox(f"مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{clean_s_name}_{i}")
                            a = c3.number_input(f"اٹکن", 0, 20, key=f"sqa_{clean_s_name}_{i}")
                            e = c4.number_input(f"غلطی", 0, 20, key=f"sqe_{clean_s_name}_{i}")
                            sq_list.append(f"{p}:{v}"); sq_atk += a; sq_err += e
                        if st.button("➕ مزید سبقی شامل کریں", key=f"add_sq_{clean_s_name}"): 
                            st.session_state[f"sq_c_{clean_s_name}"] += 1
                            st.rerun()
                    else: 
                        sq_list = ["ناغہ"]

                    # منزل کا سیکشن
                    st.markdown("### 🏠 منزل")
                    m_nagha = st.checkbox("آج منزل کا ناغہ ہے؟", key=f"mn_{clean_s_name}")
                    m_list, m_err, m_atk = [], 0, 0
                    if not m_nagha:
                        if f"m_c_{clean_s_name}" not in st.session_state: st.session_state[f"m_c_{clean_s_name}"] = 1
                        for i in range(st.session_state[f"m_c_{clean_s_name}"]):
                            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                            p = c1.selectbox(f"پارہ (منزل)", paras, key=f"mp_{clean_s_name}_{i}")
                            v = c2.selectbox(f"مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{clean_s_name}_{i}")
                            a = c3.number_input(f"اٹکن", 0, 20, key=f"ma_{clean_s_name}_{i}")
                            e = c4.number_input(f"غلطی", 0, 20, key=f"me_{clean_s_name}_{i}")
                            m_list.append(f"{p}:{v}"); m_atk += a; m_err += e
                        if st.button("➕ مزید منزل شامل کریں", key=f"add_m_{clean_s_name}"): 
                            st.session_state[f"m_c_{clean_s_name}"] += 1
                            st.rerun()
                    else: 
                        m_list = ["ناغہ"]

                    if st.button(f"💾 {clean_s_name} کا مکمل ریکارڈ محفوظ کریں", key=f"save_{clean_s_name}"):
                        c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (str(sel_date), clean_s_name, clean_f_name, st.session_state.username, sabq_final, " | ".join(sq_list), sq_atk, sq_err, " | ".join(m_list), m_atk, m_err, att))
                        conn.commit()
                        st.success(f"✅ {clean_s_name} کا ریکارڈ بہترین انداز میں محفوظ ہو گیا!")
                
                else:
                    if st.button(f"💾 {clean_s_name} کی {att} محفوظ کریں", key=f"save_absent_{clean_s_name}"):
                        c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance, surah, sq_p, m_p) VALUES (?,?,?,?,?,?,?,?)", 
                                  (str(sel_date), clean_s_name, clean_f_name, st.session_state.username, att, "-", "-", "-"))
                        conn.commit()
                        st.success(f"✅ {clean_s_name} کی آج کی {att} درج ہو گئی!")

# ==========================================
# ماڈیول: یومیہ تعلیمی رپورٹ (ایڈمن)
# ==========================================
elif m == "📊 یومیہ تعلیمی رپورٹ":
    st.header("📊 یومیہ تعلیمی رپورٹ (تاریخ وار)")
    with st.sidebar:
        st.write("🔍 فلٹرز")
        d1 = st.date_input("آغاز", date.today())
        d2 = st.date_input("اختتام", get_pkt_time().date())
        t_list = ["تمام اساتذہ"] + [row[0] for row in c.execute("SELECT name FROM teachers WHERE name != 'admin'").fetchall()]
        sel_t = st.selectbox("استاد منتخب کریں", t_list)

    query = "SELECT id as 'ID', r_date as 'تاریخ', s_name as 'نام', f_name as 'ولدیت', t_name as 'استاد', attendance as 'حاضری', surah as 'سبق', sq_p as 'سبقی', sq_m as 'سبقی غلطی', m_p as 'منزل', m_m as 'منزل غلطی' FROM hifz_records WHERE r_date BETWEEN ? AND ?"
    params = [str(d1), str(d2)]
    if sel_t != "تمام اساتذہ": query += " AND t_name = ?"; params.append(sel_t)
    query += " ORDER BY r_date DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    
    if df.empty: st.info("کوئی ریکارڈ نہیں ملا۔")
    else:
        st.markdown(generate_html_print(df.drop(columns=['ID']), "یومیہ تعلیمی رپورٹ"), unsafe_allow_html=True)
        # تاریخ کے اعتبار سے الگ الگ دکھانا
        grouped = df.groupby('تاریخ')
        for date_val, group_df in grouped:
            st.markdown(f"<div class='date-divider'>📅 تاریخ: {date_val}</div>", unsafe_allow_html=True)
            st.dataframe(group_df.drop(columns=['تاریخ']), use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🗑️ ریکارڈ حذف کریں")
        del_r_id = st.number_input("غلط درج شدہ ریکارڈ کی ID درج کریں", min_value=0, step=1, key="del_hr")
        if st.button("ریکارڈ حذف کریں"): execute_delete("hifz_records", del_r_id)

# ==========================================
# ماڈیول: ٹریکنگ اور پرنٹ رپورٹ
# ==========================================
elif m == "🖨️ ٹریکنگ و پرنٹ رپورٹ":
    st.header("🖨️ انفرادی طالب علم ٹریکنگ اور پرنٹ")
    s_list = [f"{s[0]} ولد {s[1]}" for s in c.execute("SELECT name, father_name FROM students").fetchall()]
    if not s_list: st.warning("کوئی طالب علم موجود نہیں۔")
    else:
        sel_s = st.selectbox("طالب علم منتخب کریں", s_list)
        sn, fn = sel_s.split(" ولد ")
        
        df_hist = pd.read_sql_query(f"SELECT r_date as 'تاریخ', attendance as 'حاضری', surah as 'سبق', sq_p as 'سبقی', m_p as 'منزل' FROM hifz_records WHERE s_name='{sn}' AND f_name='{fn}' ORDER BY r_date DESC LIMIT 30", conn)
        
        st.dataframe(df_hist, use_container_width=True)
        st.markdown(generate_html_print(df_hist, f"رپورٹ: {sel_s}"), unsafe_allow_html=True)

# ==========================================
# ماڈیول: امتحانات (نامزدگی، نتائج، اور ریکارڈ)
# ==========================================
elif m in ["🎓 امتحانی تعلیمی رپورٹ", "🎓 امتحان کے لیے نامزدگی", "🎓 امتحانات و نتائج"]:
    st.header("🎓 امتحانی تعلیمی نظام")
    if st.session_state.user_type == "teacher":
        st.subheader("طالب علم کو امتحان کے لیے بھیجیں")
        my_students = [f"{s[0]} ولد {s[1]}" for s in c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()]
        if my_students:
            sel_s = st.selectbox("طالب علم", my_students)
            para_no = st.number_input("پارہ نمبر", 1, 30)
            if st.button("امتحان کی درخواست بھیجیں"):
                sn, fn = sel_s.split(" ولد ")
                c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)", (sn, fn, para_no, str(date.today()), "پینڈنگ"))
                conn.commit(); st.success("درخواست بھیج دی گئی!")
        else: st.warning("کوئی طالب علم نہیں۔")
    else:
        tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات", "📜 امتحانی ریکارڈ (پرنٹ/ترمیم)"])
        with tab1:
            pending = c.execute("SELECT id, s_name, f_name, para_no FROM exams WHERE status='پینڈنگ'").fetchall()
            if not pending: st.info("کوئی پینڈنگ امتحان نہیں۔")
            for eid, sn, fn, pn in pending:
                with st.expander(f"📝 {sn} - پارہ {pn}"):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    q1 = c1.number_input("س1", 0, 20, key=f"q1_{eid}")
                    q2 = c2.number_input("س2", 0, 20, key=f"q2_{eid}")
                    q3 = c3.number_input("س3", 0, 20, key=f"q3_{eid}")
                    q4 = c4.number_input("س4", 0, 20, key=f"q4_{eid}")
                    q5 = c5.number_input("س5", 0, 20, key=f"q5_{eid}")
                    tot = q1+q2+q3+q4+q5
                    if st.button("نتیجہ محفوظ کریں", key=f"sv_{eid}"):
                        g = "ممتاز" if tot>=90 else "جید جداً" if tot>=80 else "جید" if tot>=70 else "مقبول" if tot>=60 else "فیل"
                        c.execute("UPDATE exams SET total=?, grade=?, status='مکمل', end_date=? WHERE id=?", (tot, g, str(date.today()), eid))
                        conn.commit(); st.rerun()
        with tab2:
            df_exams = pd.read_sql_query("SELECT id as 'ID', s_name as 'نام', f_name as 'ولدیت', para_no as 'پارہ', total as 'نمبر', grade as 'گریڈ', end_date as 'تاریخ' FROM exams WHERE status='مکمل'", conn)
            st.dataframe(df_exams, use_container_width=True)
            if not df_exams.empty: st.markdown(generate_html_print(df_exams.drop(columns=['ID']), "امتحانی ریکارڈ"), unsafe_allow_html=True)
            
            st.divider()
            del_ex = st.number_input("حذف کرنے کے لیے امتحان کی ID درج کریں", min_value=0, step=1, key="del_ex")
            if st.button("امتحان حذف کریں"): execute_delete("exams", del_ex)

# ==========================================
# ماڈیول: ماہانہ رزلٹ کارڈ
# ==========================================
elif m == "📜 ماہانہ رزلٹ کارڈ":
    st.header("📜 ماہانہ رزلٹ کارڈ (Generate & Print)")
    m_year = st.selectbox("سال", [2024, 2025, 2026])
    m_month = st.selectbox("مہینہ", range(1, 13))
    t_list = ["تمام"] + [row[0] for row in c.execute("SELECT name FROM teachers WHERE name != 'admin'").fetchall()]
    sel_t = st.selectbox("استاد", t_list)
    
    if st.button("رپورٹ تیار کریں"):
        start_dt = f"{m_year}-{m_month:02d}-01"
        end_dt = f"{m_year}-{m_month:02d}-31"
        q = "SELECT s_name as 'نام', COUNT(*) as 'کل دن', SUM(CASE WHEN attendance='حاضر' THEN 1 ELSE 0 END) as 'حاضریاں', SUM(CASE WHEN attendance!='حاضر' THEN 1 ELSE 0 END) as 'چھٹیاں', SUM(sq_m) as 'کل سبقی غلطیاں', SUM(m_m) as 'کل منزل غلطیاں' FROM hifz_records WHERE r_date BETWEEN ? AND ?"
        p = [start_dt, end_dt]
        if sel_t != "تمام": q += " AND t_name=?"; p.append(sel_t)
        q += " GROUP BY s_name"
        
        df_month = pd.read_sql_query(q, conn, params=p)
        if df_month.empty: st.warning("اس مہینے کا کوئی ریکارڈ نہیں۔")
        else:
            st.dataframe(df_month, use_container_width=True)
            st.markdown(generate_html_print(df_month, f"ماہانہ رزلٹ کارڈ ({m_year}-{m_month:02d})"), unsafe_allow_html=True)

# ==========================================
# ماڈیول: اساتذہ کا ریکارڈ (میری حاضری)
# ==========================================
elif m == "🕒 میری حاضری":
    st.header("🕒 میری یومیہ حاضری")
    st.markdown("<p style='color: #008CBA; font-weight: bold;'>اپنی آج کی حاضری کا بروقت اندراج یقینی بنائیں۔</p>", unsafe_allow_html=True)
    
    with st.form("attendance_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        m_date = c1.date_input("حاضری کی تاریخ", date.today())
        m_time = c2.time_input("آمد کا وقت", get_pkt_time().time())
        
        if st.form_submit_button("✅ حاضری درج کریں"):
            sys_t = get_pkt_time().strftime("%Y-%m-%d %H:%M:%S")
            
            # چیک کریں کہ کیا حاضری پہلے ہی لگ چکی ہے؟
            chk = c.execute("SELECT 1 FROM t_attendance WHERE t_name=? AND manual_date=?", (st.session_state.username, str(m_date))).fetchone()
            
            if chk: 
                st.error(f"🛑 آپ کی {m_date} کی حاضری پہلے ہی لگ چکی ہے۔ ایک دن میں دو بار حاضری نہیں لگائی جا سکتی۔")
            else:
                try:
                    c.execute("""
                        INSERT INTO t_attendance (t_name, manual_date, manual_time, system_timestamp) 
                        VALUES (?, ?, ?, ?)
                    """, (st.session_state.username, str(m_date), str(m_time), sys_t))
                    conn.commit()
                    st.success("✅ آپ کی حاضری کامیابی سے درج ہو گئی ہے!")
                except sqlite3.OperationalError as e:
                    st.error("❌ سسٹم ایرر: ڈیٹا بیس میں کالمز کی تبدیلی کا مسئلہ ہے۔")
                    st.info("💡 مہربانی فرما کر ایپ کے فولڈر میں موجود 'jamia_millia_final.db' فائل کو حذف (Delete) کر دیں، تاکہ سسٹم نیا اور درست ٹیبل خود بخود بنا لے۔")

# ==========================================
# ماڈیول: مہتمم پینل (رخصت)
# ==========================================
elif m == "📩 درخواستِ رخصت":
    st.header("📩 چھٹی کی درخواست بھیجیں")
    with st.form("leave"):
        l_type = st.selectbox("نوعیت", ["بیماری", "ضروری کام", "دیگر"])
        days = st.number_input("کتنے دن؟", 1, 30)
        rsn = st.text_area("تفصیل")
        if st.form_submit_button("ارسال کریں"):
            c.execute("INSERT INTO leave_requests (t_name, l_type, days, reason, start_date, status) VALUES (?,?,?,?,?,?)", (st.session_state.username, l_type, days, rsn, str(date.today()), "پینڈنگ"))
            conn.commit(); st.success("درخواست بھیج دی گئی!")
            
elif m == "🏛️ مہتمم پینل (رخصت)":
    st.header("🏛️ مہتمم پینل - درخواستِ رخصت")
    reqs = c.execute("SELECT id, t_name, l_type, days, reason, start_date FROM leave_requests WHERE status='پینڈنگ'").fetchall()
    if not reqs: st.info("کوئی نئی درخواست نہیں۔")
    for rid, tn, lt, d, rsn, sd in reqs:
        with st.expander(f"درخواست: {tn} ({lt} - {d} دن)"):
            st.write(f"**تفصیل:** {rsn}")
            st.write(f"**تاریخِ آغاز:** {sd}")
            c1, c2 = st.columns(2)
            if c1.button("✅ منظور کریں", key=f"app_{rid}"):
                c.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (rid,))
                conn.commit(); st.rerun()
            if c2.button("❌ مسترد کریں", key=f"rej_{rid}"):
                c.execute("UPDATE leave_requests SET status='مسترد' WHERE id=?", (rid,))
                conn.commit(); st.rerun()
    
    st.divider()
    st.subheader("سابقہ رخصت کا ریکارڈ")
    df_lv = pd.read_sql_query("SELECT t_name as 'استاد', l_type as 'نوعیت', days as 'دن', start_date as 'تاریخ', status as 'سٹیٹس' FROM leave_requests WHERE status!='پینڈنگ'", conn)
    st.dataframe(df_lv, use_container_width=True)
    if not df_lv.empty: st.markdown(generate_html_print(df_lv, "اساتذہ کی رخصت کا ریکارڈ"), unsafe_allow_html=True)

conn.close()

