-- =============================================================================
-- Migration 006: pgvector Semantic Similarity Search RPC
-- Provides match_embeddings() function utilizing PostgreSQL pgvector (<=> cosine distance)
-- =============================================================================

CREATE OR REPLACE FUNCTION match_embeddings (
    query_embedding vector(768),
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 5,
    filter_organization_id text DEFAULT '',
    filter_repo_id text DEFAULT ''
)
RETURNS TABLE (
    id text,
    entity_type text,
    entity_id text,
    content_chunk text,
    similarity float,
    metadata jsonb
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        embeddings.id::text,
        embeddings.entity_type::text,
        embeddings.entity_id::text,
        embeddings.content_chunk,
        (1 - (embeddings.embedding <=> query_embedding))::float AS similarity,
        embeddings.metadata
    FROM embeddings
    WHERE (filter_organization_id = '' OR embeddings.organization_id = filter_organization_id)
      AND (filter_repo_id = '' OR embeddings.repo_id = filter_repo_id)
      AND (1 - (embeddings.embedding <=> query_embedding)) >= match_threshold
    ORDER BY embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_embeddings IS 'RPC endpoint for pgvector cosine similarity search over code and context chunks';
