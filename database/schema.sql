CREATE TABLE wallet (
    address text NOT NULL,
    status text NOT NULL,
    transactions_count int NOT NULL,
    PRIMARY KEY (address)
);
