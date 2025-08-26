import sqlite3
DB_PATH = "src/data/ComboSender.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute(
    """CREATE TABLE IF NOT EXISTS emails (
    email TEXT PRIMARY KEY,
    status TEXT
)"""
)
c.execute(
    """CREATE TABLE IF NOT EXISTS input_channels (
    channel_id TEXT PRIMARY KEY
)"""
)
c.execute(
    """CREATE TABLE IF NOT EXISTS output_channels (
    channel_id TEXT PRIMARY KEY,
    file_name TEXT
)"""
)
c.execute(
    """CREATE TABLE IF NOT EXISTS channel_rights_emails (
    channel_id TEXT,
    email TEXT,
    PRIMARY KEY (channel_id, email)
)"""
)
conn.commit()
