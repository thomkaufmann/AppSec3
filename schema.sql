-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS user;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  pin INTEGER
);

INSERT INTO user (username,password,pin) VALUES ('admin','pbkdf2:sha256:150000$FvnZM8fM$f37c7ec344b2aaef2d23ffd50507222e3215518c45ed7a326f986b4912c4c12b','19008675309');