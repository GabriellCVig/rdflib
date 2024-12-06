
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


# TODO:
def fix(val: str) -> str:
    "strip off _: from nodeIDs... as they are not valid NCNames"
    if val.startswith("_:"):
        return val[2:]
    else:
        return val

class CIMXMLSerializer(Serializer):
    def __init__(self, store: Graph, max_depth=3):
        super(CIMXMLSerializer, self).__init__(store)
        self.forceRDFAbout: set[URIRef] = set()

    def serialize(
        self,
        stream: IO[bytes],
        base: str | None = None,
        encoding: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.__serialized: dict[IdentifiedNode | Literal, int] = {}
        store = self.store
        # if base is given here, use that, if not and a base is set for the graph use that
        if base is not None:
            self.base = base
        elif store.base is not None:
            self.base = store.base
        self.max_depth = kwargs.get("max_depth", 3)
        assert self.max_depth > 0, "max_depth must be greater than 0"

        self.nm = nm = store.namespace_manager
        self.writer = writer = XMLWriter(stream, nm, encoding)
        namespaces = {}

        possible: set[Node] = set(store.predicates()).union(
            store.objects(None, RDF.type)
        )

        for predicate in possible:
            # type error: Argument 1 to "compute_qname_strict" of "NamespaceManager" has incompatible type "Node"; expected "str"
            prefix, namespace, local = nm.compute_qname_strict(predicate)  # type: ignore[arg-type]
            namespaces[prefix] = namespace

        namespaces["rdf"] = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

        writer.push(RDFVOC.RDF)

        if "xml_base" in kwargs:
            writer.attribute(XMLBASE, kwargs["xml_base"])
        elif self.base:
            writer.attribute(XMLBASE, self.base)

        writer.namespaces(namespaces.items())

        subject: IdentifiedNode | Literal
        # Write out subjects that can not be inline
        # type error: Incompatible types in assignment (expression has type "Node", variable has type "IdentifiedNode")
        for subject in store.subjects():  # type: ignore[assignment]
            if (None, None, subject) in store:
                if (subject, None, subject) in store:
                    self.subject(subject, 1)
            else:
                self.subject(subject, 1)

        # write out anything that has not yet been reached
        # write out BNodes last (to ensure they can be inlined where possible)
        bnodes = set()

        # type error: Incompatible types in assignment (expression has type "Node", variable has type "IdentifiedNode")
        for subject in store.subjects():  # type: ignore[assignment]
            if isinstance(subject, BNode):
                bnodes.add(subject)
                continue
            self.subject(subject, 1)

        # now serialize only those BNodes that have not been serialized yet
        for bnode in bnodes:
            if bnode not in self.__serialized:
                self.subject(subject, 1)

        writer.pop(RDFVOC.RDF)
        stream.write("\n".encode("latin-1"))

        # Set to None so that the memory can get garbage collected.
        self.__serialized = None  # type: ignore[assignment]

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