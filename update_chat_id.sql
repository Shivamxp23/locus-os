UPDATE users SET telegram_chat_id = '8249321165' WHERE display_name = 'Shivam' AND telegram_chat_id = '8089688853';
SELECT id, display_name, telegram_chat_id FROM users WHERE telegram_chat_id IS NOT NULL;
