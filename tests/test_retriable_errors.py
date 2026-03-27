"""TEST-2: Table-driven tests for is_retriable_error() string matching."""
from __future__ import annotations

import pytest

from tps_cita_check.steps.common import is_retriable_error


@pytest.mark.parametrize("error_text,expected", [
    # WAF/block patterns
    ("The requested URL was rejected", True),
    ("url was rejected by security", True),
    ("FortiGate block page detected", True),
    ("fortigate intrusion prevention", True),
    # Session/service patterns
    ("La sesión ha caducado por inactividad", True),
    ("sesión ha caducado", True),
    ("La provincia seleccionada no ofrece el servicio de Cita Previa Internet", True),
    ("no ofrece el servicio de Cita Previa", True),
    ("Se ha producido un error en el sistema, por favor inténtelo de nuevo", True),
    ("error en el sistema", True),
    # Timeout patterns
    ("Timeout waiting for selector #btnAceptar", True),
    ("timeout exceeded", True),
    ("playwright timeout", True),
    # Non-matching
    ("No hay citas disponibles", False),
    ("Unexpected element not found", False),
    ("Connection refused", False),
    ("", False),
    (None, False),
])
def test_is_retriable_error(error_text, expected):
    assert is_retriable_error(error_text) == expected


def test_is_retriable_error_case_insensitive():
    """Matching should be case-insensitive."""
    assert is_retriable_error("URL WAS REJECTED") is True
    assert is_retriable_error("TIMEOUT") is True
    assert is_retriable_error("FORTIGATE") is True
