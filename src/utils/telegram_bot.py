import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

class TelegramController:
    def __init__(self, token, owner_chat_id, engine):
        self.token = token
        self.owner_chat_id = str(owner_chat_id)
        self.engine = engine
        self.pending_trades = {}

    async def check_auth(self, update: Update) -> bool:
        if str(update.effective_chat.id) != self.owner_chat_id:
            if update.message:
                await update.message.reply_text("⛔ غير مسموح لك بالوصول (Zero-Trust).")
            return False
        return True

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        mode_text = "🟢 Auto Mode" if self.engine.auto_mode else "🎛️ Manual / Hybrid UI"
        text = f"🏛️ **Khtb Command Center v3.5**\n\nحالة النظام: {mode_text}\nاختر الإجراء المناسب:"
        keyboard = [
            [InlineKeyboardButton("🔍 فحص السوق", callback_data="scan_market"),
             InlineKeyboardButton("⚙️ تبديل الأوتو", callback_data="toggle_auto")]
        ]
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if str(query.message.chat_id) != self.owner_chat_id: return

        data = query.data
        if data == "scan_market":
            await query.edit_message_text("🔍 جاري فحص السوق وقياس الزخم وفوليوم السورج...")
            pkg = self.engine.evaluate_pair("SOL/USDT")
            if not pkg:
                await query.message.reply_text("⚠️ لا توجد فرص مطابقة حالياً.")
                return

            if self.engine.auto_mode:
                self.engine.execute_live_trade(pkg)
                await query.message.reply_text(f"🚀 **تم التنفيذ تلقائياً**\nالعملة: {pkg['symbol']}")
            else:
                trade_id = f"trade_{int(time.time())}"
                self.pending_trades[trade_id] = pkg
                card = (
                    f"🚨 **فرصة تداول (100% Position Ride)** 🚨\n\n"
                    f"🪙 العملة: {pkg['symbol']}\n💵 الدخول: `{pkg['entry']}`\n"
                    f"🛡️ الستوب الأولي: `{pkg['sl']}`\n🎯 TP1 (للتأمين الهيكلي وإلغائه): `{pkg['tp1']}`\n"
                    f"📦 الحجم الكامل: `{pkg['units']:.4f}`"
                )
                kb = [
                    [InlineKeyboardButton("✅ تنفيذ فوري", callback_data=f"exec_{trade_id}"),
                     InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_{trade_id}")],
                    [InlineKeyboardButton("📈 شارت 15د", callback_data=f"chart_{trade_id}"),
                     InlineKeyboardButton("⚙️ الرافعة", callback_data=f"lev_{trade_id}")]
                ]
                await query.message.reply_text(card, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

        elif data.startswith("exec_"):
            tid = data.split("_", 1)[1]
            if tid in self.pending_trades:
                pkg = self.pending_trades[tid]
                self.engine.execute_live_trade(pkg)
                await query.edit_message_text(f"✅ **تم التنفيذ بنجاح بكامل البوزيشن!** ({pkg['symbol']})")
                del self.pending_trades[tid]

        elif data.startswith("chart_"):
            tid = data.split("_", 1)[1]
            if tid in self.pending_trades:
                buf = self.engine.generate_chart_image(self.pending_trades[tid]['df_15m'])
                await query.message.reply_photo(photo=InputFile(buf, filename="chart.png"), caption="📊 شارت 15د")

        elif data.startswith("lev_"):
            tid = data.split("_", 1)[1]
            if tid in self.pending_trades:
                kb = [[InlineKeyboardButton(f"{l}x", callback_data=f"setlev_{tid}_{l}") for l in [5, 10, 20, 50]]]
                await query.message.reply_text("اختر رافعة الصفقة:", reply_markup=InlineKeyboardMarkup(kb))

        elif data.startswith("setlev_"):
            parts = data.split("_")
            tid = f"{parts[1]}_{parts[2]}"
            if tid in self.pending_trades:
                self.pending_trades[tid]['leverage'] = int(parts[3])
                await query.edit_message_text(f"⚙️ تم تعديل الرافعة إلى **{parts[3]}x**", parse_mode="Markdown")

        elif data == "toggle_auto":
            self.engine.auto_mode = not self.engine.auto_mode
            await query.edit_message_text(f"تم تعديل وضع الأوتو: {self.engine.auto_mode}")

    def run(self):
        app = ApplicationBuilder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.run_polling()
