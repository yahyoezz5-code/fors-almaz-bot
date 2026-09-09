import asyncio
import base64
import io
import json
import logging
import os
import urllib.request
from aiohttp import ClientSession, ClientTimeout, web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    BufferedInputFile,
    ReplyKeyboardRemove
)

import config
import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

def get_webapp_url():
    return config.WEB_APP_URL

# ----------------- TELEGRAM BOT HANDLERS -----------------

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    database.get_or_create_user(user.id, user.username or "", user.first_name or "")

    welcome_text = (
        f"👋 **Ассалому алейкум ва раҳматуллоҳи ва баракотуҳ, {user.first_name}!**\n\n"
        f"💎 **Хуш омадед ба платформаи расмӣ ва боэътимоди «Fors Almaz Bot»!**\n\n"
        f"⚡️ Ин ҷо беҳтарин ва арзонтарин макон барои хариди алмосҳои Free Fire ва дигар хизматрасониҳои рақамӣ бо кафолати 100% мебошад.\n\n"
        f"📌 **Афзалиятҳои мо:**\n"
        f"└ 🚀 **Хариди худкор:** Иҷрои фаврии фармоишҳо дар чанд сония\n"
        f"└ 🛡 **Бехатарии комил:** Ҳимояи пурраи аккаунти шумо\n"
        f"└ 💰 **Нархҳои дастрас:** Беҳтарин тарифҳо дар бозори Тоҷикистон\n"
        f"└ 🔥 **Бозиҳои маҳбуб:** Махсус барои бозингарони Free Fire ва дигар лоиҳаҳо\n"
        f"└ 👨‍💻 **Дастгирии 24/7:** Ҳамеша омодаем ба саволҳои шумо ҷавоб диҳем\n\n"
        f"👇 Барои ворид шудан ба мағоза ва харид, тугмаи зеринро пахш кунед:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Донат кардан ✅", web_app=WebAppInfo(url=get_webapp_url()))]
    ])

    # Remove any old reply keyboard for clean chat experience
    await message.answer(welcome_text, reply_markup=kb, parse_mode="Markdown")

