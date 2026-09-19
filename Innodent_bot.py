# این کد رو توی یه سلول گوگل کولب اجرا کن.
# فقط BOT_TOKEN، MY_USER_ID و TARGET_CHAT_ID رو پر کن.
# فرم فقط توی پی‌وی خودِ بات جواب می‌ده؛ نتیجه‌ی نهایی فقط به TARGET_CHAT_ID (گروه) ارسال می‌شه.

# !pip install requests -q   <-- اگه لازم شد این خط رو هم اجرا کن (خط اول یه سلول جدا)

import os
import time
import requests

# ================== تنظیمات ==================
BOT_TOKEN = os.environ["InnodentBot"]

innodent = 1940159581
abbaspour = 983635873
almohammad= 1023856969
farhadi = 52744
javanmard = 1252727399

SELLERS = {
    abbaspour: "عباسپور",
    innodent: "عباسپور",
    almohammad: "آل محمد",
    farhadi : "فرهادی",
    javanmard: "جوانمرد",
}
# فعلاً نتیجه برای خودت ارسال می‌شه. برای ارسال به گروه، این خط رو با
# آیدی منفی گروه (که از خروجی چاپ‌شده‌ی همین کد می‌گیری) جایگزین کن:
TARGET_CHAT_ID = 4970954045
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"
# ===============================================

PRODUCTS = ["واترجت", "فرز", "لیدوکایین"]

# قیمت واحد محصولاتی که قیمت‌شون ثابته
UNIT_PRICES = {
    "واترجت": 68_000_000,
    "لیدوکایین": 37_500_000,
}

# قیمت‌های فرز بر اساس دسته: (قیمت پایه, تعداد عدد در هر بسته)
DRILL_CATEGORY_PRICES = {
    "الماسه": [(2_800_000, 6)],
    "کاربایدی": [(3_600_000, 2), (4_800_000, 2)],
}
# نگاشت کمکی: قیمت پایه -> تعداد عدد در بسته (برای محاسبه‌ی مبلغ نهایی)
DRILL_PACK_SIZE_BY_PRICE = {
    base: pack_size
    for options in DRILL_CATEGORY_PRICES.values()
    for base, pack_size in options
}

FIELD_LABELS = {
    "customer_name": "نام مشتری",
    "mobile": "تلفن تماس",
    "landline": "تلفن ثابت",
    "address": "آدرس",
    "delivery_time": "ساعت تحویل",
}

TEXT_FIELDS_ORDER = ["customer_name", "mobile", "landline", "address", "delivery_time"]
TEXT_FIELD_PROMPTS = {
    "customer_name": "نام مشتری را وارد کنید:",
    "mobile": "تلفن همراه را وارد کنید:",
    "landline": "تلفن ثابت را وارد کنید :",
    "address": "آدرس را وارد کنید:",
    "delivery_time": "ساعت تحویل را وارد کنید :",
}

user_states = {}  # user_id -> {"step":..., "data": {...}}


# ---------------- ابزارهای پایه ----------------

def api_call(method, params=None):
    return requests.post(f"{API_URL}/{method}", json=params or {}, timeout=30).json()


def send_message(chat_id, text, keyboard=None):
    params = {"chat_id": chat_id, "text": text}
    if keyboard:
        params["reply_markup"] = {"inline_keyboard": keyboard}
    api_call("sendMessage", params)


def answer_callback(callback_id):
    api_call("answerCallbackQuery", {"callback_query_id": callback_id})


def format_price(n):
    return f"{n:,}"


def parse_int(text):
    digits = "".join(ch for ch in str(text) if ch.isdigit())
    return int(digits) if digits else 0


# ---------------- کیبوردها ----------------

def product_keyboard():
    return [[{"text": p, "callback_data": f"product:{p}"}] for p in PRODUCTS]


def drill_category_keyboard():
    return [[{"text": cat, "callback_data": f"drillcat:{cat}"}] for cat in DRILL_CATEGORY_PRICES]


