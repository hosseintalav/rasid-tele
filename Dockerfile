FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# نصب پیش‌نیازهای پایتونی
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کردن کدهای ربات و عکس‌ها
COPY . .

# پورت رندر
ENV PORT=10000
EXPOSE 10000

# اجرای ربات
CMD ["python", "bot.py"]
