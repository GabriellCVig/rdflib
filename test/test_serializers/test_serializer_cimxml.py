"""Tests for the CIM-XML serializer (rdflib.plugins.serializers.cimxml).

Input:  rdflib.Graph populated with CIM triples
Output: Verified XML bytes from CIMXMLSerializer
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from io import BytesIO

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from rdflib.plugins.serializers.cimxml import CIMXMLSerializer

CIM = Namespace("http://iec.ch/TC57/CIM100#")
PROFILE_URI = "http://iec.ch/TC57/ns/CIM/CoreEquipment-EU/3.0"


def _make_graph() -> tuple[Graph, URIRef]:
    g = Graph()
    g.bind("cim", CIM)
    subj = URIRef("urn:uuid:test-acline-1")
    g.add((subj, RDF.type, CIM.ACLineSegment))
    return g, subj


def _serialize(graph: Graph, **kwargs: object) -> bytes:
    serializer = CIMXMLSerializer(graph)
    stream = BytesIO()
    serializer.serialize(stream, profile_uri=PROFILE_URI, **kwargs)
    stream.seek(0)
    return stream.read()


def test_raises_without_profile_uri() -> None:
    g, _ = _make_graph()
    serializer = CIMXMLSerializer(g)
    with pytest.raises(ValueError, match="profile_uri"):
        serializer.serialize(BytesIO())


def test_raises_with_zero_max_depth() -> None:
    g, _ = _make_graph()
    serializer = CIMXMLSerializer(g)
    with pytest.raises(AssertionError):
        serializer.serialize(BytesIO(), profile_uri=PROFILE_URI, max_depth=0)


def test_output_is_valid_xml() -> None:
    g, _ = _make_graph()
    data = _serialize(g)
    ET.fromstring(data)  # raises if not valid XML


def test_full_model_child_elements() -> None:
    g, _ = _make_graph()
    data = _serialize(
        g,
        scenarioTime="2026-04-15T00:00:00Z",
        created="2026-04-15T00:00:00Z",
        description="Test model",
        version="001",
        modelingAuthoritySet="https://www.elvia.no",
        applicationSoftware="cimfo/1.0.0",
    )
    assert b"Model.scenarioTime" in data
    assert b"Model.created" in data
    assert b"Model.description" in data
    assert b"Model.version" in data
    assert b"Model.profile" in data
    assert b"Model.modelingAuthoritySet" in data
    assert b"Model.applicationSoftware" in data
    assert PROFILE_URI.encode() in data
    assert b"cimfo/1.0.0" in data
    assert b"https://www.elvia.no" in data


def test_dependent_on_emitted_when_provided() -> None:
    g, _ = _make_graph()
    dep_uri = "urn:uuid:eq-model-abc123"
    data = _serialize(g, dependent_on_eq=dep_uri)
    assert b"DependentOn" in data
    assert dep_uri.encode() in data


def test_dependent_on_absent_when_not_provided() -> None:
    g, _ = _make_graph()
    data = _serialize(g)
    assert b"DependentOn" not in data


def test_cim_xml_registered_as_format() -> None:
    """Graph.serialize(format='cim-xml') should resolve CIMXMLSerializer.

    It requires profile_uri, so it raises ValueError (not a plugin lookup error).
    """
    g, _ = _make_graph()
    with pytest.raises(ValueError, match="profile_uri"):
        g.serialize(destination=BytesIO(), format="cim-xml")


def test_subject_typed_element_present() -> None:
    g, _ = _make_graph()
    data = _serialize(g)
    assert b"ACLineSegment" in data
