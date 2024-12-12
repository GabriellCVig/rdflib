Title: Setting the correct Base IRI

High-Level Instruction: The current CIMXML serializer is adding the namespace to the rdf:resource attributes, instead of using the '#_' prefix. This is incorrect according to the CIMXML standard. Please update the code to use the correct Base IRI and the '#_' prefix for rdf:resource attributes.

Specific Code Changes:

* Locate the `relativize` function in the `CIMXMLSerializer` class. 
* Modify the logic to prepend "#_" to the resource identifier instead of adding the namespace.