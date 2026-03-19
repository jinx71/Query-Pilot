-- QueryPilot demo schema: a small pharmaceutical manufacturing operations DB.
-- Tables are connected by foreign keys so the agent can join across them:
-- products <- batches -> equipment / operators, batches <- qc_tests,
-- batches/equipment <- deviations.

DROP TABLE IF EXISTS deviations CASCADE;
DROP TABLE IF EXISTS qc_tests CASCADE;
DROP TABLE IF EXISTS batches CASCADE;
DROP TABLE IF EXISTS operators CASCADE;
DROP TABLE IF EXISTS equipment CASCADE;
DROP TABLE IF EXISTS products CASCADE;

CREATE TABLE products (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(120) NOT NULL,
    dosage_form      VARCHAR(40)  NOT NULL,   -- tablet, capsule, injection, syrup, ointment
    strength         VARCHAR(40)  NOT NULL,
    therapeutic_area VARCHAR(60)  NOT NULL    -- cardiology, oncology, ...
);

CREATE TABLE equipment (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(120) NOT NULL,
    equipment_type VARCHAR(60)  NOT NULL,     -- tablet press, autoclave, ...
    location       VARCHAR(60)  NOT NULL,     -- Block A - Line 1
    status         VARCHAR(20)  NOT NULL,     -- operational, maintenance, decommissioned
    installed_date DATE         NOT NULL
);

CREATE TABLE operators (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(120) NOT NULL,
    role       VARCHAR(40)  NOT NULL,         -- operator, supervisor, qa_analyst
    department VARCHAR(60)  NOT NULL
);

CREATE TABLE batches (
    id                SERIAL PRIMARY KEY,
    batch_number      VARCHAR(30)  NOT NULL UNIQUE,
    product_id        INTEGER      NOT NULL REFERENCES products(id),
    equipment_id      INTEGER      REFERENCES equipment(id),
    operator_id       INTEGER      REFERENCES operators(id),
    manufactured_date DATE         NOT NULL,
    quantity_units    INTEGER      NOT NULL,
    status            VARCHAR(20)  NOT NULL    -- released, rejected, quarantine
);

CREATE TABLE qc_tests (
    id             SERIAL PRIMARY KEY,
    batch_id       INTEGER       NOT NULL REFERENCES batches(id),
    test_name      VARCHAR(80)   NOT NULL,    -- assay, dissolution, hardness, microbial
    result         VARCHAR(10)   NOT NULL,    -- pass, fail
    measured_value NUMERIC(10,3),
    spec_min       NUMERIC(10,3),
    spec_max       NUMERIC(10,3),
    tested_date    DATE          NOT NULL
);

CREATE TABLE deviations (
    id             SERIAL PRIMARY KEY,
    batch_id       INTEGER      REFERENCES batches(id),
    equipment_id   INTEGER      REFERENCES equipment(id),
    deviation_type VARCHAR(60)  NOT NULL,     -- temperature excursion, equipment failure, ...
    severity       VARCHAR(10)  NOT NULL,     -- minor, major, critical
    status         VARCHAR(10)  NOT NULL,     -- open, closed
    description    TEXT,
    reported_date  DATE         NOT NULL,
    closed_date    DATE
);

-- Helpful indexes for the kinds of filters the agent tends to write.
CREATE INDEX idx_batches_product ON batches(product_id);
CREATE INDEX idx_batches_status ON batches(status);
CREATE INDEX idx_batches_mfg_date ON batches(manufactured_date);
CREATE INDEX idx_qc_batch ON qc_tests(batch_id);
CREATE INDEX idx_qc_result ON qc_tests(result);
CREATE INDEX idx_dev_batch ON deviations(batch_id);
CREATE INDEX idx_dev_equipment ON deviations(equipment_id);
CREATE INDEX idx_dev_severity ON deviations(severity);
