CREATE DATABASE chat_universidad;
USE chat_universidad;


CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    contrasena VARCHAR(255) NOT NULL,
    rol ENUM('estudiante', 'administrador') NOT NULL
);



CREATE TABLE areas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
);



CREATE TABLE chats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estudiante_id INT NOT NULL,
    administrador_id INT DEFAULT NULL,
    area_id INT NOT NULL,
    mensajes_no_leidos INT DEFAULT 0,
    FOREIGN KEY (estudiante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (administrador_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE CASCADE
);



CREATE TABLE mensajes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    chat_id INT NOT NULL,
    mensaje TEXT NOT NULL,
    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
);



INSERT INTO areas (nombre) VALUES
('Finanzas'),
('Comedor Universitario'),
('Bienestar Estudiantil'),
('Departamento de Inglés'),
('Departamento de Música');
