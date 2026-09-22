import asyncio
import sqlite3
from datetime import datetime
from config import api_key, admin_password
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

bot = Bot(api_key)
dp = Dispatcher()

db = 'database.sql'

class Bid(StatesGroup):
    waitingText = State()

class auth(StatesGroup):
    password = State()

class editBidState(StatesGroup):
    waitingText = State()

class ReplyState(StatesGroup):
    waitingId = State()
    waitingText = State()

class closeBidState(StatesGroup):
    waitingId = State()
    sumbit = State()

def DbInit():
    conn = sqlite3.connect(db)
    conn.execute('CREATE TABLE IF NOT EXISTS bid(id INTEGER PRIMARY KEY AUTOINCREMENT, first_name VARCHAR(20), user_id VARCHAR(20), user_tg_id VARCHAR(20), bid TEXT, status VARCHAR(10))')
    conn.commit()
    conn.close()

def SaveBid(name, username, userId, bid):
    conn = sqlite3.connect(db)
    conn.execute('INSERT INTO bid(first_name, user_id, user_tg_id, bid, status) VALUES(?, ?, ?, ?, ?)', (name, username, userId, bid, 'active'))
    conn.commit()
    conn.close()

def EditBid(bid, userId):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM bid WHERE user_tg_id = ?', (userId,))
    data = cur.fetchall()
    if data:
        conn.execute('UPDATE bid SET bid = ? WHERE user_tg_id = ? AND status = ?', (bid, userId, 'active',))
        conn.commit()
    else:
        pass

    cur.close()
    conn.close()


@dp.message(Command('start'))
async def main(message: types.Message, state: FSMContext):
    await state.clear()
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Оставить заявку', callback_data='bid')],
        [types.InlineKeyboardButton(text='Меню', callback_data='back')]
    ])

    hour = datetime.now().hour
    helloMsg = 'Доброго'

    if 5 <= hour <= 11:
        time = 'утра'
    elif 12 <= hour <= 16:
        time = 'дня'
    elif 17 <= hour <= 23:
        time = 'вечера'
    else:
        helloMsg = 'Доброй'
        time = 'ночи'

    await message.delete()
    await message.answer(f'{helloMsg} {time}! Здесь вы можете прислать мне сообщение или оставить заявку.\nЯ обязательно свяжусь с вами!', reply_markup=markup)

@dp.callback_query(F.data == 'bid')
async def sumbitRequest(callback: types.CallbackQuery, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Назад', callback_data='back')]
    ])

    conn = sqlite3.connect('database.sql')
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM bid WHERE user_tg_id = ? AND status = ?', (callback.from_user.id, 'active',))
    exists = cur.fetchall()
    cur.close()
    conn.close()

    if exists:
        await callback.message.edit_text(text='У вас уже открыта заявка, ожидайте.', reply_markup=markup)
        await callback.answer()
        return

    await state.set_state(Bid.waitingText)
    await callback.message.edit_text(text='Пожалуйста, опишите вашу заявку одним сообщением!')
    await callback.answer()

@dp.message(Bid.waitingText, F.text)
async def getBidText(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Назад', callback_data='back')]
    ])

    user = message.from_user
    SaveBid(user.first_name, user.username, user.id, message.text)

    await message.answer(text='Ваша заявка успешно принята.', reply_markup=markup)
    await state.clear()

@dp.callback_query(F.data == 'back')
async def backToMenu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Отправить заявку', callback_data='bid')],
        [types.InlineKeyboardButton(text='Просмотреть свою заявку', callback_data='checkBid')],
        [types.InlineKeyboardButton(text='Закрыть меню', callback_data='close')]        
    ])
    await callback.message.edit_text(text='MAIN MENU', reply_markup=markup)

@dp.callback_query(F.data == 'checkBid')
async def checkYourBid(callback: types.CallbackQuery):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Редактировать заявку', callback_data='edit_bid')],
        [types.InlineKeyboardButton(text='Назад', callback_data='back')]
    ])

    conn = sqlite3.connect('database.sql')
    cur = conn.cursor()
    cur.execute('SELECT * FROM bid WHERE user_tg_id = ? AND status = ?', (callback.from_user.id, 'active',))
    data = cur.fetchall()
    cur.close()
    conn.close()

    if not data:
        info = 'У вас нет активных заявок.'
    else:
        info = ''
        for i in data:
            info += f'Ваше сообщение:\n\n{i[4]}'

    await callback.message.edit_text(text=info, reply_markup=markup)
    await callback.answer()

