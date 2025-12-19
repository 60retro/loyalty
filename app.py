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

# --- เชื่อมต่อ Google Sheet ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # โหลด Key จาก Secrets (Cloud) หรือไฟล์ JSON (Local)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        except:
            st.error("ไม่พบไฟล์ Key หรือ Secrets")
            st.stop()
            
    client = gspread.authorize(creds)
    return client

try:
    client = init_connection()
    sheet = client.open(SHEET_NAME).sheet1
except Exception as e:
    st.error(f"❌ เชื่อมต่อ Google Sheet ไม่ได้: {e}")
    st.stop()

# ================= ตรวจสอบโหมดการทำงาน =================
query_params = st.query_params
points_param = query_params.get("points", None)
table_param = query_params.get("table", "-") # รับค่าเบอร์โต๊ะจากลิงก์ (ถ้าไม่มีให้เป็น -)

# -------------------------------------------
# 🟢 MODE 1: ลูกค้า (Customer View)
# -------------------------------------------
if points_param:
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f6; }
        h1 { color: #4CAF50; text-align: center; }
        </style>
        """, unsafe_allow_html=True)

    st.markdown("<h1>🍃 Nami Member</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.write("---")
        # แสดงข้อมูลให้ลูกค้าเห็น (คะแนน และ โต๊ะ)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("คะแนนที่ได้รับ", f"{points_param} แต้ม")
        with col2:
            st.metric("โต๊ะที่", f"{table_param}")

        with st.form("customer_form"):
            phone = st.text_input("📱 เบอร์โทรศัพท์สมาชิก", placeholder="กรอกเบอร์โทรศัพท์ 10 หลัก", max_chars=10)
            
            submitted = st.form_submit_button("สะสมแต้มทันที", use_container_width=True)
            
            if submitted:
                if len(phone) < 9:
                    st.warning("กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง")
                else:
                    try:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        # บันทึกลง Sheet: Timestamp, Table, Phone, Points, Status
                        # (ต้องตรงกับลำดับคอลัมน์ใน Sheet)
                        sheet.append_row([timestamp, table_param, phone, points_param, "รอตรวจสอบ"])
                        
                        st.balloons()
                        st.success("✅ บันทึกเรียบร้อย! ขอบคุณที่ใช้บริการครับ")
                        time.sleep(3)
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

# -------------------------------------------
# 🔵 MODE 2: ร้านค้า (Admin Dashboard)
# -------------------------------------------
else:
    st.title("🛡️ Nami Manager Dashboard")
    
    with st.sidebar:
        st.header("Login")
        password = st.text_input("รหัสผ่านร้าน", type="password")
        st.markdown("---")
        base_url = st.text_input("URL ของเว็บนี้", value="http://loyalty.streamlit.app/")

    if password != "34573457":
        st.warning("กรุณาใส่รหัสผ่านร้านที่ Sidebar ด้านซ้าย")
        st.stop()

    tab1, tab2 = st.tabs(["🖨️ สร้าง QR Code", "📋 ตรวจสอบยอด"])

    with tab1:
        st.subheader("ออกแต้มให้ลูกค้า")
        col1, col2 = st.columns(2)
        with col1:
            pts = st.number_input("จำนวนคะแนน", min_value=1, value=100, step=10)
        with col2:
            # เพิ่มช่องกรอกเบอร์โต๊ะ
            tbl = st.text_input("เบอร์โต๊ะ", value="", placeholder="เช่น 5, A1")

        if st.button("Generate QR", use_container_width=True):
            if not tbl:
                st.error("กรุณาระบุเบอร์โต๊ะ")
            else:
                clean_url = base_url.rstrip("/")
                # แนบทั้ง points และ table ไปในลิงก์
                target_url = f"{clean_url}?points={pts}&table={tbl}"
                
                qr = qrcode.QRCode(box_size=10, border=2)
                qr.add_data(target_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                st.image(img.get_image(), width=250)
                st.success(f"โต๊ะ: {tbl} | คะแนน: {pts}")

    with tab2:
        st.subheader("รายการรอยืนยัน")
        if st.button("🔄 รีเฟรชข้อมูล"):
            st.rerun()
            
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
        except:
            df = pd.DataFrame()
            
        if not df.empty:
            # --- แก้ไขเรื่องเลข 0 หาย (Force String format) ---
            if 'Phone' in df.columns:
                # แปลงเป็น String แล้วเติม 0 ข้างหน้าถ้ามันขาดไป (และต้องเป็นตัวเลขล้วน)
                df['Phone'] = df['Phone'].astype(str).apply(
                    lambda x: x.zfill(10) if x.isdigit() and len(x) < 10 else x
                )

            # ตรวจสอบว่ามีคอลัมน์ครบไหม (ถ้าเพิ่งเพิ่ม Table มาอาจจะยังไม่ error แต่ต้องดักไว้)
            required_cols = ['Status', 'Phone', 'Points', 'Table', 'Timestamp']
            if all(col in df.columns for col in required_cols):
                
                df['Status'] = df['Status'].astype(str)
                pending = df[df['Status'].str.upper() != 'TRUE'].copy()
                
                if not pending.empty:
                    pending.insert(0, "Approved", False)
                    edited = st.data_editor(
                        pending,
                        column_config={
                            "Approved": st.column_config.CheckboxColumn("เลือก", default=False),
                            "Timestamp": "เวลา",
                            "Table": "โต๊ะ",       # แสดงเบอร์โต๊ะ
                            "Phone": "เบอร์โทร",
                            "Points": "แต้ม",
                            "Status": "สถานะ"
                        },
                        disabled=["Timestamp", "Table", "Phone", "Points", "Status"],
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    if st.button("✅ บันทึกรายการที่เลือก"):
                        to_process = edited[edited['Approved'] == True]
                        count = 0
                        for index, row in to_process.iterrows():
                            # หา row ใน df หลัก (ใช้ Timestamp เทียบ)
                            real_idx = df.index[df['Timestamp'] == row['Timestamp']].tolist()
                            if real_idx:
                                row_num = real_idx[0] + 2
                                # หาตำแหน่งคอลัมน์ Status (เปลี่ยนตามโครงสร้างจริง)
                                col_idx = df.columns.get_loc("Status") + 1
                                sheet.update_cell(row_num, col_idx, "TRUE")
                                count += 1
                        
                        st.success(f"บันทึกแล้ว {count} รายการ")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info("ไม่มียอดค้าง ตรวจสอบครบแล้ว")
            else:
                st.warning(f"หัวตารางใน Google Sheet ไม่ครบ หรือชื่อไม่ตรง (ต้องมี: {required_cols})")

