-- Migration: Create isolated table for chatbot_demo records in Allintos DB
-- This table is purely for isolated data ingestion from the admin panel
-- and has no foreign keys to existing Allintos tables to prevent conflicts.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chatbot_demo_qa_embeddings (
    id SERIAL PRIMARY KEY,
    mesaj TEXT NOT NULL,
    beklenen_sektor VARCHAR(100) NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chatbot_demo_qa_embeddings_sektor 
    ON chatbot_demo_qa_embeddings(beklenen_sektor);
