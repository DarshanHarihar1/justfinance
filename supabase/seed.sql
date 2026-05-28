-- ════════════════════════════════════════════════════════════════════
-- seed.sql — default categories + merchant rule-pack
-- ════════════════════════════════════════════════════════════════════
-- Idempotent: re-running this file produces zero new rows.
-- Mounted into the dev Postgres container at
--   /docker-entrypoint-initdb.d/zz_seed.sql
-- so it always runs after every migration file in supabase/migrations/.
--
-- Every merchant_pattern below must round-trip cleanly through
-- app.services.categorizer.normalize.normalize(); a Phase 2 test enforces this.

-- ──────────────────────────────────────────────
-- Categories (18 total)
-- ──────────────────────────────────────────────
INSERT INTO categories (name, color, icon, is_system, excluded_from_spending, sort_order) VALUES
    ('Groceries',     '#4CAF50', '🛒', FALSE, FALSE, 10),
    ('Food & Dining', '#FF9800', '🍔', FALSE, FALSE, 20),
    ('Transport',     '#2196F3', '🚌', FALSE, FALSE, 30),
    ('Utilities',     '#9C27B0', '⚡', FALSE, FALSE, 40),
    ('Entertainment', '#E91E63', '🎬', FALSE, FALSE, 50),
    ('Subscriptions', '#673AB7', '📺', FALSE, FALSE, 55),
    ('Healthcare',    '#00BCD4', '🏥', FALSE, FALSE, 60),
    ('Shopping',      '#FF5722', '🛍️', FALSE, FALSE, 70),
    ('Sports & Fitness','#8BC34A', '🏸', FALSE, FALSE, 72),
    ('Personal Care', '#F06292', '💇', FALSE, FALSE, 75),
    ('Home Services', '#8D6E63', '🧹', FALSE, FALSE, 78),
    ('Fuel',          '#795548', '⛽', FALSE, FALSE, 80),
    ('Rent & Bills',  '#3F51B5', '🏠', FALSE, FALSE, 85),
    ('Investments',   '#607D8B', '📈', FALSE, FALSE, 90),
    ('Income',        '#8BC34A', '💰', FALSE, FALSE, 95),
    ('Transfers',     '#9E9E9E', '↔️',  TRUE,  TRUE,  100),
    ('Cash Withdrawal','#BDBDBD','🏧', FALSE, FALSE, 105),
    ('Others',        '#9E9E9E', '📦', TRUE,  FALSE, 110)
ON CONFLICT (name) DO NOTHING;