def price_option_values(product, category=None):
    """برمی‌گردونه: لیست قیمت‌های پایه (همون که روی دکمه نشون داده می‌شه) برای این محصول"""
    if product in UNIT_PRICES:
        return [UNIT_PRICES[product]]
    if product == "فرز":
        return [base for base, _pack_size in DRILL_CATEGORY_PRICES.get(category, [])]
    return []


def compute_item_total(product, base_price, quantity):
    """محاسبه‌ی مبلغ نهایی آیتم با اعمال ضریب بسته (برای فرز) و تعداد"""
    if product == "فرز":
        pack_size = DRILL_PACK_SIZE_BY_PRICE.get(base_price, 1)
        return base_price * pack_size * quantity
    return base_price * quantity


def price_select_keyboard(product, category=None):
    rows = [[{"text": f"{format_price(v)} ریال", "callback_data": f"priceopt:{v}"}]
            for v in price_option_values(product, category)]
    rows.append([{"text": "✍️ دستی", "callback_data": "price:manual"}])
    return rows


def item_added_keyboard():
    return [
        [{"text": "➕ افزودن سفارش دیگر", "callback_data": "additem"}],
        [{"text": "✅ ادامه و مشاهده خلاصه", "callback_data": "finish_items"}],
    ]


def confirm_keyboard():
    return [
        [{"text": "✅ تایید و ارسال", "callback_data": "confirm:yes"}],
        [{"text": "✏️ ویرایش", "callback_data": "confirm:edit"}],
        [{"text": "❌ لغو", "callback_data": "confirm:cancel"}],
    ]


def edit_keyboard(data):
    rows = [[{"text": FIELD_LABELS[f], "callback_data": f"edit:{f}"}] for f in TEXT_FIELDS_ORDER]
    for idx, item in enumerate(data.get("items", [])):
        rows.append([
            {"text": f"✏️ آیتم {idx + 1}: {item['product']}", "callback_data": f"edititem:{idx}"},
            {"text": "🗑 حذف", "callback_data": f"delitem:{idx}"},
        ])
    rows.append([{"text": "➕ افزودن آیتم جدید", "callback_data": "additem"}])
    rows.append([{"text": "🔙 بازگشت", "callback_data": "confirm:back"}])
    return rows


# ---------------- ساخت خلاصه سفارش ----------------

def build_summary(data):
    lines = [
        "📋 فرم سفارش",
        "",
        f"🧑‍💼 فروشنده: {data.get('seller', '-')}",
        f"👤 نام مشتری: {data.get('customer_name', '-')}",
        f"📱 تماس: {data.get('mobile', '-')}",
        f"☎️ ثابت: {data.get('landline', '-')}",
        f"📍 آدرس: {data.get('address', '-')}",
        f"🕒 ساعت تحویل: {data.get('delivery_time', '-')}",
        "",
    ]

    total = 0
    for i, item in enumerate(data.get("items", []), start=1):
        product = item["product"]
        detail = item.get("detail", {})
        price = item.get("price", 0)
        quantity = parse_int(detail.get("quantity", "0"))
        unit_price = price // quantity if quantity else price
        total += price
        if product == "فرز":
            pack_size = detail.get("pack_size", 1)
            category = detail.get("category", "-")
            lines.append(
                f"{i}. {detail.get('quantity', '-')}بسته {pack_size}عددی فرز {category} "
                f"{detail.get('type', '-')}، قیمت واحد: {format_price(unit_price)} ریال — "
                f"جمع: {format_price(price)} ریال"
            )
        else:
            lines.append(
                f"{i}. {product}، تعداد: {detail.get('quantity', '-')}، "
                f"قیمت واحد: {format_price(unit_price)} ریال — جمع: {format_price(price)} ریال"
            )

    lines.append("")
    lines.append(f"💰 جمع کل: {format_price(total)} ریال")
    return "\n".join(lines)


# ---------------- جریان فرم سفارش ----------------

