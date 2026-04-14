ALTER TABLE train_data
    DROP INDEX idx_train_data_id,
    ADD PRIMARY KEY (ID);
