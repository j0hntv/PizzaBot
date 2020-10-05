import logging
import os
import redis
import telegram
import elasticpath

from dotenv import load_dotenv
from functools import partial
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils import fetch_coordinates


logger = logging.getLogger('telegram_shop')


def start(bot, update):
    token = elasticpath_token()
    products = {product['name']: product['id'] for product in elasticpath.get_products(token)['data']}
    keyboard = [[InlineKeyboardButton(product_name, callback_data=product_id)] for product_name, product_id in products.items()]
    keyboard.append([InlineKeyboardButton('🛒 Корзина', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        update.message.reply_text(
            'Выбирайте, пожалуйста:',
            reply_markup=reply_markup
        )
    else:
        chat_id = update.callback_query.message.chat_id
        message_id = update.callback_query.message.message_id
        bot.send_message(
            chat_id=chat_id,
            reply_markup=reply_markup,
            text='Выбирайте, пожалуйста:'
        )
        bot.delete_message(chat_id=chat_id, message_id=message_id)

    return 'HANDLE_MENU'


def handle_menu(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    token = elasticpath_token()

    if query.data == 'cart':
        send_cart_keyboard(bot, chat_id)
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        return 'HANDLE_CART'

    product_id = query.data
    product = elasticpath.get_products(token, product_id)
    product_image_id = product['data']['relationships']['main_image']['data']['id']
    product_image_url = elasticpath.get_image_url(token, product_image_id)

    caption = elasticpath.get_product_markdown_output(product)

    keyboard = [
        [InlineKeyboardButton('🛒 Положить в корзину', callback_data=f'buy/{product_id}')],
        [InlineKeyboardButton('◀️ Назад', callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_photo(
        chat_id=chat_id,
        photo=product_image_url,
        caption=caption,
        parse_mode=telegram.ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

    bot.delete_message(chat_id=chat_id, message_id=message_id)

    return 'HANDLE_DESCRIPTION'


def handle_description(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id

    action = query.data.split('/')

    if action[0] == 'back':
        return start(bot, update)

    elif action[0] == 'buy':
        product_id = action[1]
        token = elasticpath_token()
        elasticpath.add_product_to_cart(token, chat_id, product_id)
        update.callback_query.answer('Товар добавлен в корзину')
        return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id


    if query.data == 'menu':
        return start(bot, update)

    elif query.data == 'pay':
        bot.send_message(
            chat_id=chat_id,
            text='Пришлите нам ваш адрес текстом или геолокацию.'
        )
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        return 'HANDLE_WAITING_LOCATION'

    product_id = query.data
    token = elasticpath_token()
    elasticpath.remove_cart_item(token, chat_id, product_id)

    send_cart_keyboard(bot, chat_id)
    bot.delete_message(chat_id=chat_id, message_id=message_id)
    return 'HANDLE_CART'


def handle_waiting_location(bot, update):
    chat_id = update.message.chat_id
    message = update.edited_message or update.message

    if message.location:
        latitude = message.location.latitude
        longitude = message.location.longitude
    else:
        try:
            latitude, longitude = fetch_coordinates(YANDEX_GEOCODER_KEY, message.text)
        except IndexError:
            bot.send_message(
                chat_id = chat_id,
                text=f'Кажется, вы ошиблись в адресе, повторите пожалуйста:'
            )
            return 'HANDLE_WAITING_LOCATION'

    keyboard = [
        [InlineKeyboardButton(f'◀️ В меню', callback_data='start')]
    ]

    bot.send_message(
        chat_id = chat_id,
        text=f'Ваши координаты:\n{latitude}, {longitude}\n\n*Заказ уже в пути.* 🚀',
        parse_mode=telegram.ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    # customer_name = message.chat.first_name
    # token = elasticpath_token()
    # elasticpath.create_customer(token, name=customer_name, email=text)
    return 'START'


def handle_users_reply(bot, update):
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
    else:
        try:
            user_state = db.get(chat_id)
        except redis.exceptions.RedisError as error:
            logger.error(error)

    
    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'HANDLE_WAITING_LOCATION': handle_waiting_location
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(bot, update)
        db.set(chat_id, next_state)
    except Exception as error:
        logger.error(error)


def send_cart_keyboard(bot, chat_id):
    token = elasticpath_token()
    cart = elasticpath.get_a_cart(token, chat_id)
    cart_items = elasticpath.get_cart_items(token, chat_id)
    menu_button = [[InlineKeyboardButton('◀️ Меню', callback_data='menu')]]
    pay_button = [[InlineKeyboardButton('🤑 Оплатить', callback_data='pay')]]

    if not cart_items:
        bot.send_message(
            chat_id=chat_id,
            text='В корзине ничего нет :(',
            reply_markup=InlineKeyboardMarkup(menu_button),
        )

        return

    cart_items_formatted = elasticpath.get_formatted_cart_items(cart, cart_items)
    keyboard = [
        [InlineKeyboardButton(f'❌ Удалить {product["name"]}', callback_data=product['id'])] for product in cart_items
    ] + pay_button + menu_button

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(
        chat_id=chat_id,
        text=cart_items_formatted,
        reply_markup=reply_markup,
        parse_mode=telegram.ParseMode.MARKDOWN
    )


def get_database_connection():
    db = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )

    return db


if __name__ == '__main__':
    load_dotenv()

    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = os.getenv('REDIS_PORT')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    YANDEX_GEOCODER_KEY = os.getenv('YANDEX_GEOCODER_KEY')

    db = get_database_connection()
    elasticpath_token = partial(elasticpath.get_oauth_access_token, db, CLIENT_ID, CLIENT_SECRET)

    updater = Updater(TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.location, handle_waiting_location))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()
