ALTER TABLE insur_pred
    ADD COLUMN ID INT NOT NULL DEFAULT 0 AFTER pred_id;

CREATE INDEX idx_insur_pred_id ON insur_pred (ID);
