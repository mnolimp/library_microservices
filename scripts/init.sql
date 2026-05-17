-- Создаем схемы для каждого микросервиса
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS lending;
CREATE SCHEMA IF NOT EXISTS digital;
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE auth.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    github_id VARCHAR(64) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE auth.oauth_states (
    id SERIAL PRIMARY KEY,
    state VARCHAR(128) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_auth_users_email ON auth.users(email);
CREATE INDEX idx_auth_users_github_id ON auth.users(github_id);
CREATE INDEX idx_auth_oauth_states_state ON auth.oauth_states(state);

CREATE TABLE catalog.books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    isbn VARCHAR(20) UNIQUE NOT NULL,
    publication_year INTEGER,
    description TEXT,
    book_type VARCHAR(20) DEFAULT 'physical' CHECK (book_type IN ('physical', 'digital', 'both')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE catalog.book_copies (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES catalog.books(id) ON DELETE CASCADE,
    copy_number INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'available' CHECK (status IN ('available', 'loaned', 'maintenance', 'lost')),
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, copy_number)
);

CREATE INDEX idx_catalog_books_title ON catalog.books(title);
CREATE INDEX idx_catalog_books_author ON catalog.books(author);
CREATE INDEX idx_catalog_books_isbn ON catalog.books(isbn);
CREATE INDEX idx_catalog_copies_book_id ON catalog.book_copies(book_id);
CREATE INDEX idx_catalog_copies_status ON catalog.book_copies(status);

CREATE TABLE users.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Индексы для users
CREATE INDEX idx_users_email ON users.users(email);
CREATE INDEX idx_users_full_name ON users.users(full_name);

CREATE TABLE lending.loans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    book_copy_id INTEGER NOT NULL,
    loan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP NOT NULL,
    return_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'returned', 'overdue', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE RESTRICT,
    FOREIGN KEY (book_copy_id) REFERENCES catalog.book_copies(id) ON DELETE RESTRICT
);

CREATE INDEX idx_lending_loans_user_id ON lending.loans(user_id);
CREATE INDEX idx_lending_loans_book_copy_id ON lending.loans(book_copy_id);
CREATE INDEX idx_lending_loans_status ON lending.loans(status);
CREATE INDEX idx_lending_loans_due_date ON lending.loans(due_date);
CREATE INDEX idx_lending_loans_user_status ON lending.loans(user_id, status);

CREATE TABLE digital.digital_books (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    format VARCHAR(20) DEFAULT 'pdf' CHECK (format IN ('pdf', 'epub', 'mobi')),
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES catalog.books(id) ON DELETE CASCADE,
    UNIQUE(book_id)
);

CREATE TABLE digital.digital_access_log (
    id SERIAL PRIMARY KEY,
    digital_book_id INTEGER REFERENCES digital.digital_books(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users.users(id) ON DELETE CASCADE,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);

CREATE INDEX idx_digital_books_book_id ON digital.digital_books(book_id);
CREATE INDEX idx_digital_access_log_user ON digital.digital_access_log(user_id);
CREATE INDEX idx_digital_access_log_time ON digital.digital_access_log(access_time);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_loans_updated_at 
    BEFORE UPDATE ON lending.loans 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON SCHEMA catalog IS 'Схема для сервиса каталога книг';
COMMENT ON SCHEMA users IS 'Схема для сервиса пользователей';
COMMENT ON SCHEMA lending IS 'Схема для сервиса выдачи книг';
COMMENT ON SCHEMA digital IS 'Схема для сервиса электронных книг';

COMMENT ON TABLE catalog.books IS 'Книги в библиотеке';
COMMENT ON TABLE catalog.book_copies IS 'Физические экземпляры книг';
COMMENT ON TABLE users.users IS 'Пользователи библиотеки';
COMMENT ON TABLE lending.loans IS 'Записи о выдаче/возврате книг';
COMMENT ON TABLE digital.digital_books IS 'Электронные версии книг';
COMMENT ON TABLE digital.digital_access_log IS 'Лог доступа к электронным книгам';

-- =====================================================
-- ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ (100+ записей)
-- =====================================================

-- Генерация 100 книг
INSERT INTO catalog.books (title, author, isbn, publication_year, description, book_type)
SELECT 
    'Book ' || generate_series,
    'Author ' || (random() * 20)::int,
    'ISBN-' || generate_series,
    1900 + (random() * 120)::int,
    'Description for book ' || generate_series,
    (ARRAY['physical', 'digital', 'both'])[floor(random() * 3) + 1]
FROM generate_series(1, 100);

-- Генерация 150 экземпляров книг
INSERT INTO catalog.book_copies (book_id, copy_number, status, location)
SELECT 
    (random() * 99 + 1)::int,
    generate_series,
    (ARRAY['available', 'available', 'loaned', 'maintenance'])[floor(random() * 4) + 1],
    'Shelf ' || (random() * 20)::int
FROM generate_series(1, 150)
CROSS JOIN (SELECT generate_series as copy_num FROM generate_series(1, 1)) t;

-- Генерация 100 пользователей
INSERT INTO users.users (email, full_name, phone, address)
SELECT 
    'user' || generate_series || '@example.com',
    'User ' || generate_series,
    '+7-900-' || LPAD(generate_series::text, 7, '0'),
    'Address ' || generate_series
FROM generate_series(1, 100);

-- Генерация 100+ выдач
INSERT INTO lending.loans (user_id, book_copy_id, loan_date, due_date, status)
SELECT 
    (random() * 99 + 1)::int,
    (random() * 149 + 1)::int,
    CURRENT_TIMESTAMP - (random() * 180 || ' days')::interval,
    CURRENT_TIMESTAMP + (random() * 30 || ' days')::interval,
    (ARRAY['active', 'active', 'returned', 'overdue'])[floor(random() * 4) + 1]
FROM generate_series(1, 150);
