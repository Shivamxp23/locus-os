UPDATE users SET telegram_chat_id = '8089688853' WHERE display_name = 'Shivam' AND telegram_chat_id = '8249321165';
SELECT display_name, telegram_chat_id FROM users WHERE telegram_chat_id IS NOT NULL;