# Admin photo approval callbacks
@dp.callback_query(F.data.startswith("dep_app_"))
async def callback_deposit_approve(call: types.CallbackQuery):
    parts = call.data.split("_")
    dep_id = int(parts[2])
    amount = float(parts[3])

    dep = database.get_deposit(dep_id)
    if not dep or dep["status"] != "pending":
        await call.answer("Ин чек аллакай санҷида шудааст!", show_alert=True)
        return

    database.update_deposit_status(dep_id, "approved")
    database.add_balance(dep["user_id"], amount)

    await call.message.edit_caption(
        caption=call.message.caption + f"\n\n✅ **ТАСДИҚ ШУД (+{amount:.1f} сомонӣ)**",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await call.answer(f"Тасдиқ шуд: +{amount} TJS")

    try:
        await bot.send_message(
            dep["user_id"],
            f"🎉 **Муборак бошад!**\n\n"
            f"Баланси шумо ба миқдори **+{amount:.1f} сомонӣ** пур карда шуд!\n"
            f"Акнун метавонед ба мағоза ворид шуда, алмаз харед.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify user about deposit: {e}")

@dp.callback_query(F.data.startswith("dep_rej_"))
async def callback_deposit_reject(call: types.CallbackQuery):
    parts = call.data.split("_")
    dep_id = int(parts[2])

    dep = database.get_deposit(dep_id)
    if not dep or dep["status"] != "pending":
        await call.answer("Ин чек аллакай баррасӣ шудааст!", show_alert=True)
        return

    database.update_deposit_status(dep_id, "rejected")

    await call.message.edit_caption(
        caption=call.message.caption + "\n\n❌ **РАД КАРДА ШУД**",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await call.answer("Чек рад карда шуд")

    try:
        await bot.send_message(
            dep["user_id"],
            "❌ **Мутаассифона чеки пардохти шумо тасдиқ нашуд.**\n"
            "Агар хатогӣ рух дода бошад, ба дастгирӣ (@yahyoezz5) муроҷиат намоед.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify user about rejection: {e}")

# Order fulfillment callbacks
@dp.callback_query(F.data.startswith("ord_done_"))
async def callback_order_done(call: types.CallbackQuery):
    order_id = int(call.data.split("_")[2])
    order = database.get_order(order_id)
    if not order:
        await call.answer("Фармоиш ёфт нашуд!", show_alert=True)
        return

    database.update_order_status(order_id, "completed")
    await call.message.edit_text(
        text=call.message.text + "\n\n✅ **АЛМАЗҲО ВОРИД КАРДА ШУДАНД!**",
        reply_markup=None
    )
    await call.answer("Иҷро шуд!")

    try:
        await bot.send_message(
            order["user_id"],
            f"💎 **МУБОРАК БОШАД!**\n\n"
            f"Алмазҳои шумо барои маҳсулоти **«{order['item_title']}»** ба аккаунти Free Fire (ID: `{order['uid']}`) бо муваффақият партофта шуданд! 🚀\n\n"
            f"🎮 Бозии хуш ва ғалабаҳои нав таманно дорем! 🔥",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

@dp.callback_query(F.data.startswith("ord_canc_"))
async def callback_order_cancel(call: types.CallbackQuery):
    order_id = int(call.data.split("_")[2])
    order = database.get_order(order_id)
    if not order or order["status"] != "pending":
        await call.answer("Фармоиш аллакай баррасӣ шудааст!", show_alert=True)
        return

    database.update_order_status(order_id, "cancelled")
    database.refund_balance(order["user_id"], order["price"])

    await call.message.edit_text(
        text=call.message.text + f"\n\n❌ **БЕКОР ШУД ВА ПУЛ БОЗГАРДОНИДА ШУД ({order['price']} TJS)**",
        reply_markup=None
    )
    await call.answer("Фармоиш бекор ва пул баргардонида шуд")

    try:
        await bot.send_message(
            order["user_id"],
            f"⚠️ **Фармоиши шумо барои «{order['item_title']}» бекор карда шуд.**\n"
            f"Маблағи **{order['price']:.1f} сомонӣ** ба баланси шумо баргардонида шуд.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

# WebApp Data received via sendData
@dp.message(F.web_app_data)
async def handle_webapp_direct_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("type") == "order":
            await process_incoming_order(
                user_id=message.from_user.id,
                username=message.from_user.username or "",
                first_name=message.from_user.first_name or "",
                item_id=data.get("item_id", ""),
                item_title=data.get("item_title", data.get("title", "")),
                diamonds=int(data.get("diamonds", 0)),
                price=float(data.get("price", 0.0)),
                uid=str(data.get("uid", "")),
                nickname=str(data.get("nickname", "")),
                region=str(data.get("region", "СНГ"))
            )
    except Exception as e:
        logger.error(f"Error webapp data: {e}")

async def process_incoming_order(user_id, username, first_name, item_id, item_title, diamonds, price, uid, nickname, region="СНГ"):
    success = database.deduct_balance(user_id, price)
    if not success:
        return False, "Маблағ дар баланси шумо кифоя нест!"

    order_id = database.create_order(user_id, item_id, item_title, diamonds, price, uid, nickname, region)

    # Notify User
    try:
        await bot.send_message(
            user_id,
            f"🛒 **ФАРМОИШИ ШУМО ҚАБУЛ ШУД #{order_id}**\n\n"
            f"💎 Маҳсулот: **{item_title}**\n"
            f"🎮 Free Fire ID: `{uid}`\n"
            f"👤 Ник: **{nickname}**\n"
            f"🌐 Минтақа: **{region}**\n"
            f"💰 Нарх: **{price:.1f} сомонӣ** (Аз баланс пардохта шуд)\n\n"
            f"⏳ **Статус: Дар раванди иҷро...**\n"
            f"Алмазҳо дар давоми 1-3 дақиқа ворид карда мешаванд!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"User order notification error: {e}")

    # Notify Admin
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Алмазҳо ворид шуданд", callback_data=f"ord_done_{order_id}"),
            InlineKeyboardButton(text="❌ Бекор кардан", callback_data=f"ord_canc_{order_id}")
        ]
    ])

    admin_text = (
        f"🚨 **ФАРМОИШИ НАВИ FREE FIRE #{order_id}**\n\n"
        f"👤 Корбар: [{first_name}](tg://user?id={user_id}) (@{username})\n"
        f"🆔 Telegram ID: `{user_id}`\n\n"
        f"🎮 **Free Fire UID:** `{uid}`\n"
        f"📛 **Ник:** `{nickname}`\n"
        f"🌐 **Минтақа:** `{region}`\n"
        f"💎 **Маҳсулот:** {item_title}\n"
        f"💰 **Нарх:** {price:.1f} TJS (Пардохта шуд)\n\n"
        f"Алмазҳоро ба аккаунти бозигар партоед ва тугмаи зерро пахш намоед:"
    )

    try:
        await bot.send_message(config.ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Admin order notification error: {e}")

    return True, order_id

# ----------------- HTTP SERVER & REST API -----------------

async def api_get_user(request):
    user_id = request.query.get("user_id")
    if not user_id:
        return web.json_response({"success": False}, headers={"Access-Control-Allow-Origin": "*"})

    u = database.get_user(int(user_id))
    if not u:
        u = database.get_or_create_user(int(user_id))
    return web.json_response({
        "success": True,
        "user_id": u["user_id"],
        "balance": u["balance"],
        "spent": u["spent"]
    }, headers={"Access-Control-Allow-Origin": "*"})

async def api_get_history(request):
    user_id = request.query.get("user_id")
    if not user_id:
        return web.json_response({"success": False, "orders": [], "deposits": []}, headers={"Access-Control-Allow-Origin": "*"})

    orders = database.get_user_orders(int(user_id), limit=30)
    deposits = database.get_user_deposits(int(user_id), limit=30)
    return web.json_response({
        "success": True,
        "orders": orders,
        "deposits": deposits
    }, headers={"Access-Control-Allow-Origin": "*"})


async def api_payment_config(request):
    """Public payment details displayed by the Mini App.

    The editable source of truth is config.DC_NEXT_NUMBER, so the card number
    never has to be changed in HTML or JavaScript.
    """
    return web.json_response({
        "success": True,
        "method": "DC.NEXT",
        "card_number": config.DC_NEXT_NUMBER,
    }, headers={"Access-Control-Allow-Origin": "*"})

async def api_check_uid(request):
    uid = request.query.get("uid", "").strip()
    region = request.query.get("region", "CIS").strip().upper()
    # The provider groups CIS and several neighbouring regions under SG.
    region = {"СНГ": "SG", "CIS": "SG", "RU": "SG", "ID": "SG", "ME": "SG", "VN": "SG", "TH": "SG", "TW": "SG", "MY": "SG", "PK": "SG", "BD": "SG", "US": "BR", "NA": "BR", "LATAM": "BR"}.get(region, region)
    headers = {"Access-Control-Allow-Origin": "*"}

    if not uid.isdigit() or not 6 <= len(uid) <= 12:
        return web.json_response({"success": False, "status": "invalid", "message": "UID must contain 6–12 digits."}, status=400, headers=headers)

    api_key = getattr(config, "FF_API_KEY", "")
    profile_api_url = getattr(config, "FF_PROFILE_API_URL", "https://developers.freefirecommunity.com/api/v1/info")
    ban_check_api_url = getattr(config, "FF_BAN_CHECK_API_URL", "https://developers.freefirecommunity.com/api/v1/bancheck")
    if not api_key:
        logger.error("FF_API_KEY is not configured")
        return web.json_response({"success": False, "status": "unavailable", "message": "Player-check service is not configured."}, status=503, headers=headers)

    # The lookup may take longer after a provider's cold start. Do not fabricate
    # a nickname when it is unavailable: the client must never treat a failure as
    # a verified game account.
    try:
        timeout = ClientTimeout(total=15)
        async with ClientSession(timeout=timeout, headers={"User-Agent": "ForsAlmaz/1.0", "x-api-key": api_key}) as session:
            async with session.get(profile_api_url, params={"region": region, "uid": uid}) as response:
                if response.status == 404:
                    return web.json_response({"success": False, "status": "not_found", "message": "Player was not found."}, status=404, headers=headers)
                if response.status != 200:
                    logger.warning("FF profile API returned %s for UID %s", response.status, uid)
                    return web.json_response({"success": False, "status": "unavailable", "message": "Player-check service is temporarily unavailable."}, status=503, headers=headers)
                profile = await response.json(content_type=None)
    except Exception as exc:
        logger.warning("FF profile lookup failed for UID %s: %s", uid, exc)
        return web.json_response({"success": False, "status": "unavailable", "message": "Player-check service is temporarily unavailable."}, status=503, headers=headers)

    basic_info = profile.get("basicInfo") if isinstance(profile, dict) else None
    nickname = basic_info.get("nickname", "").strip() if isinstance(basic_info, dict) else ""
    if not nickname:
        return web.json_response({"success": False, "status": "not_found", "message": "Player was not found in this region."}, status=404, headers=headers)

    ban_checked = False
    is_banned = False
    ban_status = "unknown"
    if ban_check_api_url:
        try:
            timeout = ClientTimeout(total=12)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(ban_check_api_url, params={"uid": uid, "lang": "ru"}, headers={"x-api-key": api_key}) as response:
                    if response.status == 200:
                        ban_data = await response.json(content_type=None)
                        raw_status = str(ban_data.get("ban_status", "")).lower()
                        is_banned = ban_data.get("is_banned") in (True, 1, "1", "true", "True") or ("banned" in raw_status and "not banned" not in raw_status)
                        ban_status = str(ban_data.get("ban_status") or ("banned" if is_banned else "not banned"))
                        ban_checked = True
        except Exception as exc:
            logger.warning("FF ban lookup failed for UID %s: %s", uid, exc)

    if is_banned:
        return web.json_response({"success": False, "status": "banned", "uid": uid, "region": region, "nickname": nickname, "ban_checked": True, "ban_status": ban_status, "message": "This Free Fire account is blocked."}, headers=headers)

    return web.json_response({"success": True, "status": "active", "uid": uid, "region": region, "nickname": nickname, "level": basic_info.get("level"), "ban_checked": ban_checked, "ban_status": ban_status}, headers=headers)

async def api_buy(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"success": False, "message": "Invalid JSON"}, headers={"Access-Control-Allow-Origin": "*"})

    user_id = int(data.get("user_id", 0))
    u = database.get_user(user_id)
    if not u or u["balance"] < float(data.get("price", 0.0)):
        return web.json_response({"success": False, "message": "Маблағ дар баланси шумо кифоя нест!"}, headers={"Access-Control-Allow-Origin": "*"})

    ok, res = await process_incoming_order(
        user_id=user_id,
        username=u.get("username", ""),
        first_name=u.get("first_name", ""),
        item_id=data.get("item_id", ""),
        item_title=data.get("item_title", ""),
        diamonds=int(data.get("diamonds", 0)),
        price=float(data.get("price", 0.0)),
        uid=str(data.get("uid", "")),
        nickname=str(data.get("nickname", "")),
        region=str(data.get("region", "СНГ"))
    )

    if ok:
        updated_u = database.get_user(user_id)
        return web.json_response({"success": True, "order_id": res, "new_balance": updated_u["balance"]}, headers={"Access-Control-Allow-Origin": "*"})
    else:
        return web.json_response({"success": False, "message": res}, headers={"Access-Control-Allow-Origin": "*"})

async def api_upload_receipt(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        amount = float(data.get("amount", 20.0))
        img_b64 = data.get("image_base64", "")

        if "," in img_b64:
            img_b64 = img_b64.split(",")[1]

        image_bytes = base64.b64decode(img_b64)
        dep_id = database.create_deposit(user_id, amount, "b64_upload")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"✅ Тасдиқ ({amount:.0f} с.)", callback_data=f"dep_app_{dep_id}_{amount}"),
                InlineKeyboardButton(text="❌ Рад кардан", callback_data=f"dep_rej_{dep_id}")
            ]
        ])

        u = database.get_user(user_id) or {}
        caption = (
            f"📥 **ЧЕКИ НАВ АЗ САЙТ #DEP{dep_id}**\n\n"
            f"👤 Корбар: [{u.get('first_name', 'Корбар')}](tg://user?id={user_id})\n"
            f"🆔 ID: `{user_id}`\n"
            f"💰 Маблағ: **{amount:.1f} сомонӣ**\n\n"
            f"Барои тасдиқ тугмаи зерро пахш намоед:"
        )

        input_file = BufferedInputFile(image_bytes, filename=f"receipt_{dep_id}.jpg")
        await bot.send_photo(config.ADMIN_ID, photo=input_file, caption=caption, reply_markup=kb, parse_mode="Markdown")

        return web.json_response({"success": True, "deposit_id": dep_id}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"Receipt upload error: {e}")
        return web.json_response({"success": False, "message": str(e)}, headers={"Access-Control-Allow-Origin": "*"})

def setup_web_app():
    app = web.Application()
    app.router.add_get("/api/user", api_get_user)
    app.router.add_get("/api/history", api_get_history)
    app.router.add_get("/api/payment_config", api_payment_config)
    app.router.add_get("/api/check_uid", api_check_uid)
    app.router.add_post("/api/buy", api_buy)
    app.router.add_post("/api/upload_receipt", api_upload_receipt)

    static_path = os.path.join(os.path.dirname(__file__), "static")
    app.router.add_static("/", path=static_path, name="static", show_index=True)
    return app

async def main():
    database.init_db()

    app = setup_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    host = getattr(config, "HOST", "0.0.0.0")
    port = int(getattr(config, "PORT", 8080))
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"🚀 Web Server running at http://localhost:{port}")
    logger.info("🤖 Bot polling started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
