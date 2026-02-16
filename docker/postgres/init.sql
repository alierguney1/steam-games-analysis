-- Steam Games Analysis - Star Schema DDL
-- PostgreSQL initialization script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- Dimension Tables
-- ========================================

-- dim_date: Calendar dimension with Steam sale period flags
CREATE TABLE dim_date (
    date_id SERIAL PRIMARY KEY,
    full_date DATE UNIQUE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    day INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    is_weekend BOOLEAN NOT NULL,
    is_steam_sale_period BOOLEAN DEFAULT FALSE,
    steam_sale_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for date lookups
CREATE INDEX idx_dim_date_full_date ON dim_date(full_date);
CREATE INDEX idx_dim_date_steam_sale ON dim_date(is_steam_sale_period) WHERE is_steam_sale_period = TRUE;

-- dim_genre: Game genres
CREATE TABLE dim_genre (
    genre_id SERIAL PRIMARY KEY,
    genre_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- dim_tag: Game tags (many-to-many with games)
CREATE TABLE dim_tag (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- dim_game: Core game dimension
CREATE TABLE dim_game (
    game_id SERIAL PRIMARY KEY,
    appid INTEGER UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    developer VARCHAR(500),
    publisher VARCHAR(500),
    release_date DATE,
    is_free BOOLEAN DEFAULT FALSE,
    steamspy_owners_min INTEGER,
    steamspy_owners_max INTEGER,
    positive_reviews INTEGER DEFAULT 0,
    negative_reviews INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for game lookups
CREATE INDEX idx_dim_game_appid ON dim_game(appid);
CREATE INDEX idx_dim_game_name ON dim_game(name);
CREATE INDEX idx_dim_game_release_date ON dim_game(release_date);

-- bridge_game_tag: Many-to-many relationship between games and tags
CREATE TABLE bridge_game_tag (
    game_id INTEGER NOT NULL REFERENCES dim_game(game_id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES dim_tag(tag_id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, tag_id)
);

CREATE INDEX idx_bridge_game_tag_game ON bridge_game_tag(game_id);
CREATE INDEX idx_bridge_game_tag_tag ON bridge_game_tag(tag_id);

-- ========================================
-- Fact Table
-- ========================================

-- fact_player_price: Monthly player counts and pricing data
CREATE TABLE fact_player_price (
    fact_id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES dim_game(game_id) ON DELETE CASCADE,
    date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
    genre_id INTEGER REFERENCES dim_genre(genre_id),
    
    -- Player metrics (from SteamCharts)
    concurrent_players_avg INTEGER,
    concurrent_players_peak INTEGER,
    gain_pct DECIMAL(10, 2),
    avg_players_month INTEGER,
    peak_players_month INTEGER,
    
    -- Pricing metrics (from Steam Store)
    current_price DECIMAL(10, 2),
    original_price DECIMAL(10, 2),
    discount_pct DECIMAL(5, 2) DEFAULT 0,
    is_discount_active BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure uniqueness per game per month
    UNIQUE(game_id, date_id)
);

-- Create indexes for fact table queries
CREATE INDEX idx_fact_player_price_game ON fact_player_price(game_id);
CREATE INDEX idx_fact_player_price_date ON fact_player_price(date_id);
CREATE INDEX idx_fact_player_price_genre ON fact_player_price(genre_id);
CREATE INDEX idx_fact_player_price_discount ON fact_player_price(is_discount_active) WHERE is_discount_active = TRUE;

-- ========================================
-- Analysis Results Table
-- ========================================

-- analysis_results: Store analytical model outputs
CREATE TYPE analysis_type_enum AS ENUM ('did', 'kaplan_meier', 'cox_ph', 'elasticity');

CREATE TABLE analysis_results (
    result_id SERIAL PRIMARY KEY,
    analysis_type analysis_type_enum NOT NULL,
    game_id INTEGER REFERENCES dim_game(game_id),
    genre_id INTEGER REFERENCES dim_genre(genre_id),
    parameters JSONB NOT NULL,
    results JSONB NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50) DEFAULT '1.0.0'
);

-- Create indexes for analysis queries
CREATE INDEX idx_analysis_results_type ON analysis_results(analysis_type);
CREATE INDEX idx_analysis_results_game ON analysis_results(game_id);
CREATE INDEX idx_analysis_results_executed ON analysis_results(executed_at DESC);

-- ========================================
-- Seed Data
-- ========================================

-- Populate dim_date with date range (2020-2030)
INSERT INTO dim_date (full_date, year, quarter, month, day, day_of_week, is_weekend, is_steam_sale_period, steam_sale_name)
SELECT 
    d::date AS full_date,
    EXTRACT(YEAR FROM d)::INTEGER AS year,
    EXTRACT(QUARTER FROM d)::INTEGER AS quarter,
    EXTRACT(MONTH FROM d)::INTEGER AS month,
    EXTRACT(DAY FROM d)::INTEGER AS day,
    EXTRACT(DOW FROM d)::INTEGER AS day_of_week,
    CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,
    FALSE AS is_steam_sale_period,
    NULL AS steam_sale_name
FROM generate_series('2020-01-01'::date, '2030-12-31'::date, '1 day'::interval) d;

-- Mark known Steam sale periods
-- Winter Sale (typically mid-late December to early January)
UPDATE dim_date 
SET is_steam_sale_period = TRUE, steam_sale_name = 'Winter Sale'
WHERE (month = 12 AND day >= 20) OR (month = 1 AND day <= 5);

-- Summer Sale (typically late June to early July)
UPDATE dim_date 
SET is_steam_sale_period = TRUE, steam_sale_name = 'Summer Sale'
WHERE (month = 6 AND day >= 20) OR (month = 7 AND day <= 10);

-- Spring Sale (typically late March)
UPDATE dim_date 
SET is_steam_sale_period = TRUE, steam_sale_name = 'Spring Sale'
WHERE month = 3 AND day >= 15 AND day <= 30;

-- Autumn Sale (typically late November)
UPDATE dim_date 
SET is_steam_sale_period = TRUE, steam_sale_name = 'Autumn Sale'
WHERE month = 11 AND day >= 20 AND day <= 30;

-- Seed common game genres
INSERT INTO dim_genre (genre_name) VALUES
    ('Action'),
    ('Adventure'),
    ('RPG'),
    ('Strategy'),
    ('Simulation'),
    ('Sports'),
    ('Racing'),
    ('Puzzle'),
    ('Indie'),
    ('Casual'),
    ('MMO'),
    ('Shooter'),
    ('Fighting'),
    ('Platformer'),
    ('Horror')
ON CONFLICT (genre_name) DO NOTHING;

-- ========================================
-- Utility Functions
-- ========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to dim_game
CREATE TRIGGER update_dim_game_updated_at
    BEFORE UPDATE ON dim_game
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- Views for Common Queries
-- ========================================

-- View: Game player trends with pricing
CREATE OR REPLACE VIEW v_game_player_trends AS
SELECT 
    g.appid,
    g.name,
    g.developer,
    d.full_date,
    d.year,
    d.month,
    gen.genre_name,
    f.concurrent_players_avg,
    f.concurrent_players_peak,
    f.current_price,
    f.original_price,
    f.discount_pct,
    f.is_discount_active,
    d.is_steam_sale_period,
    d.steam_sale_name
FROM fact_player_price f
JOIN dim_game g ON f.game_id = g.game_id
JOIN dim_date d ON f.date_id = d.date_id
LEFT JOIN dim_genre gen ON f.genre_id = gen.genre_id;

-- View: Game summary statistics
CREATE OR REPLACE VIEW v_game_summary AS
SELECT 
    g.game_id,
    g.appid,
    g.name,
    g.developer,
    g.release_date,
    COUNT(DISTINCT f.date_id) as months_tracked,
    AVG(f.concurrent_players_avg) as avg_concurrent_players,
    MAX(f.concurrent_players_peak) as max_peak_players,
    MIN(f.current_price) as min_price,
    MAX(f.current_price) as max_price,
    AVG(f.discount_pct) as avg_discount_pct,
    COUNT(CASE WHEN f.is_discount_active THEN 1 END) as discount_periods
FROM dim_game g
LEFT JOIN fact_player_price f ON g.game_id = f.game_id
GROUP BY g.game_id, g.appid, g.name, g.developer, g.release_date;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO steam_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO steam_user;

COMMENT ON TABLE dim_game IS 'Game dimension containing core game metadata from SteamSpy';
COMMENT ON TABLE dim_date IS 'Calendar dimension with Steam sale period flags for DiD analysis';
COMMENT ON TABLE fact_player_price IS 'Monthly granularity fact table combining player counts and pricing data';
COMMENT ON TABLE analysis_results IS 'Storage for analytical model outputs (DiD, Kaplan-Meier, Cox PH, etc.)';
