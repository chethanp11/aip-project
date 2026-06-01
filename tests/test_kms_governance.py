import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock
from src.kms.index import (
    advanced_retrieval_orchestration,
    chunk_knowledge_text,
    get_faiss_paths,
    ingest_custom_file_to_kms,
    act_on_candidate_knowledge,
    get_sqlite_db,
    require_active_kms_team
)


def test_knowledge_text_chunking_is_token_bounded_and_overlapped():
    long_policy = " ".join(f"token{i}" for i in range(130))

    chunks = chunk_knowledge_text(long_policy, max_tokens=40, overlap_tokens=8)

    assert len(chunks) > 1
    assert all(len(chunk.split()) <= 40 for chunk in chunks)
    assert chunks[0].split()[-8:] == chunks[1].split()[:8]

def test_kms_ingestion_staged_vs_auto_approved():
    """Verify staged document uploads remain staged and are only indexed in FAISS on active SME approval."""
    # Mock context requirements
    with patch('src.kms.index.require_active_kms_team', return_value='TestTeam'), \
         patch('src.kms.index.get_openai_embedding', return_value=[0.1]*1536), \
         patch('src.kms.index.call_llm', return_value="Staged dynamic AI summary"):
        
        # 1. Execute Staged Ingestion (auto_approve = False)
        res_staged = asyncio.run(ingest_custom_file_to_kms(
            filename="staged_test.txt",
            content="This is some corporate policy text about concentration sweeps.",
            owner="Test Owner",
            security_class="Internal",
            sme="Marcus Vance",
            business_domain="Enterprise Analytics",
            prompt="",
            auto_approve=False
        ))
        assert res_staged['success'] is True
        assert res_staged['status'] == "Pending Review"
        candidate_id = res_staged['candidateId']
        
        # 2. Verify that NO vector chunks are created yet in the database
        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vector_chunks WHERE node_id = ?;", (candidate_id,))
        count_chunks_staged = cursor.fetchone()[0]
        assert count_chunks_staged == 0
        
        # 3. Verify candidate_knowledge has been staged correctly as Pending Review
        cursor.execute("SELECT review_status FROM candidate_knowledge WHERE candidate_id = ?;", (candidate_id,))
        status_in_db = cursor.fetchone()[0]
        assert status_in_db == "Pending Review"
        
        # 4. Action the candidate: Approve & Ingest!
        res_approve = act_on_candidate_knowledge(candidate_id, "Approved", "Approved via unit test")
        assert res_approve['success'] is True
        assert res_approve['reviewStatus'] == "Approved"
        
        # 5. Verify that it IS now indexed in vector_chunks under the target node_id
        node_id = "node_" + candidate_id
        cursor.execute("SELECT COUNT(*) FROM vector_chunks WHERE node_id = ?;", (node_id,))
        count_chunks_approved = cursor.fetchone()[0]
        assert count_chunks_approved > 0
        
        # 6. Verify that review_status is updated in metadata table
        cursor.execute("SELECT review_status FROM candidate_knowledge WHERE candidate_id = ?;", (candidate_id,))
        status_after_approve = cursor.fetchone()[0]
        assert status_after_approve == "Approved"

def test_kms_ingestion_auto_approved_direct():
    """Verify that auto-approved uploads bypass the staging queue and are indexed in FAISS immediately."""
    with patch('src.kms.index.require_active_kms_team', return_value='TestTeam'), \
         patch('src.kms.index.get_openai_embedding', return_value=[0.1]*1536), \
         patch('src.kms.index.call_llm', return_value="Auto-Approved dynamic AI summary"):
        
        # 1. Execute direct Auto-Approved Ingestion (auto_approve = True)
        res_auto = asyncio.run(ingest_custom_file_to_kms(
            filename="auto_test.txt",
            content="This is some corporate policy text about interest rate swaps exposure.",
            owner="Test Owner",
            security_class="Internal",
            sme="Marcus Vance",
            business_domain="Enterprise Analytics",
            prompt="",
            auto_approve=True
        ))
        assert res_auto['success'] is True
        assert res_auto['status'] == "Approved"
        candidate_id = res_auto['candidateId']
        
        # 2. Verify that it IS immediately indexed in vector_chunks under the target node_id
        conn = get_sqlite_db()
        cursor = conn.cursor()
        node_id = "node_" + candidate_id
        cursor.execute("SELECT COUNT(*) FROM vector_chunks WHERE node_id = ?;", (node_id,))
        count_chunks = cursor.fetchone()[0]
        assert count_chunks > 0
        
        # 3. Verify that review_status is immediately Approved in metadata table
        cursor.execute("SELECT review_status FROM candidate_knowledge WHERE candidate_id = ?;", (candidate_id,))
        status_in_db = cursor.fetchone()[0]
        assert status_in_db == "Approved"


def test_approved_ingestion_writes_multiple_bounded_chunks_for_long_content():
    long_content = (
        "Liquidity sweep controls require documented approvals and daily monitoring. "
        + " ".join(f"policyterm{i}" for i in range(180))
        + ". Exception handling must preserve audit evidence and business-owner review."
    )

    with patch('src.kms.index.require_active_kms_team', return_value='TestTeam'), \
         patch('src.kms.index.get_openai_embedding', return_value=[0.1]*1536), \
         patch('src.kms.index.call_llm', return_value="Chunking regression summary"):

        res_auto = asyncio.run(ingest_custom_file_to_kms(
            filename="chunking_test.txt",
            content=long_content,
            owner="Test Owner",
            security_class="Internal",
            sme="Marcus Vance",
            business_domain="Enterprise Analytics",
            prompt="",
            auto_approve=True
        ))

        conn = get_sqlite_db()
        cursor = conn.cursor()
        node_id = "node_" + res_auto['candidateId']
        cursor.execute("SELECT chunk_text FROM vector_chunks WHERE node_id = ?;", (node_id,))
        stored_chunks = [row[0] for row in cursor.fetchall()]

        assert len(stored_chunks) > 1
        assert all(len(chunk.split()) <= 90 for chunk in stored_chunks)


def test_approved_ingestion_creates_team_vector_files_and_query_reads_them():
    content = (
        "Team-specific liquidity policy requires sweep approvals before cutoff. "
        "Treasury operations must monitor intraday liquidity buffers and exception evidence."
    )

    with patch('src.kms.index.require_active_kms_team', return_value='TestTeam'), \
         patch('src.kms.index.call_llm', return_value="Team vector file summary"):

        res_auto = asyncio.run(ingest_custom_file_to_kms(
            filename="team_vector_file_test.txt",
            content=content,
            owner="Test Owner",
            security_class="Internal",
            sme="Marcus Vance",
            business_domain="Enterprise Analytics",
            prompt="",
            auto_approve=True
        ))

        paths = get_faiss_paths("TestTeam")
        assert res_auto['success'] is True
        assert os.path.exists(paths['chunks'])
        assert os.path.exists(paths['index'])

        result = advanced_retrieval_orchestration(
            "liquidity sweep approvals",
            user_role="Analyst",
            security_clearance="Internal"
        )

        assert result['matched_chunks']
        assert any(
            trace['action'] in {'FAISS_SEARCH', 'CHUNKS_JSON_SEARCH'}
            for trace in result['agent_traces']
        )
