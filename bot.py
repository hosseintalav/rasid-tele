import os
import random
import base64
import asyncio
import traceback
from datetime import datetime
import jdatetime
from aiohttp import web

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from playwright.async_api import async_playwright

TOKEN = "8866229929:AAGWxOLvSJQp5JbRQ-NVh3OOZnGafnZDQlM"

CHOOSE_TEMPLATE, GET_DEST_CARD, GET_DEST_NAME, GET_AMOUNT, GET_SRC_CARD, GET_SRC_NAME = range(6)

def get_image_base64(rel_path):
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)
    if not os.path.exists(full_path):
        return ""
    ext = os.path.splitext(full_path)[1].replace('.', '').lower()
    mime = "image/webp" if ext == "webp" else ("image/png" if ext == "png" else "image/jpeg")
    with open(full_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"

PERSIAN_DIGITS = {'0':'۰', '1':'۱', '2':'۲', '3':'۳', '4':'۴', '5':'۵', '6':'۶', '7':'۷', '8':'۸', '9':'۹'}
ENGLISH_DIGITS = {'۰':'0', '۱':'1', '۲':'2', '۳':'3', '۴':'4', '۵':'5', '۶':'6', '۷':'7', '۸':'8', '۹':'9'}

def to_persian(text):
    if not text: return ""
    return "".join(PERSIAN_DIGITS.get(ch, ch) for ch in str(text))

def to_english(text):
    if not text: return ""
    return "".join(ENGLISH_DIGITS.get(ch, ch) for ch in str(text))

def clean_card(card_str):
    raw = to_english(card_str)
    return "".join([c for c in raw if c.isdigit()])

def format_card_spaced(card_str):
    c = clean_card(card_str)
    parts = [c[i:i+4] for i in range(0, len(c), 4)]
    return to_persian(" ".join(parts))

def mask_card_blu(card_str):
    c = clean_card(card_str)
    if len(c) >= 10:
        return f"{to_persian(c[:4])}  {to_persian(c[4:6])}** **** {to_persian(c[-4:])}"
    return to_persian(c)

def mask_card_724(card_str):
    c = clean_card(card_str)
    if len(c) >= 10:
        return f"{to_persian(c[:6])}••••••{to_persian(c[-4:])}"
    return to_persian(c)

def format_amount(amount_str):
    clean = clean_card(amount_str)
    if not clean: return "۰"
    return to_persian("{:,}".format(int(clean)))

def get_persian_date_blu():
    now = datetime.now()
    j_now = jdatetime.datetime.fromgregorian(datetime=now)
    days = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یک‌شنبه"]
    months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    time_str = now.strftime("%H:%M")
    return to_persian(f"{time_str} {days[j_now.weekday()]}، {j_now.day} {months[j_now.month - 1]} {j_now.year}"), time_str

def get_persian_date_724():
    now = datetime.now()
    j_now = jdatetime.datetime.fromgregorian(datetime=now)
    time_str = now.strftime("%H:%M")
    return to_persian(f"{j_now.year}/{j_now.month:02d}/{j_now.day:02d} {time_str}"), time_str

def generate_random_digits(n):
    return to_persian("".join(str(random.randint(0, 9)) for _ in range(n)))

def render_blu_html(data):
    persian_date, time_str = get_persian_date_blu()
    ref_num = generate_random_digits(12)
    amount_persian = format_amount(data['amount'])
    dest_card_fmt = format_card_spaced(data['dest_card'])
    src_card_masked = mask_card_blu(data['src_card'])
    status_icon_src = get_image_base64("images/status-icons.png")
    blu_icon_src = get_image_base64("images/blu.webp")

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" />
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; }}
body {{ background-color: #0b0e14; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
#receipt-capture-area {{
    width: 450px; height: 1000px; background-color: #1a1e29;
    display: flex; flex-direction: column; padding: 0 24px 10px 24px;
    color: #ffffff; box-sizing: border-box; overflow: hidden;
}}
.phone-status-bar {{ height: 42px; padding: 0 4px; display: flex; justify-content: space-between; align-items: center; direction: rtl; }}
.status-time {{ font-size: 15px; font-weight: 600; direction: ltr; }}
.status-icons-img {{ height: 21px; width: auto; object-fit: contain; }}
.header {{ display: flex; justify-content: space-between; align-items: center; padding: 6px 0 28px 0; }}
.header-title {{ font-size: 19px; font-weight: 700; }}
.help-btn {{ background-color: #5a94dd; color: #1a1e29; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 15px; }}
.top-fixed {{ display: flex; flex-direction: column; padding-bottom: 15px; }}
.profile-section {{ display: flex; flex-direction: column; align-items: center; }}
.avatar-wrapper {{ width: 80px; height: 80px; background-color: #242a37; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; overflow: hidden; }}
.avatar-img {{ width: 65%; height: 65%; object-fit: contain; }}
.profile-name {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
.profile-card {{ font-size: 16px; color: #858e9e; letter-spacing: 2px; margin-bottom: 14px; direction: ltr; }}
.amount-section {{ text-align: center; margin-bottom: 12px; }}
.amount {{ font-size: 32px; font-weight: 800; margin-bottom: 2px; }}
.amount-label {{ font-size: 15px; color: #858e9e; }}
.status-badge-container {{ display: flex; justify-content: center; }}
.status-badge {{ background-color: #02bd92; color: #07231a; border-radius: 12px; padding: 9px 20px; display: inline-flex; align-items: center; gap: 8px; font-size: 15.5px; font-weight: 700; }}
.status-icon-circle {{ background-color: #07231a; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
.dotted-sep {{ margin: 0 4px 6px 4px; opacity: 0.85; background-image: radial-gradient(circle, #363e4f 1.5px, transparent 1.5px); background-size: 20px 3px; background-repeat: repeat-x; background-position: bottom; height: 3px; }}
.spacer-top, .spacer-bottom {{ flex-grow: 1; }}
.details-list {{ display: flex; flex-direction: column; }}
.detail-row {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 2px; border-bottom: 1px solid #232a38; }}
.detail-row:last-child {{ border-bottom: none; }}
.detail-label {{ font-size: 15.5px; color: #858e9e; }}
.detail-value {{ font-size: 16px; font-weight: 600; }}
.ltr-text {{ direction: ltr; }}
.bottom-actions {{ display: flex; gap: 14px; padding-bottom: 10px; }}
.action-btn {{ flex: 1; background-color: #242b38; border-radius: 14px; padding: 14px 6px; color: #8faecc; font-size: 15px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 7px; }}
.home-indicator {{ width: 134px; height: 4.5px; background-color: #ffffff; opacity: 0.45; border-radius: 3px; margin: 8px auto 2px auto; }}
</style>
</head>
<body>
<div id="receipt-capture-area">
    <div class="phone-status-bar">
        <span class="status-time">{to_english(time_str)}</span>
        <img src="{status_icon_src}" class="status-icons-img">
    </div>
    <div class="header">
        <div class="help-btn">?</div>
        <div class="header-title">رسید</div>
        <div style="font-size:24px; color:#4289df; transform: rotate(180deg);">➔</div>
    </div>
    <div class="top-fixed">
        <div class="profile-section">
            <div class="avatar-wrapper"><img src="{blu_icon_src}" class="avatar-img"></div>
            <div class="profile-name">{data['dest_name']}</div>
            <div class="profile-card">{dest_card_fmt}</div>
        </div>
        <div class="amount-section">
            <div class="amount">{amount_persian} <span style="font-size: 20px;">ریال</span></div>
            <div class="amount-label">مبلغ انتقال</div>
        </div>
        <div class="status-badge-container">
            <div class="status-badge">
                <div class="status-icon-circle">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#02bd92" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                </div>
                <span>انتقال موفق</span>
            </div>
        </div>
    </div>
    <div class="spacer-top"></div>
    <div class="details-list">
        <div class="dotted-sep"></div>
        <div class="detail-row"><div class="detail-label">زمان</div><div class="detail-value">{persian_date}</div></div>
        <div class="detail-row"><div class="detail-label">انتقال دهنده</div><div class="detail-value">{data['src_name']}</div></div>
        <div class="detail-row"><div class="detail-label">روش انتقال</div><div class="detail-value">کارت به کارت</div></div>
        <div class="detail-row"><div class="detail-label">کارت مبدا</div><div class="detail-value ltr-text">{src_card_masked}</div></div>
        <div class="detail-row"><div class="detail-label">شماره مرجع</div><div class="detail-value ltr-text">{ref_num}</div></div>
    </div>
    <div class="spacer-bottom"></div>
    <div class="bottom-actions">
        <div class="action-btn"><span>اشتراک‌گذاری</span></div>
        <div class="action-btn"><span>ذخیره در گالری</span></div>
    </div>
    <div class="home-indicator"></div>
</div>
</body>
</html>"""

def render_724_html(data):
    persian_date, time_str = get_persian_date_724()
    ref_track = generate_random_digits(9)
    ref_num = generate_random_digits(12)
    amount_persian = format_amount(data['amount'])
    dest_card_num = to_persian(clean_card(data['dest_card']))
    src_card_masked = mask_card_724(data['src_card'])
    status_icon_src = get_image_base64("images/status-icons.png")
    app_724_src = get_image_base64("images/724.webp")

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" />
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; }}
body {{ background-color: #0b0e14; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
#receipt-capture-area {{
    width: 450px; height: 1000px; background-color: #141318;
    display: flex; flex-direction: column; padding: 0 22px 10px 22px;
    box-sizing: border-box; overflow: hidden; color: #ffffff;
}}
.phone-status-bar {{ height: 42px; padding: 0 4px; display: flex; justify-content: space-between; align-items: center; direction: rtl; }}
.status-time {{ font-size: 15px; font-weight: 600; direction: ltr; }}
.status-icons-img {{ height: 21px; width: auto; object-fit: contain; }}
.header {{ display: flex; justify-content: space-between; align-items: center; padding: 6px 0 30px 0; position: relative; }}
.header h1 {{ font-size: 20px; font-weight: 700; position: absolute; left: 50%; transform: translateX(-50%); }}
.success-badge {{ background-color: #35A87B; color: #ffffff; padding: 8px 22px; border-radius: 12px; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0 auto; width: fit-content; }}
.check-circle {{ width: 20px; height: 20px; background-color: #ffffff; border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
.amount-title {{ font-size: 20px; font-weight: 700; color: #ffffff; text-align: center; }}
.title-spacer-top, .title-spacer-bottom, .spacer-bottom {{ flex-grow: 1; }}
.details-card {{ background-color: #1E1C24; border-radius: 20px; padding: 10px 20px 16px 20px; }}
.detail-row {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #282630; }}
.detail-row.no-border {{ border-bottom: none; }}
.detail-label {{ color: #8E919A; font-size: 15px; }}
.detail-value {{ color: #ffffff; font-weight: 500; font-size: 16px; direction: ltr; }}
.detail-value.rtl {{ direction: rtl; }}
.branding-section {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 0 4px 0; margin-top: 6px; border-top: 1px solid #282630; }}
.branding-right {{ display: flex; align-items: center; gap: 8px; }}
.brand-img {{ height: 40px; width: auto; object-fit: contain; border-radius: 8px; }}
.branding-url {{ font-size: 15px; font-weight: 800; color: #E51C74; letter-spacing: 0.5px; text-align: left; }}
.branding-sub {{ font-size: 9px; color: #5D6069; margin-top: 2px; text-align: left; }}
.lucky-banner {{ background-color: #1A2338; border-radius: 16px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
.lucky-title {{ font-size: 14.5px; font-weight: 600; color: #ffffff; }}
.lucky-left {{ font-size: 14px; color: #40A9FF; display: flex; align-items: center; gap: 4px; }}
.bottom-nav {{ display: flex; justify-content: space-around; align-items: center; padding: 10px 12px 4px 12px; }}
.nav-item {{ display: flex; flex-direction: column; align-items: center; gap: 6px; color: #ffffff; font-size: 13.5px; }}
.home-indicator {{ width: 134px; height: 4.5px; background-color: #ffffff; opacity: 0.45; border-radius: 3px; margin: 8px auto 2px auto; }}
</style>
</head>
<body>
<div id="receipt-capture-area">
    <div class="phone-status-bar">
        <span class="status-time">{to_english(time_str)}</span>
        <img src="{status_icon_src}" class="status-icons-img">
    </div>
    <div class="header">
        <span style="font-size:24px;">✕</span>
        <h1>کارت به کارت</h1>
        <div style="width:24px;"></div>
    </div>
    <div class="success-badge">
        <span>تراکنش موفق</span>
        <div class="check-circle"><svg width="12" height="12" viewBox="0 0 24 24" fill="#35A87B"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg></div>
    </div>
    <div class="title-spacer-top"></div>
    <div class="amount-title">{data['dest_name']} - {amount_persian} ریال</div>
    <div class="title-spacer-bottom"></div>
    <div class="details-card">
        <div class="detail-row"><span class="detail-label">مبلغ</span><span class="detail-value">{amount_persian} ریال</span></div>
        <div class="detail-row"><span class="detail-label">تاریخ</span><span class="detail-value">{persian_date}</span></div>
        <div class="detail-row"><span class="detail-label">کارت مبدا</span><span class="detail-value">{src_card_masked}</span></div>
        <div class="detail-row"><span class="detail-label">کارت مقصد</span><span class="detail-value">{dest_card_num}</span></div>
        <div class="detail-row"><span class="detail-label">دارنده کارت مقصد</span><span class="detail-value rtl">{data['dest_name']}</span></div>
        <div class="detail-row"><span class="detail-label">شماره پیگیری</span><span class="detail-value">{ref_track}</span></div>
        <div class="detail-row no-border"><span class="detail-label">شماره مرجع</span><span class="detail-value">{ref_num}</span></div>
        <div class="branding-section">
            <div class="branding-right"><img src="{app_724_src}" class="brand-img"><span style="font-size:13px; color:#8E919A;">ساده‌ترین روش کارت به کارت</span></div>
            <div><div class="branding-url">WWW.724.IR</div><div class="branding-sub">support724@sep.ir 021-84080</div></div>
        </div>
    </div>
    <div class="spacer-bottom"></div>
    <div class="lucky-banner"><span class="lucky-title">🎁 ۱ جایزه گردونه برای این تراکنش</span><span class="lucky-left">شانستو امتحان کن! ➔</span></div>
    <div class="bottom-nav">
        <div class="nav-item"><span>ذخیره/ارسال</span></div>
        <div class="nav-item"><span>تکرار تراکنش</span></div>
    </div>
    <div class="home-indicator"></div>
</div>
</body>
</html>"""

async def generate_receipt_image(template_type, data):
    html_content = render_blu_html(data) if template_type == 'blu' else render_724_html(data)
    filename = f"receipt_{data['user_id']}_{int(datetime.now().timestamp())}.png"

    async with async_playwright() as p:
        # آرگومان‌های کاملاً سازگار و پایدار با داکر لینوکسی (حذف فلگ مخرب single-process)
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run"
            ]
        )
        page = await browser.new_page(
            viewport={"width": 450, "height": 1000},
            device_scale_factor=2
        )
        
        # لود بدون بلاک شدن روی منابع خارجی و اطمینان از لود فونت‌ها
        await page.set_content(html_content, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.evaluate("() => document.fonts.ready")
        except Exception:
            pass
        await asyncio.sleep(0.5)

        element = await page.query_selector("#receipt-capture-area")
        if element:
            await element.screenshot(path=filename)
        else:
            await page.screenshot(path=filename)

        await browser.close()

    return filename

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("🔵 رسید بلو بانک"), KeyboardButton("🔴 رسید ۷۲۴")]],
    resize_keyboard=True
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup([[KeyboardButton("❌ انصراف")]], resize_keyboard=True)

SRC_CARD_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("🎲 کارت تصادفی مبدأ")], [KeyboardButton("❌ انصراف")]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "<b>سلام به سیستم صدور رسید شبیه‌ساز خوش آمدید.</b>\n\nقالب رسید مد نظر خود را انتخاب کنید:"
    await update.message.reply_text(text, reply_markup=MAIN_KEYBOARD, parse_mode=ParseMode.HTML)
    return CHOOSE_TEMPLATE

async def template_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = update.message.text.strip()
    if "بلو" in msg_text:
        context.user_data['template'] = 'blu'
        t_name = "بلو بانک"
    elif "۷۲۴" in msg_text or "724" in msg_text:
        context.user_data['template'] = '724'
        t_name = "۷۲۴"
    else:
        await update.message.reply_text("لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=MAIN_KEYBOARD)
        return CHOOSE_TEMPLATE

    text = f"قالب انتخابی: <b>{t_name}</b>\n\nلطفاً <b>شماره کارت مقصد</b> (۱۶ رقمی) را ارسال کنید:"
    await update.message.reply_text(text, reply_markup=CANCEL_KEYBOARD, parse_mode=ParseMode.HTML)
    return GET_DEST_CARD

async def get_dest_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = clean_card(update.message.text)
    if len(raw) < 16:
        await update.message.reply_text("<b>شماره کارت باید حداقل ۱۶ رقم باشد.</b> دوباره وارد کنید:", parse_mode=ParseMode.HTML)
        return GET_DEST_CARD

    context.user_data['dest_card'] = raw
    await update.message.reply_text("لطفاً <b>نام و نام خانوادگی دارنده کارت مقصد</b> را وارد کنید:", parse_mode=ParseMode.HTML)
    return GET_DEST_NAME

async def get_dest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dest_name'] = update.message.text.strip()
    await update.message.reply_text("لطفاً <b>مبلغ تراکنش به ریال</b> را وارد کنید:", parse_mode=ParseMode.HTML)
    return GET_AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_clean = clean_card(update.message.text)
    if not amount_clean or int(amount_clean) <= 0:
        await update.message.reply_text("<b>مبلغ نامعتبر است.</b> فقط عدد بفرستید:", parse_mode=ParseMode.HTML)
        return GET_AMOUNT

    context.user_data['amount'] = amount_clean
    await update.message.reply_text("لطفاً <b>شماره کارت مبدأ</b> را بنویسید یا دکمه تصادفی را بزنید:", reply_markup=SRC_CARD_KEYBOARD, parse_mode=ParseMode.HTML)
    return GET_SRC_CARD

async def get_src_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if user_input == "🎲 کارت تصادفی مبدأ":
        prefix = "621986" if context.user_data.get('template') == 'blu' else "603799"
        card_num = prefix + "".join(str(random.randint(0, 9)) for _ in range(10))
        context.user_data['src_card'] = card_num
        await update.message.reply_text(f"شماره کارت مبدأ تصادفی ثبت شد:\n<code>{card_num}</code>\n\nاکنون <b>نام دارنده کارت مبدأ</b> را ارسال کنید:", reply_markup=CANCEL_KEYBOARD, parse_mode=ParseMode.HTML)
        return GET_SRC_NAME

    raw = clean_card(user_input)
    if len(raw) < 16:
        await update.message.reply_text("<b>شماره کارت نامعتبر است.</b> باید ۱۶ رقم باشد:", parse_mode=ParseMode.HTML)
        return GET_SRC_CARD

    context.user_data['src_card'] = raw
    await update.message.reply_text("لطفاً <b>نام دارنده کارت مبدأ</b> را بنویسید:", reply_markup=CANCEL_KEYBOARD, parse_mode=ParseMode.HTML)
    return GET_SRC_NAME

async def get_src_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['src_name'] = update.message.text.strip()
    context.user_data['user_id'] = update.effective_user.id

    wait_msg = await update.message.reply_text(
        "در حال پردازش و تولید عکس رسید، لطفاً چند لحظه صبر کنید...",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )

    image_path = None
    try:
        image_path = await generate_receipt_image(context.user_data['template'], context.user_data)
        tpl_title = "بلو بانک" if context.user_data['template'] == 'blu' else "۷۲۴"
        caption = (
            f"<b>رسید شبیه‌ساز {tpl_title} صادر شد</b>\n\n"
            f"• <b>گیرنده:</b> {context.user_data['dest_name']}\n"
            f"• <b>مبلغ:</b> {format_amount(context.user_data['amount'])} ریال\n"
            f"• <b>فرستنده:</b> {context.user_data['src_name']}"
        )

        with open(image_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=caption,
                reply_markup=MAIN_KEYBOARD,
                parse_mode=ParseMode.HTML
            )

        await wait_msg.delete()

    except Exception as e:
        print(f"Error in receipt generation: {traceback.format_exc()}")
        await wait_msg.edit_text(f"<b>خطایی رخ داد:</b>\n<code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.", reply_markup=MAIN_KEYBOARD, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def health_check(request):
    return web.Response(text="Bot is online 24/7!")

# ----------------- اجرای همزمان وب سرور و بات -----------------
async def main_async():
    server = web.Application()
    server.router.add_get('/', health_check)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server running on port {port}")

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^(🔵 رسید بلو بانک|🔴 رسید ۷۲۴)$"), template_chosen)
        ],
        states={
            CHOOSE_TEMPLATE: [MessageHandler(filters.Regex("^(🔵 رسید بلو بانک|🔴 رسید ۷۲۴)$"), template_chosen)],
            GET_DEST_CARD: [MessageHandler(filters.Regex("^❌ انصراف$"), cancel), MessageHandler(filters.TEXT & ~filters.COMMAND, get_dest_card)],
            GET_DEST_NAME: [MessageHandler(filters.Regex("^❌ انصراف$"), cancel), MessageHandler(filters.TEXT & ~filters.COMMAND, get_dest_name)],
            GET_AMOUNT: [MessageHandler(filters.Regex("^❌ انصراف$"), cancel), MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            GET_SRC_CARD: [MessageHandler(filters.Regex("^❌ انصراف$"), cancel), MessageHandler(filters.TEXT & ~filters.COMMAND, get_src_card)],
            GET_SRC_NAME: [MessageHandler(filters.Regex("^❌ انصراف$"), cancel), MessageHandler(filters.TEXT & ~filters.COMMAND, get_src_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex("^❌ انصراف$"), cancel)],
    )

    app.add_handler(conv_handler)

    await app.initialize()
    await app.updater.start_polling(drop_pending_updates=True)
    await app.start()
    print("Telegram Bot is listening...")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main_async())
