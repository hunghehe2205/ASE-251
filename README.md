# ASE-251


## Project Structure

```text
.
├── BE/
│   ├── app/
│   │   ├── config/
│   │   │   └── settings.py     # Quản lý biến môi trường
│   │   ├── database/
│   │   │   └── db_client.py    # Client kết nối MongoDB
│   │   ├── routers/            # API endpoints (controllers)
│   │   ├── schemas/            # Pydantic models (validate dữ liệu)
│   │   └── main.py             # Entry point khởi chạy server
│   └── requirements.txt
├── docker-compose.yml          # Cấu hình MongoDB local
├── FE/
└── README.md
```

## Vai trò các thư mục/file chính

- `app/schemas/`: Chứa các class Pydantic để validate request body từ frontend và định dạng response.

- `app/routers/`: Nơi khai báo API endpoint, nhận request, gọi database xử lý logic và trả kết quả. Ví dụ:
  - `auth.py`: API `/login` kiểm tra email/password trong DB.
  - `bookings.py`: API `/booking` (POST) lưu thông tin đặt phòng vào MongoDB.

- `app/main.py`: Entry point FastAPI; khởi tạo app, gắn router (auth, booking...), cấu hình CORS cho frontend, và khởi động các hook kết nối DB.