def start_order(chat_id, user_id):
    seller_name = SELLERS[user_id]
    user_states[user_id] = {
        "step": TEXT_FIELDS_ORDER[0],
        "data": {
            "seller": seller_name,
            "items": [],
            "editing_index": None,
            "product": None,
            "detail": {},
        },
    }
    send_message(chat_id, "شروع سفارش جدید. برای لغو در هر مرحله /cancel را بزنید.\n\n" + TEXT_FIELD_PROMPTS[TEXT_FIELDS_ORDER[0]])


def cancel_order(chat_id, user_id):
    user_states.pop(user_id, None)
    send_message(chat_id, "سفارش لغو شد.")


def goto_confirm(chat_id, user_id):
    state = user_states[user_id]
    state["step"] = "confirm"
    send_message(chat_id, build_summary(state["data"]), keyboard=confirm_keyboard())


def goto_price_select(chat_id, user_id):
    state = user_states[user_id]
    state["step"] = "price_select"
    product = state["data"]["product"]
    category = state["data"]["detail"].get("category")
    send_message(chat_id, "قیمت را انتخاب کنید:", keyboard=price_select_keyboard(product, category))


def start_new_item(chat_id, user_id):
    state = user_states[user_id]
    state["data"]["product"] = None
    state["data"]["detail"] = {}
    state["step"] = "product_select"
    send_message(chat_id, "محصول را انتخاب کنید:", keyboard=product_keyboard())


def finalize_item(chat_id, user_id, price_value):
    state = user_states[user_id]
    data = state["data"]
    item = {"product": data["product"], "detail": data["detail"], "price": price_value}

    idx = data.get("editing_index")
    if idx is not None:
        data["items"][idx] = item
        data["editing_index"] = None
        data["product"] = None
        data["detail"] = {}
        goto_confirm(chat_id, user_id)
    else:
        data.setdefault("items", []).append(item)
        data["product"] = None
        data["detail"] = {}
        state["step"] = "item_added"
        send_message(chat_id, "آیتم ثبت شد. ✅", keyboard=item_added_keyboard())


def handle_order_text(chat_id, user_id, text):
    state = user_states.get(user_id)
    if state is None:
        send_message(chat_id, "برای شروع سفارش جدید /start را بزنید.")
        return

    step = state["step"]
    text = text.strip()

    if step in TEXT_FIELDS_ORDER:
        state["data"][step] = text
        idx = TEXT_FIELDS_ORDER.index(step)
        if idx + 1 < len(TEXT_FIELDS_ORDER):
            next_field = TEXT_FIELDS_ORDER[idx + 1]
            state["step"] = next_field
            send_message(chat_id, TEXT_FIELD_PROMPTS[next_field])
        else:
            start_new_item(chat_id, user_id)
        return

    if step.startswith("editing_"):
        field = step[len("editing_"):]
        state["data"][field] = text
        goto_confirm(chat_id, user_id)
        return

    if step == "await_drilltype":
        state["data"]["detail"]["type"] = text
        state["step"] = "await_quantity"
        send_message(chat_id, "تعداد بسته فرز را وارد کنید:")
        return

    if step == "await_quantity":
        if not text.isdigit():
            send_message(chat_id, "تعداد باید فقط عدد باشد. لطفاً دوباره وارد کنید:")
            return
        state["data"]["detail"]["quantity"] = text
        goto_price_select(chat_id, user_id)
        return

    if step == "await_manual_price":
        unit_price = parse_int(text)
        quantity = parse_int(state["data"]["detail"].get("quantity", "0"))
        finalize_item(chat_id, user_id, unit_price * quantity)
        return

    send_message(chat_id, "لطفاً از دکمه‌ها استفاده کنید یا /start را بزنید.")


