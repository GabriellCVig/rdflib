from __future__ import annotations

import xml.dom.minidom
from collections.abc import Generator
from typing import IO, TYPE_CHECKING, Any
from xml.sax.saxutils import escape, quoteattr

from rdflib.collection import Collection
from rdflib.graph import Graph
from rdflib.namespace import RDF, RDFS, Namespace  # , split_uri
from rdflib.plugins.parsers.RDFVOC import RDFVOC
from rdflib.plugins.serializers.xmlwriter import XMLWriter
from rdflib.serializer import Serializer
from rdflib.term import BNode, IdentifiedNode, Identifier, Literal, Node, URIRef
from rdflib.util import first, more_than

from .xmlwriter import ESCAPE_ENTITIES

XMLLANG = "http://www.w3.org/XML/1998/namespacelang"
XMLBASE = "http://www.w3.org/XML/1998/namespacebase"
OWL_NS = Namespace("http://www.w3.org/2002/07/owl#")
CIM_PROFILE_NAMESPACE = Namespace("http://iec.ch/TC57/61970-552/ModelDescription/1#")


# TODO:
def fix(val: str) -> str:
    "strip off _: from nodeIDs... as they are not valid NCNames"
    if val.startswith("_:"):
        return val[2:]
    else:
        return val

class CIMXMLSerializer(Serializer):
    def __init__(self, store: Graph):
        super(CIMXMLSerializer, self).__init__(store)
        self.profile_uri = None
        self.max_depth = 3
        self.forceRDFAbout: set[URIRef] = set()

    def serialize(
        self,
        stream: IO[bytes],
        base: str | None = None,
        encoding: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.profile_uri = kwargs.get('profile_uri')
        if not self.profile_uri:
            raise ValueError("Missing required 'profile_uri' parameter.")

        self.max_depth = kwargs.get("max_depth", 3)
        assert self.max_depth > 0, "max_depth must be greater than 0"

        self.__serialized: dict[IdentifiedNode | Literal, int] = {}
        store = self.store
        if base is not None:
            self.base = base
        elif store.base is not None:
            self.base = store.base

        self.nm = nm = store.namespace_manager

        
        self.writer = writer = XMLWriter(stream, nm, encoding)
        namespaces = {}
        
        # Collect all the namespaces used in the graph
        possible: set[Node] = set(store.predicates()).union(
            store.objects(None, RDF.type)
        )

        for predicate in possible:
            try:
                prefix, namespace, local = nm.compute_qname_strict(predicate)
                namespaces[prefix] = namespace
            except Exception:
                continue

        # Add required namespaces
        namespaces["rdf"] = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        namespaces["md"] = CIM_PROFILE_NAMESPACE
        namespaces["cim"] = "http://iec.ch/TC57/2013/"
        
        # Write the XML declaration
        stream.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')

        # Write the CIMXML processing instruction
        stream.write(b'<?iec61970-552 version="2.0"?>\n')

        # Start the rdf:RDF element
        writer.push(RDFVOC.RDF)
        writer.attribute(XMLBASE, "urn:uuid:")
        writer.namespaces(namespaces.items())

        # Serialize the FullModel
        self.serialize_full_model(**kwargs)

        # Serialize the rest of the graph
        for subject in store.subjects():
            self.subject(subject, 1)

        # Close the rdf:RDF element
        writer.pop(RDFVOC.RDF)
        stream.write(b"\n")
        self.__serialized = None  # Clear serialized subjects

    def serialize_full_model(self, **kwargs) -> None:
        writer = self.writer
        nm = self.nm  # Namespace manager

        md_ns = CIM_PROFILE_NAMESPACE
        
        nm.bind("md", md_ns)

        # Start md:FullModel element
        writer.push(md_ns.FullModel)
        writer.attribute(RDFVOC.about, kwargs.get('rdf_about', '_[UUID]'))

        # List of child elements and their values
        elements = [
            (md_ns.ModelScenarioTime, kwargs.get('scenarioTime', '')),
            (md_ns.ModelCreated, kwargs.get('created', '')),
            (md_ns.ModelDescription, kwargs.get('description', '')),
            (md_ns.ModelVersion, kwargs.get('version', '')),
            (md_ns.ModelProfile, self.profile_uri),
            (md_ns.ModelModelingAuthoritySet, kwargs.get('modelingAuthoritySet', '')),
        ]

        for element_uri, text in elements:
            writer.element(element_uri, text)

        # End md:FullModel element
        writer.pop(md_ns.FullModel)

    def subject(self, subject: IdentifiedNode | Literal, depth: int = 1):
        store = self.store
        writer = self.writer

        if subject in self.forceRDFAbout:
            writer.push(RDFVOC.Description)
            writer.attribute(RDFVOC.ID, self.relativize(subject))
            writer.pop(RDFVOC.Description)
            self.forceRDFAbout.remove(subject)

        elif subject not in self.__serialized:
            self.__serialized[subject] = 1
            type = first(store.objects(subject, RDF.type))

            try:
                self.nm.qname(type)
            except Exception:
                type = None

            element = type or RDFVOC.Description
            writer.push(element)

            if isinstance(subject, BNode):
                def subj_as_obj_more_than(ceil):
                    return True

                if subj_as_obj_more_than(1):
                    writer.attribute(RDFVOC.nodeID, fix(subject))
            else:
                writer.attribute(RDFVOC.ID, self.relativize(subject))

            if (subject, None, None) in store:
                for _predicate, _object in store.predicate_objects(subject):
                    object_ = _object
                    predicate = _predicate
                    if not (predicate == RDF.type and object_ == type):
                        self.predicate(predicate, object_, depth + 1)

            writer.pop(element)

        elif subject in self.forceRDFAbout:
            writer.push(RDFVOC.Description)
            writer.attribute(RDFVOC.ID, self.relativize(subject))
            writer.pop(RDFVOC.Description)
            self.forceRDFAbout.remove(subject)

    def predicate(
        self, predicate: Identifier, object: Identifier, depth: int = 1
    ) -> None:
        writer = self.writer
        store = self.store
        writer.push(predicate)

        if isinstance(object, Literal):
            if object.language:
                writer.attribute(XMLLANG, object.language)
            writer.text(object)
        elif (
            object in self.__serialized
            or not (object, None, None) in store  # noqa: E713
        ):
            if isinstance(object, BNode):
                if more_than(store.triples((None, None, object)), 0):
                    writer.attribute(RDFVOC.nodeID, fix(object))
            else:
                writer.attribute(RDFVOC.resource, self.relativize(object))
        else:
            if first(store.objects(object, RDF.first)):  # may not have type
                # RDF.List

                self.__serialized[object] = 1

                # Warn that any assertions on object other than
                # RDF.first and RDF.rest are ignored... including RDF.List
                import warnings

                warnings.warn(
                    "Assertions on %s other than RDF.first " % repr(object)
                    + "and RDF.rest are ignored ... including RDF.List",
                    UserWarning,
                    stacklevel=2,
                )
                writer.attribute(RDFVOC.parseType, "Collection")

                col = Collection(store, object)

                for item in col:
                    if isinstance(item, URIRef):
                        self.forceRDFAbout.add(item)
                    self.subject(item)

                    if not isinstance(item, URIRef):
                        self.__serialized[item] = 1
            else:
                if first(
                    store.triples_choices(
                        (object, RDF.type, [OWL_NS.Class, RDFS.Class])
                    )
                ) and isinstance(object, URIRef):
                    writer.attribute(RDFVOC.resource, self.relativize(object))
                elif depth <= self.max_depth:
                    self.subject(object, depth + 1)
                elif isinstance(object, BNode):
                    if (
                        object not in self.__serialized
                        and (object, None, None) in store
                        and len(list(store.subjects(object=object))) == 1
                    ):
                        self.subject(object, depth + 1)
                    else:
                        writer.attribute(RDFVOC.nodeID, fix(object))
                else:
                    writer.attribute(RDFVOC.resource, self.relativize(object))

        writer.pop(predicate)

    def relativize(self, uri):
        uri_str = str(uri)
        for prefix, namespace in self.nm.namespaces():
            ns_str = str(namespace)
            if uri_str.startswith(ns_str):
                return "_" + uri_str[len(ns_str):]
        return "_" + uri_str