-- ──────────────────────────────────────────────
-- Merchant rule-pack (India-focused)
-- Patterns are in the exact form produced by the merchant normalizer.
-- ──────────────────────────────────────────────
WITH cat AS (
    SELECT name, id FROM categories
)
INSERT INTO merchant_mappings (merchant_pattern, category_id, source, confidence)
SELECT v.pattern, cat.id, 'seed', NULL
FROM (VALUES
    -- Food delivery
    ('SWIGGY',                          'Food & Dining'),
    ('SWIGGY INSTAMART',                'Groceries'),
    ('ZOMATO',                          'Food & Dining'),
    ('EATSURE',                         'Food & Dining'),
    ('FAASOS',                          'Food & Dining'),
    ('BOX8',                            'Food & Dining'),
    ('FRESHMENU',                       'Food & Dining'),

    -- Quick commerce / groceries
    ('ZEPTO',                           'Groceries'),
    ('ZEPTO MARKETPLACE',               'Groceries'),
    ('ZEPTONOW',                        'Groceries'),
    ('BLINKIT',                         'Groceries'),
    ('BIGBASKET',                       'Groceries'),
    ('BB DAILY',                        'Groceries'),
    ('DUNZO',                           'Groceries'),
    ('SWIGGY GENIE',                    'Others'),
    ('LICIOUS',                         'Groceries'),
    ('FRESHTOHOME',                     'Groceries'),
    ('COUNTRY DELIGHT',                 'Groceries'),
    ('MILKBASKET',                      'Groceries'),
    ('CTRLX TECHNOLOGIES',              'Groceries'),

    -- Cafes & food chains
    ('STARBUCKS',                       'Food & Dining'),
    ('BLUE TOKAI',                      'Food & Dining'),
    ('THIRD WAVE COFFEE',               'Food & Dining'),
    ('CHAI POINT',                      'Food & Dining'),
    ('KAMAT',                           'Food & Dining'),
    ('UDUPI VEG RESTAURANT',            'Food & Dining'),
    ('MEGHANA FOODS',                   'Food & Dining'),
    ('NATURALS',                        'Food & Dining'),
    ('PIZZA 4PS',                       'Food & Dining'),
    ('DOMINOS',                         'Food & Dining'),
    ('MCDONALDS',                       'Food & Dining'),
    ('KFC',                             'Food & Dining'),
    ('BURGER KING',                     'Food & Dining'),
    ('SUBWAY',                          'Food & Dining'),
    ('A1 FOODS',                        'Food & Dining'),
    ('MTR',                             'Food & Dining'),
    ('SAMOSA',                          'Food & Dining'),
    ('SWISH',                           'Food & Dining'),
    ('MUNCHMART TECHNOLOGIES',          'Food & Dining'),
    ('KAMAT CAFE & PASTRIES',           'Food & Dining'),
    ('MEGHANA FOODS SARJAPURA',         'Food & Dining'),
    ('CHAI KAPPI',                      'Food & Dining'),
    ('THYME AND WHISK',                 'Food & Dining'),
    ('BIG MISHRA PEDHA',                'Food & Dining'),
    ('BIG MISHRA SWEET INN',            'Food & Dining'),

    -- Transport
    ('BMTC',                            'Transport'),
    ('BMTC BUS',                        'Transport'),
    ('UBER',                            'Transport'),
    ('OLA',                             'Transport'),
    ('RAPIDO',                          'Transport'),
    ('IRCTC',                           'Transport'),
    ('NAMMA YATRI',                     'Transport'),
    ('YULU',                            'Transport'),

    -- Fuel
    ('INDIAN OIL',                      'Fuel'),
    ('INDIAN OIL PETROL PUMP',          'Fuel'),
    ('HP PETROL PUMP',                  'Fuel'),
    ('BHARAT PETROLEUM',                'Fuel'),
    ('SHELL',                           'Fuel'),
    ('S C NAREGAL',                     'Fuel'),

    -- Bills / FASTag
    ('FASTAG',                          'Transport'),
    ('AIRTEL',                          'Utilities'),
    ('JIO',                             'Utilities'),
    ('VI',                              'Utilities'),
    ('BSNL',                            'Utilities'),
    ('TATA POWER',                      'Utilities'),
    ('BESCOM',                          'Utilities'),
    ('BWSSB',                           'Utilities'),

    -- Subscriptions / digital
    ('NETFLIX',                         'Subscriptions'),
    ('NETFLIX COM',                     'Subscriptions'),
    ('APPLE MEDIA SERVICES',            'Subscriptions'),
    ('APPLE',                           'Subscriptions'),
    ('GOOGLE',                          'Subscriptions'),
    ('SPOTIFY',                         'Subscriptions'),
    ('YOUTUBE',                         'Subscriptions'),
    ('PRIME VIDEO',                     'Subscriptions'),
    ('HOTSTAR',                         'Subscriptions'),
    ('JIOCINEMA',                       'Subscriptions'),
    ('OPENAI',                          'Subscriptions'),
    ('ANTHROPIC',                       'Subscriptions'),
    ('CURSOR',                          'Subscriptions'),
    ('GITHUB',                          'Subscriptions'),

    -- Cloud / dev
    ('AWS INDIA',                       'Subscriptions'),
    ('AWS',                             'Subscriptions'),

    -- Shopping
    ('AMAZON',                          'Shopping'),
    ('FLIPKART',                        'Shopping'),
    ('MYNTRA',                          'Shopping'),
    ('AJIO',                            'Shopping'),
    ('NYKAA',                           'Personal Care'),
    ('MEESHO',                          'Shopping'),

    -- Healthcare
    ('PHARMEASY',                       'Healthcare'),
    ('1MG',                             'Healthcare'),
    ('TATA 1MG',                        'Healthcare'),
    ('APOLLO',                          'Healthcare'),
    ('PRACTO',                          'Healthcare'),
    ('CULT FIT',                        'Personal Care'),
    ('CULTFIT',                         'Personal Care'),

    -- Personal services
    ('URBANCOMPANY',                    'Personal Care'),
    ('RENTOMOJO',                       'Rent & Bills'),
    ('FURLENCO',                        'Rent & Bills'),
    ('DIVJOT',                          'Rent & Bills'),

    -- Sports & fitness
    ('******1492',                      'Sports & Fitness'),

    -- Home services (maid, cook, domestic help)
    ('DEV DHAMI',                       'Home Services'),

    -- Cash withdrawal / banking
    ('SBI ATM',                         'Cash Withdrawal'),
    ('SBI ATM CASH WITHDRAWAL',         'Cash Withdrawal'),

    -- Investments
    ('ZERODHA',                         'Investments'),
    ('GROWW',                           'Investments'),
    ('UPSTOX',                          'Investments'),
    ('COIN BY ZERODHA',                 'Investments'),
    ('INDMONEY',                        'Investments'),

    -- Insurance
    ('HDFC ERGO',                       'Rent & Bills'),
    ('HDFC ERGO GENERAL INSURANCE',     'Rent & Bills'),
    ('ACKO',                            'Rent & Bills'),
    ('LIC',                             'Rent & Bills')
) AS v(pattern, category_name)
JOIN cat ON cat.name = v.category_name
ON CONFLICT (merchant_pattern) DO NOTHING;
