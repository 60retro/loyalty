import streamlit as st
import qrcode
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time
import json

# =================ตั้งค่าระบบ=================
# ชื่อ Google Sheet (ต้องแชร์ให้ Service Email แล้ว)
SHEET_NAME = 'Loyalty_Points_Data'

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Nami Loyalty", page_icon="☕", layout="centered")

# --- ฟังก์ชันเชื่อมต่อ Google Sheet (รองรับทั้ง Local และ Cloud) ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # วิธีที่ 1: พยายามโหลดจาก Streamlit Secrets (สำหรับตอนเอาขึ้น Cloud)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    # วิธีที่ 2: โหลดจากไฟล์ JSON (สำหรับรันในเครื่องตัวเอง)
    else:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        except:
            st.error("ไม่พบไฟล์ Key (service_account.json) หรือการตั้งค่า Secrets")
            st.stop()
            
    client = gspread.authorize(creds)
    return client

# เชื่อมต่อ
try:
    client = init_connection()
    sheet = client.open(SHEET_NAME).sheet1
except Exception as e:
    st.error(f"❌ เชื่อมต่อ Google Sheet ไม่ได้: {e}")
    st.stop()

# ================= ตรวจสอบโหมดการทำงาน =================
# เช็คว่าใน URL มี parameter ชื่อ 'points' หรือไม่?
query_params = st.query_params
points_param = query_params.get("points", None)

# -------------------------------------------
# 🟢 MODE 1: ลูกค้า (Customer View)
# ทำงานเมื่อ URL มี ?points=XX
# -------------------------------------------
if points_param:
    # ตกแต่งหน้าจอลูกค้าให้สวยงาม (ใส่โลโก้ร้านได้ตรงนี้)
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f6; }
        .main-card { padding: 20px; border-radius: 10px; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #4CAF50; text-align: center; }
        </style>
        """, unsafe_allow_html=True)

    st.markdown("<h1>🍃 Nami Member</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.write("---")
        st.info(f"🎉 คุณได้รับคะแนนสะสม: **{points_param} แต้ม**")
        
        with st.form("customer_form"):
            phone = st.text_input("📱 เบอร์โทรศัพท์สมาชิก", placeholder="กรอกเบอร์โทรศัพท์ 10 หลัก", max_chars=10)
            
            # ปุ่มส่งข้อมูล
            submitted = st.form_submit_button("สะสมแต้มทันที", use_container_width=True)
            
            if submitted:
                if len(phone) < 9:
                    st.warning("กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง")
                else:
                    try:
                        # บันทึกลง Sheet: Timestamp, Phone, Points, Status
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        sheet.append_row([timestamp, phone, points_param, "รอตรวจสอบ"])
                        st.balloons()
                        st.success("✅ บันทึกคะแนนเรียบร้อยแล้ว! ขอบคุณที่ใช้บริการครับ")
                        time.sleep(3)
                        # เคลียร์หน้าจอ (หรือ Redirect)
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

# -------------------------------------------
# 🔵 MODE 2: ร้านค้า (Admin Dashboard)
# ทำงานเมื่อไม่มี URL param (เข้าหน้าเว็บปกติ)
# -------------------------------------------
else:
    st.title("🛡️ Nami Manager Dashboard")
    
    # Sidebar สำหรับใส่ Password กันคนนอกเข้า (แบบง่าย)
    with st.sidebar:
        st.header("Login")
        password = st.text_input("รหัสผ่านร้าน", type="password")
        
        # --- ช่องใส่ URL ของ App (สำคัญมาก!) ---
        st.markdown("---")
        st.markdown("**ตั้งค่าลิงก์:**")
        base_url = st.text_input("URL ของเว็บนี้ (เมื่อขึ้น Cloud)", value="http://loyalty.streamlit.app/")
        st.caption("เช่น https://nami-loyalty.streamlit.app")

    if password != "34573457": # <--- แก้รหัสผ่านตรงนี้
        st.warning("กรุณาใส่รหัสผ่านร้านที่ Sidebar ด้านซ้าย")
        st.stop()

    # แบ่งหน้าจอ Admin
    tab1, tab2 = st.tabs(["🖨️ สร้าง QR Code", "📋 ตรวจสอบยอด"])

    with tab1:
        st.subheader("สร้าง QR ให้ลูกค้า")
        col1, col2 = st.columns([1, 2])
        with col1:
            pts = st.number_input("คะแนนที่จะให้", min_value=1, value=100, step=10)
            if st.button("Generate QR", use_container_width=True):
                # สร้าง Link ที่ชี้กลับมาหาตัวเอง พร้อมแนบ points
                # ถ้า base_url ท้ายมี / ให้ลบออก
                clean_url = base_url.rstrip("/")
                target_url = f"{clean_url}?points={pts}"
                
                qr = qrcode.QRCode(box_size=10, border=2)
                qr.add_data(target_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                st.image(img.get_image(), width=300)
                st.success(f"Link: {target_url}")
                st.caption("ให้ลูกค้าสแกนรูปนี้ เพื่อเข้าหน้าสะสมแต้ม")

    with tab2:
        st.subheader("รายการรอยืนยัน")
        if st.button("🔄 รีเฟรชข้อมูล"):
            st.rerun()
            
        # (ส่วนแสดงตาราง เหมือนโค้ดเดิม)
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
        except:
            df = pd.DataFrame()
            
        if not df.empty and 'Status' in df.columns:
            # แปลงให้ Status เป็น string กัน error
            df['Status'] = df['Status'].astype(str)
            
            # กรองเอาเฉพาะที่ยังไม่ TRUE
            pending = df[df['Status'].str.upper() != 'TRUE'].copy()
            
            if not pending.empty:
                pending.insert(0, "Approved", False)
                edited = st.data_editor(
                    pending,
                    column_config={
                        "Approved": st.column_config.CheckboxColumn("เลือก", default=False),
                        "Timestamp": "เวลา",
                        "Phone": "เบอร์โทร",
                        "Points": "แต้ม",
                        "Status": "สถานะ"
                    },
                    disabled=["Timestamp", "Phone", "Points", "Status"],
                    hide_index=True,
                    use_container_width=True
                )
                
                if st.button("✅ บันทึกรายการที่เลือก"):
                    to_process = edited[edited['Approved'] == True]
                    count = 0
                    for index, row in to_process.iterrows():
                        # ค้นหา row ใน df หลักเพื่อหา index ที่แท้จริง
                        # (วิธีง่าย: ใช้ timestamp matching)
                        real_idx = df.index[df['Timestamp'] == row['Timestamp']].tolist()
                        if real_idx:
                            row_num = real_idx[0] + 2
                            # หา Column Status
                            col_idx = df.columns.get_loc("Status") + 1
                            sheet.update_cell(row_num, col_idx, "TRUE")
                            count += 1
                    
                    st.success(f"บันทึกแล้ว {count} รายการ")
                    time.sleep(1)
                    st.rerun()
            else:

                st.info("ไม่มียอดค้าง ตรวจสอบครบแล้ว")


