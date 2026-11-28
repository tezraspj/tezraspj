"""Telegram notifications for new orders.

Tokens are read from environment variables only. When the bot is not
configured the notification is skipped (logged, never raises).
"""
import logging

import httpx

from .config import settings

logger = logging.getLogger("tezraspj.telegram")


def build_order_message(order: dict) -> str:
    lines = [
        "📦 *НОВЫЙ ЗАКАЗ — tezraspj*",
        f"🏪 Заведение: {order.get('restaurant_id')}",
        "",
        f"👤 Клиент: {order.get('client_name')}",
        f"📞 Телефон: {order.get('client_phone')}",
        f"📍 Адрес: {order.get('client_address')}",
    ]
    if order.get("client_comment"):
        lines.append(f"💬 Комментарий: {order['client_comment']}")
    lines.append("")
    lines.append("📋 Состав:")
    for i, item in enumerate(order.get("items", []), 1):
        lines.append(f"{i}. {item['name']} x{item['qty']} = {item['price'] * item['qty']} смн")
    lines.append("")
    lines.append(f"💵 Сумма: {order['subtotal']} смн")
    if order.get("discount"):
        lines.append(f"• Скидка ({order.get('promo_code')}): -{order['discount']} смн")
    fee = order["delivery_fee"]
    lines.append(f"• Доставка: {'бесплатно' if fee == 0 else str(fee) + ' смн'}")
    lines.append(f"💰 ИТОГО: *{order['total']} смн*")
    return "\n".join(lines)


async def send_order_notification(order: dict) -> bool:
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        logger.info("Telegram is not configured — notification skipped")
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": build_order_message(order), "parse_mode": "Markdown"},
            )
            if resp.status_code >= 400:
                logger.warning("Telegram API error %s: %s", resp.status_code, resp.text[:200])
                return False
            return True
    except Exception as exc:  # network problems must never break checkout
        logger.warning("Telegram notification failed: %s", exc)
        return False
