FROM python:3.12-slim

WORKDIR /app

# chromium: يطبع تقرير صقر PDF بنفس تصميم الموقع. والسببُ أنه المُصفِّف
# الوحيد الذي يصل الحروف العربية ويعكس اتّجاه السطر كما في الشاشة تماماً —
# ومكتبات PDF العامّة تكتبها منفصلةً مقلوبة. وهو اختياريّ في الشيفرة:
# إن غاب أُرسلت الصفحة HTML بدل الورقة.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    tesseract-ocr \
    tesseract-ocr-ara \
    ghostscript \
    chromium \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
