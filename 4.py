import streamlit as st
from PIL import Image
from pyzbar.pyzbar import decode
import sqlite3
import pandas as pd
import base64
import qrcode
import io
import cv2
import numpy as np

# SQLite setup
conn = sqlite3.connect('scanprods.db')
c = conn.cursor()

# Function to generate QR code with specified size and product ID
def generate_qr_code(product_id, product_name, barcode, expiry_date, status):
    qr_data = f"PRODAPP: {product_id}\nProduct Name: {product_name}\nBarcode: {barcode}\nExpiry Date: {expiry_date}\nStatus: {status}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    return qr_img

# Function to create the products table if it doesn't exist
def create_table():
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            barcode TEXT NOT NULL UNIQUE,
            expiry_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('AUTHORIZED', 'COUNTERFEIT'))
        )
    ''')
    conn.commit()

# Function to save product information to database
def save_product_info_to_db(product_name, barcode, expiry_date, status):
    try:
        c.execute('''
            INSERT INTO products (product_name, barcode, expiry_date, status) 
            VALUES (?, ?, ?, ?)
        ''', (product_name, barcode, expiry_date, status))
        conn.commit()
        
        product_id = c.lastrowid
        qr_img = generate_qr_code(product_id, product_name, barcode, expiry_date, status)
        
        img_byte_arr = io.BytesIO()
        qr_img.save(img_byte_arr, format='PNG')
        qr_image_bytes = img_byte_arr.getvalue()
        
        return qr_image_bytes
    except sqlite3.IntegrityError as e:
        conn.rollback()
        st.error(f'Error: {e}')
        return None

# Function to scan QR code from image
def scan_qr_code_from_image(img):
    img_gray = img.convert('L')
    decoded_objects = decode(img_gray)
    if decoded_objects:
        qr_data = decoded_objects[0].data.decode('utf-8')
        return qr_data
    else:
        return None

# Function to fetch product details from database using product ID
def fetch_product_details(product_id):
    c.execute('SELECT product_name, barcode, expiry_date, status FROM products WHERE id = ?', (product_id,))
    product = c.fetchone()
    if product:
        return product
    else:
        return None

# Function to read products from Excel and save them to the database
def read_products_from_excel(file):
    try:
        df = pd.read_excel(file)
        qr_images = []
        for index, row in df.iterrows():
            product_name = row['Product Name']
            barcode = row['Barcode']
            expiry_date = row['Expiry Date'].strftime('%Y-%m-%d')
            status = row['Status']
            qr_image_bytes = save_product_info_to_db(product_name, barcode, expiry_date, status)
            if qr_image_bytes is not None:
                qr_images.append(qr_image_bytes)
        return qr_images, None
    except Exception as e:
        return None, e

# Function to capture video from the camera and scan for QR codes
def scan_qr_code_from_camera():
    cap = cv2.VideoCapture(0)
    qr_data = None

    stframe = st.empty()
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        decoded_objects = decode(frame)
        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')
            pts = obj.polygon
            if len(pts) > 4:
                hull = cv2.convexHull(np.array([pts], dtype=np.float32))
                hull = list(map(tuple, np.squeeze(hull)))
            else:
                hull = pts
            n = len(hull)
            for j in range(0, n):
                cv2.line(frame, hull[j], hull[(j + 1) % n], (0, 255, 0), 3)
        
        stframe.image(frame, channels="BGR")
        
        if qr_data:
            break
    
    cap.release()
    return qr_data

# Main function to run the Streamlit app
# Function to create the coupons table if it doesn't exist
# Function to create the coupons table if it doesn't exist
def create_coupon_table():
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_data TEXT NOT NULL UNIQUE,
            coupon_code TEXT NOT NULL
        )
    ''')
    conn.commit()