@dp.callback_query(F.data == 'edit_bid')
async def requestToEditBid(callback: types.CallbackQuery, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Назад', callback_data='back')]
    ])

    conn = sqlite3.connect('database.sql')
    cur = conn.cursor()

    cur.execute('SELECT 1 FROM bid WHERE user_tg_id = ? and status = "active"', (callback.from_user.id,) )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        await callback.message.edit_text(text='У вас нет активных заявок.', reply_markup=markup)
        await state.clear()
        await callback.answer()
    else:
        await state.set_state(editBidState.waitingText)
        await callback.message.answer(text='Напишите заявку заново.')
        await callback.answer()

@dp.message(editBidState.waitingText, F.text)
async def editBid(message: types.Message, state: FSMContext):
    await state.clear()
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Посмотреть заявку', callback_data='checkBid')],
        [types.InlineKeyboardButton(text='Редактировать заявку', callback_data='edit_bid')],
        [types.InlineKeyboardButton(text='Назад', callback_data='back')]
    ])

    user = message.from_user
    EditBid(message.text, user.id)

    for offset in (2, 1):
        try:
            await bot.delete_message(message.chat.id, message.message_id - offset)
        except TelegramBadRequest:
            pass

    await message.delete()
    await message.answer(text='Ваза заявка успешно отредактирована', reply_markup=markup)


@dp.message(Command('admin'))
async def authAdmin(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Назад', callback_data='back')]
    ])

    await state.set_state(auth.password)
    await message.delete()
    await message.answer(text=(
    '⠛⠛⣿⣿⣿⣿⣿⡷⢶⣦⣶⣶⣤⣤⣤⣀⠀⠀⠀\n'
    '⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀\n'
    '⠀⠀⠀⠉⠉⠉⠙⠻⣿⣿⠿⠿⠛⠛⠛⠻⣿⣿⣇⠀\n'
    '⠀⠀⢤⣀⣀⣀⠀⠀⢸⣷⡄⠀⣁⣀⣤⣴⣿⣿⣿⣆\n'
    '⠀⠀⠀⠀⠹⠏⠀⠀⠀⣿⣧⠀⠹⣿⣿⣿⣿⣿⡿⣿\n'
    '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠿⠇⢀⣼⣿⣿⠛⢯⡿⡟\n'
    '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠦⠴⢿⢿⣿⡿⠷⠀⣿⠀\n'
    '⠀⠀⠀⠀⠀⠀⠀⠙⣷⣶⣶⣤⣤⣤⣤⣤⣶⣦⠃⠀\n'
    '⠀⠀⠀⠀⠀⠀⠀⢐⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀\n'
    '⠀⠀⠀⠀⠀⠀⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀\n'
    '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠻⢿⣿⣿⣿⣿⠟'), reply_markup=markup
    )

@dp.message(auth.password, F.text)
async def get_access(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Посмотреть заявки', callback_data='check_requests')],
        [types.InlineKeyboardButton(text='Посмотреть закрытые заявки', callback_data='check_closed_requests')],
        [types.InlineKeyboardButton(text='Назад', callback_data='back')]
    ])

    if message.text == admin_password:
        await bot.delete_message(message.chat.id, message.message_id - 1)
        await message.delete()
        await message.answer(text='Админ-панель', reply_markup=markup)
        await state.clear()
    else:
        await state.clear()
        await bot.delete_message(message.chat.id, message.message_id - 1)
        await message.delete()

@dp.callback_query(F.data == 'backToAdmin')
async def adminPanel(callback: types.CallbackQuery, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text='Посмотреть заявки', callback_data='check_requests')],
            [types.InlineKeyboardButton(text='Посмотреть закрытые заявки', callback_data='check_closed_requests')],
            [types.InlineKeyboardButton(text='Назад', callback_data='back')]
        ])

    await state.clear()

    await callback.message.delete()
    await callback.message.answer(text='Админ-панель', reply_markup=markup)
      
@dp.callback_query(F.data == 'check_requests')
async def check_requests(callback: types.CallbackQuery):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Ответить на заявку', callback_data='reply_to_request')],
        [types.InlineKeyboardButton(text='Закрыть заявку', callback_data='closeBid')],
        [types.InlineKeyboardButton(text='Назад', callback_data='backToAdmin')]
    ])

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    cur.execute('SELECT * FROM bid WHERE status = ?', ('active',))

    data = cur.fetchall()
    info = ''

    for i in data:
        info += f'\nID: {i[0]}\nИмя: {i[1]}\nТег: @{i[2]}\nСтатус: {i[5]}\nСообщение:\n\n{i[4]}\n\n{'-~' * 15}\n'

    if not data:
        info = 'Активных заявок пока нет.'

    cur.close()
    conn.close()

    await callback.message.edit_text(text=f'Активные заявки\n {'-~' * 15}\n{info}', reply_markup=markup)
    await callback.answer()

