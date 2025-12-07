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

## Setup and Running the Backend

### Prerequisites
- Python 3.8 or higher
- MongoDB (via Docker or local installation)

### Installation

1. Navigate to the backend directory:
```bash
cd BE
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the `BE` directory with the following:
```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=your_database_name
```

### Running MongoDB with Docker

Start MongoDB using docker-compose:
```bash
docker-compose up -d
```

### Running the Backend Server

From the `BE` directory, run:
```bash
python -m app.main
```

Or alternatively using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Health Check: http://localhost:8000/health_check
- API Documentation: http://localhost:8000/docs
- Alternative API Documentation: http://localhost:8000/redoc
