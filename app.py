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
    # CSS ตกแต่ง
    st.markdown("""
        <style>
        .stApp { background-color: #FFFFFF !important; }
        h1, h2, h3, p, div, span, label, .stMarkdown, .stMarkdown p {
            color: #000000 !important; font-family: sans-serif;
        }
        div[data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border: 2px solid #000000 !important;
            border-radius: 5px !important;
        }
        input {
            color: #000000 !important; font-weight: bold !important; font-size: 18px !important;
        }
        label[data-testid="stWidgetLabel"] {
            color: #000000 !important; font-size: 20px !important; font-weight: 900 !important;
        }
        button[kind="secondaryFormSubmit"], button[data-testid="baseButton-secondary"] {
            background-color: #000000 !important; border: none !important;
            border-radius: 8px !important; width: 100% !important; padding: 15px 0px !important;
        }
        button[kind="secondaryFormSubmit"] *, button[data-testid="baseButton-secondary"] * {
            color: #FFFFFF !important; font-weight: 900 !important; font-size: 20px !important;
        }
        div[data-testid="stAlert"] {
            background-color: #E3F2FD !important; border: 1px solid #90CAF9 !important;
        }
        div[data-testid="stAlert"] p { color: #0D47A1 !important; }
        </style>
        """, unsafe_allow_html=True)

    st.markdown("<h1>🍃 Nami Member</h1>", unsafe_allow_html=True)
    st.write("---")

    # แสดงฟอร์ม
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📍 โต๊ะที่: {table_param}")
    with col2:
        st.info(f"🎁 คะแนน: {points_param} แต้ม")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.form("customer_form"):
        st.markdown("### 📱 กรุณากรอกเบอร์โทรศัพท์")
        phone = st.text_input("เบอร์โทรศัพท์", placeholder="เช่น 0812345678", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✅ ยืนยันการสะสมแต้ม", use_container_width=True)
        
        if submitted:
            if len(phone) < 9 or not phone.isdigit():
                st.error("❌ กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง (ตัวเลขเท่านั้น)")
            else:
                try:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([timestamp, table_param, phone, points_param, "รอตรวจสอบ"])
                    
                    st.balloons()
                    st.success("✅ บันทึกข้อมูลสำเร็จ!")
                    st.info("ขอบคุณที่ใช้บริการครับ")
                    
                    # --- แก้ปัญหาลูกค้า Refresh แล้วส่งซ้ำ ---
                    # ล้างค่า URL ทิ้งทันที (ทำให้ browser ลืมว่าเคยมี ?points=100)
                    st.query_params.clear()
                    
                    # หน่วงเวลา 3 วินาทีให้ลูกค้าอ่านข้อความ แล้วรีเฟรชหน้าจอ (จะเด้งไปหน้า Login)
                    time.sleep(3)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 🔵 โหมดร้านค้า (Admin) ---
else:
    st.title("🛡️ Nami Manager Dashboard")
    
    with st.sidebar:
        st.header("Login")
        password = st.text_input("รหัสผ่านร้าน", type="password")
        
        if password != "3457":
            st.warning("🔒 กรุณาใส่รหัสผ่าน")
            st.stop()
            
        st.markdown("---")
        menu = st.radio("เมนูหลัก", ["🖨️ สร้าง QR Code", "📋 ตรวจสอบยอด"], index=0)
        
        st.markdown("---")
        st.markdown("**ตั้งค่าลิงก์:**")
        base_url = st.text_input("URL ของเว็บนี้", value="https://loyalty.streamlit.app")

    # --- หน้า 1: สร้าง QR Code ---
    if menu == "🖨️ สร้าง QR Code":
        st.subheader("สร้าง QR ให้ลูกค้าสแกน")
        st.info("ระบุคะแนนและเลขโต๊ะ แล้วกดสร้าง QR")
        
        col_a, col_b = st.columns(2)
        with col_a:
            pts = st.number_input("คะแนน (Points)", min_value=0, value=0, step=10)
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

    # --- หน้า 2: ตรวจสอบยอด ---
    elif menu == "📋 ตรวจสอบยอด":
        st.subheader("รายการรอยืนยัน")
        
        if st.button("🔄 รีเฟรชข้อมูล"):
            st.cache_resource.clear()
            st.rerun()

        try:
            # ใช้ get_all_values ดึงข้อมูลดิบทั้งหมด
            raw_data = sheet.get_all_values()
            
            if len(raw_data) > 1:
                headers = raw_data[0]
                rows = raw_data[1:]
                
                # สร้าง DataFrame
                df = pd.DataFrame(rows, columns=headers)
                df.columns = [c.strip() for c in df.columns] # ลบช่องว่างหัวตาราง
                
                status_col_name = next((c for c in df.columns if c.lower() == 'status'), None)
                
                if status_col_name:
                    # หา Column Index ของ Status (เพื่อเอาไปใช้ update_cell)
                    # +1 เพราะ gspread นับคอลัมน์เริ่มที่ 1
                    status_col_index = df.columns.get_loc(status_col_name) + 1
                    
                    # กรองเอาเฉพาะที่ยังไม่ TRUE
                    # หมายเหตุ: index ของ pandas จะยังคงเป็นเลขแถวเดิมจาก raw_data (เริ่ม 0, 1, 2...)
                    pending = df[df[status_col_name].astype(str).str.upper() != 'TRUE'].copy()
                    
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
                            with st.spinner("กำลังบันทึกข้อมูล..."):
                                to_process = edited[edited['Approved'] == True]
                                count = 0
                                
                                # วนลูปอัปเดตข้อมูล
                                for index, row in to_process.iterrows():
                                    # --- แก้ไขจุดสำคัญ (ใช้ Index คำนวณแถวโดยตรง) ---
                                    # index คือลำดับใน list rows เดิม
                                    # แถวใน Sheet = (index) + 2 
                                    # (+1 เพราะ rows เริ่มหลัง header, +1 เพราะ sheet เริ่มนับ 1)
                                    row_number_in_sheet = index + 2
                                    
                                    try:
                                        # อัปเดตช่อง Status โดยตรง ไม่ต้องค้นหา
                                        sheet.update_cell(row_number_in_sheet, status_col_index, "TRUE")
                                        count += 1
                                    except Exception as e:
                                        st.error(f"Error saving row {row_number_in_sheet}: {e}")
                                
                                time.sleep(2) # รอ Sheet อัปเดต
                                st.success(f"บันทึกเรียบร้อย {count} รายการ")
                                st.cache_resource.clear()
                                st.rerun()
                    else:
                        st.info("✅ ไม่มียอดค้าง ตรวจสอบครบแล้ว")
                else:
                    st.error("ไม่พบหัวตารางชื่อ Status")
            else:
                st.warning("ยังไม่มีข้อมูล")

        except Exception as e:
            st.error(f"Error: {e}")
