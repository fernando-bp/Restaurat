-- Script para insertar mesas en la base de datos
-- Estructura: id, numero, capacidad, zona, estado, activa, created_at

INSERT INTO mesas (numero, capacidad, zona, estado, activa, created_at) VALUES
-- ZONA TERRAZA
('T-01', 4, 'Terraza', 'libre', TRUE, NOW()),
('T-02', 4, 'Terraza', 'libre', TRUE, NOW()),
('T-03', 2, 'Terraza', 'libre', TRUE, NOW()),
('T-04', 6, 'Terraza', 'libre', TRUE, NOW()),
('T-05', 4, 'Terraza', 'libre', TRUE, NOW()),

-- ZONA INTERIOR
('I-01', 4, 'Interior', 'libre', TRUE, NOW()),
('I-02', 4, 'Interior', 'libre', TRUE, NOW()),
('I-03', 6, 'Interior', 'libre', TRUE, NOW()),
('I-04', 2, 'Interior', 'libre', TRUE, NOW()),
('I-05', 8, 'Interior', 'libre', TRUE, NOW()),
('I-06', 4, 'Interior', 'libre', TRUE, NOW()),

-- ZONA BAR
('B-01', 2, 'Bar', 'libre', TRUE, NOW()),
('B-02', 2, 'Bar', 'libre', TRUE, NOW()),
('B-03', 4, 'Bar', 'libre', TRUE, NOW()),

-- ZONA VIP
('VIP-01', 6, 'VIP', 'libre', TRUE, NOW()),
('VIP-02', 8, 'VIP', 'libre', TRUE, NOW());
