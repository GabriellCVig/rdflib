Title: Implementing the FullModel Object

High-Level Instruction: The CIMXML standard requires a FullModel object within the rdf:RDF block. This object contains metadata about the model being serialized. Please modify the serializer code to include the FullModel object with the following attributes: scenarioTime, created, description, version, profile, and modelingAuthoritySet. 

The 'profile' attribute should be able to accept a list of profile URIs as input. The other attributes should accept string values. 

Specific Code Changes:

1. Add a new function, `serialize_full_model`, to the `CIMXMLSerializer` class. This function should take the FullModel attributes as arguments.
2. Inside the `serialize` function, call `serialize_full_model` before serializing any other objects.
3. Implement the logic for serializing the FullModel object and its attributes according to the CIMXML standard and example provided.