# Function to generate a coupon code
# Function to create the coupons table if it doesn't exist
def create_coupon_table():
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_data TEXT NOT NULL UNIQUE,
            coupon_code TEXT NOT NULL
        )
    ''')
    conn.commit()

# Function to generate a coupon code
def generate_coupon_code():
    return f'COUPON-{np.random.randint(100000, 999999)}'

# Function to save coupon code to database
def save_coupon_to_db(qr_data, coupon_code):
    try:
        c.execute('''
            INSERT INTO coupons (qr_data, coupon_code) 
            VALUES (?, ?)
        ''', (qr_data, coupon_code))
        conn.commit()
        return coupon_code
    except sqlite3.IntegrityError as e:
        conn.rollback()
        st.error(f'Error: {e}')
        return None

# Function to fetch coupon code from database
def fetch_coupon_code(qr_data):
    c.execute('SELECT coupon_code FROM coupons WHERE qr_data = ?', (qr_data,))
    coupon = c.fetchone()
    if coupon:
        return coupon[0]
    else:
        return None

# Main function to run the Streamlit app
def main():
    st.title('Product Track App')
    menu = ['Add Product', 'View Products', 'Scan QR Code', 'Bulk Upload', 'Redeem Coupon']
    choice = st.sidebar.selectbox('Menu', menu)

    if choice == 'Add Product':
        st.subheader('Add a New Product')
        product_name = st.text_input('Product Name')
        barcode = st.text_input('Barcode')
        expiry_date = st.date_input('Expiry Date')
        status = st.selectbox('Status', ('AUTHORIZED', 'COUNTERFEIT'))

        if st.button('Save Product'):
            save_product_info_to_db(product_name, barcode, expiry_date, status)

    elif choice == 'View Products':
        st.subheader('View Products')
        c.execute('SELECT id, product_name, barcode, expiry_date, status FROM products ORDER BY id ASC')
        products = c.fetchall()

        if products:
            product_data = []
            for product in products:
                product_id, product_name, barcode, expiry_date, status = product
                qr_img = generate_qr_code(product_id, product_name, barcode, expiry_date, status)
                img_byte_arr = io.BytesIO()
                qr_img.save(img_byte_arr, format='PNG')
                qr_image_bytes = img_byte_arr.getvalue()
                qr_image_base64 = base64.b64encode(qr_image_bytes).decode('utf-8')
                qr_image_html = f'<img src="data:image/png;base64,{qr_image_base64}" alt="QR Code" width="100">'
                
                product_data.append((product_id, product_name, barcode, expiry_date, status, qr_image_html))
            
            df = pd.DataFrame(product_data, columns=['Product ID', 'Product Name', 'Barcode', 'Expiry Date', 'Status', 'QR Code'])
            st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        else:
            st.write("No products found.")

    elif choice == 'Scan QR Code':
        st.subheader('Shoot & Scan QR Code')
        uploaded_file = st.file_uploader("Upload an image...", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            img = Image.open(uploaded_file)
            qr_data = scan_qr_code_from_image(img)
            if qr_data:
                if qr_data.startswith('PRODAPP:'):
                    try:
                        product_id = int(qr_data.split('\n')[0].split(': ')[1])
                        product_details = fetch_product_details(product_id)
                        if product_details:
                            product_name, barcode, expiry_date, status = product_details
                            st.success(f"Decoded QR Code Data:")
                            st.write(f"Product Name: {product_name}")
                            st.write(f"Barcode: {barcode}")
                            st.write(f"Expiry Date: {expiry_date}")
                            st.write(f"Status: {status}")

                            if status == 'AUTHORIZED':
                                st.success('Product is Authorized')
                                if st.button('the world can do with a smart shopper like you!'):
                                    st.write('Keep being a good citizen')
                            else:
                                st.warning('Product is Counterfeit')
                                if st.button('Report'):
                                    st.write('Report submitted!')
                        else:
                            st.warning("Product details not found.")
                    except Exception as e:
                        st.warning("Error decoding QR code data.")
                        st.warning(f"Details: {e}")
                else:
                    st.warning("This QR code was not generated by PRODTRACK app.")
            else:
                st.warning("No QR code found in the uploaded image.")

        st.subheader('Or Scan with Camera')
        if st.button('Start Camera Scan'):
            qr_data = scan_qr_code_from_camera()
            if qr_data:
                st.write(f"QR Code Data: {qr_data}")
                if qr_data.startswith('PRODAPP:'):
                    try:
                        product_id = int(qr_data.split('\n')[0].split(': ')[1])
                        product_details = fetch_product_details(product_id)
                        if product_details:
                            product_name, barcode, expiry_date, status = product_details
                            st.success(f"Decoded QR Code Data:")
                            st.write(f"Product Name: {product_name}")
                            st.write(f"Barcode: {barcode}")
                            st.write(f"Expiry Date: {expiry_date}")
                            st.write(f"Status: {status}")

                            if status == 'AUTHORIZED':
                                st.success('Product is Authorized')
                                if st.button('the world can do with a smart shopper like you!'):
                                    st.write('Keep being a good citizen')
                            else:
                                st.warning('Product is Counterfeit')
                                if st.button('Report'):
                                    st.write('Report submitted!')
                        else:
                            st.warning("Product details not found.")
                    except Exception as e:
                        st.warning("Error decoding QR code data.")
                        st.warning(f"Details: {e}")
                else:
                    st.warning("This QR code was not generated by PRODTRACK app.")
            else:
                st.warning("No QR code found in the camera feed.")

    elif choice == 'Bulk Upload':
        st.subheader('Bulk Upload Products')
        uploaded_file = st.file_uploader("Upload an Excel file...", type=["xls", "xlsx"])

        if uploaded_file is not None:
            qr_images, error = read_products_from_excel(uploaded_file)
            if error:
                st.error(f"Error: {error}")
            else:
                st.success('Products uploaded and QR codes generated successfully!')
                for qr_image_bytes in qr_images:
                    st.image(qr_image_bytes, caption='Generated QR Code', use_column_width=True)

    elif choice == 'Redeem Coupon':
        st.subheader('Redeem Coupon Code')
        st.text('Upload a QR code image or use the camera to scan a QR code.')
        
        uploaded_file = st.file_uploader("Upload a QR code image...", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            img = Image.open(uploaded_file)
            qr_data = scan_qr_code_from_image(img)
            if qr_data:
                if qr_data.startswith('PRODAPP:'):
                    coupon_code = fetch_coupon_code(qr_data)
                    if coupon_code:
                        st.success(f'Your Coupon Code: {coupon_code}')
                    else:
                        coupon_code = generate_coupon_code()
                        save_coupon_to_db(qr_data, coupon_code)
                        st.success(f'Your Coupon Code: {coupon_code}')
                else:
                    st.warning("This QR code was not generated by PRODTRACK app.")
            else:
                st.warning("No QR code found in the uploaded image.")
        
        st.subheader('Or Scan with Camera')
        if st.button('Start Camera Scan'):
            qr_data = scan_qr_code_from_camera()
            if qr_data:
                if qr_data.startswith('PRODAPP:'):
                    coupon_code = fetch_coupon_code(qr_data)
                    if coupon_code:
                        st.success(f'Your Coupon Code: {coupon_code}')
                    else:
                        coupon_code = generate_coupon_code()
                        save_coupon_to_db(qr_data, coupon_code)
                        st.success(f'Your Coupon Code: {coupon_code}')
                else:
                    st.warning("This QR code was not generated by PRODTRACK app.")
            else:
                st.warning("No QR code found in the camera feed.")

if __name__ == '__main__':
    create_table()
    create_coupon_table()
    main()
