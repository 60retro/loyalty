import streamlit as st
import qrcode
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# =================ตั้งค่าระบบ=================
SHEET_NAME = 'Loyalty_Points_Data'

st.set_page_config(page_title="Nami Loyalty", page_icon="☕", layout="centered")

# --- ฟังก์ชันเชื่อมต่อ Google Sheet ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        except:
            st.error("❌ ไม่พบไฟล์ Key (service_account.json) หรือ Secrets")
            st.stop()
            
    client = gspread.authorize(creds)
    return client

try:
    client = init_connection()
    sheet = client.open(SHEET_NAME).sheet1
except Exception as e:
    st.error(f"❌ เชื่อมต่อ Google Sheet ไม่ได้: {e}")
    st.stop()

# ================= ส่วนการทำงานหลัก =================

# รับค่าจาก URL
query_params = st.query_params
points_param = query_params.get("points", None)
table_param = query_params.get("table", "-")

# --- 🟢 โหมดลูกค้า (Customer) ---
if points_param:
    # --- CSS แก้ไขใหม่: พื้นขาว ตัวหนังสือดำหนา ---
    st.markdown("""
        <style>
        /* บังคับพื้นหลังสีขาว */
        .stApp {
            background-color: #FFFFFF !important;
        }
        
        /* บังคับตัวหนังสือทุกอย่างเป็นสีดำและตัวหนา */
        h1, h2, h3, p, div, span, label, .stMarkdown {
            color: #000000 !important;
            font-family: 'Sarabun', sans-serif; /* ถ้าเครื่องมีฟอนต์นี้ */
        }
        
        /* หัวข้อ Nami Member */
        h1 {
            color: #000000 !important;
            font-weight: 900 !important; /* หนามาก */
            text-align: center;
            text-transform: uppercase;
        }
        
        /* กล่องข้อความ (Alert/Info) ให้ตัวหนังสือชัด */
        .stAlert {
            background-color: #f0f2f6 !important;
            color: #000000 !important;
            border: 1px solid #ddd;
            font-weight: bold !important;
        }
        
        /* ช่องกรอกข้อมูล (Input) */
        .stTextInput input {
            color: #000000 !important;
            background-color: #FFFFFF !important;
            border: 2px solid #333 !important; /* ขอบดำให้เห็นชัด */
            font-weight: bold !important;
        }
        .stTextInput label {
            font-size: 18px !important;
            font-weight: 800 !important;
            color: #000000 !important;
        }
        
        /* ปุ่มกด */
        .stButton button {
            font-weight: bold !important;
            font-size: 18px !important;
            background-color: #000000 !important; /* ปุ่มสีดำ */
            color: #FFFFFF !important; /* ตัวหนังสือขาว */
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown("<h1>🍃 Nami Member</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.write("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📍 โต๊ะที่: {table_param}")
        with col2:
            st.info(f"🎁 คะแนน: {points_param} แต้ม")
        
        with st.form("customer_form"):
            st.markdown("**กรุณากรอกเบอร์โทรศัพท์เพื่อสะสมแต้ม**")
            phone = st.text_input("เบอร์โทรศัพท์", placeholder="08xxxxxxxx", max_chars=10)
            
            submitted = st.form_submit_button("ยืนยันการสะสมแต้ม", use_container_width=True)
            
            if submitted:
                if len(phone) < 9 or not phone.isdigit():
                    st.warning("❌ กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง (ตัวเลขเท่านั้น)")
                else:
                    try:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        sheet.append_row([timestamp, table_param, phone, points_param, "รอตรวจสอบ"])
                        
                        st.balloons()
                        st.success("✅ บันทึกคะแนนเรียบร้อยแล้ว!")
                        time.sleep(3)
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 🔵 โหมดร้านค้า (Admin) ---
else:
    st.title("🛡️ Nami Manager Dashboard")
    
    with st.sidebar:
        st.header("Login")
        password = st.text_input("รหัสผ่านร้าน", type="password")
        st.markdown("---")
        # ใส่ Link จริงของคุณตรงนี้
        base_url = st.text_input("URL ของเว็บนี้", value="https://loyalty.streamlit.app")

    if password != "3457":
        st.warning("กรุณาใส่รหัสผ่านร้าน")
        st.stop()

    tab1, tab2 = st.tabs(["🖨️ สร้าง QR Code", "📋 ตรวจสอบยอด"])

    with tab1:
        st.subheader("สร้าง QR ให้ลูกค้าสแกน")
        col_a, col_b = st.columns(2)
        
        with col_a:
            pts = st.number_input("คะแนน (Points)", min_value=1, value=100, step=10)
        with col_b:
            tbl = st.text_input("เลขโต๊ะ (Table No.)", value="10")

        if st.button("สร้าง QR Code", use_container_width=True):
            clean_url = base_url.rstrip("/")
            target_url = f"{clean_url}?points={pts}&table={tbl}"
            
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            st.image(img.get_image(), width=300)
            st.success(f"QR โต๊ะ {tbl} ({pts} แต้ม) เสร็จแล้ว")

    with tab2:
        st.subheader("รายการรอยืนยัน")
        if st.button("🔄 รีเฟรชข้อมูล (ล้าง Cache)"):
            st.cache_resource.clear()
            st.rerun()

        try:
            raw_data = sheet.get_all_values()
            
            if len(raw_data) > 1:
                headers = raw_data[0]
                rows = raw_data[1:]
                df = pd.DataFrame(rows, columns=headers)
                
                # Trim spaces
                df.columns = [c.strip() for c in df.columns]
                
                status_col = next((c for c in df.columns if c.lower() == 'status'), None)
                
                if status_col:
                    pending = df[df[status_col].astype(str).str.upper() != 'TRUE'].copy()
                    
                    if not pending.empty:
                        pending.insert(0, "Approved", False)
                        
                        edited = st.data_editor(
                            pending,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Approved": st.column_config.CheckboxColumn("เลือก", default=False)
                            }
                        )
                        
                        if st.button("✅ บันทึกรายการที่เลือก"):
                            to_process = edited[edited['Approved'] == True]
                            count = 0
                            for index, row in to_process.iterrows():
                                ts_val = row.get('Timestamp')
                                try:
                                    cell = sheet.find(str(ts_val), in_column=1)
                                    if cell:
                                        # อัปเดต Column 5 (Status)
                                        sheet.update_cell(cell.row, 5, "TRUE")
                                        count += 1
                                except:
                                    pass
                                    
                            st.success(f"บันทึกแล้ว {count} รายการ")
                            time.sleep(1)
                            st.cache_resource.clear()
                            st.rerun()
                    else:
                        st.info("✅ ไม่มียอดค้าง ตรวจสอบครบแล้ว")
                else:
                    st.error(f"ไม่พบหัวตารางชื่อ 'Status' (พบแต่: {df.columns.tolist()})")
            else:
                st.warning("ยังไม่มีข้อมูลใน Google Sheet")

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอ่านข้อมูล: {e}")
