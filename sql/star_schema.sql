-- Star-schema DDL for the reporting warehouse (PostgreSQL / Azure SQL).
-- Conformed dimensions around a single transaction fact. Surrogate integer
-- keys keep the fact narrow and joins fast for Power BI.

CREATE TABLE IF NOT EXISTS dim_date (
    date_key     INTEGER      PRIMARY KEY,   -- yyyymmdd
    date         DATE         NOT NULL,
    year         SMALLINT     NOT NULL,
    quarter      SMALLINT     NOT NULL,
    month        SMALLINT     NOT NULL,
    month_name   VARCHAR(3)   NOT NULL,
    day          SMALLINT     NOT NULL,
    day_of_week  VARCHAR(9)   NOT NULL,
    is_weekend   BOOLEAN      NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_account (
    account_key  INTEGER      PRIMARY KEY,
    account_id   VARCHAR(20)  NOT NULL UNIQUE,
    region       VARCHAR(40),
    segment      VARCHAR(20),
    opened_on    DATE
);

CREATE TABLE IF NOT EXISTS dim_merchant (
    merchant_key   INTEGER    PRIMARY KEY,
    merchant_id    INTEGER    NOT NULL UNIQUE,
    merchant_name  VARCHAR(80),
    category       VARCHAR(40)
);

CREATE TABLE IF NOT EXISTS fact_transaction (
    transaction_id  VARCHAR(20)   PRIMARY KEY,
    date_key        INTEGER       REFERENCES dim_date(date_key),
    account_key     INTEGER       REFERENCES dim_account(account_key),
    merchant_key    INTEGER       REFERENCES dim_merchant(merchant_key),
    amount          NUMERIC(18,2) NOT NULL,
    signed_amount   NUMERIC(18,2) NOT NULL,   -- refunds negated
    is_refund       BOOLEAN       NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_fact_date     ON fact_transaction (date_key);
CREATE INDEX IF NOT EXISTS ix_fact_account  ON fact_transaction (account_key);
CREATE INDEX IF NOT EXISTS ix_fact_merchant ON fact_transaction (merchant_key);
