CREATE TABLE wallet (
    address text NOT NULL,
    status text NOT NULL,
    transactions_count int NOT NULL,
    PRIMARY KEY (address)
);

CREATE TABLE exchange (
    address text NOT NULL,
    name text NOT NULL
);

INSERT INTO exchange VALUES ('6ZRCB7AAqGre6c72PRz3MHLC73VMYvJ8bi9KHf1HFpNk', 'FTX');