@dp.callback_query(F.data == 'check_closed_requests')
async def check_closed_requests(callback: types.CallbackQuery):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Назад', callback_data='backToAdmin')]
    ])

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    cur.execute('SELECT * FROM bid WHERE status = ?', ('closed',))

    data = cur.fetchall()
    info = ''

    for i in data:
        info += f'\nID: {i[0]}\nИмя: {i[1]}\nТег: @{i[2]}\nСтатус: {i[5]}\nСообщение:\n\n{i[4]}\n\n{'-~' * 15}\n'

    if not data:
        info = 'Закрытых заявок пока нет.'

    cur.close()
    conn.close()

    await callback.message.edit_text(text=f'Закрытые заявки\n {'-~' * 15}\n{info}', reply_markup=markup)
    await callback.answer()


@dp.callback_query(F.data == 'closeBid')
async def closeBidGetId(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(closeBidState.waitingId)
    await callback.message.answer(text='ID заявки для закрытия:')
    await callback.answer()

@dp.message(closeBidState.waitingId, F.text)  
async def closeBid(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Да', callback_data='sumbitClose')],
        [types.InlineKeyboardButton(text='Назад', callback_data='backToAdmin')]
    ])

    if not message.text.isdigit():
        markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text='Назад', callback_data='backToAdmin')]
        ])
        await message.answer('ID должен быть числом. Попробуйте ещё раз.')
        return

    bidId = message.text
    await state.update_data(bidId=int(bidId))

    conn = sqlite3.connect('database.sql')
    cur = conn.cursor()
    cur.execute('SELECT * FROM bid WHERE id = ? and status = ?', (bidId, 'active',))
    data = cur.fetchall()

    cur.close()
    conn.close()

    info = ''
    for i in data:
        info += f'Тег отправителя: @{i[2]}\nСообщение:\n\n{i[4]}'

    if not data:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text='Назад', callback_data='backToAdmin')]
        ])
        await message.answer('Заявка с таким ID не найдена. Введите ID ещё раз.', reply_markup=markup)
        return


    await bot.delete_message(message.chat.id, message.message_id - 1)
    await message.delete()
    await message.answer(text=f'Вы уверены точно хотите закрыть заявку №{bidId}?\n{info}', reply_markup=markup)
    await state.set_state(closeBidState.sumbit)

@dp.callback_query(F.data == 'sumbitClose')
async def closingBid(callback: types.CallbackQuery, state:FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Назад', callback_data='close')]
    ])

    data = await state.get_data()
    targetId = data['bidId']

    conn = sqlite3.connect('database.sql')
    cur = conn.cursor()

    cur.execute('UPDATE bid SET status = ? WHERE id = ?', ('closed',targetId,))
    conn.commit()

    cur.close()
    conn.close()

    await state.clear()
    await callback.message.edit_text('Заявка была успешно закрыта.', reply_markup=markup)

@dp.callback_query(F.data == 'reply_to_request')
async def replyToRequest(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ReplyState.waitingId)
    await callback.message.answer(text='ID заявки для ответа:')
    await callback.answer()

@dp.message(ReplyState.waitingId, F.text)
async def getIdToRrequest(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Назад', callback_data='backToAdmin')]
    ])

    bidId = message.text

    conn = sqlite3.connect('database.sql')
    cur = conn.cursor()
    cur.execute('SELECT user_tg_id FROM bid WHERE id = ? AND status = ?', (bidId, 'active',))
    row = cur.fetchone()

    cur.close()
    conn.close()


    if not row:
        await message.answer('Заявка с таким ID не найдена. Введите ID ещё раз.', reply_markup=markup)
        return

    await state.update_data(targerUserId=int(row[0]), bidId=bidId)
    await state.set_state(ReplyState.waitingText)
    await message.answer(text='Текст ответа:')


@dp.message(ReplyState.waitingText, F.text)
async def sendReply(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='Назад', callback_data='backToAdmin')]
    ])
    data = await state.get_data()
    targerId = data['targerUserId']

    try:
        await bot.send_message(chat_id=targerId, text=f'Ответ на вашу заявку:\n\n{message.text}')
    except TelegramBadRequest:
        await message.answer(text='Не удалось отправить сообщение.', reply_markup=markup)
        await state.clear()
        return

    await state.clear()
    await message.answer(text='Ответ отправлен.', reply_markup=markup)

@dp.callback_query(F.data == 'close')
async def closeMenu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

async def run():
    DbInit()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(run())