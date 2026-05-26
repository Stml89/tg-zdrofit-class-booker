"""Tests for broadcast message feature."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TgUser, Message, Chat
from telegram.ext import ContextTypes

from src.telegram_bot.handlers import broadcast_command
from src.telegram_bot.notifications import NotificationSender


class TestBroadcastCommand(unittest.IsolatedAsyncioTestCase):
    """Test the /broadcast command handler."""

    def _make_update(self, user_id: int, text: str = "/broadcast Hello"):
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TgUser)
        update.effective_user.id = user_id
        update.message = AsyncMock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update

    def _make_context(self, args=None, bot=None):
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []
        context.bot = bot or AsyncMock()
        return context

    @patch("src.telegram_bot.handlers.ADMIN_TELEGRAM_IDS", [123456])
    async def test_non_admin_rejected(self):
        """Non-admin users should be rejected."""
        update = self._make_update(user_id=999999)
        context = self._make_context(args=["Hello"])

        await broadcast_command(update, context)

        update.message.reply_text.assert_called_once_with(
            "⛔ You are not authorized to use this command."
        )

    @patch("src.telegram_bot.handlers.ADMIN_TELEGRAM_IDS", [123456])
    async def test_empty_message_rejected(self):
        """Empty broadcast message should show usage."""
        update = self._make_update(user_id=123456)
        context = self._make_context(args=[])

        await broadcast_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Usage:", call_args)

    @patch("src.telegram_bot.handlers.db")
    @patch("src.telegram_bot.handlers.ADMIN_TELEGRAM_IDS", [123456])
    async def test_no_users_to_broadcast(self, mock_db):
        """Should inform admin when no users registered."""
        mock_db.get_all_user_telegram_ids.return_value = []
        update = self._make_update(user_id=123456)
        context = self._make_context(args=["Hello", "everyone"])

        await broadcast_command(update, context)

        update.message.reply_text.assert_called_once_with(
            "No registered users to broadcast to."
        )

    @patch("src.telegram_bot.handlers.db")
    @patch("src.telegram_bot.handlers.ADMIN_TELEGRAM_IDS", [123456])
    async def test_successful_broadcast(self, mock_db):
        """Should broadcast message and report results."""
        mock_db.get_all_user_telegram_ids.return_value = [111, 222, 333]
        update = self._make_update(user_id=123456)
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        context = self._make_context(args=["Maintenance", "tonight"], bot=bot)

        await broadcast_command(update, context)

        # Bot should have sent messages to all users
        self.assertEqual(bot.send_message.call_count, 3)
        # Admin should get summary
        reply_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Sent: 3", reply_text)
        self.assertIn("Failed: 0", reply_text)

    @patch("src.telegram_bot.handlers.db")
    @patch("src.telegram_bot.handlers.ADMIN_TELEGRAM_IDS", [123456])
    async def test_broadcast_with_failures(self, mock_db):
        """Should report failures when some sends fail."""
        mock_db.get_all_user_telegram_ids.return_value = [111, 222]
        update = self._make_update(user_id=123456)
        bot = AsyncMock()
        bot.send_message = AsyncMock(side_effect=[None, Exception("Blocked")])
        context = self._make_context(args=["Hello"], bot=bot)

        await broadcast_command(update, context)

        reply_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Sent: 1", reply_text)
        self.assertIn("Failed: 1", reply_text)


class TestNotificationSenderBroadcast(unittest.IsolatedAsyncioTestCase):
    """Test NotificationSender.broadcast_message method."""

    async def test_broadcast_message_success(self):
        """Should send to all users and return correct counts."""
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        sender = NotificationSender(bot=bot)

        result = await sender.broadcast_message([1, 2, 3], "Test message")

        self.assertEqual(result, {"sent": 3, "failed": 0})
        self.assertEqual(bot.send_message.call_count, 3)

    async def test_broadcast_message_partial_failure(self):
        """Should handle partial failures gracefully."""
        bot = AsyncMock()
        bot.send_message = AsyncMock(side_effect=[None, Exception("Blocked"), None])
        sender = NotificationSender(bot=bot)

        result = await sender.broadcast_message([1, 2, 3], "Test")

        self.assertEqual(result, {"sent": 2, "failed": 1})

    async def test_broadcast_message_empty_list(self):
        """Should handle empty user list."""
        bot = AsyncMock()
        sender = NotificationSender(bot=bot)

        result = await sender.broadcast_message([], "Test")

        self.assertEqual(result, {"sent": 0, "failed": 0})
        bot.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
