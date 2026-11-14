# Splitbill

เว็บแอปตัวอย่างสำหรับบันทึกและแบ่งค่าใช้จ่ายในกลุ่ม รองรับการหารเท่ากัน (Equal split), ระบุส่วนแบ่งเอง (Exact split), ดูรายการและ net balances รวมถึง soft delete รายการ

## เทคโนโลยี

- Frontend: Next.js, React, TypeScript และ Tailwind CSS
- Backend: FastAPI, SQLAlchemy และ Alembic
- Database: PostgreSQL
- Local runtime: Docker Compose
- Tests: pytest สำหรับ backend และ Playwright สำหรับ E2E frontend

## เริ่มใช้งานจาก Fresh Clone

### สิ่งที่ต้องเตรียม

- Git
- Docker Desktop พร้อม Docker Compose

### 1. Clone repository

```powershell
git clone https://github.com/Wipat/SplitBill.git
```

### 2. ตั้งค่า environment

สร้าง `.env` จาก .env.example 

### 3. เริ่มฐานข้อมูล

```powershell
docker compose up -d db
```

### 4. สร้าง/ปรับ schema และใส่ข้อมูลตัวอย่าง

```powershell
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python seed.py
```


### 5. เริ่มแอป

```powershell
docker compose up -d --build
```

เปิดบริการ:

| บริการ | URL |
|---|---|
| Frontend | <http://localhost:3000> |
| Backend API | <http://localhost:8000> |
| Swagger UI | <http://localhost:8000/docs> |
| Adminer | <http://localhost:8080> |

Adminer เชื่อมกับ server `db` โดยใช้ database, username และ password จาก `.env`

### หยุดแอป

```powershell
docker compose down
```

คำสั่งนี้เก็บข้อมูลใน named volume ไว้ หากต้องการลบฐานข้อมูลและข้อมูลทั้งหมดด้วย ให้ใช้ `docker compose down -v` **คำสั่งนี้ลบข้อมูลใน PostgreSQL volume อย่างถาวร**

## ข้อมูล Demo และการเลือกผู้ใช้

หน้าเว็บโหลดรายชื่อผู้ใช้จาก `GET /users` และโหลดกลุ่มของผู้ใช้ที่เลือกจาก `GET /groups` โดยส่ง header `X-User` จากนั้น backend ตรวจ membership ซ้ำทุกครั้งที่เรียก API ซึ่งอ่านหรือแก้ไขข้อมูลภายในกลุ่ม

ผู้ใช้และกลุ่มตั้งต้นมาจาก `backend/seed.py`; โปรเจกต์ยังไม่มีหน้าหรือ API CRUD สำหรับสร้าง/แก้ไข/ลบ users และ groups อย่างครบถ้วน การเพิ่มหรือจัดการข้อมูลเหล่านี้จึงต้องทำผ่าน seed script หรือจัดการฐานข้อมูลสำหรับ demo

## การตัดสินใจด้านการออกแบบ

### การตอบ `403 Forbidden` กับ `404 Not Found`

- ใช้ **404** เมื่อไม่พบกลุ่มหรือ expense ที่ร้องขอ หรือกลุ่มถูก soft delete เพื่อสื่อว่าทรัพยากรนั้นไม่มีให้ใช้งาน
- ใช้ **403** เมื่อพบกลุ่ม แต่ผู้ใช้ที่ระบุใน `X-User` ไม่ได้เป็นสมาชิก หรือผู้เรียก DELETE ไม่ใช่ผู้จ่าย expense
- ใช้ **401** เมื่อไม่มี `X-User` หรือ header มีค่าไม่ใช่ user ID จำนวนเต็มบวก

การตรวจเหล่านี้บังคับที่ backend ไม่ได้อาศัยเพียงการซ่อนข้อมูลใน frontend

### การจัดการเศษสตางค์

สำหรับ Equal split ระบบหารยอดเป็นจำนวนหน่วยสตางค์ก่อน จากนั้นแจกเศษที่เหลือทีละ `0.01` ให้สมาชิกตามลำดับที่ส่งเข้ามา ตัวอย่าง `100.00` หารสามคนได้ `33.34`, `33.33`, `33.33` และผลรวมตรงกับยอดเดิมทุกครั้ง