def handle_callback(chat_id, user_id, callback_id, data_str):
    answer_callback(callback_id)
    state = user_states.get(user_id)
    if state is None:
        return
    data = state["data"]

    if data_str.startswith("product:"):
        product = data_str.split(":", 1)[1]
        data["product"] = product
        data["detail"] = {}
        if product == "فرز":
            state["step"] = "await_drillcategory"
            send_message(chat_id, "دسته‌ی فرز را انتخاب کنید:", keyboard=drill_category_keyboard())
        else:
            state["step"] = "await_quantity"
            send_message(chat_id, f"تعداد {product} را وارد کنید:")
        return

    if data_str.startswith("drillcat:"):
        category = data_str.split(":", 1)[1]
        data["detail"]["category"] = category
        state["step"] = "await_drilltype"
        send_message(chat_id, "نوع فرز را وارد کنید:")
        return

    if data_str.startswith("priceopt:"):
        base_price = int(data_str.split(":", 1)[1])
        quantity = parse_int(data["detail"].get("quantity", "0"))
        if data["product"] == "فرز":
            data["detail"]["pack_size"] = DRILL_PACK_SIZE_BY_PRICE.get(base_price, 1)
        total = compute_item_total(data["product"], base_price, quantity)
        finalize_item(chat_id, user_id, total)
        return

    if data_str == "price:manual":
        state["step"] = "await_manual_price"
        send_message(chat_id, "قیمت هر عدد را وارد کنید (ریال):")
        return

    if data_str == "additem":
        data["editing_index"] = None
        start_new_item(chat_id, user_id)
        return

    if data_str == "finish_items":
        goto_confirm(chat_id, user_id)
        return

    if data_str.startswith("edititem:"):
        idx = int(data_str.split(":", 1)[1])
        item = data["items"][idx]
        data["editing_index"] = idx
        data["product"] = item["product"]
        data["detail"] = dict(item["detail"])
        state["step"] = "product_select"
        send_message(chat_id, f"ویرایش آیتم {idx + 1} — محصول را دوباره انتخاب کنید:", keyboard=product_keyboard())
        return

    if data_str.startswith("delitem:"):
        idx = int(data_str.split(":", 1)[1])
        if 0 <= idx < len(data["items"]):
            data["items"].pop(idx)
        goto_confirm(chat_id, user_id)
        return

    if data_str.startswith("edit:"):
        field = data_str.split(":", 1)[1]
        state["step"] = f"editing_{field}"
        send_message(chat_id, f"{FIELD_LABELS[field]} جدید را وارد کنید:")
        return

    if data_str == "confirm:yes":
        send_message(TARGET_CHAT_ID, build_summary(data))
        send_message(chat_id, "سفارش ثبت و ارسال شد. ✅")
        user_states.pop(user_id, None)
        return

    if data_str == "confirm:edit":
        send_message(chat_id, "کدام بخش را ویرایش می‌کنید؟", keyboard=edit_keyboard(data))
        return

    if data_str == "confirm:back":
        goto_confirm(chat_id, user_id)
        return

    if data_str == "confirm:cancel":
        cancel_order(chat_id, user_id)
        return


# ---------------- حلقه اصلی ----------------

def run():
    offset = None
    print("بات در حال اجراست... این سلول باید در حال اجرا (running) باقی بمونه.")
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset

            result = api_call("getUpdates", params)
            for update in result.get("result", []):
                offset = update["update_id"] + 1

                if "callback_query" in update:
                    cq = update["callback_query"]
                    chat_id = cq["message"]["chat"]["id"]
                    user_id = cq["from"]["id"]
                    if user_id not in SELLERS:
                        continue
                    handle_callback(chat_id, user_id, cq["id"], cq.get("data", ""))
                    continue

                message = update.get("message")
                if not message:
                    continue

                # فقط پیام‌های پی‌وی پردازش بشه؛ به پیام‌های داخل گروه واکنشی نشون نده
                if message["chat"].get("type") != "private":
                    continue

                chat_id = message["chat"]["id"]
                user_id = message["from"]["id"]
                text = message.get("text", "")

                print(f"chat_id={chat_id} user_id={user_id} text={text}")

                if not text:
                    continue

                if user_id not in SELLERS:
                    send_message(chat_id, "شما مجاز به استفاده از این بات نیستید.")
                    continue

                if text == "/start":
                    start_order(chat_id, user_id)
                elif text == "/cancel":
                    cancel_order(chat_id, user_id)
                else:
                    handle_order_text(chat_id, user_id, text)

        except Exception as e:
            print("خطا:", e)
            time.sleep(3)


run()
