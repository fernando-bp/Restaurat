-- Migración: credenciales Factus por restaurante
-- Ejecutar en Railway (MySQL) una sola vez

ALTER TABLE restaurantes
  ADD COLUMN factus_enabled         TINYINT(1)   NOT NULL DEFAULT 0      AFTER updated_at,
  ADD COLUMN factus_api_base_url    VARCHAR(255)          DEFAULT NULL    AFTER factus_enabled,
  ADD COLUMN factus_client_id       VARCHAR(255)          DEFAULT NULL    AFTER factus_api_base_url,
  ADD COLUMN factus_client_secret   VARCHAR(500)          DEFAULT NULL    AFTER factus_client_id,
  ADD COLUMN factus_username        VARCHAR(255)          DEFAULT NULL    AFTER factus_client_secret,
  ADD COLUMN factus_password        VARCHAR(255)          DEFAULT NULL    AFTER factus_username,
  ADD COLUMN factus_numbering_range_id INT                DEFAULT NULL    AFTER factus_password,
  ADD COLUMN factus_customer_municipality_code VARCHAR(20) DEFAULT NULL   AFTER factus_numbering_range_id;
