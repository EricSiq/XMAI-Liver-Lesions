"""Comprehensive integration tests auditing frontend-to-ML pipeline connectivity,
live PyTorch inference, fallback mechanisms, and REST API endpoints.
"""

import json
from pathlib import Path
import threading
import time
import urllib.request
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
from scripts.serve_frontend import (
    compute_live_prediction,
    XMAIHTTPHandler,
    TORCH_AVAILABLE,
)
import socketserver


def test_live_prediction_gated_fusion_logic():
    """Verify that compute_live_prediction executes expected multimodal gating logic."""
    # Test Rescued Case HCC_48: 65y Male, Borderline visual prior 0.281
    res_hcc = compute_live_prediction(
        model_id="A4",
        age=65,
        sex="Male",
        mask=1,
        visual_prior=0.281,
    )
    assert res_hcc["status"] == "success"
    assert res_hcc["fallback_active"] is False
    assert res_hcc["decision"] == "HCC"
    assert res_hcc["p_hcc"] > 0.50
    assert 0.0 < res_hcc["gate_c"] < 1.0

    # Test Rescued Case Hem_5: 44y Female, False Positive visual prior 0.671
    res_hem = compute_live_prediction(
        model_id="A4",
        age=44,
        sex="Female",
        mask=1,
        visual_prior=0.671,
    )
    assert res_hem["status"] == "success"
    assert res_hem["fallback_active"] is False
    assert res_hem["decision"] == "Hemangioma"
    assert res_hem["p_hcc"] < 0.50


def test_hypothesis_h3_missing_modality_fallback():
    """Verify Hypothesis H3: When clinical mask=0, system gracefully degrades to B-mode."""
    res_fallback = compute_live_prediction(
        model_id="A4",
        age=75,
        sex="Male",
        mask=0,
        visual_prior=0.281,
    )
    assert res_fallback["fallback_active"] is True
    assert res_fallback["gate_b"] == 1.0
    assert res_fallback["gate_c"] == 0.0
    assert res_fallback["p_hcc"] == 0.281
    assert res_fallback["decision"] == "Hemangioma"


def test_evidential_belief_decomposition():
    """Verify Subjective Logic evidential decomposition sum to 1.0 (b_HCC + b_Hem + u == 1.0)."""
    for age in [30, 50, 70]:
        for sex in ["Male", "Female"]:
            res = compute_live_prediction(
                model_id="A9",
                age=age,
                sex=sex,
                mask=1,
                visual_prior=0.50,
            )
            evid = res["evidential"]
            total_mass = evid["b_hcc"] + evid["b_hem"] + evid["u"]
            assert abs(total_mass - 1.0) < 0.01, f"Total evidential mass must be 1.0, got {total_mass}"


def test_live_server_endpoints_http():
    """Start an ephemeral test server on an open port and audit all REST API endpoints."""
    # Find free port
    server = socketserver.TCPServer(("127.0.0.1", 0), XMAIHTTPHandler)
    host, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        base_url = f"http://{host}:{port}"
        time.sleep(0.1)

        # 1. Audit /api/status
        req = urllib.request.Request(f"{base_url}/api/status")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "online"
            assert data["models"] == 9
            assert data["cohort_patients"] == 743

        # 2. Audit /api/audit (CLAIM checklist)
        req = urllib.request.Request(f"{base_url}/api/audit")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["overall_status"] == "PASS"
            assert len(data["claim_items"]) == 7

        # 3. Audit /api/cases
        req = urllib.request.Request(f"{base_url}/api/cases")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert len(data["cases"]) == 5

        # 4. Audit POST /api/predict
        payload = json.dumps({
            "model_id": "A4",
            "age": 65,
            "sex": "Male",
            "mask": 1,
            "visual_prior": 0.281,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/api/predict",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "success"
            assert data["p_hcc"] > 0.50
            assert "evidential" in data

        # 5. Audit malformed JSON error handling (HTTP 400)
        req_bad = urllib.request.Request(
            f"{base_url}/api/predict",
            data=b"INVALID_MALFORMED_JSON{{{",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req_bad) as resp_bad:
                pass
        except urllib.error.HTTPError as e:
            assert e.code == 400
            err_body = json.loads(e.read().decode("utf-8"))
            assert "error" in err_body

        # 6. Audit 404 for unknown POST endpoints
        req_404 = urllib.request.Request(
            f"{base_url}/api/non_existent_endpoint",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req_404) as resp_404:
                pass
        except urllib.error.HTTPError as e:
            assert e.code == 404

        # 7. Stress test rapid concurrent requests across threads
        errors = []

        def worker():
            try:
                with urllib.request.urlopen(f"{base_url}/api/status") as r:
                    if r.status != 200:
                        errors.append(f"Bad status: {r.status}")
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent requests had failures: {errors}"

    finally:
        server.shutdown()
        server.server_close()


def test_extreme_input_clamping_in_live_inference():
    """Verify live inference clamps outlier inputs (e.g., negative age, visual prior > 1.0)."""
    # Negative age & excessive visual prior
    res = compute_live_prediction(model_id="A4", age=-20, sex="Male", mask=1, visual_prior=5.0)
    assert res["status"] == "success"
    assert 0.0 <= res["p_hcc"] <= 1.0
    assert 0.0 <= res["p_hem"] <= 1.0

    # Age 200 & negative visual prior
    res2 = compute_live_prediction(model_id="A4", age=200, sex="Female", mask=1, visual_prior=-0.5)
    assert res2["status"] == "success"
    assert 0.0 <= res2["p_hcc"] <= 1.0