Frontend ใช้จำนวนเต็มหน่วยสตางค์ (integer cents) ในการคำนวณ preview เพื่อหลีกเลี่ยงความคลาดเคลื่อนจาก floating point เช่น `0.1 + 0.2` และจัดรูปแบบเพื่อแสดงผลด้วย locale ไทย

### การใช้ `Decimal`

Backend ใช้ Python `Decimal` สำหรับจำนวนเงิน ตรวจไม่ให้มีเศษต่ำกว่าหนึ่งสตางค์ และใช้คอลัมน์ PostgreSQL `NUMERIC(12, 2)` สำหรับยอด expense และ shares หลีกเลี่ยงการใช้ binary floating-point ในการคำนวณยอดเงิน

Exact split จะถูกปฏิเสธหากยอด shares รวมไม่ตรงกับยอด expense

### กลยุทธ์ Idempotency

`POST /groups/{group_id}/expenses` ต้องรับ `Idempotency-Key` โดย key มีขอบเขตภายในกลุ่มและถูกบังคับไม่ให้ซ้ำด้วย unique constraint `(group_id, idempotency_key)` ในฐานข้อมูล ระบบบันทึก fingerprint ของ request ด้วย:

- key เดิมและ payload เดิม: คืน expense ที่สร้างไว้แล้ว ไม่สร้าง expense/share ซ้ำ
- key เดิมแต่ payload ต่างกัน: ตอบ `409 Conflict`
- requests ที่เข้าพร้อมกัน: unique constraint ของฐานข้อมูลเป็นตัวป้องกันการ insert ซ้ำ แล้ว endpoint อ่านรายการเดิมกลับเมื่อพบ key ที่ชนกัน

Expense และ shares ถูกบันทึกใน transaction เดียวกัน กลยุทธ์นี้ต้องใช้ migration ปัจจุบันให้ตรงกับฐานข้อมูลก่อนใช้งาน

## การทดสอบ

### Backend

จาก root ของ repository:

```powershell
cd backend
python -m pytest tests -q
```

### Frontend lint และ production build

```powershell
cd frontend
npm ci
npm run lint
npm run build
```

### Frontend E2E

ต้องเปิด frontend/backend และมีข้อมูล demo ที่พร้อมใช้งานก่อน จากนั้นติดตั้ง browser ของ Playwright และรัน:

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

E2E test สร้าง expense ชั่วคราวและพยายาม soft delete รายการนั้นใน cleanup ควรรันกับฐานข้อมูล demo เท่านั้น

## Known Limitations

1. **`X-User` ไม่ใช่ authentication ที่ปลอดภัย:** frontend ส่ง user ID มาใน header โดยตรง ผู้เรียกสามารถแก้ค่าเป็น ID ของผู้ใช้อื่นได้ การตรวจ group membership ช่วยจำกัดการเข้าถึงตาม ID ที่ส่งมา แต่ไม่ได้พิสูจน์ตัวตนของผู้ส่ง จึงมีความเสี่ยงสูงหากนำไปใช้จริงใน production ควรเปลี่ยนเป็นระบบ login/session หรือ token ที่ backend ตรวจสอบ
2. **Users และ groups ใช้ seed script:** ยังไม่มี CRUD workflow สำหรับจัดการผู้ใช้ กลุ่ม และ membership ผ่าน UI/API อย่างครบถ้วน
3. **ข้อมูล demo เป็นข้อมูลเริ่มต้น:** ต้องเตรียม group memberships ให้ตรงกับกลุ่มที่ต้องการทดสอบก่อนเรียก endpoints ที่มี authorization guard

## เวลาที่ใช้โดยประมาณ

เวลาพัฒนาโดยประมาณสำหรับงาน Milestone 1–5 รวม backend, frontend, tests, Docker integration และเอกสาร: **ประมาณ 5 ชั่วโมง**